"""
Pydantic models for bank statement data
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Transaction(BaseModel):
    """Single transaction in bank statement"""
    date: Optional[str] = None
    description: Optional[str] = None
    debit: Optional[float] = 0.0
    credit: Optional[float] = 0.0
    balance: Optional[float] = None
    transaction_type: Optional[str] = None  # 'debit' or 'credit'
    
    # Enrichment fields (optional)
    category: Optional[str] = None
    merchant: Optional[str] = None


class BankStatementData(BaseModel):
    """Complete bank statement data structure"""
    # Account information
    account_holder_name: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    
    # Statement period
    statement_period_from: Optional[str] = None
    statement_period_to: Optional[str] = None
    
    # Balances
    opening_balance: Optional[float] = None
    closing_balance: Optional[float] = None
    
    # Transaction summary
    total_credits: Optional[float] = None
    total_debits: Optional[float] = None
    number_of_transactions: Optional[int] = None
    
    # Transactions
    transactions: List[Transaction] = Field(default_factory=list)
    
    # Additional info
    currency: Optional[str] = "INR"
    account_type: Optional[str] = None  # savings, current, etc.


class BankStatementMetadata(BaseModel):
    """Metadata about extraction process"""
    extraction_method: str  # 'excel', 'ocr', 'pdf'
    extraction_confidence: float
    fields_extracted: int
    fields_expected: int
    processing_time_ms: int
    
    # File info
    source_file: str
    file_type: str
    
    # Quality metrics
    quality_score: Optional[float] = None


class ValidationResult(BaseModel):
    """Validation results from validators"""
    balance_validation: dict
    date_validation: dict
    overall_status: str  # 'passed', 'warnings', 'failed'
    total_errors: int = 0
    total_warnings: int = 0


class BankStatement(BaseModel):
    """Complete bank statement record"""
    statement_id: str
    data: BankStatementData
    metadata: BankStatementMetadata
    validation: Optional[ValidationResult] = None
    file_url: Optional[str] = None
    cloudinary_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class BankStatementSummary(BaseModel):
    """Summary of bank statement for list view"""
    statement_id: str
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    statement_period: Optional[str] = None
    closing_balance: Optional[float] = None
    validation_status: Optional[str] = None
    file_url: Optional[str] = None
    created_at: datetime
