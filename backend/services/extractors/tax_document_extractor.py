"""
Tax Document Extractor - For tax returns, Form 16, etc.
"""

from services.extractors.base_extractor import BaseExtractor


class TaxDocumentExtractor(BaseExtractor):
    """Extract structured data from tax documents"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate tax document extraction prompt"""
        return f"""You are a financial document extraction AI specializing in tax documents.

DOCUMENT TYPE: Tax Document (Form 16, ITR, 26AS, etc.)

EXTRACTED TEXT:
{text}

TASK: Extract tax document information in JSON format:

FIELDS:
- document_type: Type (Form 16, ITR, Form 26AS, etc.)
- taxpayer_name: Taxpayer's name
- pan_number: PAN number
- financial_year: Financial year (e.g., "2023-2024")
- assessment_year: Assessment year (e.g., "2024-2025")
- employer_name: Employer name (if Form 16)
- employer_tan: Employer TAN (if Form 16)
- gross_income: Gross total income (number)
- deductions: Total deductions under Chapter VI-A (number)
- taxable_income: Total taxable income (number)
- tax_paid: Total tax paid/deducted (number)
- tds_deducted: TDS deducted (number)
- refund_or_payable: Refund due or tax payable (number, positive for refund, negative for payable)

RULES:
1. Extract factual information only
2. Dates in YYYY-MM-DD, amounts as numbers
3. Use null for missing fields

OUTPUT: Valid JSON only.
"""
    
    def get_expected_fields(self) -> list:
        return ["taxpayer_name", "pan_number", "financial_year", "gross_income"]
