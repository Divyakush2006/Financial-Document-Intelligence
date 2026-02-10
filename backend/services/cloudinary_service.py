"""Cloudinary cloud storage service for invoice images"""

import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class CloudinaryService:
    """
    Service for uploading and managing document files in Cloudinary
    """
    
    def __init__(self):
        """Initialize Cloudinary with credentials from environment"""
        # Ensure .env is loaded
        load_dotenv()
        
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")
        
        if not all([cloud_name, api_key, api_secret]):
            logger.warning("Cloudinary credentials not configured - image upload will be skipped")
            self.enabled = False
            return
        
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )
        
        self.enabled = True
        logger.info("Cloudinary service initialized")
    
    def upload_file(self, file_path: str, document_id: str, folder: str = "bank_statements") -> Optional[Dict[str, str]]:
        """
        Upload document file to Cloudinary
        
        Args:
            file_path: Local path to document file
            document_id: Unique document ID (used as public_id)
            folder: Cloudinary folder (default: "bank_statements")
            
        Returns:
            Dict with url, public_id, format or None if disabled
        """
        if not self.enabled:
            logger.debug("Cloudinary disabled - skipping upload")
            return None
        
        try:
            logger.info(f"Uploading document {document_id} to Cloudinary...")
            
            result = cloudinary.uploader.upload(
                file_path,
                folder=folder,
                public_id=document_id,
                resource_type="auto",
                overwrite=True,
                invalidate=True,  # Clear CDN cache
                transformation={
                    "quality": "auto:good",  # Optimize file size
                    "fetch_format": "auto"   # Best format for browser
                }
            )
            
            upload_info = {
                "url": result["secure_url"],
                "public_id": result["public_id"],
                "format": result.get("format"),  # Optional: images only
                "size": result["bytes"],
                "width": result.get("width"),   # Optional: images only
                "height": result.get("height")  # Optional: images only
            }
            
            logger.info(f"✅ Uploaded to Cloudinary: {upload_info['url']}")
            return upload_info
            
        except Exception as e:
            logger.error(f"❌ Cloudinary upload failed: {e}")
            return None
    
    # Legacy method for backwards compatibility
    def upload_invoice(self, file_path: str, invoice_id: str) -> Optional[Dict[str, str]]:
        """Deprecated: Use upload_file() instead"""
        return self.upload_file(file_path, invoice_id, folder="invoices")
    
    def delete_file(self, public_id: str) -> bool:
        """
        Delete document file from Cloudinary
        
        Args:
            public_id: Cloudinary public ID (e.g., 'bank_statements/stmt_abc123')
            
        Returns:
            True if deleted successfully
        """
        if not self.enabled:
            return False
        
        try:
            result = cloudinary.uploader.destroy(public_id)
            success = result.get("result") == "ok"
            
            if success:
                logger.info(f"Deleted from Cloudinary: {public_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Cloudinary delete failed: {e}")
            return False
    
    # Legacy method for backwards compatibility
    def delete_invoice(self, public_id: str) -> bool:
        """Deprecated: Use delete_file() instead"""
        return self.delete_file(public_id)
    
    def get_image_url(self, public_id: str, transformation: Optional[Dict] = None) -> Optional[str]:
        """
        Get optimized image URL with optional transformations
        
        Args:
            public_id: Cloudinary public ID
            transformation: Optional transformations (resize, crop, etc.)
            
        Returns:
            Secure image URL or None if disabled
        """
        if not self.enabled:
            return None
        
        return cloudinary.CloudinaryImage(public_id).build_url(
            secure=True,
            transformation=transformation
        )


# Singleton instance
_cloudinary_service = None

def get_cloudinary_service() -> CloudinaryService:
    """Get or create Cloudinary service instance"""
    global _cloudinary_service
    if _cloudinary_service is None:
        _cloudinary_service = CloudinaryService()
    return _cloudinary_service
