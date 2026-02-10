"""
Loan Agreement Extractor - For loan documents and agreements
"""

from services.extractors.base_extractor import BaseExtractor


class LoanAgreementExtractor(BaseExtractor):
    """Extract structured data from loan agreements"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate loan agreement extraction prompt"""
        return f"""You are a financial document extraction AI specializing in loan agreements.

DOCUMENT TYPE: Loan Agreement

EXTRACTED TEXT:
{text}

TASK: Extract loan agreement information in JSON format:

FIELDS:
- loan_type: Type of loan (Personal, Home, Auto, Business, etc.)
- borrower_name: Borrower's name
- borrower_address: Borrower's address
- lender_name: Lender/bank name
- lender_address: Lender address
- loan_amount: Principal loan amount (number)
- interest_rate: Annual interest rate (number, e.g., 10.5 for 10.5%)  
- tenure_months: Loan tenure in months (number)
- emi_amount: Monthly EMI amount (number)
- processing_fee: Processing/origination fee (number)
- start_date: Loan start/disbursement date (YYYY-MM-DD)
- maturity_date: Loan maturity/end date (YYYY-MM-DD)
- collateral_details: Collateral/security details (if mentioned)
- guarantor_name: Guarantor name (if applicable)

RULES:
1. Extract factual information only
2. Dates in YYYY-MM-DD, amounts/rates as numbers
3. Use null for missing fields

OUTPUT: Valid JSON only.
"""
    
    def get_expected_fields(self) -> list:
        return ["borrower_name", "lender_name", "loan_amount", "interest_rate"]
