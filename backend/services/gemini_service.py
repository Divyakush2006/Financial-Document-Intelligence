"""
Gemini LLM Service - Alternative to Groq
Uses Google's Gemini API for data extraction
"""

import os
import json
import logging
import time
from typing import Dict, Optional
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class GeminiLLM:
    """LLM service using Google Gemini"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini LLM service
        
        Args:
            api_key: Gemini API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        # Configure Gemini
        genai.configure(api_key=self.api_key)
        
        # Use Gemini 2.0 Flash for fast extraction
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.max_retries = 3
        self.retry_delay = 15  # seconds
        
        logger.info("Gemini LLM service initialized with model: gemini-2.0-flash")
    
    def structure_data(self, prompt: str) -> Optional[Dict]:
        """
        Structure data using Gemini with custom prompt.
        Includes retry logic for rate limits.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Sending extraction request to Gemini (attempt {attempt}/{self.max_retries})...")
                
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.1,
                        'top_p': 0.95,
                        'top_k': 40,
                    }
                )
                
                # Extract response text
                response_text = response.text.strip()
                
                # Clean markdown code blocks
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()
                
                extracted_data = json.loads(response_text)
                
                logger.info("Successfully structured data with Gemini")
                return extracted_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                logger.error(f"Response was: {response_text[:500]}")
                return None
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate" in error_str.lower() or "quota" in error_str.lower():
                    if attempt < self.max_retries:
                        wait = self.retry_delay * attempt
                        logger.warning(f"Rate limited. Waiting {wait}s before retry...")
                        time.sleep(wait)
                        continue
                logger.error(f"Gemini structuring failed: {e}")
                return None
        
        logger.error("All retries failed")
        return None


# Singleton instance
_gemini_llm = None

def get_gemini_llm() -> GeminiLLM:
    """Get or create Gemini LLM instance"""
    global _gemini_llm
    if _gemini_llm is None:
        _gemini_llm = GeminiLLM()
    return _gemini_llm
