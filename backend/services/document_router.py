"""
Document Router - Intelligent routing to document-specific extractors
"""

import logging
from typing import Dict, Optional
from pathlib import Path

from services.classifier_wrapper import get_classifier
from services.ocr_azure import get_azure_ocr
from services.llm_service import get_llm_service
from services.extractors import EXTRACTOR_MAP

logger = logging.getLogger(__name__)


class DocumentRouter:
    """
    Intelligent document router
    
    Workflow:
    1. Classify document type
    2. Select appropriate extractor
    3. Extract and structure data
    4. Return JSON result
    """
    
    def __init__(self):
        """Initialize router with services"""
        self.classifier = get_classifier()
        self.azure_ocr = get_azure_ocr()
        self.llm = get_llm_service()
        
        # Initialize all extractors
        self.extractors = {}
        for doc_type, ExtractorClass in EXTRACTOR_MAP.items():
            try:
                self.extractors[doc_type] = ExtractorClass(self.azure_ocr, self.llm)
                logger.info(f"Initialized {doc_type} extractor")
            except Exception as e:
                logger.error(f"Failed to initialize {doc_type} extractor: {e}")
        
        logger.info(f"DocumentRouter initialized with {len(self.extractors)} extractors")
    
    def process_document(self, image_path: str) -> Dict:
        """
        Main entry point: classify and extract document
        
        Args:
            image_path: Path to document image
            
        Returns:
            Dict with classification and extraction results
        """
        try:
            # Step 1: Classify document
            logger.info(f"Processing document: {Path(image_path).name}")
            classification = self.classifier.classify_document(image_path)
            
            if not classification['success']:
                return {
                    "success": False,
                    "error": "Document classification failed",
                    "image_path": image_path
                }
            
            doc_type = classification['document_type']
            classification_confidence = classification['confidence']
            
            logger.info(f"Classified as: {doc_type} ({classification_confidence:.1%} confidence)")
            
            # Step 2: Get appropriate extractor
            extractor = self._get_extractor(doc_type)
            
            if not extractor:
                return {
                    "success": False,
                    "error": f"No extractor available for document type: {doc_type}",
                    "classification": classification
                }
            
            # Step 3: Extract data
            extraction = extractor.extract(image_path)
            
            # Step 4: Combine results
            result = {
                "success": extraction['success'],
                "document_type": doc_type,
                "classification_confidence": classification_confidence,
                "extraction": extraction,
                "image_path": image_path
            }
            
            if extraction['success']:
                logger.info(f"Extraction complete: {extraction.get('fields_extracted', 0)} fields extracted")
            else:
                logger.error(f"Extraction failed: {extraction.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "image_path": image_path
            }
    
    def process_batch(self, image_paths: list) -> Dict:
        """
        Process multiple documents
        
        Args:
            image_paths: List of paths to document images
            
        Returns:
            Dict with batch processing results
        """
        results = []
        success_count = 0
        
        for i, image_path in enumerate(image_paths, 1):
            logger.info(f"\nProcessing document {i}/{len(image_paths)}")
            result = self.process_document(image_path)
            results.append(result)
            
            if result['success']:
                success_count += 1
        
        return {
            "total": len(image_paths),
            "successful": success_count,
            "failed": len(image_paths) - success_count,
            "results": results
        }
    
    def _get_extractor(self, doc_type: str):
        """Get extractor for document type"""
        # Normalize document type
        normalized_type = doc_type.lower().replace(" ", "_")
        
        extractor = self.extractors.get(normalized_type)
        
        if not extractor:
            logger.warning(f"No extractor found for type: {doc_type}")
            # Try to find close match
            for key in self.extractors.keys():
                if key in normalized_type or normalized_type in key:
                    logger.info(f"Using closest match: {key}")
                    return self.extractors[key]
        
        return extractor
    
    def get_supported_types(self) -> list:
        """Get list of supported document types"""
        return list(self.extractors.keys())


# Singleton instance
_router = None

def get_document_router() -> DocumentRouter:
    """Get or create document router instance"""
    global _router
    
    if _router is None:
        _router = DocumentRouter()
    
    return _router
