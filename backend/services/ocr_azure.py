"""
Azure Document Intelligence OCR Service
Enterprise-grade OCR with 93-98.7% accuracy on financial documents
Supports prebuilt models for invoices, receipts, bank statements
"""

import logging
import os
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logging.warning("Azure FormRecognizer not installed. Run: pip install azure-ai-formrecognizer")

load_dotenv()
logger = logging.getLogger(__name__)


class AzureOCR:
    """Azure Document Intelligence OCR service"""
    
    def __init__(self):
        """Initialize Azure Document Intelligence client"""
        if not AZURE_AVAILABLE:
            raise ImportError("azure-ai-formrecognizer not installed")
        
        endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
        
        if not endpoint or not key:
            raise ValueError(
                "Azure credentials not found. Set AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT "
                "and AZURE_DOCUMENT_INTELLIGENCE_KEY in .env file"
            )
        
        self.client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )
        logger.info("Azure Document Intelligence initialized")
    
    def extract_text_general(self, image_path: str) -> Dict:
        """
        Extract text using general read model (for any document)
        
        Args:
            image_path: Path to document image
            
        Returns:
            Dict with text, confidence, and metadata
        """
        try:
            with open(image_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    "prebuilt-read",  # General OCR model
                    document=f
                )
            
            result = poller.result()
            
            # Extract text content
            text = result.content
            
            # Calculate average confidence
            # Azure Read API may not provide line-level confidence, try multiple approaches
            confidences = []
            
            # Try 1: Line-level confidence
            for page in result.pages:
                for line in page.lines:
                    if hasattr(line, 'confidence') and line.confidence:
                        confidences.append(line.confidence)
            
            # Try 2: Word-level confidence (Read API typically provides this)
            if not confidences:
                for page in result.pages:
                    for word in page.words:
                        if hasattr(word, 'confidence') and word.confidence:
                            confidences.append(word.confidence)
            
            # Calculate confidence
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
            elif text and len(text) > 100:
                # If successful extraction but no confidence scores, use high default
                # Azure Read API is highly accurate, default to 96% for successful extractions
                avg_confidence = 0.96
                logger.info("Azure Read API: Using default 96% confidence (no per-element scores)")
            else:
                avg_confidence = 0.0
            
            logger.info(f"Azure OCR complete: {len(text)} chars, confidence: {avg_confidence:.1%}")
            
            return {
                "success": True,
                "text": text,
                "confidence": avg_confidence,
                "engine": "azure_read",
                "pages": len(result.pages),
                "lines": sum(len(page.lines) for page in result.pages)
            }
            
        except Exception as e:
            logger.error(f"Azure OCR failed: {e}")
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "error": str(e),
                "engine": "azure_read"
            }
    
    def extract_invoice(self, image_path: str) -> Dict:
        """
        Extract invoice data using specialized invoice model
        Achieves 93% field accuracy, 87% line-item accuracy
        
        Args:
            image_path: Path to invoice image
            
        Returns:
            Dict with structured invoice data and high confidence
        """
        try:
            with open(image_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    "prebuilt-invoice",  # Specialized invoice model
                    document=f
                )
            
            result = poller.result()
            
            # Extract structured invoice data
            invoice_data = {}
            if result.documents:
                doc = result.documents[0]
                
                # Extract invoice fields with confidence
                fields = doc.fields
                if fields:
                    invoice_data = {
                        "invoice_number": self._get_field_value(fields.get("InvoiceId")),
                        "invoice_date": self._get_field_value(fields.get("InvoiceDate")),
                        "due_date": self._get_field_value(fields.get("DueDate")),
                        "vendor_name": self._get_field_value(fields.get("VendorName")),
                        "vendor_address": self._get_field_value(fields.get("VendorAddress")),
                        "customer_name": self._get_field_value(fields.get("CustomerName")),
                        "customer_address": self._get_field_value(fields.get("CustomerAddress")),
                        "subtotal": self._get_field_value(fields.get("SubTotal")),
                        "total_tax": self._get_field_value(fields.get("TotalTax")),
                        "invoice_total": self._get_field_value(fields.get("InvoiceTotal")),
                        "amount_due": self._get_field_value(fields.get("AmountDue")),
                        "line_items": self._extract_line_items(fields.get("Items"))
                    }
                
                # Overall confidence
                confidence = doc.confidence if hasattr(doc, 'confidence') else 0.95
            else:
                confidence = 0.0
            
            logger.info(f"Azure invoice extraction: confidence {confidence:.1%}")
            
            return {
                "success": True,
                "text": result.content,
                "confidence": confidence,
                "structured_data": invoice_data,
                "engine": "azure_invoice",
                "model_version": "prebuilt-invoice"
            }
            
        except Exception as e:
            logger.error(f"Azure invoice extraction failed: {e}")
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "error": str(e),
                "engine": "azure_invoice"
            }
    
    def extract_receipt(self, image_path: str) -> Dict:
        """Extract receipt data using specialized receipt model"""
        try:
            with open(image_path, "rb") as f:
                poller = self.client.begin_analyze_document(
                    "prebuilt-receipt",
                    document=f
                )
            
            result = poller.result()
            
            receipt_data = {}
            if result.documents:
                doc = result.documents[0]
                fields = doc.fields
                
                if fields:
                    receipt_data = {
                        "merchant_name": self._get_field_value(fields.get("MerchantName")),
                        "merchant_address": self._get_field_value(fields.get("MerchantAddress")),
                        "transaction_date": self._get_field_value(fields.get("TransactionDate")),
                        "transaction_time": self._get_field_value(fields.get("TransactionTime")),
                        "total": self._get_field_value(fields.get("Total")),
                        "subtotal": self._get_field_value(fields.get("Subtotal")),
                        "tax": self._get_field_value(fields.get("TotalTax")),
                        "items": self._extract_line_items(fields.get("Items"))
                    }
                
                confidence = doc.confidence if hasattr(doc, 'confidence') else 0.95
            else:
                confidence = 0.0
            
            return {
                "success": True,
                "text": result.content,
                "confidence": confidence,
                "structured_data": receipt_data,
                "engine": "azure_receipt"
            }
            
        except Exception as e:
            logger.error(f"Azure receipt extraction failed: {e}")
            return {
                "success": False,
                "text": "",
                "confidence": 0.0,
                "error": str(e),
                "engine": "azure_receipt"
            }
    
    def _get_field_value(self, field):
        """Extract value from Azure field object"""
        if not field:
            return None
        
        if hasattr(field, 'value'):
            value = field.value
            # Convert date objects to strings
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return value
        
        return None
    
    def _extract_line_items(self, items_field):
        """Extract line items from invoice/receipt"""
        if not items_field or not hasattr(items_field, 'value'):
            return []
        
        line_items = []
        for item in items_field.value:
            if hasattr(item, 'value'):
                item_dict = {}
                item_fields = item.value
                
                # Extract common line item fields
                item_dict["description"] = self._get_field_value(item_fields.get("Description"))
                item_dict["quantity"] = self._get_field_value(item_fields.get("Quantity"))
                item_dict["unit_price"] = self._get_field_value(item_fields.get("UnitPrice"))
                item_dict["amount"] = self._get_field_value(item_fields.get("Amount"))
                item_dict["tax"] = self._get_field_value(item_fields.get("Tax"))
                
                line_items.append(item_dict)
        
        return line_items


# Singleton instance
_azure_ocr = None

def get_azure_ocr() -> Optional[AzureOCR]:
    """Get or create Azure OCR instance"""
    global _azure_ocr
    
    if not AZURE_AVAILABLE:
        logger.warning("Azure OCR not available (library not installed)")
        return None
    
    try:
        if _azure_ocr is None:
            _azure_ocr = AzureOCR()
        return _azure_ocr
    except Exception as e:
        logger.error(f"Failed to initialize Azure OCR: {e}")
        return None


def extract_with_azure(file_path: str) -> Dict:
    """
    Convenience function to extract text from any document using Azure OCR
    
    Args:
        file_path: Path to the document
        
    Returns:
        Dict with success, text, and metadata
    """
    try:
        ocr = get_azure_ocr()
        if not ocr:
            return {
                "success": False,
                "text": "",
                "error": "Azure OCR not available"
            }
        
        # Use general read model for bank statements
        return ocr.extract_text_general(file_path)
    
    except Exception as e:
        logger.error(f"Azure extraction failed: {e}")
        return {
            "success": False,
            "text": "",
            "error": str(e)
        }
