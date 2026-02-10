"""Chat API routes for natural language queries"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    thread_id: Optional[str] = None


@router.get("/status")
async def chat_status():
    """Check if chat endpoint is enabled"""
    try:
        from services.backboard_service import get_backboard_service
        from services.backboard_statement_service import get_statement_service
        
        invoice_service = get_backboard_service()
        statement_service = get_statement_service()
        
        return {
            "enabled": invoice_service.enabled or statement_service.enabled,
            "invoice_chat": invoice_service.enabled,
            "statement_chat": statement_service.enabled,
            "message": "Chat services available"
        }
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return {
            "enabled": False,
            "message": str(e)
        }


@router.post("/statements")
async def chat_statements(request: ChatRequest):
    """
    Natural language query for bank statements.
    
    Examples:
    - "Show me all Dream11 payments"
    - "UPI transactions over ₹5000 from Account 1"
    - "What's my total spending in May?"
    - "Find NEFT transactions from April to June"
    """
    try:
        from services.backboard_statement_service import get_statement_service
        
        service = get_statement_service()
        
        if not service.enabled:
            raise HTTPException(status_code=503, detail="Statement chat not configured")
        
        result = service.query(request.message, request.thread_id)
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Statement chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
