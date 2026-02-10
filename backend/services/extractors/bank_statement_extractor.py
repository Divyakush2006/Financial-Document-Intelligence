"""
Bank Statement Extractor - Specialized extractor for bank statements
"""

from services.extractors.base_extractor import BaseExtractor


class BankStatementExtractor(BaseExtractor):
    """Extract structured data from bank statements"""
    
    def __init__(self, groq_llm):
        """Initialize with LLM service only (OCR done separately)"""
        # Pass None for azure_ocr since we handle text extraction separately
        super().__init__(azure_ocr=None, groq_llm=groq_llm)
    
    def extract(self, text: str) -> dict:
        """
        Extract from pre-extracted text (bypass OCR)
        
        Args:
            text: Already extracted text from Excel/OCR
            
        Returns:
            Dict with extraction results
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Starting extraction... Text length: {len(text)} chars")
            
            # Generate extraction prompt
            prompt = self.get_extraction_prompt(text)
            logger.info(f"Generated prompt, length: {len(prompt)} chars")
            
            # LLM structuring
            logger.info("Calling LLM structure_data()...")
            structured_data = self._structure_with_llm(prompt)
            
            logger.info(f"LLM returned: {type(structured_data)}, value: {bool(structured_data)}")
            
            if not structured_data:
                logger.error("LLM returned None or empty data!")
                return {
                    "success": False,
                    "error": "LLM structuring failed - returned None"
                }
            
            # Validate required fields
            validation = self._validate_extraction(structured_data)
            logger.info(f"Validation: {validation['fields_extracted']}/{validation['fields_expected']} fields")
            
            return {
                "success": True,
                "data": structured_data,
                "extraction_confidence": validation['confidence'],
                "fields_extracted": validation['fields_extracted'],
                "fields_expected": validation['fields_expected']
            }
            
        except Exception as e:
            logger.error(f"Extraction error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate bank statement-specific extraction prompt"""
        
        # TEMPORARILY DISABLED: Token optimizer was truncating data
        # Smart token-based optimization (instead of fixed character limit)
        # from services.token_optimizer import get_token_optimizer
        # 
        # optimizer = get_token_optimizer()
        # optimized_text, optimization_stats = optimizer.optimize_for_llm(text)
        # 
        # # Log optimization results
        # if optimization_stats['truncated']:
        #     logger.info(f"🔧 Token optimization: {optimization_stats['original_tokens']} → {optimization_stats['final_tokens']} tokens")
        #     logger.info(f"📊 Kept: Header={optimization_stats['header_lines']} | Middle={optimization_stats['middle_samples']} | Footer={optimization_stats['footer_lines']} lines")
        # 
        # text = optimized_text
        
        # Use full text for now (test without optimization)
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Using full text: {len(text)} chars")
        
        
        return f"""You are a financial document extraction AI specializing in bank statements.

CRITICAL: Focus on extracting header/metadata information FIRST before transactions.

DOCUMENT TEXT:
{text}

TASK: Extract bank statement data and return as valid JSON.

EXTRACTION PRIORITY (extract in this order):
1. METADATA (CRITICAL):
   - bank_name: Bank's name - CHECK TRANSACTION DESCRIPTIONS for UPI codes like "YES BANK", "HDFC BANK", "ICICI", etc.
   - account_number: Account number (if found in header or filename)
   - account_holder_name: Account holder's name (if found)
   - branch_name: Branch name if mentioned
   - ifsc_code: IFSC code (11 characters, format: BANK0123456)
   NOTE: Bank statements from Excel may not have traditional headers. Look in UPI/IMPS transaction descriptions!

2. PERIOD & BALANCES:
   - statement_period_from: Start date (YYYY-MM-DD)
   - statement_period_to: End date (YYYY-MM-DD)
   - opening_balance: Opening balance (number only)
   - closing_balance: Closing balance (number only)
   - currency: Currency (INR, USD, etc.)

3. TRANSACTION SUMMARY:
   - total_credits: Sum of all credits (number)
   - total_debits: Sum of all debits (number)
   - number_of_transactions: Total transaction count

4. TRANSACTIONS (extract ALL rows):
   Each transaction must have:
   - date: Transaction date (YYYY-MM-DD)
   - description: Transaction description/narration
   - debit: Debit amount (0 if credit transaction)
   - credit: Credit amount (0 if debit transaction)
   - balance: Balance after transaction
   - transaction_type: "debit" or "credit"

EXTRACTION RULES:
1. Look at the TOP of the document for bank name and account info
2. Bank names are usually in CAPS or bold at the top
3. Account numbers are typically labeled as "Account No:", "A/C No:", "Account Number"
4. Use null for fields not found (don't guess)
5. Normalize dates to YYYY-MM-DD format
6. Extract amounts as numbers without ₹, Rs., or commas
7. For each transaction: either debit OR credit should be non-zero (not both)
8. Preserve transaction order chronologically

EXAMPLE OUTPUT FORMAT:
{{
  "bank_name": "HDFC Bank",
  "account_number": "1234567890",
  "account_holder_name": "John Doe",
  "branch_name": "Mumbai Main",
  "ifsc_code": "HDFC0001234",
  "statement_period_from": "2024-01-01",
  "statement_period_to": "2024-01-31",
  "opening_balance": 10000.00,
  "closing_balance": 15000.00,
  "currency": "INR",
  "total_credits": 20000.00,
  "total_debits": 15000.00,
  "number_of_transactions": 50,
  "transactions": [
    {{
      "date": "2024-01-01",
      "description": "Salary Credit",
      "debit": 0,
      "credit": 5000.00,
      "balance": 15000.00,
      "transaction_type": "credit"
    }},
    {{
      "date": "2024-01-02",
      "description": "ATM Withdrawal",
      "debit": 2000.00,
      "credit": 0,
      "balance": 13000.00,
      "transaction_type": "debit"
    }}
  ]
}}

Return ONLY valid JSON. No additional text or explanations.
"""
    
    def get_expected_fields(self) -> list:
        """Return expected bank statement fields"""
        return [
            "account_holder_name",
            "account_number",
            "bank_name",
            "statement_period_from",
            "statement_period_to",
            "opening_balance",
            "closing_balance",
            "transactions"
        ]
    
    def postprocess_data(self, data: dict) -> dict:
        """Validate and calculate bank statement data"""
        # Ensure transactions is a list
        if not isinstance(data.get('transactions'), list):
            data['transactions'] = []
        
        # Calculate totals if missing
        if data.get('transactions'):
            if data.get('total_credits') is None:
                data['total_credits'] = sum(t.get('credit', 0) for t in data['transactions'])
            
            if data.get('total_debits') is None:
                data['total_debits'] = sum(t.get('debit', 0) for t in data['transactions'])
            
            if data.get('number_of_transactions') is None:
                data['number_of_transactions'] = len(data['transactions'])
        
        return data
