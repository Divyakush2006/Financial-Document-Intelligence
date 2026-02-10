"""
Document Extractors Package
Individual extractors for each document type
"""

from .base_extractor import BaseExtractor
from .invoice_extractor import InvoiceExtractor
from .bank_statement_extractor import BankStatementExtractor
from .salary_slip_extractor import SalarySlipExtractor
from .receipt_extractor import ReceiptExtractor
from .tax_document_extractor import TaxDocumentExtractor
from .loan_agreement_extractor import LoanAgreementExtractor
from .id_document_extractor import IDDocumentExtractor
from .utility_bill_extractor import UtilityBillExtractor

# Extractor registry for document router
EXTRACTOR_MAP = {
    "invoice": InvoiceExtractor,
    "bank_statement": BankStatementExtractor,
    "salary_slip": SalarySlipExtractor,
    "receipt": ReceiptExtractor,
    "tax_document": TaxDocumentExtractor,
    "loan_agreement": LoanAgreementExtractor,
    "id_document": IDDocumentExtractor,
    "utility_bill": UtilityBillExtractor,
}

__all__ = [
    "BaseExtractor",
    "InvoiceExtractor",
    "BankStatementExtractor",
    "SalarySlipExtractor",
    "ReceiptExtractor",
    "TaxDocumentExtractor",
    "LoanAgreementExtractor",
    "IDDocumentExtractor",
    "UtilityBillExtractor",
    "EXTRACTOR_MAP",
]
