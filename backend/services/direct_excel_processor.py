"""
Direct Excel to JSON Extraction - No LLM Required!
Rule-based bank statement processor using intelligent parsing
"""

import logging
from typing import Dict
from pathlib import Path

from services.excel_to_json_converter import get_converter
from services.extraction_validator import get_validator

logger = logging.getLogger(__name__)


class DirectExcelProcessor:
    """
    Process bank statements directly from Excel to JSON.
    No LLM required - uses pure rule-based parsing.
    """
    
    def __init__(self):
        """Initialize with converter and validator"""
        self.converter = get_converter()
        self.validator = get_validator()
        logger.info("Direct Excel Processor initialized (No LLM)")
    
    def process_excel(self, file_path: str) -> Dict:
        """
        Process Excel file directly to JSON.
        
        Args:
            file_path: Path to Excel file
            
        Returns:
            Dictionary with extracted data and validation
        """
        file_path = Path(file_path)
        
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Step 1: Convert Excel to JSON (rule-based)
            conversion_result = self.converter.convert(str(file_path))
            
            if not conversion_result['success']:
                return {
                    "success": False,
                    "file": file_path.name,
                    "error": conversion_result.get('error')
                }
            
            extracted_data = conversion_result['data']
            
            logger.info(f"Extracted {len(extracted_data.get('transactions', []))} transactions")
            
            # Step 2: Validate data
            validation_result = self.validator.validate(extracted_data)
            
            # Prepare validation summary
            validation_summary = {
                "is_valid": validation_result.is_valid,
                "validation_level": validation_result.validation_level.value,
                "balance_check": validation_result.balance_check,
                "date_check": validation_result.date_check,
                "completeness_check": validation_result.completeness_check,
                "issues": [
                    {
                        "type": issue.issue_type.value,
                        "severity": issue.severity,
                        "message": issue.message,
                        "details": issue.details
                    }
                    for issue in validation_result.issues
                ]
            }
            
            logger.info(f"Validation: {validation_result.validation_level.value}")
            
            return {
                "success": True,
                "file": file_path.name,
                "file_path": str(file_path),
                "data": extracted_data,
                "validation": validation_summary,
                "metadata": {
                    **conversion_result['metadata'],
                    "validation_level": validation_result.validation_level.value,
                    "issues_found": len(validation_result.issues)
                }
            }
            
        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return {
                "success": False,
                "file": file_path.name,
                "error": str(e)
            }


# Singleton instance
_processor = None

def get_direct_processor():
    """Get or create direct processor instance"""
    global _processor
    if _processor is None:
        _processor = DirectExcelProcessor()
    return _processor
