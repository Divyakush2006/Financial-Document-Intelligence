"""
ID Document Extractor - For PAN, Aadhaar, Passport, etc.
"""

from services.extractors.base_extractor import BaseExtractor


class IDDocumentExtractor(BaseExtractor):
    """Extract structured data from ID documents"""
    
    def get_extraction_prompt(self, text: str) -> str:
        """Generate ID document extraction prompt"""
        return f"""You are a financial document extraction AI specializing in ID documents.

DOCUMENT TYPE: ID Document (PAN, Aadhaar, Passport, DL, Voter ID, etc.)

EXTRACTED TEXT:
{text}

TASK: Extract ID information in JSON format:

FIELDS:
- document_type: Type of ID (PAN, Aadhaar, Passport, DL, Voter ID, etc.)
- id_number: ID number (mask if privacy-sensitive)
- name: Full name on ID
- father_name: Father's name (if present)
- date_of_birth: Date of birth (YYYY-MM-DD)
- gender: Gender (Male/Female/Other)
- address: Complete address
- issue_date: Issue date (YYYY-MM-DD if available)
- expiry_date: Expiry date (YYYY-MM-DD if available)
- issuing_authority: Issuing authority/office

RULES:
1. Extract factual information only
2. For Aadhaar, mask to XXXX-XXXX-1234 format
3. Dates in YYYY-MM-DD
4. Use null for missing fields

OUTPUT: Valid JSON only.
"""
    
    def get_expected_fields(self) -> list:
        return ["document_type", "id_number", "name", "date_of_birth"]
