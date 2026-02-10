"""
Receipt Extractor - Specialized extractor for receipts
"""

from services.extractors.base_extractor import BaseExtractor


class ReceiptExtractor(BaseExtractor):
    """Extract structured data from receipts"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate receipt-specific extraction prompt"""
        return f"""You are a financial document extraction AI specializing in receipts.

DOCUMENT TYPE: Receipt

EXTRACTED TEXT:
{text}

TASK: Extract the following receipt information in JSON format:

REQUIRED FIELDS:
- merchant_name: Store/merchant name
- merchant_address: Merchant address
- receipt_number: Receipt/transaction number
- date: Receipt date (YYYY-MM-DD)
- time: Transaction time (HH:MM format if available)
- items: Array of purchased items with:
  - description: Item name/description
  - quantity: Quantity (number)
  - unit_price: Price per unit (number)
  - total: Line item total (number)
- subtotal: Subtotal before tax (number)
- tax: Tax amount (number)
- total: Final total amount (number)
- payment_method: Payment method (Cash, Card, UPI, etc.)
- currency: Currency code (e.g., INR, USD)

EXTRACTION RULES:
1. Extract ONLY factual information present in the text
2. Use null for fields not found
3. Normalize dates to YYYY-MM-DD format
4. Extract amounts as numbers without currency symbols
5. For items, extract ALL purchased items listed
6. If tax breakdown (CGST/SGST/GST), sum them
7. Verify: subtotal + tax = total

OUTPUT FORMAT:
Return a valid JSON object. Do not include any explanation, only the JSON.
"""
    
    def get_expected_fields(self) -> list:
        """Return expected receipt fields"""
        return [
            "merchant_name",
            "date",
            "total",
            "items"
        ]
