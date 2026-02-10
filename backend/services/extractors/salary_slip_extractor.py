"""
Salary Slip Extractor - Specialized extractor for salary slips/pay stubs
"""

from services.extractors.base_extractor import BaseExtractor


class SalarySlipExtractor(BaseExtractor):
    """Extract structured data from salary slips"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate salary slip-specific extraction prompt"""
        return f"""You are a financial document extraction AI specializing in salary slips/pay stubs.

DOCUMENT TYPE: Salary Slip / Pay Stub

EXTRACTED TEXT:
{text}

TASK: Extract the following salary information in JSON format:

REQUIRED FIELDS:
- employee_name: Employee's full name
- employee_id: Employee ID/number
- designation: Job title/designation
- department: Department name if available
- employer_name: Company/employer official name
- employer_address: Company address
- pay_period_month: Month of salary (e.g., "January", "Jan", "01")
- pay_period_year: Year (e.g., "2024")
- payment_date: Salary payment/credit date (YYYY-MM-DD)
- earnings: Object with earning components:
  - basic_salary: Basic salary amount (number)
  - hra: House Rent Allowance (number)
  - da: Dearness Allowance (number, if available)
  - special_allowance: Special/Other allowances (number)
  - bonus: Bonus/incentive (number, if available)
  - overtime: Overtime pay (number, if available)
  - other_earnings: Any other earnings (number)
- deductions: Object with deduction components:
  - pf: Provident Fund (number)
  - esi: ESI/Health insurance (number, if available)
  - professional_tax: Professional tax (number, if available)
  - tds: Tax Deducted at Source (number)
  - loan_recovery: Loan deduction (number, if available)
  - other_deductions: Any other deductions (number)
- gross_salary: Total earnings before deductions (number)
- total_deductions: Sum of all deductions (number)
- net_salary: Take-home salary after deductions (number)
- bank_account_number: Salary credited to account (last 4 digits or masked)
- ifsc_code: Bank IFSC code if available
- pan_number: Employee PAN if available
- uan_number: UAN number if available

EXTRACTION RULES:
1. Extract ONLY factual information present in the text
2. Use null for fields not found in the document
3. Use 0 for earning/deduction components if not listed
4. Normalize dates to YYYY-MM-DD format
5. Extract amounts as numbers without currency symbols or commas
6. gross_salary should equal sum of all earnings
7. net_salary should equal gross_salary minus total_deductions
8. If pay_period_month is numeric (e.g., "01"), keep as string

OUTPUT FORMAT:
Return a valid JSON object with the structure above. Do not include any explanation, only the JSON.

Example:
{{
  "employee_name": "Shreyash Srivastava",
  "employee_id": "EMP12345",
  "designation": "Software Engineer",
  "employer_name": "Tech Solutions Pvt Ltd",
  "pay_period_month": "March",
  "pay_period_year": "2024",
  "earnings": {{
    "basic_salary": 40000.00,
    "hra": 16000.00,
    "special_allowance": 10000.00,
    "bonus": 0
  }},
  "deductions": {{
    "pf": 4800.00,
    "tds": 3000.00,
    "professional_tax": 200.00
  }},
  "gross_salary": 66000.00,
  "total_deductions": 8000.00,
  "net_salary": 58000.00
}}"""
    
    def get_expected_fields(self) -> list:
        """Return expected salary slip fields"""
        return [
            "employee_name",
            "employer_name",
            "pay_period_month",
            "pay_period_year",
            "gross_salary",
            "net_salary"
        ]
    
    def postprocess_data(self, data: dict) -> dict:
        """Validate and calculate salary data"""
        # Ensure earnings and deductions are dicts
        if not isinstance(data.get('earnings'), dict):
            data['earnings'] = {}
        if not isinstance(data.get('deductions'), dict):
            data['deductions'] = {}
        
        # Calculate gross_salary if missing
        if data.get('gross_salary') is None and data.get('earnings'):
            gross = sum(v for v in data['earnings'].values() if isinstance(v, (int, float)))
            data['gross_salary'] = gross
        
        # Calculate total_deductions if missing
        if data.get('total_deductions') is None and data.get('deductions'):
            total_ded = sum(v for v in data['deductions'].values() if isinstance(v, (int, float)))
            data['total_deductions'] = total_ded
        
        # Calculate net_salary if missing
        if data.get('net_salary') is None:
            gross = data.get('gross_salary', 0)
            deductions = data.get('total_deductions', 0)
            data['net_salary'] = gross - deductions if isinstance(gross, (int, float)) and isinstance(deductions, (int, float)) else None
        
        return data
