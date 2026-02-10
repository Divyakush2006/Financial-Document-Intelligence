"""
Document Classification Service
Auto-detects document type: invoice, bank_statement, salary_slip, loan_agreement, etc.
Uses OCR preview + LLM analysis for intelligent classification
"""

import logging
from typing import Dict, Optional
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Intelligent document type classifier"""
    
    # Supported document types
    DOCUMENT_TYPES = {
        "invoice": "Commercial invoice or bill",
        "bank_statement": "Bank account statement",
        "salary_slip": "Salary slip or payslip",
        "loan_agreement": "Loan agreement or contract",
        "receipt": "Payment receipt",
        "tax_document": "Tax form or return",
        "identity_proof": "ID card, passport, or identity document",
        "unknown": "Unable to classify"
    }
    
    def __init__(self):
        """Initialize classifier with Groq LLM"""
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        
        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"
        logger.info("Document classifier initialized")
    
    def classify_from_text(self, ocr_text: str) -> Dict:
        """
        Classify document type from OCR text
        
        Args:
            ocr_text: Extracted text from document
            
        Returns:
            Dict with document_type, confidence, reasoning
        """
        try:
            # Build classification prompt
            prompt = f"""You are a financial document classifier. Analyze the following text extracted from a document and determine its type.

Document Text:
{ocr_text[:2000]}  # First 2000 chars for context

Classification Categories:
1. invoice - Commercial invoice or bill (keywords: invoice, bill, amount due, line items, vendor)
2. bank_statement - Bank account statement (keywords: account number, transactions, balance, debit/credit)
3. salary_slip - Salary slip or payslip (keywords: salary, employee, employer, gross pay, deductions, net pay)
4. loan_agreement - Loan agreement or contract (keywords: loan, interest rate, tenure, principal, EMI)
5. receipt - Payment receipt (keywords: receipt, payment received, thank you)
6. tax_document - Tax form (keywords: tax, PAN, GST, income tax, return)
7. identity_proof - ID document (keywords: passport, license, Aadhaar, DOB)
8. unknown - Cannot determine type

Instructions:
1. Analyze keywords, structure, and content
2. Return ONLY a JSON object with this exact structure:
{{
    "document_type": "invoice",
    "confidence": 0.95,
    "reasoning": "Contains invoice number, vendor details, line items, and total amount"
}}

Respond with ONLY the JSON, no other text."""

            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise document classification AI. Respond only with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for consistent classification
                max_tokens=300
            )
            
            # Parse response
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON
            import json
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            classification = json.loads(result_text)
            
            # Validate document type
            doc_type = classification.get("document_type", "unknown")
            if doc_type not in self.DOCUMENT_TYPES:
                doc_type = "unknown"
                classification["document_type"] = doc_type
            
            # Add description
            classification["type_description"] = self.DOCUMENT_TYPES[doc_type]
            
            logger.info(f"Classified as: {doc_type} (confidence: {classification.get('confidence', 0):.2%})")
            
            return {
                "success": True,
                "classification": classification,
                "model": self.model
            }
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return {
                "success": False,
                "classification": {
                    "document_type": "unknown",
                    "confidence": 0.0,
                    "reasoning": f"Classification error: {str(e)}"
                },
                "error": str(e)
            }
    
    def classify_with_keywords(self, ocr_text: str) -> Dict:
        """
        Fast keyword-based classification (backup method)
        
        Args:
            ocr_text: Document text
            
        Returns:
            Classification result
        """
        text_lower = ocr_text.lower()
        
        # Keyword patterns
        patterns = {
            "invoice": ["invoice", "bill to", "invoice no", "invoice date", "amount due", "line items"],
            "bank_statement": ["account statement", "account number", "opening balance", "closing balance", "transaction", "debit", "credit"],
            "salary_slip": ["salary slip", "payslip", "gross salary", "net salary", "employee", "employer", "deductions", "basic pay"],
            "loan_agreement": ["loan agreement", "loan amount", "interest rate", "tenure", "emi", "principal", "repayment"],
            "receipt": ["receipt", "payment received", "thank you for your payment"],
            "tax_document": ["income tax", "tax return", "pan", "gst", "assessment year"]
        }
        
        # Score each type
        scores = {}
        for doc_type, keywords in patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            scores[doc_type] = score / len(keywords)  # Normalize
        
        # Get best match
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        if confidence < 0.2:  # Too low
            best_type = "unknown"
            confidence = 0.0
        
        return {
            "success": True,
            "classification": {
                "document_type": best_type,
                "confidence": confidence,
                "reasoning": f"Keyword-based classification (matched {int(confidence * 100)}% of patterns)",
                "type_description": self.DOCUMENT_TYPES.get(best_type, "Unknown")
            },
            "model": "keyword_matcher"
        }


# Singleton instance
_classifier = None

def get_document_classifier() -> DocumentClassifier:
    """Get or create document classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = DocumentClassifier()
    return _classifier
