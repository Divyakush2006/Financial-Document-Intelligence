"""
Query Validator Service
Validates and sanitizes user queries before processing
Prevents injection attacks and enforces business rules
"""

import re
import logging
from typing import Dict, Optional, Tuple
from api.error_codes import ErrorCode, ErrorMessage

logger = logging.getLogger(__name__)


class QueryValidator:
    """
    Validates and sanitizes user queries
    Enforces security and business rules
    """
    
    # Configuration
    MAX_QUERY_LENGTH = 500
    MIN_QUERY_LENGTH = 1
    
    # Patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE)\b",  # DDL/DML commands
        r"(--|#|/\*|\*/)",  # SQL comments
        r"\bUNION\b.*\bSELECT\b",  # UNION attacks
        r"\b(EXEC|EXECUTE)\b",  # Execution commands
        r";\s*\b(SELECT|DROP|DELETE|UPDATE|INSERT)\b",  # Chained queries
        r"^\s*SELECT\b",  # SELECT at start (likely SQL query, not natural language)
        r"\bFROM\s+(bank_statements|transactions|users|statements)\b",  # Table references
        r"\b(OR|AND)\s+['\"]*\d+['\"]*\s*=\s*['\"]*\d+['\"]*",  # OR 1=1, AND 1=1 patterns
    ]
    
    XSS_PATTERNS = [
        r"<script[\s>]",  # Script tags (opening)
        r"</script>",  # Script tags (closing)
        r"javascript\s*:",  # JavaScript protocol
        r"on\w+\s*=",  # Event handlers
        r"<iframe[\s>]",  # Iframe tags
    ]
    
    # Allowed special characters for natural language queries
    ALLOWED_SPECIAL_CHARS = set("?,.'!₹$€£¥-/()[]{}@#%&*+=:;\"")
    
    def __init__(self):
        """Initialize query validator"""
        self.sql_pattern = re.compile(
            '|'.join(self.SQL_INJECTION_PATTERNS),
            re.IGNORECASE
        )
        self.xss_pattern = re.compile(
            '|'.join(self.XSS_PATTERNS),
            re.IGNORECASE
        )
    
    def validate(self, query: str) -> Tuple[bool, Optional[ErrorCode], Optional[str]]:
        """
        Validate query against all rules
        
        Args:
            query: User query string
            
        Returns:
            Tuple of (is_valid, error_code, error_details)
        """
        # Check if query is empty or None
        if not query or not query.strip():
            return False, ErrorCode.QUERY_EMPTY, "Query is empty"
        
        query = query.strip()
        
        # Check length
        if len(query) < self.MIN_QUERY_LENGTH:
            return False, ErrorCode.QUERY_EMPTY, "Query is too short"
        
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, ErrorCode.QUERY_TOO_LONG, f"Query exceeds {self.MAX_QUERY_LENGTH} characters"
        
        # Check for SQL injection
        if self.sql_pattern.search(query):
            logger.warning(f"SQL injection attempt detected: {query[:100]}")
            return False, ErrorCode.QUERY_INJECTION_DETECTED, "Potential SQL injection detected"
        
        # Check for XSS
        if self.xss_pattern.search(query):
            logger.warning(f"XSS attempt detected: {query[:100]}")
            return False, ErrorCode.QUERY_INJECTION_DETECTED, "Potential XSS detected"
        
        # Check for excessive special characters
        special_char_count = sum(1 for c in query if not c.isalnum() and not c.isspace() and c not in self.ALLOWED_SPECIAL_CHARS)
        if special_char_count > 10:
            return False, ErrorCode.QUERY_INVALID_CHARACTERS, "Too many invalid special characters"
        
        return True, None, None
    
    def sanitize(self, query: str) -> str:
        """
        Sanitize query string
        
        Args:
            query: User query string
            
        Returns:
            Sanitized query string
        """
        if not query:
            return ""
        
        # Trim whitespace
        query = query.strip()
        
        # Remove null bytes
        query = query.replace('\x00', '')
        
        # Normalize whitespace
        query = ' '.join(query.split())
        
        # Remove any HTML tags
        query = re.sub(r'<[^>]+>', '', query)
        
        # Limit consecutive special characters
        query = re.sub(r'([^\w\s₹$€£¥])\1{2,}', r'\1\1', query)
        
        return query
    
    def validate_and_sanitize(self, query: str) -> Dict:
        """
        Validate and sanitize query in one step
        
        Args:
            query: User query string
            
        Returns:
            Dict with validation result and sanitized query
        """
        # Check for XSS BEFORE sanitization (since sanitize removes HTML)
        if not query:
            query_to_check = ""
        else:
            query_to_check = query.strip()
        
        # Check XSS first on unsanitized input
        if self.xss_pattern.search(query_to_check):
            logger.warning(f"XSS attempt detected: {query_to_check[:100]}")
            error_response, status_code = ErrorMessage.get_error_response(
                ErrorCode.QUERY_INJECTION_DETECTED,
                "Potential XSS detected"
            )
            return {
                "valid": False,
                "query": None,
                "error": error_response["error"],
                "status_code": status_code
            }
        
        # Then sanitize
        sanitized_query = self.sanitize(query)
        
        # Then validate (sanitized version)
        is_valid, error_code, error_details = self.validate(sanitized_query)
        
        if not is_valid:
            error_response, status_code = ErrorMessage.get_error_response(
                error_code,
                error_details
            )
            return {
                "valid": False,
                "query": None,
                "error": error_response["error"],
                "status_code": status_code
            }
        
        return {
            "valid": True,
            "query": sanitized_query,
            "error": None,
            "status_code": 200
        }
    
    def check_rate_limit(self, user_id: Optional[str] = None, max_queries: int = 100, window_minutes: int = 1) -> bool:
        """
        Check if user has exceeded rate limit
        Note: This is a placeholder for future implementation with Redis/cache
        
        Args:
            user_id: User identifier
            max_queries: Maximum queries allowed in time window
            window_minutes: Time window in minutes
            
        Returns:
            True if within rate limit, False if exceeded
        """
        # TODO: Implement with Redis or in-memory cache
        # For now, always return True (no rate limiting)
        return True


# Singleton instance
_validator = None

def get_query_validator() -> QueryValidator:
    """Get or create query validator instance"""
    global _validator
    if _validator is None:
        _validator = QueryValidator()
    return _validator
