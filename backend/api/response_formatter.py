"""
Response Formatter Service
Standardizes API response format across all endpoints
Ensures consistent structure for frontend consumption
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Formats API responses with consistent structure
    Includes metadata, pagination, and performance metrics
    """
    
    @staticmethod
    def success_response(
        data: Any = None,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None,
        execution_time_ms: Optional[int] = None
    ) -> Dict:
        """
        Format successful API response
        
        Args:
            data: Response data
            message: Optional success message
            metadata: Optional metadata
            execution_time_ms: Optional execution time in milliseconds
            
        Returns:
            Standardized success response
        """
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if message:
            response["message"] = message
        
        if data is not None:
            response["data"] = data
        
        if metadata:
            response["metadata"] = metadata
        
        if execution_time_ms is not None:
            response["execution_time_ms"] = execution_time_ms
        
        return response
    
    @staticmethod
    def error_response(
        error_code: str,
        message: str,
        suggestion: Optional[str] = None,
        details: Optional[str] = None,
        status_code: int = 500
    ) -> tuple[Dict, int]:
        """
        Format error API response
        
        Args:
            error_code: Error code
            message: Error message
            suggestion: Optional suggestion for resolution
            details: Optional additional details
            status_code: HTTP status code
            
        Returns:
            Tuple of (error response dict, status code)
        """
        response = {
            "success": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": {
                "code": error_code,
                "message": message
            }
        }
        
        if suggestion:
            response["error"]["suggestion"] = suggestion
        
        if details:
            response["error"]["details"] = details
        
        return response, status_code
    
    @staticmethod
    def query_response(
        query: str,
        transactions: Optional[List[Dict]] = None,
        analytics: Optional[Dict] = None,
        message: Optional[str] = None,
        filters_used: Optional[Dict] = None,
        thread_id: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
        fallback_used: bool = False
    ) -> Dict:
        """
        Format query-specific response
        
        Args:
            query: Original query string
            transactions: List of matching transactions
            analytics: Analytics results
            message: Response message
            filters_used: Filters that were applied
            thread_id: Conversation thread ID
            execution_time_ms: Execution time
            fallback_used: Whether fallback method was used
            
        Returns:
            Formatted query response
        """
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": query
        }
        
        if message:
            response["message"] = message
        
        # Add transaction results if present
        if transactions is not None:
            count = len(transactions)
            response["count"] = count
            response["transactions"] = transactions
            
            # Calculate totals
            total_debits = sum(t.get('debit', 0) for t in transactions)
            total_credits = sum(t.get('credit', 0) for t in transactions)
            
            response["summary"] = {
                "total_transactions": count,
                "total_debits": round(total_debits, 2),
                "total_credits": round(total_credits, 2),
                "net_amount": round(total_credits - total_debits, 2)
            }
        
        # Add analytics if present
        if analytics:
            response["analytics"] = analytics
        
        # Add metadata
        metadata = {}
        
        if filters_used:
            metadata["filters_applied"] = filters_used
        
        if thread_id:
            metadata["thread_id"] = thread_id
        
        if fallback_used:
            metadata["ai_status"] = "fallback_used"
            metadata["note"] = "AI service unavailable, using keyword-based search"
        
        if execution_time_ms is not None:
            metadata["execution_time_ms"] = execution_time_ms
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    @staticmethod
    def paginated_response(
        items: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 50,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Format paginated response
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Items per page
            metadata: Optional additional metadata
            
        Returns:
            Paginated response
        """
        total_pages = (total + page_size - 1) // page_size
        
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
        
        if metadata:
            response["metadata"] = metadata
        
        return response
    
    @staticmethod
    def transaction_list_response(
        transactions: List[Dict],
        filters: Optional[Dict] = None,
        execution_time_ms: Optional[int] = None
    ) -> Dict:
        """
        Format transaction list response
        
        Args:
            transactions: List of transactions
            filters: Filters that were applied
            execution_time_ms: Execution time
            
        Returns:
            Formatted transaction list response
        """
        count = len(transactions)
        
        # Calculate summary statistics
        total_debits = sum(t.get('debit', 0) for t in transactions)
        total_credits = sum(t.get('credit', 0) for t in transactions)
        
        response = {
            "success": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "transactions": transactions,
            "count": count,
            "summary": {
                "total_debits": round(total_debits, 2),
                "total_credits": round(total_credits, 2),
                "net_amount": round(total_credits - total_debits, 2)
            }
        }
        
        metadata = {}
        if filters:
            metadata["filters_applied"] = filters
        if execution_time_ms is not None:
            metadata["execution_time_ms"] = execution_time_ms
        
        if metadata:
            response["metadata"] = metadata
        
        return response


# Singleton instance
_formatter = None

def get_response_formatter() -> ResponseFormatter:
    """Get or create response formatter instance"""
    global _formatter
    if _formatter is None:
        _formatter = ResponseFormatter()
    return _formatter
