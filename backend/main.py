"""
Financial Document Intelligence API
Main FastAPI application with invoice extraction endpoints
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv

# Invoice processing disabled - Bank statements only
# from api.routes import invoice_router
from api.routes.chat_routes import router as chat_router
from api.routes.statement_routes import router as statement_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Financial Document Intelligence API",
    description="AI-powered invoice extraction and validation system with Azure OCR + Groq LLM",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.routes.upload_routes import router as upload_router

app.include_router(chat_router, prefix="/api")
app.include_router(upload_router)  # Statement upload and processing
app.include_router(statement_router)  # Legacy bank statements via /api/invoices


@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "online",
        "service": "Bank Statement Intelligence API",
        "version": "3.0.0",
        "docs": "/docs",
        "description": "AI-powered bank statement analysis with Excel upload and natural language queries",
        "endpoints": {
            "upload": "POST /api/statements/upload",
            "list_statements": "GET /api/statements/",
            "get_statement": "GET /api/statements/{id}",
            "query_ai": "POST /api/statements/query",
            "search_transactions": "GET /api/statements/transactions/search",
            "analytics": "GET /api/statements/analytics/summary",
            "chat": "POST /api/chat/statements"
        },
        "workflow": "Upload Excel → Auto-parse → Store in DB → Query with AI"
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "excel_parser": "openpyxl (structured data extraction)",
            "llm": "Groq Llama 3.3 70B",
            "validators": "Balance + Date validation",
            "storage": "Supabase (PostgreSQL)"
        },
        "supported_formats": [".xlsx", ".xls"]
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Financial Document Intelligence API...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
