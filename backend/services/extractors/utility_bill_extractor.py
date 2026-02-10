"""
Utility Bill Extractor - For electricity, water, gas bills
"""

from services.extractors.base_extractor import BaseExtractor


class UtilityBillExtractor(BaseExtractor):
    """Extract structured data from utility bills"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate utility bill extraction prompt"""
        return f"""You are a financial document extraction AI specializing in utility bills.

DOCUMENT TYPE: Utility Bill (Electricity, Water, Gas, Internet, etc.)

EXTRACTED TEXT:
{text}

TASK: Extract utility bill information in JSON format:

FIELDS:
- utility_type: Type (Electricity, Water, Gas, Internet, etc.)
- provider_name: Utility provider/company name
- account_number: Consumer/account number
- customer_name: Customer name
- billing_address: Service/billing address
- bill_number: Bill number
- billing_period_from: Billing period start (YYYY-MM-DD)
- billing_period_to: Billing period end (YYYY-MM-DD)
- previous_reading: Previous meter reading (number)
- current_reading: Current meter reading (number)
- consumption: Units consumed (number)
- consumption_unit: Unit type (kWh, liters, cubic meters, etc.)
- amount: Total bill amount (number)
- due_date: Payment due date (YYYY-MM-DD)
- payment_status: Status (Paid/Unpaid/Overdue)

RULES:
1. Extract factual information only
2. Dates in YYYY-MM-DD, amounts as numbers
3. Use null for missing fields

OUTPUT: Valid JSON only.
"""
    
    def get_expected_fields(self) -> list:
        return ["utility_type", "customer_name", "amount", "due_date"]
