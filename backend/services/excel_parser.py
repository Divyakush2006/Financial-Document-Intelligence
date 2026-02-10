"""
Excel Parser for Bank Statements
Converts structured Excel files to text for LLM processing
"""

import pandas as pd
import logging
from typing import Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ExcelParser:
    """
    Smart Excel parser that converts bank statement Excel files to structured text
    Handles various Excel formats and normalizes data
    """
    
    def __init__(self):
        self.supported_extensions = {'.xlsx', '.xls', '.xlsm'}
    
    def is_supported(self, filename: str) -> bool:
        """Check if file is a supported Excel format"""
        return Path(filename).suffix.lower() in self.supported_extensions
    
    def parse_to_text(self, file_path: str, sheet_name: Optional[str] = None) -> Dict:
        """
        Parse Excel file and convert to structured text for LLM
        
        Args:
            file_path: Path to Excel file
            sheet_name: Specific sheet to parse (None = first sheet)
            
        Returns:
            Dict with 'text' (formatted string) and 'raw_data' (DataFrame)
        """
        try:
            # Read Excel file
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            else:
                # Try to auto-detect the statement sheet
                excel_file = pd.ExcelFile(file_path)
                sheet_name = self._find_statement_sheet(excel_file)
                df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            logger.info(f"Loaded Excel: {df.shape[0]} rows, {df.shape[1]} columns")
            
            # Clean the dataframe
            df_cleaned = self._clean_dataframe(df)
            
            # Convert to structured text
            text = self._dataframe_to_text(df_cleaned)
            
            return {
                'success': True,
                'text': text,
                'raw_data': df_cleaned,
                'metadata': {
                    'rows': df_cleaned.shape[0],
                    'columns': df_cleaned.shape[1],
                    'sheet_name': sheet_name
                }
            }
        
        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': None
            }
    
    def _find_statement_sheet(self, excel_file: pd.ExcelFile) -> str:
        """
        Auto-detect which sheet contains transaction data
        
        Looks for sheets with keywords like 'statement', 'transactions', etc.
        Falls back to first sheet if no match
        """
        sheet_names = excel_file.sheet_names
        
        # Keywords that indicate transaction sheet
        keywords = ['statement', 'transaction', 'account', 'ledger', 'detail']
        
        for sheet in sheet_names:
            sheet_lower = sheet.lower()
            if any(keyword in sheet_lower for keyword in keywords):
                logger.info(f"Auto-detected statement sheet: {sheet}")
                return sheet
        
        # Fallback to first sheet
        logger.info(f"Using default sheet: {sheet_names[0]}")
        return sheet_names[0]
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and normalize DataFrame
        - Remove empty rows/columns
        - Strip whitespace
        - Handle missing values
        """
        # Drop completely empty rows
        df = df.dropna(how='all')
        
        # Drop completely empty columns
        df = df.dropna(axis=1, how='all')
        
        # Fill NaN with empty string for text columns
        df = df.fillna('')
        
        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
        
        # Reset index
        df = df.reset_index(drop=True)
        
        return df
    
    def _dataframe_to_text(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to structured text for LLM parsing
        
        Format:
        - Header information (account, bank, period)
        - Transaction table in readable format
        - Summary totals
        """
        text_parts = []
        
        # Add header
        text_parts.append("=== BANK STATEMENT DATA ===\n")
        
        # Detect and add header fields (first few rows often contain account info)
        text_parts.append(self._extract_header_info(df))
        
        # Add transaction table
        text_parts.append("\n=== TRANSACTIONS ===")
        text_parts.append(self._format_transaction_table(df))
        
        # Add summary
        text_parts.append("\n=== SUMMARY ===")
        text_parts.append(self._extract_summary(df))
        
        return '\n'.join(text_parts)
    
    def _extract_header_info(self, df: pd.DataFrame) -> str:
        """Extract account holder, account number, bank name from first rows"""
        header_text = []
        
        # Look at first 5 rows for header information
        header_rows = min(5, len(df))
        
        for idx in range(header_rows):
            row_text = ' | '.join([str(val) for val in df.iloc[idx].values if val])
            if row_text:
                header_text.append(row_text)
        
        return '\n'.join(header_text)
    
    def _format_transaction_table(self, df: pd.DataFrame) -> str:
        """Format transaction rows as table"""
        # Skip header rows (usually first few rows)
        # Try to find where actual transaction data starts
        start_row = self._find_transaction_start(df)
        
        transaction_df = df.iloc[start_row:]
        
        # Format as pipe-separated table
        table_text = transaction_df.to_string(index=False, max_rows=None)
        
        return table_text
    
    def _find_transaction_start(self, df: pd.DataFrame) -> int:
        """
        Find the row where transaction data starts
        Looks for row with date-like patterns in first column
        """
        for idx in range(min(10, len(df))):
            first_val = str(df.iloc[idx, 0])
            # Check if looks like a date or transaction number
            if any(char.isdigit() for char in first_val):
                # Check if subsequent rows also have similar pattern
                if idx + 1 < len(df):
                    next_val = str(df.iloc[idx + 1, 0])
                    if any(char.isdigit() for char in next_val):
                        logger.info(f"Transaction data starts at row {idx}")
                        return idx
        
        # Default to row 3 (common for bank statements)
        return 3
    
    def _extract_summary(self, df: pd.DataFrame) -> str:
        """Extract summary information (totals, balances)"""
        summary_parts = []
        
        # Look at last 5 rows for summary
        last_rows = min(5, len(df))
        summary_df = df.tail(last_rows)
        
        for idx, row in summary_df.iterrows():
            row_text = ' | '.join([str(val) for val in row.values if val])
            if row_text:
                summary_parts.append(row_text)
        
        return '\n'.join(summary_parts)


# Singleton instance
_excel_parser = None

def get_excel_parser() -> ExcelParser:
    """Get or create Excel parser instance"""
    global _excel_parser
    if _excel_parser is None:
        _excel_parser = ExcelParser()
    return _excel_parser
