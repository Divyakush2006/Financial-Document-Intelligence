"""Supabase-based invoice storage (persistent database)"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, date
import os
import logging
from supabase import create_client, Client

# Invoice models disabled - Bank statements only
# from api.models import Invoice, InvoiceData, InvoiceMetadata, InvoiceSummary
import uuid

logger = logging.getLogger(__name__)


class SupabaseInvoiceStore:
    """Persistent invoice storage using Supabase PostgreSQL"""
    
    def __init__(self):
        """Initialize Supabase client"""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        
        self.client: Client = create_client(url, key)
        logger.info("Supabase invoice store initialized")
    
    def generate_id(self) -> str:
        """Generate unique invoice ID"""
        return f"inv_{uuid.uuid4().hex[:12]}"
    
    def create(self, data: InvoiceData, metadata: InvoiceMetadata, image_url: Optional[str] = None, cloudinary_id: Optional[str] = None) -> Invoice:
        """
        Create new invoice record in database
        
        Args:
            data: Extracted invoice data
            metadata: Extraction metadata
            image_url: Optional Cloudinary image URL
            cloudinary_id: Optional Cloudinary public ID
            
        Returns:
            Created invoice with ID
        """
        invoice_id = self.generate_id()
        
        # Prepare database record
        record = {
            "invoice_id": invoice_id,
            "invoice_number": data.invoice_number,
            "vendor_name": data.vendor_name,
            "customer_name": data.customer_name,
            "date": data.date,
            "total_amount": float(data.total_amount) if data.total_amount else None,
            "currency": data.currency if data.currency else "INR",  # Default to INR
            "image_url": image_url,
            "cloudinary_id": cloudinary_id,
            "data": data.model_dump(mode='json'),
            "metadata": metadata.model_dump(mode='json')
        }
        
        # Insert into database
        result = self.client.table("invoices").insert(record).execute()
        
        if not result.data:
            raise Exception("Failed to create invoice in database")
        
        logger.info(f"Created invoice in database: {invoice_id}")
        
        # Return Invoice model
        return Invoice(
            invoice_id=invoice_id,
            data=data,
            metadata=metadata,
            image_url=image_url,
            cloudinary_id=cloudinary_id,
            created_at=datetime.utcnow()
        )
    
    def get(self, invoice_id: str) -> Optional[Invoice]:
        """
        Get invoice by ID
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Invoice or None if not found
        """
        result = self.client.table("invoices").select("*").eq("invoice_id", invoice_id).execute()
        
        if not result.data or len(result.data) == 0:
            return None
        
        row = result.data[0]
        
        return Invoice(
            invoice_id=row["invoice_id"],
            data=InvoiceData(**row["data"]),
            metadata=InvoiceMetadata(**row["metadata"]),
            image_url=row.get("image_url"),
            cloudinary_id=row.get("cloudinary_id"),
            created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        )
    
    def list(
        self, 
        limit: int = 50, 
        offset: int = 0,
        sort: str = "date_desc",
        filters: Optional[Dict] = None
    ) -> Tuple[List[InvoiceSummary], int]:
        """
        List invoices with pagination and filters
        
        Args:
            limit: Max invoices to return
            offset: Number to skip
            sort: Sort order (date_desc, date_asc, amount_desc, amount_asc)
            filters: Optional filters (search, vendor, date_from, date_to, etc.)
            
        Returns:
            Tuple of (invoice_summaries, total_count)
        """
        # Build query
        query = self.client.table("invoices").select("*", count="exact")
        
        # Apply filters
        if filters:
            if filters.get("search"):
                search_term = filters["search"]
                query = query.or_(f"vendor_name.ilike.%{search_term}%,customer_name.ilike.%{search_term}%,invoice_number.ilike.%{search_term}%")
            
            if filters.get("vendor"):
                query = query.eq("vendor_name", filters["vendor"])
            
            if filters.get("date_from"):
                query = query.gte("date", filters["date_from"])
            
            if filters.get("date_to"):
                query = query.lte("date", filters["date_to"])
            
            if filters.get("min_amount"):
                query = query.gte("total_amount", filters["min_amount"])
            
            if filters.get("max_amount"):
                query = query.lte("total_amount", filters["max_amount"])
        
        # Apply sorting
        if sort == "date_desc":
            query = query.order("date", desc=True)
        elif sort == "date_asc":
            query = query.order("date", desc=False)
        elif sort == "amount_desc":
            query = query.order("total_amount", desc=True)
        elif sort == "amount_asc":
            query = query.order("total_amount", desc=False)
        else:
            query = query.order("created_at", desc=True)
        
        # Apply pagination
        query = query.range(offset, offset + limit - 1)
        
        # Execute query
        result = query.execute()
        
        total = result.count if result.count else 0
        
        # Convert to summaries
        summaries = [
            InvoiceSummary(
                invoice_id=row["invoice_id"],
                invoice_number=row["invoice_number"],
                vendor_name=row["vendor_name"],
                date=row["date"],
                total_amount=row["total_amount"],
                image_url=row.get("image_url"),
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            )
            for row in result.data
        ]
        
        return summaries, total
    
    def search(self, query: str) -> List[InvoiceSummary]:
        """
        Full-text search on invoices
        
        Args:
            query: Search query
            
        Returns:
            List of matching invoice summaries
        """
        result = self.client.table("invoices").select("*").or_(
            f"vendor_name.ilike.%{query}%,customer_name.ilike.%{query}%,invoice_number.ilike.%{query}%"
        ).execute()
        
        return [
            InvoiceSummary(
                invoice_id=row["invoice_id"],
                invoice_number=row["invoice_number"],
                vendor_name=row["vendor_name"],
                date=row["date"],
                total_amount=row["total_amount"],
                created_at=datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
            )
            for row in result.data
        ]
    
    def delete(self, invoice_id: str) -> bool:
        """
        Delete invoice by ID
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            True if deleted, False if not found
        """
        result = self.client.table("invoices").delete().eq("invoice_id", invoice_id).execute()
        
        if result.data and len(result.data) > 0:
            logger.info(f"Deleted invoice: {invoice_id}")
            return True
        
        return False
    
    def count(self) -> int:
        """Get total invoice count"""
        result = self.client.table("invoices").select("*", count="exact").execute()
        return result.count if result.count else 0


# Singleton instance
_supabase_store = None

def get_supabase_store() -> SupabaseInvoiceStore:
    """Get or create Supabase store instance"""
    global _supabase_store
    if _supabase_store is None:
        _supabase_store = SupabaseInvoiceStore()
    return _supabase_store
