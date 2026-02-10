"""
Invoice Extractor - Specialized extractor for invoices
"""

from services.extractors.base_extractor import BaseExtractor


class InvoiceExtractor(BaseExtractor):
    """Extract structured data from invoices"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate invoice-specific extraction prompt"""
        return f"""You are a financial document extraction AI specializing in invoices.

DOCUMENT TYPE: Invoice

EXTRACTED TEXT:
{text}

TASK: Extract the following invoice information in JSON format:

REQUIRED FIELDS:
- invoice_number: Invoice/Bill number
- date: Invoice date (YYYY-MM-DD format)
- due_date: Payment due date (YYYY-MM-DD format if available)
- vendor_name: Seller/vendor company name
- vendor_address: Seller's complete address
- customer_name: Buyer/customer name
- customer_address: Buyer's complete address
- subtotal: Subtotal amount before tax (number only)
- tax_amount: Total tax amount (number only)
- total_amount: Final total amount (number only)
- currency: Currency code (e.g., INR, USD)
- payment_terms: Payment terms/conditions
- line_items: Array of items with:
  - description: Item/service description
  - quantity: Quantity (number only)
  - unit_price: Price per unit (number only)
  - total: Line item total (number only)

EXTRACTION RULES:
1. Extract ONLY factual information present in the text
2. Use null for fields not found in the document
3. Normalize dates to YYYY-MM-DD format
4. Extract amounts as numbers without currency symbols
5. For line_items, extract ALL items/services listed
6. If multiple dates, invoice_date is the issue/billing date
7. Vendor is the seller (Bill From), Customer is the buyer (Bill To)

OUTPUT FORMAT:
Return a valid JSON object with the structure above. Do not include any explanation, only the JSON.

Example:
{{
  "invoice_number": "INV-2024-001",
  "date": "2024-03-21",
  "vendor_name": "ABC Company",
  ...
}}"""
    
    def get_expected_fields(self) -> list:
        """Return expected invoice fields"""
        return [
            "invoice_number",
            "date",
            "vendor_name",
            "customer_name",
            "total_amount",
            "line_items"
        ]
    
    def postprocess_data(self, data: dict) -> dict:
        """Validate and format invoice data"""
        # Ensure line_items is a list
        if isinstance(data.get('line_items'), list):
            # Calculate totals if missing
            if data.get('subtotal') is None and data.get('line_items'):
                subtotal = sum(item.get('total', 0) for item in data['line_items'] if isinstance(item.get('total'), (int, float)))
                data['subtotal'] = subtotal
        
        return data
