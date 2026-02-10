"""
Rule-Based Excel to JSON Converter
Intelligent parser that converts bank statement Excel files to structured JSON
WITHOUT using any LLM - pure rule-based parsing with pattern matching
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re
from pathlib import Path

logger = logging.getLogger(__name__)


class ExcelToJSONConverter:
    """
    Smart Excel to JSON converter for bank statements.
    Uses pattern matching and heuristics to identify columns and extract data.
    """
    
    # Column detection patterns
    DATE_PATTERNS = ['date', 'tran date', 'txn date', 'transaction date', 'value date']
    DESCRIPTION_PATTERNS = ['description', 'narration', 'particulars', 'details', 'transaction details']
    DEBIT_PATTERNS = ['debit', 'withdrawal', 'dr', 'amount withdrawn', 'paid']
    CREDIT_PATTERNS = ['credit', 'deposit', 'cr', 'amount deposited', 'received']
    BALANCE_PATTERNS = ['balance', 'closing balance', 'available balance']
    REFERENCE_PATTERNS = ['chq no', 'cheque', 'ref no', 'reference', 'transaction id']
    
    def __init__(self):
        """Initialize converter"""
        logger.info("Excel to JSON Converter initialized (Rule-Based)")
    
    def convert(self, file_path: str) -> Dict:
        """
        Convert Excel bank statement to structured JSON.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Dictionary with structured bank statement data
        """
        try:
            logger.info(f"Converting: {Path(file_path).name}")
            
            # Step 1: Load and clean Excel
            df = self._load_excel(file_path)
            
            # Step 2: Identify header row and columns
            header_row, column_mapping = self._identify_structure(df)
            
            # Step 3: Extract header metadata
            metadata = self._extract_metadata(df, header_row)
            
            # Step 4: Extract transactions
            transactions_df = df.iloc[header_row + 1:].copy()
            transactions = self._extract_transactions(transactions_df, column_mapping)
            
            # Step 5: Calculate summaries
            summary = self._calculate_summary(transactions)
            
            # Step 6: Build final JSON
            result = {
                **metadata,
                **summary,
                "transactions": transactions,
                "number_of_transactions": len(transactions)
            }
            
            logger.info(f"✅ Converted successfully: {len(transactions)} transactions")
            
            return {
                "success": True,
                "data": result,
                "metadata": {
                    "source_file": Path(file_path).name,
                    "total_rows": len(df),
                    "header_row": header_row,
                    "converter": "rule_based"
                }
            }
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _load_excel(self, file_path: str) -> pd.DataFrame:
        """Load and clean Excel file"""
        # Read Excel
        df = pd.read_excel(file_path, sheet_name=0)
        
        # Drop completely empty rows and columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df
    
    def _identify_structure(self, df: pd.DataFrame) -> Tuple[int, Dict]:
        """
        Identify header row and map columns to their purposes.
        
        Returns:
            Tuple of (header_row_index, column_mapping_dict)
        """
        # Find header row (row containing keywords like 'Date', 'Debit', 'Credit')
        header_row = 0
        for idx in range(min(10, len(df))):
            row_text = ' '.join([str(val).lower() for val in df.iloc[idx].values])
            
            # Check if this row contains header keywords
            if any(pattern in row_text for pattern in self.DATE_PATTERNS + self.DEBIT_PATTERNS + self.CREDIT_PATTERNS):
                header_row = idx
                logger.info(f"Detected header row: {idx}")
                break
        
        # Map columns based on header row
        header_values = df.iloc[header_row].values
        column_mapping = {}
        
        for col_idx, header in enumerate(header_values):
            header_lower = str(header).lower().strip()
            
            # Identify column purpose
            if any(pattern in header_lower for pattern in self.DATE_PATTERNS):
                column_mapping['date'] = col_idx
            elif any(pattern in header_lower for pattern in self.DESCRIPTION_PATTERNS):
                column_mapping['description'] = col_idx
            elif any(pattern in header_lower for pattern in self.DEBIT_PATTERNS):
                column_mapping['debit'] = col_idx
            elif any(pattern in header_lower for pattern in self.CREDIT_PATTERNS):
                column_mapping['credit'] = col_idx
            elif any(pattern in header_lower for pattern in self.BALANCE_PATTERNS):
                column_mapping['balance'] = col_idx
            elif any(pattern in header_lower for pattern in self.REFERENCE_PATTERNS):
                column_mapping['reference'] = col_idx
        
        logger.info(f"Column mapping: {column_mapping}")
        
        return header_row, column_mapping
    
    def _extract_metadata(self, df: pd.DataFrame, header_row: int) -> Dict:
        """Extract account metadata from header rows"""
        metadata = {
            "bank_name": None,
            "account_number": None,
            "account_holder_name": None,
            "branch_name": None,
            "ifsc_code": None,
            "currency": "INR"
        }
        
        # Look in first few rows before header
        for idx in range(header_row):
            row_text = ' '.join([str(val) for val in df.iloc[idx].values if pd.notna(val)])
            
            # Try to find account number (10-16 digits)
            acc_match = re.search(r'\b\d{10,16}\b', row_text)
            if acc_match and not metadata['account_number']:
                metadata['account_number'] = acc_match.group()
            
            # Try to find IFSC code (format: ABCD0123456)
            ifsc_match = re.search(r'\b[A-Z]{4}0[A-Z0-9]{6}\b', row_text)
            if ifsc_match:
                metadata['ifsc_code'] = ifsc_match.group()
            
            # Common bank names
            bank_keywords = ['HDFC', 'ICICI', 'SBI', 'AXIS', 'KOTAK', 'YES BANK', 'PNB', 'BOB', 'BANK OF']
            for bank in bank_keywords:
                if bank in row_text.upper():
                    metadata['bank_name'] = bank
                    break
        
        return metadata
    
    def _extract_transactions(self, transactions_df: pd.DataFrame, column_mapping: Dict) -> List[Dict]:
        """Extract transaction data from DataFrame"""
        transactions = []
        skipped_count = 0
        skipped_reasons = {"empty_row": 0, "no_date": 0, "parse_fail": 0}
        
        logger.info(f"Processing {len(transactions_df)} potential transaction rows...")
        
        for idx, row in transactions_df.iterrows():
            # Skip empty rows
            if row.isna().all():
                skipped_count += 1
                skipped_reasons["empty_row"] += 1
                continue
            
            # Extract date
            date_col = column_mapping.get('date', 0)
            date_value = row.iloc[date_col]
            
            # Skip if no valid date
            if pd.isna(date_value):
                skipped_count += 1
                skipped_reasons["no_date"] += 1
                continue
            
            # Parse date
            parsed_date = self._parse_date(date_value)
            if not parsed_date:
                skipped_count += 1
                skipped_reasons["parse_fail"] += 1
                logger.debug(f"Row {idx}: Failed to parse date '{date_value}'")
                continue
            
            # Extract other fields
            description = ""
            if 'description' in column_mapping:
                desc_col = column_mapping['description']
                description = str(row.iloc[desc_col]) if pd.notna(row.iloc[desc_col]) else ""
            
            debit = 0.0
            if 'debit' in column_mapping:
                debit_col = column_mapping['debit']
                debit = self._parse_amount(row.iloc[debit_col])
            
            credit = 0.0
            if 'credit' in column_mapping:
                credit_col = column_mapping['credit']
                credit = self._parse_amount(row.iloc[credit_col])
            
            balance = 0.0
            if 'balance' in column_mapping:
                balance_col = column_mapping['balance']
                balance = self._parse_amount(row.iloc[balance_col])
            
            reference = None
            if 'reference' in column_mapping:
                ref_col = column_mapping['reference']
                reference = str(row.iloc[ref_col]) if pd.notna(row.iloc[ref_col]) else None
            
            # Determine transaction type
            transaction_type = "credit" if credit > 0 else "debit"
            
            # Build transaction
            transaction = {
                "date": parsed_date,
                "description": description.strip(),
                "debit": debit,
                "credit": credit,
                "balance": balance,
                "transaction_type": transaction_type,
                "reference_number": reference
            }
            
            transactions.append(transaction)
        
        logger.info(f"✅ Extracted {len(transactions)} transactions (skipped {skipped_count})")
        if skipped_count > 0:
            logger.info(f"   Skip reasons: {skipped_reasons}")
        
        return transactions
    
    def _calculate_summary(self, transactions: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        if not transactions:
            return {
                "statement_period_from": None,
                "statement_period_to": None,
                "opening_balance": 0.0,
                "closing_balance": 0.0,
                "total_credits": 0.0,
                "total_debits": 0.0
            }
        
        # Extract dates
        dates = [t['date'] for t in transactions if t['date']]
        
        # Calculate totals
        total_credits = sum(t['credit'] for t in transactions)
        total_debits = sum(t['debit'] for t in transactions)
        
        # Get balances
        opening_balance = transactions[0]['balance'] - transactions[0]['credit'] + transactions[0]['debit']
        closing_balance = transactions[-1]['balance']
        
        return {
            "statement_period_from": dates[0] if dates else None,
            "statement_period_to": dates[-1] if dates else None,
            "opening_balance": round(opening_balance, 2),
            "closing_balance": round(closing_balance, 2),
            "total_credits": round(total_credits, 2),
            "total_debits": round(total_debits, 2)
        }
    
    def _parse_date(self, date_value) -> Optional[str]:
        """Parse date to YYYY-MM-DD format"""
        if pd.isna(date_value):
            return None
        
        try:
            # If already datetime
            if isinstance(date_value, pd.Timestamp) or isinstance(date_value, datetime):
                return date_value.strftime('%Y-%m-%d')
            
            # Try parsing string
            date_str = str(date_value).strip()
            
            # Skip if looks like header text
            if any(keyword in date_str.lower() for keyword in ['date', 'tran', 'txn', 'transaction']):
                return None
            
            # Try pandas to_datetime (handles many formats automatically)
            try:
                dt = pd.to_datetime(date_str, dayfirst=True)  # Indian format preference
                return dt.strftime('%Y-%m-%d')
            except:
                pass
            
            # Try common formats manually
            for fmt in ['%d-%m-%Y', '%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%d-%b-%Y', '%d-%B-%Y', '%Y%m%d']:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Last resort: try to extract date pattern
            # Format: DD-MM-YYYY or DD/MM/YYYY
            date_match = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})', date_str)
            if date_match:
                day, month, year = date_match.groups()
                if len(year) == 2:
                    year = '20' + year if int(year) < 50 else '19' + year
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            logger.warning(f"Could not parse date: '{date_value}' (type: {type(date_value)})")
            return None
            
        except Exception as e:
            logger.warning(f"Date parsing error for '{date_value}': {e}")
            return None
    
    def _parse_amount(self, amount_value) -> float:
        """Parse amount to float"""
        if pd.isna(amount_value):
            return 0.0
        
        try:
            # If already numeric
            if isinstance(amount_value, (int, float)):
                return float(amount_value)
            
            # Clean string (remove commas, currency symbols)
            amount_str = str(amount_value)
            amount_str = amount_str.replace(',', '').replace('₹', '').replace('Rs', '').replace('INR', '').strip()
            
            # Handle negative/parentheses
            if '(' in amount_str:
                amount_str = amount_str.replace('(', '-').replace(')', '')
            
            return float(amount_str) if amount_str else 0.0
            
        except Exception:
            return 0.0


# Singleton instance
_converter = None

def get_converter() -> ExcelToJSONConverter:
    """Get or create converter instance"""
    global _converter
    if _converter is None:
        _converter = ExcelToJSONConverter()
    return _converter
