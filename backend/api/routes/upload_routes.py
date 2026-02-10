"""
Bank Statement Upload and Processing Routes
User flow: Upload Excel → Parse → Store → Query
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import logging
import os
import shutil
import time
from pathlib import Path
from datetime import datetime
import tempfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/statements", tags=["Bank Statements"])

# Models
class UploadResponse(BaseModel):
    success: bool
    statement_id: str
    account_number: str
    transaction_count: int
    message: str
    processing_status: str

class StatementSummary(BaseModel):
    statement_id: str
    account_number: str
    bank_name: Optional[str]
    closing_balance: Optional[float]
    transaction_count: int
    period_from: Optional[str]
    period_to: Optional[str]

class QueryRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    statement_id: Optional[str] = None  # NEW: Filter to specific statement
    account: Optional[str] = None  # NEW: Filter to specific account


# Background processing function
async def process_statement_background(file_path: str, original_filename: str):
    """
    Process Excel file in background:
    1. Extract to JSON
    2. Import to Supabase
    3. Create individual transactions
    """
    try:
        from services.excel_to_json_converter import get_converter
        from automated_import_pipeline import AutomatedImportPipeline
        
        # Step 1: Extract using correct method
        converter = get_converter()
        result = converter.convert(file_path)  # Fixed: convert() not convert_file()
        
        if not result.get('success'):
            logger.error(f"Extraction failed: {original_filename}")
            return
        
        # Step 2: Save JSON temporarily
        temp_json = file_path.replace('.xlsx', '_result.json')
        import json
        with open(temp_json, 'w') as f:
            json.dump(result, f)
        
        # Step 3: Import to Supabase
        pipeline = AutomatedImportPipeline()
        import_result = pipeline.import_statement(Path(temp_json))
        
        logger.info(f"Background processing complete: {import_result}")
        
    except Exception as e:
        logger.error(f"Background processing failed: {e}")


@router.post("/upload", response_model=UploadResponse)
async def upload_statement(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Excel file (.xlsx or .xls)")
):
    """
    Upload and process bank statement Excel file
    
    **Flow**:
    1. Upload Excel file
    2. Extract transactions (rule-based, no LLM)
    3. Store in Supabase (statements + individual transactions)
    4. Return statement summary
    
    **Returns**: Statement ID and transaction count
    """
    # Validate file type
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "Only .xlsx and .xls files are supported")
    
    try:
        # Save uploaded file temporarily
        upload_dir = Path("uploads")
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        logger.info(f"File uploaded: {file.filename} -> {file_path}")
        
        # Process immediately (synchronous for now)
        from services.excel_to_json_converter import get_converter
        from automated_import_pipeline import AutomatedImportPipeline
        
        # Extract using correct method name
        converter = get_converter()
        extraction_result = converter.convert(str(file_path))  # Fixed: convert() not convert_file()
        
        if not extraction_result.get('success'):
            raise HTTPException(500, f"Extraction failed: {extraction_result.get('error', 'Unknown error')}")
        
        # Save JSON
        temp_json = str(file_path).replace('.xlsx', '_result.json').replace('.xls', '_result.json')
        import json
        with open(temp_json, 'w', encoding='utf-8') as f:
            json.dump(extraction_result, f)
        
        # Import to Supabase
        pipeline = AutomatedImportPipeline()
        import_result = pipeline.import_statement(Path(temp_json))
        
        if not import_result.get('success'):
            raise HTTPException(500, f"Import failed: {import_result.get('error', 'Unknown error')}")
        
        # Clean up files
        os.remove(file_path)
        os.remove(temp_json)
        
        return UploadResponse(
            success=True,
            statement_id=import_result['statement_id'],
            account_number=import_result['account'],
            transaction_count=import_result['transaction_count'],
            message=f"Successfully processed {import_result['transaction_count']} transactions",
            processing_status="completed"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(500, f"Processing failed: {str(e)}")


@router.get("/")
async def list_statements():
    """
    Get all uploaded bank statements
    
    **Returns**: List of all statements with summaries
    """
    try:
        from supabase import create_client
        import os
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise HTTPException(500, "Database not configured")
        
        client = create_client(url, key)
        result = client.table("bank_statements").select(
            "statement_id, account_number, bank_name, closing_balance, transaction_count, statement_period_from, statement_period_to, created_at"
        ).order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "count": len(result.data),
            "statements": result.data
        }
        
    except Exception as e:
        logger.error(f"List failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/{statement_id}")
async def get_statement(statement_id: str):
    """
    Get specific statement with all transactions
    
    **Parameters**:
    - statement_id: Unique statement identifier
    
    **Returns**: Complete statement data including all transactions
    """
    try:
        from supabase import create_client
        import os
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        client = create_client(url, key)
        
        # Get statement
        stmt_result = client.table("bank_statements").select("*").eq("statement_id", statement_id).execute()
        
        if not stmt_result.data:
            raise HTTPException(404, f"Statement {statement_id} not found")
        
        # Get transactions
        txn_result = client.table("transactions").select("*").eq("statement_id", statement_id).execute()
        
        statement = stmt_result.data[0]
        statement['transactions'] = txn_result.data
        
        return {
            "success": True,
            "statement": statement
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get statement failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/query")
async def query_statements(request: QueryRequest):
    """
    Natural language query for bank statements using Backboard AI
    
    **Enhanced with**:
    - Input validation and sanitization
    - Comprehensive error handling
    - Fallback query processing
    - Performance monitoring
    - Detailed logging
    
    **Examples**:
    - "Show all UPI payments over ₹5000"
    - "Dream11 transactions from Account 1"
    - "Total spending in May 2025"
    - "What's my balance?"
    
    **Parameters**:
    - message: Natural language query
    - thread_id: Optional thread ID for context retention
    - statement_id: Optional - query only this statement
    - account: Optional - query only this account
    
    **Returns**: Matching transactions or analytics
    """
    start_time = time.time()
    
    try:
        from services.query_validator import get_query_validator
        from api.response_formatter import get_response_formatter
        from api.error_codes import ErrorCode, ErrorMessage
        from services.backboard_statement_service import get_statement_service
        
        validator = get_query_validator()
        formatter = get_response_formatter()
        
        # Step 1: Validate and sanitize query
        logger.info(f"[QUERY] Received: '{request.message[:100]}...'")
        
        validation_result = validator.validate_and_sanitize(request.message)
        
        if not validation_result["valid"]:
            logger.warning(f"[QUERY] Validation failed: {validation_result['error']}")
            return JSONResponse(
                status_code=validation_result["status_code"],
                content=formatter.error_response(
                    error_code=validation_result["error"]["code"],
                    message=validation_result["error"]["message"],
                    suggestion=validation_result["error"]["suggestion"]
                )[0]
            )
        
        sanitized_query = validation_result["query"]
        logger.info(f"[QUERY] Sanitized: '{sanitized_query}'")
        
        # Step 2: Get account filter from statement_id if provided
        account_filter = request.account
        
        if request.statement_id and not account_filter:
            try:
                from supabase import create_client
                import os
                
                url = os.getenv("SUPABASE_URL")
                key = os.getenv("SUPABASE_KEY")
                
                if url and key:
                    client = create_client(url, key)
                    stmt_result = client.table("bank_statements").select("account_number").eq("statement_id", request.statement_id).execute()
                    
                    if stmt_result.data and len(stmt_result.data) > 0:
                        account_filter = stmt_result.data[0]['account_number']
                        logger.info(f"[QUERY] Resolved statement {request.statement_id} to account: {account_filter}")
                    else:
                        logger.warning(f"[QUERY] Statement {request.statement_id} not found")
                        error_response, status_code = ErrorMessage.get_error_response(
                            ErrorCode.NO_DATA_AVAILABLE,
                            f"Statement {request.statement_id} not found"
                        )
                        return JSONResponse(status_code=status_code, content=error_response)
            except Exception as e:
                logger.error(f"[QUERY] Failed to resolve statement_id: {e}")
                # Continue without account filter
        
        # Step 3: Process query with Backboard AI
        service = get_statement_service()
        
        if not service.enabled:
            logger.warning("[QUERY] Backboard AI not available, using fallback")
            
            # Fallback: Direct database search
            try:
                from services.storage.supabase_query import get_supabase_query
                
                query_service = get_supabase_query()
                
                if not query_service.enabled:
                    error_response, status_code = ErrorMessage.get_error_response(
                        ErrorCode.DATABASE_CONNECTION_FAILED,
                        "Both AI and database services are unavailable"
                    )
                    return JSONResponse(status_code=status_code, content=error_response)
                
                # Use fallback filter extraction
                from services.backboard_statement_service import BackboardStatementService
                fallback_service = BackboardStatementService()
                filter_result = fallback_service._fallback_filter_extraction(sanitized_query)
                
                filters = filter_result.get('filters', {})
                if account_filter:
                    filters['account'] = account_filter
                
                analytics_type = filter_result.get('analytics')
                
                # Execute query
                if analytics_type:
                    results = query_service.get_analytics(analytics_type, filters)
                    message_text = f"Analytics results for: {sanitized_query}"
                    transactions = None
                    analytics = results
                else:
                    transactions = query_service.search_transactions(filters)
                    results = transactions
                    analytics = None
                    
                    if not transactions:
                        error_response, status_code = ErrorMessage.get_error_response(
                            ErrorCode.NO_TRANSACTIONS_FOUND,
                            "No transactions match your query"
                        )
                        return JSONResponse(status_code=status_code, content=error_response)
                    
                    message_text = f"Found {len(transactions)} transaction(s)"
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                logger.info(f"[QUERY] Fallback completed in {execution_time_ms}ms")
                
                response = formatter.query_response(
                    query=sanitized_query,
                    transactions=transactions,
                    analytics=analytics,
                    message=message_text,
                    filters_used=filters,
                    thread_id=request.thread_id,
                    execution_time_ms=execution_time_ms,
                    fallback_used=True
                )
                
                return response
                
            except Exception as e:
                logger.error(f"[QUERY] Fallback failed: {e}", exc_info=True)
                error_response, status_code = ErrorMessage.get_error_response(
                    ErrorCode.INTERNAL_SERVER_ERROR,
                    str(e)
                )
                return JSONResponse(status_code=status_code, content=error_response)
        
        # Step 4: Execute AI-powered query
        try:
            logger.info(f"[QUERY] Processing with Backboard AI (account_filter={account_filter})")
            
            result = service.query(
                sanitized_query,
                request.thread_id,
                account_filter=account_filter
            )
            
            # Check for errors in result
            if result.get('error'):
                logger.error(f"[QUERY] Backboard error: {result['error']}")
                error_response, status_code = ErrorMessage.get_error_response(
                    ErrorCode.BACKBOARD_API_ERROR,
                    result.get('message', 'Query processing failed')
                )
                return JSONResponse(status_code=status_code, content=error_response)
            
            # Check if no transactions found
            transactions = result.get('transactions', [])
            if transactions is not None and len(transactions) == 0 and not result.get('analytics'):
                error_response, status_code = ErrorMessage.get_error_response(
                    ErrorCode.NO_TRANSACTIONS_FOUND
                )
                return JSONResponse(status_code=status_code, content=error_response)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[QUERY] Successfully completed in {execution_time_ms}ms")
            
            # Format response
            response = {
                "success": True,
                "query": sanitized_query,
                "message": result.get('message', 'Query processed successfully'),
                "transactions": transactions,
                "count": len(transactions) if transactions else 0,
                "thread_id": result.get('thread_id'),
                "filters_used": result.get('filters_used'),
                "analytics_type": result.get('analytics_type'),
                "metadata": {
                    "execution_time_ms": execution_time_ms,
                    "ai_status": "active"
                }
            }
            
            # Add analytics if present
            if result.get('analytics'):
                response["analytics"] = result['analytics']
            
            # Add summary if transactions present
            if transactions:
                total_debits = sum(t.get('debit', 0) for t in transactions)
                total_credits = sum(t.get('credit', 0) for t in transactions)
                response["summary"] = {
                    "total_debits": round(total_debits, 2),
                    "total_credits": round(total_credits, 2),
                    "net_amount": round(total_credits - total_debits, 2)
                }
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"[QUERY] AI query failed: {e}", exc_info=True)
            error_response, status_code = ErrorMessage.get_error_response(
                ErrorCode.INTERNAL_SERVER_ERROR,
                str(e)
            )
            return JSONResponse(status_code=status_code, content=error_response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[QUERY] Unexpected error: {e}", exc_info=True)
        error_response, status_code = ErrorMessage.get_error_response(
            ErrorCode.UNEXPECTED_ERROR,
            str(e)
        )
        return JSONResponse(status_code=status_code, content=error_response)


@router.get("/transactions/search")
async def search_transactions(
    account: Optional[str] = None,
    description: Optional[str] = None,
    payment_method: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_amount: Optional[float] = None
):
    """
    Search transactions with filters
    
    **Query Parameters**:
    - account: Account number
    - description: Search in description
    - payment_method: UPI, NEFT, ATM, etc.
    - date_from / date_to: Date range (YYYY-MM-DD)
    - min_amount / max_amount: Amount range
    
    **Returns**: Matching transactions
    """
    try:
        from services.storage.supabase_query import get_supabase_query
        
        store = get_supabase_query()
        
        filters = {}
        if account:
            filters['account'] = account
        if description:
            filters['description_contains'] = description
        if payment_method:
            filters['payment_method'] = payment_method
        if date_from:
            filters['date_from'] = date_from
        if date_to:
            filters['date_to'] = date_to
        if min_amount is not None:
            filters['min_amount'] = min_amount
        if max_amount is not None:
            filters['max_amount'] = max_amount
        
        transactions = store.search_transactions(filters)
        
        return {
            "success": True,
            "count": len(transactions),
            "filters_applied": filters,
            "transactions": transactions  # Return ALL results (removed limit)
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/analytics/summary")
async def get_analytics_summary():
    """
    Get overall analytics summary
    
    **Returns**: Total balance, spending, income across all statements
    """
    try:
        from services.storage.supabase_query import get_supabase_query
        
        store = get_supabase_query()
        summary = store.get_account_summary()
        
        return {
            "success": True,
            **summary
        }
        
    except Exception as e:
        logger.error(f"Analytics failed: {e}")
        raise HTTPException(500, str(e))
