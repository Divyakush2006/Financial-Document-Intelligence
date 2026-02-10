"""
Centralized Error Code Definitions
Provides consistent error handling across the Financial Document Intelligence API
"""

from enum import Enum
from typing import Dict, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for API responses"""
    
    # Query Validation Errors (1000-1099)
    QUERY_EMPTY = "QUERY_1000"
    QUERY_TOO_LONG = "QUERY_1001"
    QUERY_INVALID_CHARACTERS = "QUERY_1002"
    QUERY_INJECTION_DETECTED = "QUERY_1003"
    QUERY_RATE_LIMIT = "QUERY_1004"
    
    # Data Errors (2000-2099)
    NO_DATA_AVAILABLE = "DATA_2000"
    NO_STATEMENTS_UPLOADED = "DATA_2001"
    NO_TRANSACTIONS_FOUND = "DATA_2002"
    INVALID_ACCOUNT_NUMBER = "DATA_2003"
    INVALID_DATE_RANGE = "DATA_2004"
    
    # Service Errors (3000-3099)
    AI_SERVICE_UNAVAILABLE = "SERVICE_3000"
    DATABASE_CONNECTION_FAILED = "SERVICE_3001"
    DATABASE_QUERY_FAILED = "SERVICE_3002"
    BACKBOARD_API_ERROR = "SERVICE_3003"
    TIMEOUT_ERROR = "SERVICE_3004"
    
    # Authentication/Authorization Errors (4000-4099)
    UNAUTHORIZED = "AUTH_4000"
    FORBIDDEN = "AUTH_4001"
    INVALID_API_KEY = "AUTH_4002"
    
    # Internal Errors (5000-5099)
    INTERNAL_SERVER_ERROR = "INTERNAL_5000"
    CONFIGURATION_ERROR = "INTERNAL_5001"
    UNEXPECTED_ERROR = "INTERNAL_5002"
    
    # File Upload Errors (6000-6099)
    INVALID_FILE_FORMAT = "FILE_6000"
    FILE_TOO_LARGE = "FILE_6001"
    UPLOAD_FAILED = "FILE_6002"


class ErrorMessage:
    """User-friendly error messages and suggested actions"""
    
    MESSAGES: Dict[ErrorCode, Dict[str, str]] = {
        # Query Validation Errors
        ErrorCode.QUERY_EMPTY: {
            "message": "Query cannot be empty",
            "suggestion": "Please enter a question about your bank statements (e.g., 'What is my balance?')",
            "status_code": 400
        },
        ErrorCode.QUERY_TOO_LONG: {
            "message": "Query is too long",
            "suggestion": "Please shorten your query to less than 500 characters",
            "status_code": 400
        },
        ErrorCode.QUERY_INVALID_CHARACTERS: {
            "message": "Query contains invalid characters",
            "suggestion": "Please remove special characters and try again",
            "status_code": 400
        },
        ErrorCode.QUERY_INJECTION_DETECTED: {
            "message": "Query contains potentially harmful content",
            "suggestion": "Please rephrase your query using natural language",
            "status_code": 400
        },
        ErrorCode.QUERY_RATE_LIMIT: {
            "message": "Too many queries in a short time",
            "suggestion": "Please wait a moment before trying again",
            "status_code": 429
        },
        
        # Data Errors
        ErrorCode.NO_DATA_AVAILABLE: {
            "message": "No data available for this query",
            "suggestion": "Please upload a bank statement first",
            "status_code": 404
        },
        ErrorCode.NO_STATEMENTS_UPLOADED: {
            "message": "No bank statements have been uploaded yet",
            "suggestion": "Upload an Excel bank statement to start querying your data",
            "status_code": 404
        },
        ErrorCode.NO_TRANSACTIONS_FOUND: {
            "message": "No transactions match your query",
            "suggestion": "Try a broader search or check your filters",
            "status_code": 404
        },
        ErrorCode.INVALID_ACCOUNT_NUMBER: {
            "message": "Invalid account number",
            "suggestion": "Please check the account number and try again",
            "status_code": 400
        },
        ErrorCode.INVALID_DATE_RANGE: {
            "message": "Invalid date range",
            "suggestion": "Ensure 'from' date is before 'to' date",
            "status_code": 400
        },
        
        # Service Errors
        ErrorCode.AI_SERVICE_UNAVAILABLE: {
            "message": "AI query service is temporarily unavailable",
            "suggestion": "Using fallback search. Results may be less accurate",
            "status_code": 503
        },
        ErrorCode.DATABASE_CONNECTION_FAILED: {
            "message": "Database connection failed",
            "suggestion": "Please try again in a moment. Contact support if issue persists",
            "status_code": 503
        },
        ErrorCode.DATABASE_QUERY_FAILED: {
            "message": "Failed to retrieve data from database",
            "suggestion": "Please try again or contact support",
            "status_code": 500
        },
        ErrorCode.BACKBOARD_API_ERROR: {
            "message": "AI processing service encountered an error",
            "suggestion": "Using fallback search method",
            "status_code": 503
        },
        ErrorCode.TIMEOUT_ERROR: {
            "message": "Query took too long to process",
            "suggestion": "Try a simpler query or narrow your search criteria",
            "status_code": 504
        },
        
        # Authentication/Authorization Errors
        ErrorCode.UNAUTHORIZED: {
            "message": "Authentication required",
            "suggestion": "Please log in to continue",
            "status_code": 401
        },
        ErrorCode.FORBIDDEN: {
            "message": "Access denied",
            "suggestion": "You don't have permission to access this resource",
            "status_code": 403
        },
        ErrorCode.INVALID_API_KEY: {
            "message": "Invalid API key",
            "suggestion": "Check your API configuration",
            "status_code": 401
        },
        
        # Internal Errors
        ErrorCode.INTERNAL_SERVER_ERROR: {
            "message": "An unexpected error occurred",
            "suggestion": "Please try again. Contact support if issue persists",
            "status_code": 500
        },
        ErrorCode.CONFIGURATION_ERROR: {
            "message": "System configuration error",
            "suggestion": "Please contact support",
            "status_code": 500
        },
        ErrorCode.UNEXPECTED_ERROR: {
            "message": "An unexpected error occurred",
            "suggestion": "Please try again later",
            "status_code": 500
        },
        
        # File Upload Errors
        ErrorCode.INVALID_FILE_FORMAT: {
            "message": "Invalid file format",
            "suggestion": "Please upload an Excel file (.xlsx or .xls)",
            "status_code": 400
        },
        ErrorCode.FILE_TOO_LARGE: {
            "message": "File is too large",
            "suggestion": "Please upload a file smaller than 10MB",
            "status_code": 413
        },
        ErrorCode.UPLOAD_FAILED: {
            "message": "File upload failed",
            "suggestion": "Please try uploading again",
            "status_code": 500
        }
    }
    
    @classmethod
    def get_error_response(cls, error_code: ErrorCode, details: Optional[str] = None) -> Dict:
        """
        Get standardized error response
        
        Args:
            error_code: Error code from ErrorCode enum
            details: Optional additional details
            
        Returns:
            Standardized error response dictionary
        """
        error_info = cls.MESSAGES.get(error_code, {
            "message": "An error occurred",
            "suggestion": "Please try again",
            "status_code": 500
        })
        
        response = {
            "success": False,
            "error": {
                "code": error_code.value,
                "message": error_info["message"],
                "suggestion": error_info["suggestion"]
            }
        }
        
        if details:
            response["error"]["details"] = details
        
        return response, error_info["status_code"]
    
    @classmethod
    def get_status_code(cls, error_code: ErrorCode) -> int:
        """Get HTTP status code for error"""
        return cls.MESSAGES.get(error_code, {}).get("status_code", 500)
