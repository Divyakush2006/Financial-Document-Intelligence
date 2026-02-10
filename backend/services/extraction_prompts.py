"""
Professional Extraction Prompt Templates
Centralized, version-controlled prompts for LLM-based bank statement extraction
"""

from typing import Dict
import pandas as pd


def generate_bank_statement_prompt(df: pd.DataFrame) -> str:
    """
    Generate a structured extraction prompt for bank statement data.
    
    Args:
        df: Pandas DataFrame containing raw bank statement Excel data
        
    Returns:
        Formatted prompt string for Gemini API
    """
    # Convert DataFrame to structured text
    excel_text = _dataframe_to_structured_text(df)
    
    prompt = f"""You are a professional financial data extraction specialist. Your task is to extract structured data from a bank statement Excel file.

=== INPUT DATA ===
{excel_text}

=== EXTRACTION INSTRUCTIONS ===

**CRITICAL RULES:**
1. Extract ALL transactions - do not truncate or summarize
2. Normalize all dates to YYYY-MM-DD format
3. Extract amounts as numbers (remove ₹, Rs., commas)
4. Use null for missing fields (do not guess or infer)
5. Preserve exact transaction descriptions
6. Maintain chronological order

**FIELD EXTRACTION PRIORITY:**

**1. ACCOUNT METADATA** (Check first few rows and transaction descriptions):
   - bank_name: Bank institution name (look for names in headers or UPI transaction codes like "HDFC", "ICICI", "YES BANK")
   - account_number: Full account number (if visible in header)
   - account_holder_name: Account holder's full name
   - branch_name: Branch name or code
   - ifsc_code: IFSC code (11 characters, format: BANK0123456)
   - currency: Currency code (default: "INR")

**2. STATEMENT PERIOD**:
   - statement_period_from: First transaction date (YYYY-MM-DD)
   - statement_period_to: Last transaction date (YYYY-MM-DD)
   - opening_balance: Opening balance (number)
   - closing_balance: Closing balance (number)

**3. TRANSACTION SUMMARY**:
   - total_credits: Sum of all credit transactions
   - total_debits: Sum of all debit transactions
   - number_of_transactions: Total count of transactions

**4. TRANSACTIONS** (Extract every single row):
   For each transaction, extract:
   - date: Transaction date (YYYY-MM-DD)
   - description: Full transaction description/narration
   - debit: Debit amount (0 if credit transaction)
   - credit: Credit amount (0 if debit transaction)
   - balance: Balance after transaction
   - transaction_type: "debit" or "credit"
   - reference_number: Check number or reference ID (if present)

**COMMON PATTERNS IN BANK STATEMENTS:**
- Column headers typically in rows 1-3
- Transaction data starts after headers
- Credits may be labeled as: Credit, Cr, Deposit, +
- Debits may be labeled as: Debit, Dr, Withdrawal, -
- Balance column shows running balance after each transaction

=== OUTPUT FORMAT ===

Return ONLY valid JSON with this exact structure (no additional text):

{{
  "bank_name": "string or null",
  "account_number": "string or null",
  "account_holder_name": "string or null",
  "branch_name": "string or null",
  "ifsc_code": "string or null",
  "currency": "INR",
  "statement_period_from": "YYYY-MM-DD",
  "statement_period_to": "YYYY-MM-DD",
  "opening_balance": 0.00,
  "closing_balance": 0.00,
  "total_credits": 0.00,
  "total_debits": 0.00,
  "number_of_transactions": 0,
  "transactions": [
    {{
      "date": "YYYY-MM-DD",
      "description": "Transaction description",
      "debit": 0.00,
      "credit": 0.00,
      "balance": 0.00,
      "transaction_type": "credit",
      "reference_number": "string or null"
    }}
  ]
}}

**VALIDATION CHECKS BEFORE RETURNING:**
1. All dates in YYYY-MM-DD format
2. All amounts are numbers (not strings)
3. Either debit OR credit is non-zero (never both)
4. Transaction count matches array length
5. opening_balance + total_credits - total_debits ≈ closing_balance

Extract the data now and return ONLY the JSON object.
"""
    
    return prompt


def _dataframe_to_structured_text(df: pd.DataFrame) -> str:
    """
    Convert DataFrame to clean, structured text for LLM processing.
    
    Args:
        df: Pandas DataFrame
        
    Returns:
        Formatted text representation
    """
    # Get basic info
    rows, cols = df.shape
    
    text_parts = []
    text_parts.append(f"Total Rows: {rows}")
    text_parts.append(f"Total Columns: {cols}\n")
    
    # Add column headers
    text_parts.append("COLUMNS:")
    for i, col in enumerate(df.columns):
        text_parts.append(f"  Column {i}: {col}")
    
    # Add all data in tabular format
    text_parts.append("\nDATA:")
    text_parts.append(df.to_string(index=True, max_rows=None, max_cols=None))
    
    return '\n'.join(text_parts)


# JSON Schema for validation
BANK_STATEMENT_SCHEMA = {
    "type": "object",
    "required": [
        "currency",
        "statement_period_from",
        "statement_period_to",
        "opening_balance",
        "closing_balance",
        "transactions"
    ],
    "properties": {
        "bank_name": {"type": ["string", "null"]},
        "account_number": {"type": ["string", "null"]},
        "account_holder_name": {"type": ["string", "null"]},
        "branch_name": {"type": ["string", "null"]},
        "ifsc_code": {"type": ["string", "null"]},
        "currency": {"type": "string"},
        "statement_period_from": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "statement_period_to": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
        "opening_balance": {"type": "number"},
        "closing_balance": {"type": "number"},
        "total_credits": {"type": "number"},
        "total_debits": {"type": "number"},
        "number_of_transactions": {"type": "integer"},
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["date", "description", "debit", "credit", "balance", "transaction_type"],
                "properties": {
                    "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
                    "description": {"type": "string"},
                    "debit": {"type": "number"},
                    "credit": {"type": "number"},
                    "balance": {"type": "number"},
                    "transaction_type": {"type": "string", "enum": ["debit", "credit"]},
                    "reference_number": {"type": ["string", "null"]}
                }
            }
        }
    }
}
