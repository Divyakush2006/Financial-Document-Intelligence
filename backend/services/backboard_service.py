"""Backboard.io AI assistant service for conversational invoice queries"""

import os
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)


class BackboardService:
    """
    AI-powered conversational interface for querying invoices
    Uses Backboard.io for persistent memory and natural language understanding
    """
    
    def __init__(self):
        """Initialize Backboard client"""
        api_key = os.getenv("BACKBOARD_API_KEY")
        
        if not api_key:
            logger.warning("BACKBOARD_API_KEY not configured - chat endpoint will be disabled")
            self.enabled = False
            return
        
        try:
            from backboard.client import BackboardClient
            self.client = BackboardClient(api_key=api_key)
            self.enabled = True
            self.assistant_id = None
            logger.info("Backboard service initialized")
        except ImportError as e:
            logger.warning(f"backboard-sdk import failed: {e} - chat endpoint will be disabled")
            self.enabled = False
        except Exception as e:
            logger.error(f"Backboard initialization failed: {e}")
            self.enabled = False
    
    def get_or_create_assistant(self) -> str:
        """
        Get or create invoice assistant
        
        Returns:
            Assistant ID
        """
        if not self.enabled:
            return None
        
        if self.assistant_id:
            return self.assistant_id
        
        try:
            # Create assistant with invoice querying instructions
            assistant = self.client.assistants.create(
                name="Invoice Query Assistant",
                instructions="""
You are an intelligent invoice query assistant. You help users find and analyze invoice data.

When a user asks about invoices:
1. Extract search criteria from their query (vendor name, date range, amount range)
2. Return the filters in this JSON format:
{
  "filters": {
    "vendor": "vendor name or null",
    "date_from": "YYYY-MM-DD or null",
    "date_to": "YYYY-MM-DD or null",
    "min_amount": number or null,
    "max_amount": number or null,
    "search": "general search term or null"
  },
  "type": "list" or "analytics" or "specific"
}

Examples:
- "Show me Nike invoices" → {"filters": {"vendor": "Nike", ...}, "type": "list"}
- "Invoices over ₹50,000" → {"filters": {"min_amount": 50000, ...}, "type": "list"}
- "Total spent this month" → {"filters": {...}, "type": "analytics"}
- "Nike invoices from Jan 2024 over ₹10K" → {"filters": {"vendor": "Nike", "date_from": "2024-01-01", "date_to": "2024-01-31", "min_amount": 10000}, "type": "list"}

Be conversational and helpful. Remember context from previous messages.
                """,
                model="gpt-4o"
            )
            
            self.assistant_id = assistant.id
            logger.info(f"Created invoice assistant: {self.assistant_id}")
            return self.assistant_id
            
        except Exception as e:
            logger.error(f"Failed to create assistant: {e}")
            return None
    
    def extract_filters_from_query(self, message: str, thread_id: Optional[str] = None) -> Dict:
        """
        Use AI to extract search filters from natural language query
        
        Args:
            message: User's natural language query
            thread_id: Optional thread ID for context retention
            
        Returns:
            Dict with filters and query type
        """
        if not self.enabled:
            return {"error": "Backboard not configured", "filters": {}}
        
        try:
            assistant_id = self.get_or_create_assistant()
            if not assistant_id:
                return {"error": "Assistant creation failed", "filters": {}}
            
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
                
                # Try to parse JSON from response
                try:
                    # Look for JSON in response
                    import re
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        filters_data = json.loads(json_match.group())
                        filters_data["thread_id"] = thread.id
                        filters_data["ai_response"] = response
                        return filters_data
                except:
                    pass
                
                # Fallback: simple keyword extraction
                filters = self._fallback_filter_extraction(message)
                filters["thread_id"] = thread.id
                filters["ai_response"] = response
                return filters
            
            return {"error": "No response", "filters": {}}
            
        except Exception as e:
            logger.error(f"Filter extraction failed: {e}")
            # Fallback to simple keyword matching
            return self._fallback_filter_extraction(message)
    
    def _fallback_filter_extraction(self, message: str) -> Dict:
        """
        Fallback filter extraction using simple keyword matching
        
        Args:
            message: User query
            
        Returns:
            Basic filters dict
        """
        message_lower = message.lower()
        filters = {}
        
        # Check for vendor names (simple check)
        if "nike" in message_lower:
            filters["vendor"] = "Nike"
        elif "adidas" in message_lower:
            filters["vendor"] = "Adidas"
        
        # Check for amount keywords
        if "over" in message_lower or "above" in message_lower or ">" in message:
            # Try to extract number
            import re
            numbers = re.findall(r'₹?\s*(\d+(?:,\d+)*(?:k|K)?)', message)
            if numbers:
                amount = numbers[0].replace(',', '').replace('k', '000').replace('K', '000')
                filters["min_amount"] = float(amount)
        
        return {
            "filters": filters,
            "type": "list",
            "fallback": True
        }
    
    def format_response(self, message: str, invoices: List[Dict], query_type: str = "list") -> Dict:
        """
        Format invoice results with AI-generated natural language explanation
        
        Args:
            message: Original user query
            invoices: List of invoice dicts
            query_type: Type of query (list/analytics/specific)
            
        Returns:
            Formatted response with AI explanation
        """
        if not invoices:
            return {
                "message": "I couldn't find any invoices matching your query.",
                "invoices": [],
                "count": 0
            }
        
        # Calculate totals
        total_amount = sum(inv.get('total_amount', 0) or 0 for inv in invoices)
        count = len(invoices)
        
        # Generate natural language summary
        if query_type == "analytics":
            message_text = f"Total: ₹{total_amount:,.2f} across {count} invoice(s)"
        else:
            vendors = set(inv.get('vendor_name') for inv in invoices if inv.get('vendor_name'))
            if len(vendors) == 1:
                vendor = list(vendors)[0]
                message_text = f"I found {count} {vendor} invoice(s) totaling ₹{total_amount:,.2f}"
            else:
                message_text = f"I found {count} invoice(s) from {len(vendors)} vendor(s), totaling ₹{total_amount:,.2f}"
        
        return {
            "message": message_text,
            "invoices": invoices,
            "count": count,
            "total_amount": total_amount
        }


# Singleton instance
_backboard_service = None

def get_backboard_service() -> BackboardService:
    """Get or create Backboard service instance"""
    global _backboard_service
    if _backboard_service is None:
        _backboard_service = BackboardService()
    return _backboard_service
