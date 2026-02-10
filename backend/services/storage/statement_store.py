"""
Bank Statement Storage and Query Service
Loads and searches extracted bank statement JSON files
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class StatementStore:
    """
    Storage and query service for bank statements.
    Loads extracted JSON files and provides search/analytics capabilities.
    """
    
    def __init__(self, data_dir: str = "extraction_results_direct"):
        """
        Initialize statement store.
        
        Args:
            data_dir: Directory containing extracted statement JSON files
        """
        self.data_dir = Path(data_dir)
        self.statements: List[Dict] = []
        self.all_transactions: List[Dict] = []
        
        # Load all statements
        self._load_all_statements()
        
        logger.info(f"Statement store initialized: {len(self.statements)} accounts, {len(self.all_transactions)} transactions")
    
    def _load_all_statements(self):
        """Load all statement JSON files from directory"""
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return
        
        # Find all result JSON files (exclude summary)
        json_files = [f for f in self.data_dir.glob("*_result.json") if "summary" not in f.name]
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    result = json.load(f)
                
                # Only load successful extractions
                if result.get('success'):
                    statement_data = result.get('data', {})
                    
                    # Add source info
                    statement_data['source_file'] = result.get('file')
                    statement_data['account_name'] = self._extract_account_name(result.get('file'))
                    
                    self.statements.append(statement_data)
                    
                    # Add all transactions with account reference
                    for txn in statement_data.get('transactions', []):
                        txn['account'] = statement_data['account_name']
                        txn['source_file'] = statement_data['source_file']
                        self.all_transactions.append(txn)
                
            except Exception as e:
                logger.error(f"Failed to load {json_file.name}: {e}")
        
        logger.info(f"Loaded {len(self.statements)} statements with {len(self.all_transactions)} total transactions")
    
    def _extract_account_name(self, filename: str) -> str:
        """Extract account name from filename (e.g., 'Account 1.xlsx' -> 'Account 1')"""
        if not filename:
            return "Unknown"
        
        # Remove extension
        name = Path(filename).stem
        return name
    
    def search_transactions(self, filters: Dict) -> List[Dict]:
        """
        Search transactions with filters.
        
        Args:
            filters: Dictionary of search criteria
                - account: Account name (e.g., "Account 1")
                - date_from: Start date (YYYY-MM-DD)
                - date_to: End date (YYYY-MM-DD)
                - transaction_type: "credit" or "debit"
                - description_contains: Search term in description
                - min_amount: Minimum amount
                - max_amount: Maximum amount
                - payment_method: "UPI", "NEFT", "ATM", etc.
        
        Returns:
            List of matching transactions
        """
        results = self.all_transactions.copy()
        
        # Apply account filter
        if filters.get('account'):
            account = filters['account']
            results = [t for t in results if t.get('account', '').lower() == account.lower()]
        
        # Apply date range filter
        if filters.get('date_from'):
            date_from = filters['date_from']
            results = [t for t in results if t.get('date', '') >= date_from]
        
        if filters.get('date_to'):
            date_to = filters['date_to']
            results = [t for t in results if t.get('date', '') <= date_to]
        
        # Apply transaction type filter
        if filters.get('transaction_type'):
            txn_type = filters['transaction_type'].lower()
            if txn_type in ['credit', 'debit']:
                results = [t for t in results if t.get('transaction_type', '').lower() == txn_type]
        
        # Apply description search
        if filters.get('description_contains'):
            search_term = filters['description_contains'].lower()
            results = [t for t in results if search_term in t.get('description', '').lower()]
        
        # Apply amount range filters
        if filters.get('min_amount') is not None:
            min_amt = float(filters['min_amount'])
            results = [t for t in results 
                      if (t.get('debit', 0) >= min_amt or t.get('credit', 0) >= min_amt)]
        
        if filters.get('max_amount') is not None:
            max_amt = float(filters['max_amount'])
            results = [t for t in results 
                      if (t.get('debit', 0) <= max_amt or t.get('credit', 0) <= max_amt)]
        
        # Apply payment method filter (UPI, NEFT, ATM, etc.)
        if filters.get('payment_method'):
            method = filters['payment_method'].upper()
            results = [t for t in results if method in t.get('description', '').upper()]
        
        return results
    
    def get_account_summary(self, account_name: Optional[str] = None) -> Dict:
        """
        Get summary for specific account or all accounts.
        
        Args:
            account_name: Account name or None for all accounts
        
        Returns:
            Summary dictionary with balances and totals
        """
        if account_name:
            # Get specific account
            statements = [s for s in self.statements if s.get('account_name', '').lower() == account_name.lower()]
        else:
            # All accounts
            statements = self.statements
        
        if not statements:
            return {"error": "Account not found", "accounts": []}
        
        summaries = []
        total_balance = 0.0
        total_credits = 0.0
        total_debits = 0.0
        
        for stmt in statements:
            summary = {
                "account": stmt.get('account_name'),
                "period_from": stmt.get('statement_period_from'),
                "period_to": stmt.get('statement_period_to'),
                "opening_balance": stmt.get('opening_balance', 0),
                "closing_balance": stmt.get('closing_balance', 0),
                "total_credits": stmt.get('total_credits', 0),
                "total_debits": stmt.get('total_debits', 0),
                "transaction_count": stmt.get('number_of_transactions', 0)
            }
            
            summaries.append(summary)
            total_balance += summary['closing_balance']
            total_credits += summary['total_credits']
            total_debits += summary['total_debits']
        
        return {
            "accounts": summaries,
            "total_accounts": len(summaries),
            "combined_balance": total_balance,
            "combined_credits": total_credits,
            "combined_debits": total_debits
        }
    
    def get_analytics(self, analytics_type: str, filters: Optional[Dict] = None) -> Dict:
        """
        Get analytics based on query type.
        
        Args:
            analytics_type: Type of analytics
                - "balance": Get balance summary
                - "spending": Total debits (expenses)
                - "income": Total credits
                - "summary": Complete overview
                - "top_merchants": Most frequent vendors
            filters: Optional filters to apply before analytics
        
        Returns:
            Analytics dictionary
        """
        # Apply filters if provided
        if filters:
            transactions = self.search_transactions(filters)
        else:
            transactions = self.all_transactions
        
        if analytics_type == "balance":
            return self.get_account_summary(filters.get('account') if filters else None)
        
        elif analytics_type == "spending":
            total_debits = sum(t.get('debit', 0) for t in transactions)
            return {
                "total_spending": total_debits,
                "transaction_count": len([t for t in transactions if t.get('debit', 0) > 0]),
                "average_transaction": total_debits / len(transactions) if transactions else 0
            }
        
        elif analytics_type == "income":
            total_credits = sum(t.get('credit', 0) for t in transactions)
            return {
                "total_income": total_credits,
                "transaction_count": len([t for t in transactions if t.get('credit', 0) > 0]),
                "average_transaction": total_credits / len(transactions) if transactions else 0
            }
        
        elif analytics_type == "top_merchants":
            # Extract merchant names from descriptions
            merchant_spending = {}
            
            for t in transactions:
                desc = t.get('description', '')
                amount = t.get('debit', 0)
                
                if amount > 0:
                    # Try to extract merchant name (between slashes in UPI)
                    match = re.search(r'/([^/]+)/(?:Paymen|collec)', desc)
                    if match:
                        merchant = match.group(1).strip()
                        merchant_spending[merchant] = merchant_spending.get(merchant, 0) + amount
            
            # Sort by spending
            top_merchants = sorted(merchant_spending.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                "top_merchants": [
                    {"merchant": name, "total_spent": amount}
                    for name, amount in top_merchants
                ],
                "unique_merchants": len(merchant_spending)
            }
        
        elif analytics_type == "summary":
            total_credits = sum(t.get('credit', 0) for t in transactions)
            total_debits = sum(t.get('debit', 0) for t in transactions)
            
            return {
                "total_transactions": len(transactions),
                "total_credits": total_credits,
                "total_debits": total_debits,
                "net_change": total_credits - total_debits,
                "credit_count": len([t for t in transactions if t.get('credit', 0) > 0]),
                "debit_count": len([t for t in transactions if t.get('debit', 0) > 0])
            }
        
        return {"error": "Unknown analytics type"}


# Singleton instance
_statement_store = None

def get_statement_store() -> StatementStore:
    """Get or create statement store instance"""
    global _statement_store
    if _statement_store is None:
        _statement_store = StatementStore()
    return _statement_store
