"""
LLM Service for intelligent data extraction
Uses Groq's Llama 3.1 to structure OCR text into JSON
"""

import os
import json
import logging
from typing import Dict, Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class LLMService:
    """Handles intelligent extraction using LLM"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LLM service
        
        Args:
            api_key: Groq API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"  # Updated to current active model
        logger.info(f"LLM service initialized with model: {self.model}")
    
    def extract_invoice_data(self, ocr_text: str) -> Dict:
        """
        Extract structured invoice data from OCR text
        
        Args:
            ocr_text: Raw text from OCR
            
        Returns:
            Dict with extracted invoice data
        """
        try:
            prompt = self._build_extraction_prompt(ocr_text)
            
            logger.info("Sending extraction request to LLM...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from financial documents. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=1024
            )
            
            # Extract response
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            # Sometimes LLM wraps JSON in markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            extracted_data = json.loads(response_text)
            
            logger.info("Successfully extracted invoice data")
            return {
                "success": True,
                "data": extracted_data,
                "model": self.model
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text}")
            return {
                "success": False,
                "error": "Failed to parse LLM response",
                "raw_response": response_text
            }
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def structure_data(self, prompt: str) -> Optional[Dict]:
        """
        Generic method to structure data using LLM with custom prompt
        Used by document extractors
        
        Args:
            prompt: Custom extraction prompt
            
        Returns:
            Dict with extracted data or None if failed
        """
        try:
            logger.info("Sending custom extraction request to LLM...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting structured data from financial documents. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=8000  # Increased for large bank statements
            )
            
            # Extract response
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON
            # Sometimes LLM wraps JSON in markdown code blocks
            if response_text.startswith("```json"):
                response_text = response_text.replace("```json", "").replace("```", "").strip()
            elif response_text.startswith("```"):
                response_text = response_text.replace("```", "").strip()
            
            extracted_data = json.loads(response_text)
            
            logger.info("Successfully structured data with custom prompt")
            return extracted_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"LLM structuring failed: {e}")
            return None
    
    def _build_extraction_prompt(self, ocr_text: str) -> str:
        """Build prompt for invoice data extraction"""
        return f"""
Extract the following information from this invoice text and return it as JSON:

Invoice Text:
{ocr_text}

Extract these fields (use null if not found):
- invoice_number: The invoice/document number
- date: Invoice date in YYYY-MM-DD format
- due_date: Payment due date in YYYY-MM-DD format (if present)
- vendor_name: Name of the vendor/seller
- vendor_address: Vendor's address (if present)
- customer_name: Name of the customer/buyer (if present)
- total_amount: Total amount as a number (no currency symbols)
- currency: Currency code (USD, EUR, etc.)
- line_items: Array of items with description, quantity, unit_price, total
- tax_amount: Tax amount if specified
- subtotal: Subtotal before tax (if present)

Return ONLY valid JSON, no additional text. Use this format:
{{
  "invoice_number": "...",
  "date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD",
  "vendor_name": "...",
  "vendor_address": "...",
  "customer_name": "...",
  "total_amount": 0.00,
  "currency": "USD",
  "line_items": [
    {{
      "description": "...",
      "quantity": 0,
      "unit_price": 0.00,
      "total": 0.00
    }}
  ],
  "tax_amount": 0.00,
  "subtotal": 0.00
}}
"""


# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get or create LLM service instance"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
