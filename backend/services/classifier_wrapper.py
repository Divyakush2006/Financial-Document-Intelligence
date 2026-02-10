"""
Wrapper functions for document classifier for backward compatibility
"""

from services.ocr_service import get_ocr_service
from services.document_classifier import get_document_classifier as _get_classifier


def get_classifier():
    """Alias for get_document_classifier for backwards compatibility"""
    return SmartClassifier()


class SmartClassifier:
    """Wrapper class with classify_document method"""
    
    def __init__(self):
        self.classifier = _get_classifier()
        self.ocr = get_ocr_service()
    
    def classify_document(self, image_path: str) -> dict:
        """
        Classify document from image file
        
        Args:
            image_path: Path to document image
            
        Returns:
            Dict with success, document_type, confidence
        """
        try:
            # Extract text using OCR
            ocr_result = self.ocr.extract_text(image_path)
            
            if not ocr_result['success']:
                return {
                    'success': False,
                    'error': 'OCR extraction failed'
                }
            
            # Classify from text
            classification_result = self.classifier.classify_from_text(ocr_result['text'])
            
            if classification_result['success']:
                classification = classification_result['classification']
                return {
                    'success': True,
                    'document_type': classification['document_type'],
                    'confidence': classification['confidence'],
                    'reasoning': classification.get('reasoning', '')
                }
            else:
                return classification_result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
