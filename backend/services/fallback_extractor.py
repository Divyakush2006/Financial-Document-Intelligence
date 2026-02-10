"""
Fallback Extractor - Direct Excel parsing when LLM fails
"""

import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


def extract_bank_from_text(text: str) -> Optional[str]:
    """Extract bank name from transaction descriptions"""
    # Common Indian banks in UPI transactions
    banks = [
        "AXIS BANK", "HDFC BANK", "ICICI BANK", "SBI", "State Bank Of India",
        "YES BANK", "KOTAK MAHINDRA BANK", "PUNJAB NATIONAL BANK", "PNB",
        "BANK OF BARODA", "CANARA BANK", "UNION BANK", "IDBI BANK",
        "INDUSIND BANK", "FEDERAL BANK"
    ]
    
    text_upper = text.upper()
    for bank in banks:
        if bank.upper() in text_upper:
            return bank
    
    return None


def fallback_excel_extraction(file_path: str) -> Dict:
    """
    Direct Excel extraction as fallback when LLM fails
    
    Args:
        file_path: Path to Excel file
        
    Returns:
        Dict with extracted data
    """
    try:
        logger.info(f"🔄 Using fallback extraction for {file_path}")
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Basic structure detection
        # Typically: Date | Description | Debit | Credit | Balance
        
        # Find numeric columns (likely balance, debit, credit)
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()
        
        # Try to identify balance column (usually last numeric column)
        balance_col = numeric_cols[-1] if numeric_cols else None
        
        # Extract opening and closing balances
        opening_balance = None
        closing_balance = None
        
        if balance_col:
            # Filter out NaN values
            valid_balances = df[balance_col].dropna()
            if len(valid_balances) > 0:
                opening_balance = float(valid_balances.iloc[0])
                closing_balance = float(valid_balances.iloc[-1])
        
        # Extract transactions
        transactions = []
        total_debits = 0
        total_credits = 0
        
        # Try to find debit/credit columns
        debit_col = None
        credit_col = None
        date_col = None
        desc_col = None
        
        for col in df.columns:
            col_lower = str(col).lower()
            if 'debit' in col_lower or 'withdrawal' in col_lower:
                debit_col = col
            elif 'credit' in col_lower or 'deposit' in col_lower:
                credit_col = col
            elif 'date' in col_lower:
                date_col = col
            elif 'description' in col_lower or 'narration' in col_lower or 'particular' in col_lower:
                desc_col = col
        
        # Build transactions
        for idx, row in df.iterrows():
            try:
                txn = {}
                
                # Date
                if date_col:
                    date_val = row[date_col]
                    if pd.notna(date_val):
                        txn['date'] = str(date_val)[:10]  # YYYY-MM-DD format
                
                # Description
                if desc_col:
                    desc_val = row[desc_col]
                    if pd.notna(desc_val):
                        txn['description'] = str(desc_val)
                
                # Debit
                if debit_col:
                    debit_val = row[debit_col]
                    if pd.notna(debit_val):
                        txn['debit'] = float(debit_val)
                        total_debits += float(debit_val)
                        txn['transaction_type'] = "debit"
                    else:
                        txn['debit'] = 0
                
                # Credit
                if credit_col:
                    credit_val = row[credit_col]
                    if pd.notna(credit_val):
                        txn['credit'] = float(credit_val)
                        total_credits += float(credit_val)
                        txn['transaction_type'] = "credit"
                    else:
                        txn['credit'] = 0
                
                # Balance
                if balance_col:
                    bal_val = row[balance_col]
                    if pd.notna(bal_val):
                        txn['balance'] = float(bal_val)
                
                # Only add if has some valid data
                if any(txn.values()):
                    transactions.append(txn)
                    
            except Exception as e:
                logger.debug(f"Skipping row {idx}: {e}")
                continue
        
        # Try to extract bank name from all descriptions
        bank_name = None
        all_text = " ".join(df.astype(str).values.flatten())
        bank_name = extract_bank_from_text(all_text)
        
        result = {
            "bank_name": bank_name,
            "account_number": None,  # Not available in Excel typically
            "account_holder_name": None,
            "branch_name": None,
            "ifsc_code": None,
            "statement_period_from": None,
            "statement_period_to": None,
            "opening_balance": opening_balance,
            "closing_balance": closing_balance,
            "currency": "INR",  # Assume INR for Indian banks
            "total_credits": total_credits if total_credits > 0 else None,
            "total_debits": total_debits if total_debits > 0 else None,
            "number_of_transactions": len(transactions),
            "transactions": transactions
        }
        
        logger.info(f"✅ Fallback extraction successful: {len(transactions)} transactions, Bank: {bank_name}")
        
        return {
            "success": True,
            "data": result,
            "method": "fallback_excel",
            "extraction_confidence": 0.6  # Lower confidence for fallback
        }
        
    except Exception as e:
        logger.error(f"❌ Fallback extraction failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "method": "fallback_excel"
        }
