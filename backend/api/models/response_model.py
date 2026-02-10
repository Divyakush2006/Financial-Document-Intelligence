"""Response models for API endpoints"""

from pydantic import BaseModel
from typing import Optional, List, Any
from .invoice_model import Invoice, InvoiceSummary, InvoiceData, InvoiceMetadata


class UploadResponse(BaseModel):
    """Response for successful upload"""
    success: bool = True
    invoice_id: str
    message: str
    data: InvoiceData
    metadata: InvoiceMetadata


class GetInvoiceResponse(BaseModel):
    """Response for get invoice by ID"""
    success: bool = True
    invoice: Invoice


class Pagination(BaseModel):
    """Pagination metadata"""
    limit: int
    offset: int
    total: int


class ListInvoicesResponse(BaseModel):
    """Response for list invoices"""
    success: bool = True
    count: int
    invoices: List[InvoiceSummary]
    pagination: Pagination


class ErrorDetail(BaseModel):
    """Error details"""
    code: str
    message: str
    details: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: ErrorDetail
