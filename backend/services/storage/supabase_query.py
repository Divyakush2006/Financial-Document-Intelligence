"""
Supabase-based statement query service
Replaces file-based storage with database queries for better performance
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseStatementQuery:
    """
    Query bank statements and transactions from Supabase.
    Optimized for Backboard AI service integration.
    """
    
    def __init__(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            logger.warning("Supabase not configured")
            self.enabled = False
            return
        
        try:
            self.client: Client = create_client(url, key)
            self.enabled = True
            logger.info("Supabase query service initialized")
        except Exception as e:
            logger.error(f"Supabase initialization failed: {e}")
            self.enabled = False
    
    def search_transactions(self, filters: Dict) -> List[Dict]:
        """
        Search transactions using the transactions table (MUCH faster!)
        
        Args:
            filters: Search criteria
                - account: Account number
                - date_from / date_to: Date range
                - description_contains: Search term
                - min_amount / max_amount: Amount range
                - transaction_type: 'credit' or 'debit'
                - payment_method: 'UPI', 'NEFT', etc.
        
        Returns:
            List of matching transactions
        """
        if not self.enabled:
            return []
        
        try:
            # Start with base query on transactions table
            query = self.client.table("transactions").select("*")
            
            # Apply filters at database level (FAST!)
            if filters.get('account'):
                query = query.eq("account_number", filters['account'])
            
            if filters.get('date_from'):
                query = query.gte("date", filters['date_from'])
            
            if filters.get('date_to'):
                query = query.lte("date", filters['date_to'])
            
            if filters.get('transaction_type'):
                query = query.eq("transaction_type", filters['transaction_type'])
            
            if filters.get('payment_method'):
                query = query.eq("payment_method", filters['payment_method'])
            
            # Execute query
            result = query.execute()
            transactions = result.data
            
            # Apply remaining filters in memory (for complex searches)
            if filters.get('description_contains'):
                search_term = filters['description_contains'].lower()
                transactions = [t for t in transactions 
                              if search_term in t.get('description', '').lower()]
            
            if filters.get('min_amount') is not None:
                min_amt = float(filters['min_amount'])
                transactions = [t for t in transactions 
                              if (t.get('debit', 0) >= min_amt or t.get('credit', 0) >= min_amt)]
            
            if filters.get('max_amount') is not None:
                max_amt = float(filters['max_amount'])
                transactions = [t for t in transactions 
                              if (t.get('debit', 0) <= max_amt or t.get('credit', 0) <= max_amt)]
            
            return transactions
            
        except Exception as e:
            logger.error(f"Transaction search failed: {e}")
            return []
    
    def get_account_summary(self, account_number: Optional[str] = None) -> Dict:
        """
        Get account summary from database
        
        Args:
            account_number: Specific account or None for all
        
        Returns:
            Summary dictionary
        """
        if not self.enabled:
            return {"total_accounts": 0, "accounts": [], "combined_balance": 0, "combined_credits": 0, "combined_debits": 0}
        
        try:
            query = self.client.table("bank_statements").select("*")
            
            if account_number:
                query = query.eq("account_number", account_number)
            
            result = query.execute()
            
            summaries = []
            total_balance = 0.0
            total_credits = 0.0
            total_debits = 0.0
            
            for row in result.data:
                data = row.get('data', {})
                
                summary = {
                    "account": row.get('account_number'),
                    "period_from": row.get('statement_period_from'),
                    "period_to": row.get('statement_period_to'),
                    "opening_balance": row.get('opening_balance', 0) or 0,
                    "closing_balance": row.get('closing_balance', 0) or 0,
                    "total_credits": data.get('total_credits', 0) or 0,
                    "total_debits": data.get('total_debits', 0) or 0,
                    "transaction_count": row.get('transaction_count', 0) or 0
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
            
        except Exception as e:
            logger.error(f"Account summary failed: {e}")
            return {"total_accounts": 0, "accounts": [], "combined_balance": 0, "combined_credits": 0, "combined_debits": 0, "error": str(e)}
    
    def get_analytics(self, analytics_type: str, filters: Optional[Dict] = None) -> Dict:
        """
        Get analytics using database queries
        
        Args:
            analytics_type: Type of analytics (balance, spending, income, summary)
            filters: Optional filters to apply
        
        Returns:
            Analytics dictionary
        """
        if not self.enabled:
            return {"error": "Supabase not enabled"}
        
        if analytics_type == "balance":
            return self.get_account_summary(filters.get('account') if filters else None)
        
        # For other analytics, get transactions and calculate
        transactions = self.search_transactions(filters or {})
        
        if analytics_type == "spending":
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
_query_service = None

def get_supabase_query() -> SupabaseStatementQuery:
    """Get or create Supabase query service"""
    global _query_service
    if _query_service is None:
        _query_service = SupabaseStatementQuery()
    return _query_service
