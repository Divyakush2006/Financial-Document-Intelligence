"""
OCR Service for extracting text from invoice images
Supports both EasyOCR and Tesseract with fallback mechanism
"""

# Make imports optional
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

from PIL import Image
import numpy as np
from typing import Dict, Optional
import logging
import os

logger = logging.getLogger(__name__)


class OCRService:
    """Handles text extraction from images using multiple OCR engines"""
    
    def __init__(self, preferred_engine: str = "easyocr"):
        """
        Initialize OCR service
        
        Args:
            preferred_engine: 'easyocr' or 'tesseract'
        """
        self.preferred_engine = preferred_engine
        self.easyocr_reader = None
        
        # Initialize EasyOCR if preferred and available
        if preferred_engine == "easyocr" and EASYOCR_AVAILABLE:
            try:
                logger.info("Initializing EasyOCR...")
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("EasyOCR initialized successfully")
            except Exception as e:
                logger.warning(f"EasyOCR initialization failed: {e}")
        elif preferred_engine == "easyocr" and not EASYOCR_AVAILABLE:
            logger.warning("EasyOCR not available, will use fallback if needed")
    
    def preprocess_image(self, image_path: str) -> str:
        """
        Preprocess image for better OCR accuracy
        
        Args:
            image_path: Path to original image
            
        Returns:
            Path to preprocessed image
        """
        try:
            from PIL import ImageEnhance, ImageFilter
            import os
            import tempfile
            
            # Open image
            image = Image.open(image_path)
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Enhance contrast slightly (makes text clearer)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.15)  # Reduced from 1.3
            
            # Enhance sharpness slightly (improves character edges)
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)  # Reduced from 1.5
            
            # Skip median filter on high-quality images
            # image = image.filter(ImageFilter.MedianFilter(size=3))
            
            # Save preprocessed image
            temp_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            image.save(temp_path, quality=100)
    
    
            logger.info(f"Preprocessing complete: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}, using original image")
            return image_path
    
    
    def extract_text_easyocr(self, image_path: str, preprocess: bool = True) -> Dict:
        """
        Extract text using EasyOCR
        
        Args:
            image_path: Path to image file
            preprocess: Whether to preprocess image first
            
        Returns:
            Dict with extracted text and confidence
        """
        processed_path = None
        try:
            if not self.easyocr_reader:
                self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
            
            # Preprocess image for better accuracy (gentle processing)
            if preprocess:
                processed_path = self.preprocess_image(image_path)
                image_to_process = processed_path
            else:
                image_to_process = image_path
            
            # Use optimized parameters for better confidence
            result = self.easyocr_reader.readtext(
                image_to_process,
                paragraph=False,  # Read line by line for higher confidence
                detail=1,  # Return bounding box + text + confidence
                contrast_ths=0.3,  # Optimized threshold
                adjust_contrast=0.7,  # Slight contrast adjustment
                text_threshold=0.6,  # Optimized text threshold
                low_text=0.3  # Detect more text regions
            )
            
            # Combine all text
            text = ' '.join([item[1] for item in result])
            
            # Calculate average confidence
            confidences = [item[2] for item in result]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": text,
                "confidence": avg_confidence,
                "engine": "easyocr",
                "success": True
            }
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return {
                "text": "",
                "confidence": 0,
                "engine": "easyocr",
                "success": False,
                "error": str(e)
            }
        finally:
            # Clean up preprocessed image
            if processed_path and os.path.exists(processed_path):
                try:
                    os.unlink(processed_path)
                except:
                    pass
    
    def extract_text_tesseract(self, image_path: str) -> Dict:
        """
        Extract text using Tesseract
        
        Args:
            image_path: Path to image file
            
        Returns:
            Dict with extracted text and confidence
        """
        try:
            image = Image.open(image_path)
            
            # Extract text
            text = pytesseract.image_to_string(image)
            
            # Get confidence data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "text": text.strip(),
                "confidence": avg_confidence / 100,  # Normalize to 0-1
                "engine": "tesseract",
                "success": True
            }
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return {
                "text": "",
                "confidence": 0,
                "engine": "tesseract",
                "success": False,
                "error": str(e)
            }
    
    def extract_text(self, image_path: str, use_fallback: bool = True) -> Dict:
        """
        Extract text with automatic fallback to alternate engine
        
        Args:
            image_path: Path to image file
            use_fallback: Whether to try alternate engine if primary fails
            
        Returns:
            Dict with extraction results
        """
        # Try preferred engine first
        if self.preferred_engine == "easyocr":
            result = self.extract_text_easyocr(image_path)
            if not result["success"] and use_fallback:
                logger.info("Falling back to Tesseract...")
                result = self.extract_text_tesseract(image_path)
        else:
            result = self.extract_text_tesseract(image_path)
            if not result["success"] and use_fallback:
                logger.info("Falling back to EasyOCR...")
                result = self.extract_text_easyocr(image_path)
        
        return result


# Singleton instance
_ocr_service = None

def get_ocr_service(engine: str = "easyocr") -> OCRService:
    """Get or create OCR service instance"""
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService(preferred_engine=engine)
    return _ocr_service
