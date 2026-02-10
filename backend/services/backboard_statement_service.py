"""
Backboard.io AI Service for Bank Statement Queries
Natural language interface for searching and analyzing bank statements
"""

import os
import logging
from typing import Dict, List, Optional
import json
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class BackboardStatementService:
    """
    AI-powered natural language interface for bank statement queries.
    Uses Backboard.io for intelligent filter extraction and context retention.
    """
    
    def __init__(self):
        """Initialize Backboard statement service"""
        api_key = os.getenv("BACKBOARD_API_KEY")
        
        if not api_key:
            logger.warning("BACKBOARD_API_KEY not configured - statement chat will be disabled")
            self.enabled = False
            return
        
        try:
            from backboard.client import BackboardClient
            from services.storage.supabase_query import get_supabase_query
            
            self.client = BackboardClient(api_key=api_key)
            self.store = get_supabase_query()  # Use Supabase instead of file-based
            self.enabled = self.store.enabled  # Only enabled if Supabase works
            self.assistant_id = None
            
            if self.enabled:
                logger.info("Backboard statement service initialized with Supabase")
            else:
                logger.warning("Supabase not available - service disabled")
        except ImportError as e:
            logger.warning(f"backboard-sdk import failed: {e}")
            self.enabled = False
        except Exception as e:
            logger.error(f"Backboard statement service initialization failed: {e}")
            self.enabled = False
    
    def get_or_create_assistant(self) -> str:
        """
        Get or create bank statement assistant.
        
        Returns:
            Assistant ID
        """
        if not self.enabled:
            return None
        
        if self.assistant_id:
            return self.assistant_id
        
        try:
            # Create assistant with bank statement query instructions
            assistant = self.client.assistants.create(
                name="Bank Statement Query Assistant",
                instructions="""
You are an intelligent bank statement query assistant. You help users search and analyze their bank transactions.

When a user asks about transactions, extract the search criteria and return JSON:

{
  "filters": {
    "account": "Account 1" through "Account 9" or null,
    "date_from": "YYYY-MM-DD or null",
    "date_to": "YYYY-MM-DD or null",
    "transaction_type": "credit" or "debit" or null,
    "description_contains": "search term or null",
    "min_amount": number or null,
    "max_amount": number or null,
    "payment_method": "UPI", "NEFT", "ATM", etc. or null
  },
  "analytics": "balance" or "spending" or "income" or "summary" or "top_merchants" or null
}

Examples:
- "Show Account 1 transactions" → {"filters": {"account": "Account 1"}}
- "All UPI payments over ₹5000" → {"filters": {"payment_method": "UPI", "min_amount": 5000}}
- "Dream11 payments from Account 1" → {"filters": {"account": "Account 1", "description_contains": "Dream11"}}
- "Total spending in May 2025" → {"filters": {"date_from": "2025-05-01", "date_to": "2025-05-31"}, "analytics": "spending"}
- "What's my balance?" → {"analytics": "balance"}
- "Top merchants I paid" → {"analytics": "top_merchants"}
- "NEFT transactions from April to June" → {"filters": {"payment_method": "NEFT", "date_from": "2025-04-01", "date_to": "2025-06-30"}}

Be conversational and remember context from previous questions.
                """,
                model="gpt-4o"
            )
            
            self.assistant_id = assistant.id
            logger.info(f"Created statement assistant: {self.assistant_id}")
            return self.assistant_id
            
        except Exception as e:
            logger.error(f"Failed to create assistant: {e}")
            return None
    
    def query(self, message: str, thread_id: Optional[str] = None, account_filter: Optional[str] = None) -> Dict:
        """
        Process natural language query for bank statements.
        
        Args:
            message: User's natural language query
            thread_id: Optional thread ID for context retention
            account_filter: Optional account to filter results to (for isolated querying)
        
        Returns:
            Response with transactions or analytics
        """
        if not self.enabled:
            return {
                "error": "Backboard not configured",
                "message": "Bank statement chat service is not available"
            }
        
        try:
            # Extract filters using AI
            filter_result = self._extract_filters(message, thread_id)
            
            filters = filter_result.get('filters', {})
            analytics_type = filter_result.get('analytics')
            used_thread_id = filter_result.get('thread_id')
            
            # CRITICAL: Apply account filter if provided (overrides AI-extracted account)
            if account_filter:
                filters['account'] = account_filter
            
            # Perform query
            if analytics_type:
                # Analytics query
                results = self.store.get_analytics(analytics_type, filters)
                response = self._format_analytics_response(message, results, analytics_type)
            else:
                # Transaction search
                transactions = self.store.search_transactions(filters)
                response = self._format_transaction_response(message, transactions, filters)
            
            # Add metadata
            response['thread_id'] = used_thread_id
            response['filters_used'] = filters
            response['analytics_type'] = analytics_type
            
            return response
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return {
                "error": str(e),
                "message": "Sorry, I encountered an error processing your query."
            }
    
    def _extract_filters(self, message: str, thread_id: Optional[str] = None) -> Dict:
        """
        Use AI to extract search filters from natural language.
        
        Args:
            message: User query
            thread_id: Optional thread for context
        
        Returns:
            Dict with filters and analytics type
        """
        try:
            assistant_id = self.get_or_create_assistant()
            if not assistant_id:
                return self._fallback_filter_extraction(message)
            
            # Create or use existing thread
            if thread_id:
                thread = self.client.threads.retrieve(thread_id)
            else:
                thread = self.client.threads.create()
            
            # Send message
            self.client.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            # Run assistant
            run = self.client.threads.runs.create(
                thread_id=thread.id,
                assistant_id=assistant_id
            )
            
            # Wait for completion
            while run.status in ["queued", "in_progress"]:
                run = self.client.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )
            
            # Get response
            messages = self.client.threads.messages.list(
                thread_id=thread.id,
                limit=1
            )
            
            if messages.data:
                response = messages.data[0].content[0].text.value
                
                # Parse JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    filter_data = json.loads(json_match.group())
                    filter_data['thread_id'] = thread.id
                    filter_data['ai_response'] = response
                    return filter_data
            
            # Fallback
            return self._fallback_filter_extraction(message)
            
        except Exception as e:
            logger.error(f"Filter extraction failed: {e}")
            return self._fallback_filter_extraction(message)
    
    def _fallback_filter_extraction(self, message: str) -> Dict:
        """
        Fallback filter extraction using keyword matching.
        
        Args:
            message: User query
        
        Returns:
            Basic filters dict
        """
        message_lower = message.lower()
        filters = {}
        
        # Account detection
        for i in range(1, 10):
            if f"account {i}" in message_lower:
                filters['account'] = f"Account {i}"
                break
        
        # Payment method detection
        if "upi" in message_lower:
            filters['payment_method'] = "UPI"
        elif "neft" in message_lower:
            filters['payment_method'] = "NEFT"
        elif "atm" in message_lower:
            filters['payment_method'] = "ATM"
        
        # Common merchant/description search
        merchants = ["dream11", "jio", "nike", "adidas", "airtel"]
        for merchant in merchants:
            if merchant in message_lower:
                filters['description_contains'] = merchant
                break
        
        # Amount extraction
        if "over" in message_lower or "above" in message_lower:
            numbers = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:k|K)?)', message)
            if numbers:
                amount = numbers[0].replace(',', '').replace('k', '000').replace('K', '000')
                filters['min_amount'] = float(amount)
        
        # Analytics type detection
        analytics = None
        if any(word in message_lower for word in ["balance", "total balance"]):
            analytics = "balance"
        elif any(word in message_lower for word in ["spending", "spent", "expense"]):
            analytics = "spending"
        elif any(word in message_lower for word in ["income", "earned", "credit"]):
            analytics = "income"
        elif "top merchant" in message_lower or "most paid" in message_lower:
            analytics = "top_merchants"
        elif "summary" in message_lower:
            analytics = "summary"
        
        return {
            "filters": filters,
            "analytics": analytics,
            "fallback": True
        }
    
    def _format_transaction_response(self, message: str, transactions: List[Dict], filters: Dict) -> Dict:
        """
        Format transaction search results.
        
        Args:
            message: Original query
            transactions: List of matching transactions
            filters: Applied filters
        
        Returns:
            Formatted response
        """
        if not transactions:
            return {
                "message": "I couldn't find any transactions matching your query.",
                "transactions": [],
                "count": 0,
                "total_amount": 0
            }
        
        # Calculate totals
        total_debits = sum(t.get('debit', 0) for t in transactions)
        total_credits = sum(t.get('credit', 0) for t in transactions)
        count = len(transactions)
        
        # Generate message
        if filters.get('description_contains'):
            subject = filters['description_contains']
            message_text = f"I found {count} {subject} transaction(s) totaling ₹{total_debits + total_credits:,.2f}"
        elif filters.get('account'):
            account = filters['account']
            message_text = f"I found {count} transaction(s) from {account}"
        elif filters.get('payment_method'):
            method = filters['payment_method']
            message_text = f"I found {count} {method} transaction(s) totaling ₹{total_debits + total_credits:,.2f}"
        else:
            message_text = f"I found {count} transaction(s)"
        
        return {
            "message": message_text,
            "transactions": transactions[:50],  # Limit to 50 for performance
            "count": count,
            "total_debits": total_debits,
            "total_credits": total_credits,
            "showing": min(count, 50)
        }
    
    def _format_analytics_response(self, message: str, results: Dict, analytics_type: str) -> Dict:
        """
        Format analytics results.
        
        Args:
            message: Original query
            results: Analytics results
            analytics_type: Type of analytics
        
        Returns:
            Formatted response
        """
        if analytics_type == "balance":
            accounts = results.get('accounts', [])
            combined = results.get('combined_balance', 0)
            message_text = f"Total balance across {len(accounts)} account(s): ₹{combined:,.2f}"
        
        elif analytics_type == "spending":
            total = results.get('total_spending', 0)
            count = results.get('transaction_count', 0)
            message_text = f"Total spending: ₹{total:,.2f} across {count} transactions"
        
        elif analytics_type == "income":
            total = results.get('total_income', 0)
            count = results.get('transaction_count', 0)
            message_text = f"Total income: ₹{total:,.2f} across {count} transactions"
        
        elif analytics_type == "top_merchants":
            merchants = results.get('top_merchants', [])
            if merchants:
                top = merchants[0]
                message_text = f"Top merchant: {top['merchant']} (₹{top['total_spent']:,.2f})"
            else:
                message_text = "No merchant data available"
        
        elif analytics_type == "summary":
            credits = results.get('total_credits', 0)
            debits = results.get('total_debits', 0)
            count = results.get('total_transactions', 0)
            message_text = f"Summary: {count} transactions | Income: ₹{credits:,.2f} | Spending: ₹{debits:,.2f}"
        
        else:
            message_text = "Analytics results retrieved"
        
        return {
            "message": message_text,
            "analytics": results
        }


# Singleton instance
_statement_service = None

def get_statement_service() -> BackboardStatementService:
    """Get or create Backboard statement service instance"""
    global _statement_service
    if _statement_service is None:
        _statement_service = BackboardStatementService()
    return _statement_service
