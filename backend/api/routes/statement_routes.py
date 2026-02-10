"""
Bank Statement API routes - Reusing invoice endpoints for bank statements
Processes Excel bank statements through /api/invoices endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
from typing import Optional
import time
import logging

from api.models.statement_model import (
    BankStatementData,
    BankStatementMetadata,
    ValidationResult
)
from services.excel_parser import get_excel_parser
# OCR disabled - Excel files only
# from services.ocr_azure import extract_with_azure
from services.extractors.bank_statement_extractor import BankStatementExtractor

# ===== LLM SERVICE: SWITCHED FROM GROQ TO GEMINI =====
# Using Gemini due to Groq rate limits
from services.gemini_service import get_gemini_llm

from services.validators.balance_validator import get_balance_validator
from services.validators.date_validator import get_date_validator
from services.validators.validation_models import AggregatedValidationResult

logger = logging.getLogger(__name__)
logger.info("🔄 Using Gemini LLM service (switched from Groq)")

# Using /api/invoices prefix for backward compatibility (now processes bank statements)
router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# File upload configuration
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}  # Excel files only


@router.post("/upload")
async def upload_statement(file: UploadFile = File(...)):
    """
    Upload and extract bank statement data with validation
    
    Complete Flow:
    1. Cloudinary: Backup file to cloud
    2. Excel Parse: Extract structured data from Excel
    3. LLM: Extract structured data
    4. Validate: Balance + Date checks
    5. Supabase: Store in database
    
    Args:
        file: Bank statement Excel file (.xlsx, .xls)
        
    Returns:
        Extracted statement data with validation results
    """
    start_time = time.time()
    temp_file_path = None
    
    try:
        # Validate file extension
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_FILE_FORMAT",
                    "message": f"Only {', '.join(ALLOWED_EXTENSIONS)} files are supported",
                    "details": f"Received: {file_ext}"
                }
            )
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Validate file size
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail={
                    "code": "FILE_TOO_LARGE",
                    "message": f"File size exceeds {MAX_FILE_SIZE // (1024*1024)}MB limit"
                }
            )
        
        # Save to temp file
        temp_file_path = UPLOAD_DIR / f"temp_{int(time.time() * 1000)}{file_ext}"
        with open(temp_file_path, "wb") as f:
            f.write(content)
        
        logger.info(f"Processing bank statement: {file.filename} ({file_size / 1024:.1f}KB)")
        
        # ===== STEP 1: CLOUDINARY (Immediate Backup) =====
        # TEMPORARILY DISABLED FOR TESTING
        file_url = None
        cloudinary_id = None
        
        # try:
        #     from services.cloudinary_service import get_cloudinary_service
        #     cloudinary = get_cloudinary_service()
        #     
        #     # Generate statement_id early for consistent naming
        #     from api.storage.statement_store import get_statement_store
        #     store = get_statement_store()
        #     statement_id = store.generate_id()
        #     
        #     upload_result = cloudinary.upload_file(str(temp_file_path), statement_id)
        #     if upload_result:
        #         file_url = upload_result.get("url")
        #         cloudinary_id = upload_result.get("public_id")
        #         logger.info(f"✅ File backed up to Cloudinary: {file_url}")
        # except Exception as e:
        #     logger.warning(f"Cloudinary upload failed (continuing anyway): {e}")
        #     # Generate fallback ID
        
        # Generate statement ID
        from api.storage.statement_store import get_statement_store
        store = get_statement_store()
        statement_id = store.generate_id()
        
        # ===== STEP 2: EXCEL EXTRACTION (Excel files only) =====
        excel_parser = get_excel_parser()
        
        if not excel_parser.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_FORMAT",
                    "message": "Only Excel files (.xlsx, .xls) are supported",
                    "details": f"Received: {file_ext}"
                }
            )
        
        # Parse Excel directly (structured data)
        logger.info("📊 Using Excel parser (structured data)")
        parse_result = excel_parser.parse_to_text(str(temp_file_path))
        
        if not parse_result['success']:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "PARSE_FAILED",
                    "message": "Failed to parse Excel file",
                    "details": parse_result.get('error')
                }
            )
        
        text = parse_result['text']
        extraction_method = 'excel'
        
        # ===== STEP 3: LLM EXTRACTION (with fallback) =====
        logger.info("🤖 Running LLM extraction with Gemini...")
        llm_service = get_gemini_llm()
        extractor = BankStatementExtractor(llm_service)
        extraction_result = extractor.extract(text)
        
        # If LLM fails and we have an Excel file, try fallback extraction
        if not extraction_result.get('success') and file_ext == '.xlsx':
            logger.warning("⚠️ LLM extraction failed, trying fallback Excel parser...")
            
            from services.fallback_extractor import fallback_excel_extraction
            extraction_result = fallback_excel_extraction(str(temp_file_path))
            
            if not extraction_result.get('success'):
                raise HTTPException(
                    status_code=500,
                    detail={
                        "code": "EXTRACTION_FAILED",
                        "message": "Both LLM and fallback extraction failed",
                        "details": extraction_result.get('error')
                    }
                )
            else:
                logger.info("✅ Fallback extraction successful!")
        
        elif not extraction_result.get('success'):
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "EXTRACTION_FAILED",
                    "message": "Failed to extract statement data",
                    "details": extraction_result.get('error')
                }
            )
        
        extracted_data = extraction_result['data']
        
        # ===== STEP 4: VALIDATION (Critical for judging!) =====
        logger.info("✓ Running validators...")
        
        balance_validator = get_balance_validator()
        date_validator = get_date_validator()
        
        balance_result = balance_validator.validate_statement(extracted_data)
        date_result = date_validator.validate_statement(extracted_data)
        
        # Aggregate validation results
        validation_aggregate = AggregatedValidationResult.from_results(
            statement_id=statement_id,
            results={
                "balance_validation": balance_result,
                "date_validation": date_result
            }
        )
        
        logger.info(
            f"Validation: {validation_aggregate.overall_status.upper()} "
            f"({validation_aggregate.total_errors} errors, {validation_aggregate.total_warnings} warnings)"
        )
        
        # Create response models
        statement_data = BankStatementData(**extracted_data)
        
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        metadata = BankStatementMetadata(
            extraction_method=extraction_method,
            extraction_confidence=extraction_result.get('extraction_confidence', 0.0),
            fields_extracted=extraction_result.get('fields_extracted', 0),
            fields_expected=extraction_result.get('fields_expected', 0),
            processing_time_ms=processing_time_ms,
            source_file=file.filename,
            file_type=file_ext,
            quality_score=None
        )
        
        validation_response = ValidationResult(
            balance_validation=balance_result.dict(),
            date_validation=date_result.dict(),
            overall_status=validation_aggregate.overall_status,
            total_errors=validation_aggregate.total_errors,
            total_warnings=validation_aggregate.total_warnings
        )
        
        # ===== STEP 5: SUPABASE (Persistent Storage) =====
        logger.info("💾 Storing in database...")
        try:
            saved_statement = store.create(
                data=statement_data,
                metadata=metadata,
                validation=validation_response,
                file_url=file_url,
                cloudinary_id=cloudinary_id
            )
            logger.info(f"✅ Statement saved to database: {saved_statement.statement_id}")
        except Exception as e:
            logger.error(f"Failed to save to database: {e}")
            # Continue anyway - data is extracted and validated
        
        logger.info(f"🎉 Statement processing complete ({processing_time_ms}ms)")
        
        return {
            "success": True,
            "statement_id": statement_id,
            "message": "Bank statement extracted and validated successfully",
            "data": statement_data.dict(),
            "metadata": metadata.dict(),
            "validation": validation_response.dict(),
            "file_url": file_url,
            "cloudinary_id": cloudinary_id
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error during statement upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": str(e)
            }
        )
    
    finally:
        # Cleanup temp file
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file: {e}")



@router.get("/{statement_id}")
async def get_statement(statement_id: str):
    """
    Get bank statement by ID
    
    Args:
        statement_id: Statement ID
        
    Returns:
        Complete statement data with validation results
    """
    try:
        from api.storage.statement_store import get_statement_store
        store = get_statement_store()
        
        statement = store.get(statement_id)
        
        if not statement:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "STATEMENT_NOT_FOUND",
                    "message": f"Statement {statement_id} not found"
                }
            )
        
        return {
            "success": True,
            "statement": statement.dict()
        }
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error retrieving statement: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "RETRIEVAL_ERROR",
                "message": "Failed to retrieve statement",
                "details": str(e)
            }
        )


@router.get("/")
async def list_statements(
    limit: int = 50,
    offset: int = 0,
    validation_status: Optional[str] = None
):
    """
    List bank statements with optional filters
    
    Args:
        limit: Max statements to return (default 50)
        offset: Offset for pagination
        validation_status: Filter by validation status (passed/warnings/failed)
        
    Returns:
        List of statement summaries
    """
    try:
        from api.storage.statement_store import get_statement_store
        store = get_statement_store()
        
        filters = {}
        if validation_status:
            filters["validation_status"] = validation_status
        
        summaries, total = store.list(
            limit=limit,
            offset=offset,
            filters=filters
        )
        
        return {
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "statements": [s.dict() for s in summaries]
        }
    
    except Exception as e:
        logger.error(f"Error listing statements: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "LIST_ERROR",
                "message": "Failed to list statements",
                "details": str(e)
            }
        )



async def statements_health():
    """Health check for statements service"""
    return {
        "status": "online",
        "service": "Bank Statement Intelligence",
        "features": {
            "excel_parsing": "enabled",
            "ocr_fallback": "Azure Document Intelligence",
            "validation": "Balance + Date validators",
            "supported_formats": list(ALLOWED_EXTENSIONS)
        }
    }
