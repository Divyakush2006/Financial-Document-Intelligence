"""
Supabase-based bank statement storage (persistent database)
Follows same pattern as invoice_store.py
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import os
import logging
import uuid
from supabase import create_client, Client

from api.models.statement_model import (
    BankStatement,
    BankStatementData,
    BankStatementMetadata,
    BankStatementSummary,
    ValidationResult
)

logger = logging.getLogger(__name__)


class SupabaseStatementStore:
    """Persistent bank statement storage using Supabase PostgreSQL"""
    
    def __init__(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        self.client: Client = create_client(url, key)
        logger.info("Supabase statement store initialized")
    
    def generate_id(self) -> str:
        """Generate unique statement ID"""
        return f"stmt_{uuid.uuid4().hex[:12]}"
    
    def create(
        self,
        data: BankStatementData,
        metadata: BankStatementMetadata,
        validation: ValidationResult,
        file_url: Optional[str] = None,
        cloudinary_id: Optional[str] = None
    ) -> BankStatement:
        """
        Create new bank statement record in database
        
        Args:
            data: Extracted statement data
            metadata: Extraction metadata
            validation: Validation results
            file_url: Optional Cloudinary file URL
            cloudinary_id: Optional Cloudinary public ID
            
        Returns:
            Created statement with ID
        """
        statement_id = self.generate_id()
        
        # Prepare database record
        record = {
            "statement_id": statement_id,
            "account_number": data.account_number,
            "bank_name": data.bank_name,
            "account_holder_name": data.account_holder_name,
            "statement_period_from": data.statement_period_from,
            "statement_period_to": data.statement_period_to,
            "opening_balance": float(data.opening_balance) if data.opening_balance else None,
            "closing_balance": float(data.closing_balance) if data.closing_balance else None,
            "transaction_count": data.number_of_transactions,
            "file_url": file_url,
            "cloudinary_id": cloudinary_id,
            "validation_status": validation.overall_status,
            "data": data.model_dump(mode='json'),
            "metadata": metadata.model_dump(mode='json'),
            "validation": validation.model_dump(mode='json')
        }
        
        # Insert into database
        result = self.client.table("bank_statements").insert(record).execute()
        
        if not result.data:
            raise Exception("Failed to create statement in database")
        
        logger.info(f"Created statement in database: {statement_id}")
        
        # Return BankStatement model
        return BankStatement(
            statement_id=statement_id,
            data=data,
            metadata=metadata,
            validation=validation,
            file_url=file_url,
            cloudinary_id=cloudinary_id,
            created_at=datetime.utcnow()
        )
    
    def get(self, statement_id: str) -> Optional[BankStatement]:
        """
        Get statement by ID
        
        Args:
            statement_id: Statement ID
            
        Returns:
            BankStatement or None if not found
        """
        result = self.client.table("bank_statements").select("*").eq("statement_id", statement_id).execute()
        
        if not result.data or len(result.data) == 0:
            return None
        
        row = result.data[0]
        
        return BankStatement(
            statement_id=row["statement_id"],
            data=BankStatementData(**row["data"]),
            metadata=BankStatementMetadata(**row["metadata"]),
            validation=ValidationResult(**row["validation"]) if row.get("validation") else None,
            file_url=row.get("file_url"),
            cloudinary_id=row.get("cloudinary_id"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        )
    
    def list(
        self,
        limit: int = 50,
        offset: int = 0,
        sort: str = "date_desc",
        filters: Optional[Dict] = None
    ) -> Tuple[List[BankStatementSummary], int]:
        """
        List statements with pagination and filters
        
        Args:
            limit: Max statements to return
            offset: Number to skip
            sort: Sort order
            filters: Optional filters
            
        Returns:
            Tuple of (statement_summaries, total_count)
        """
        # Build query
        query = self.client.table("bank_statements").select("*", count="exact")
        
        # Apply filters
        if filters:
            if filters.get("account_number"):
                query = query.eq("account_number", filters["account_number"])
            
            if filters.get("bank_name"):
                query = query.ilike("bank_name", f"%{filters['bank_name']}%")
            
            if filters.get("validation_status"):
                query = query.eq("validation_status", filters["validation_status"])
            
            if filters.get("date_from"):
                query = query.gte("statement_period_from", filters["date_from"])
            
            if filters.get("date_to"):
                query = query.lte("statement_period_to", filters["date_to"])
        
        # Apply sorting
        if sort == "date_desc":
            query = query.order("statement_period_to", desc=True)
        elif sort == "date_asc":
            query = query.order("statement_period_to", desc=False)
        else:
            query = query.order("created_at", desc=True)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        result = query.execute()
        
        total = result.count if result.count else 0
        
        # Convert to summaries
        summaries = [
            BankStatementSummary(
                statement_id=row["statement_id"],
                account_number=row.get("account_number"),
                bank_name=row.get("bank_name"),
                statement_period=f"{row.get('statement_period_from')} to {row.get('statement_period_to')}",
                closing_balance=row.get("closing_balance"),
                validation_status=row.get("validation_status"),
                file_url=row.get("file_url"),
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            )
            for row in result.data
        ]
        
        return summaries, total
    
    def delete(self, statement_id: str) -> bool:
        """Delete statement by ID"""
        result = self.client.table("bank_statements").delete().eq("statement_id", statement_id).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"Deleted statement: {statement_id}")
            return True
        
        return False
    
    def count(self) -> int:
        """Get total statement count"""
        result = self.client.table("bank_statements").select("*", count="exact").execute()
        return result.count if result.count else 0
    
    def get_validation_summary(self) -> Dict:
        """Get validation summary across all statements"""
        result = self.client.table("bank_statements").select("validation_status").execute()
        
        summary = {
            "total": len(result.data),
            "passed": 0,
            "warnings": 0,
            "failed": 0
        }
        
        for row in result.data:
            status = row.get("validation_status", "unknown")
            if status == "passed":
                summary["passed"] += 1
            elif status == "warnings":
                summary["warnings"] += 1
            elif status == "failed":
                summary["failed"] += 1
        
        return summary


# Singleton instance
_statement_store = None

def get_statement_store() -> SupabaseStatementStore:
    """Get or create statement store instance"""
    global _statement_store
    if _statement_store is None:
        _statement_store = SupabaseStatementStore()
    return _statement_store
