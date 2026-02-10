"""
Base Extractor - Abstract class for all document extractors
Provides common OCR and LLM structuring logic
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """
    Abstract base class for document extractors
    
    All document-specific extractors inherit from this and implement:
    - get_extraction_prompt()
    - get_expected_fields()
    """
    
    def __init__(self, azure_ocr, groq_llm):
        """
        Initialize base extractor
        
        Args:
            azure_ocr: Azure OCR service instance
            groq_llm: Groq LLM service instance
        """
        self.ocr = azure_ocr
        self.llm = groq_llm
        self.document_type = self.__class__.__name__.replace("Extractor", "").lower()
    
    def extract(self, image_path: str) -> Dict:
        """
        Main extraction workflow
        
        Args:
            image_path: Path to document image
            
        Returns:
            Dict with extraction results
        """
        try:
            # Step 1: OCR text extraction
            logger.info(f"[{self.document_type}] Starting OCR extraction...")
            ocr_result = self._extract_text(image_path)
            
            if not ocr_result['success']:
                return {
                    "success": False,
                    "error": "OCR extraction failed",
                    "document_type": self.document_type
                }
            
            extracted_text = ocr_result['text']
            ocr_confidence = ocr_result['confidence']
            
            logger.info(f"[{self.document_type}] OCR complete: {ocr_confidence:.1%} confidence, {len(extracted_text)} chars")
            
            # Step 2: Preprocess text (document-specific, optional)
            preprocessed_text = self.preprocess_text(extracted_text)
            
            # Step 3: Generate extraction prompt
            prompt = self.get_extraction_prompt(preprocessed_text)
            
            # Step 4: LLM structuring
            logger.info(f"[{self.document_type}] Sending to LLM for structuring...")
            structured_data = self._structure_with_llm(prompt)
            
            if not structured_data:
                return {
                    "success": False,
                    "error": "LLM structuring failed",
                    "document_type": self.document_type,
                    "ocr_confidence": ocr_confidence
                }
            
            # Step 5: Postprocess data (document-specific, optional)
            final_data = self.postprocess_data(structured_data)
            
            # Step 6: Validate required fields
            validation = self._validate_extraction(final_data)
            
            logger.info(f"[{self.document_type}] Extraction complete: {validation['fields_extracted']}/{validation['fields_expected']} fields")
            
            return {
                "success": True,
                "document_type": self.document_type,
                "data": final_data,
                "ocr_confidence": ocr_confidence,
                "extraction_confidence": validation['confidence'],
                "fields_extracted": validation['fields_extracted'],
                "fields_expected": validation['fields_expected'],
                "raw_text": extracted_text[:500]  # First 500 chars for debugging
            }
            
        except Exception as e:
            logger.error(f"[{self.document_type}] Extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "document_type": self.document_type
            }
    
    def _extract_text(self, image_path: str) -> Dict:
        """Extract text using Azure OCR (with fallback)"""
        try:
            # Try Azure OCR first
            if self.ocr:
                result = self.ocr.extract_text_general(image_path)
                if result['success'] and result['confidence'] > 0.5:
                    return result
            
            # Fallback to EasyOCR if Azure fails or low confidence
            logger.warning(f"[{self.document_type}] Azure OCR unavailable or low confidence, using fallback")
            from services.ocr_service import get_ocr_service
            fallback_ocr = get_ocr_service()
            return fallback_ocr.extract_text(image_path)
            
        except Exception as e:
            logger.error(f"[{self.document_type}] OCR extraction error: {e}")
            return {"success": False, "error": str(e)}
    
    def _structure_with_llm(self, prompt: str) -> Optional[Dict]:
        """Structure extracted text using Groq LLM"""
        try:
            return self.llm.structure_data(prompt)
        except Exception as e:
            logger.error(f"[{self.document_type}] LLM structuring error: {e}")
            return None
    
    def _validate_extraction(self, data: Dict) -> Dict:
        """
        Validate extracted data against expected fields
        
        Returns:
            Dict with validation metrics
        """
        expected_fields = self.get_expected_fields()
        extracted_fields = []
        
        for field in expected_fields:
            # Support nested fields with dot notation (e.g., "transactions.date")
            value = self._get_nested_field(data, field)
            if value is not None and value != "":
                extracted_fields.append(field)
        
        fields_extracted = len(extracted_fields)
        fields_expected = len(expected_fields)
        confidence = fields_extracted / fields_expected if fields_expected > 0 else 0.0
        
        return {
            "fields_extracted": fields_extracted,
            "fields_expected": fields_expected,
            "confidence": confidence,
            "missing_fields": list(set(expected_fields) - set(extracted_fields))
        }
    
    def _get_nested_field(self, data: Dict, field_path: str):
        """Get nested field value using dot notation"""
        keys = field_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    # Abstract methods (must be implemented by subclasses)
    
    @abstractmethod
    def get_extraction_prompt(self, text: str) -> str:
        """
        Generate document-specific extraction prompt for LLM
        
        Args:
            text: OCR extracted text
            
        Returns:
            Prompt string for LLM
        """
        pass
    
    @abstractmethod
    def get_expected_fields(self) -> list:
        """
        Return list of expected fields for this document type
        
        Returns:
            List of field names (supports dot notation for nested fields)
        """
        pass
    
    # Optional methods (can be overridden by subclasses)
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess OCR text before sending to LLM
        Override for document-specific cleaning
        
        Args:
            text: Raw OCR text
            
        Returns:
            Preprocessed text
        """
        return text
    
    def postprocess_data(self, data: Dict) -> Dict:
        """
        Postprocess structured data from LLM
        Override for document-specific validation/formatting
        
        Args:
            data: Structured data from LLM
            
        Returns:
            Postprocessed data
        """
        return data
