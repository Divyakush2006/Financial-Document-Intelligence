"""
Bank Statement Processor (Groq Version)
Alternative processor using Groq API to avoid Gemini quota limits
"""

import logging
from typing import Dict, Optional
from pathlib import Path
import pandas as pd

from services.llm_service import get_llm_service
from services.extraction_prompts import generate_bank_statement_prompt
from services.extraction_validator import get_validator, ValidationLevel

logger = logging.getLogger(__name__)


class ProcessingResult:
    """Result of bank statement processing"""
    
    def __init__(
        self,
        success: bool,
        file_path: str,
        data: Optional[Dict] = None,
        validation: Optional[Dict] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        self.success = success
        self.file_path = file_path
        self.data = data
        self.validation = validation
        self.error = error
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        import json
        result = {
            "success": self.success,
            "file": Path(self.file_path).name,
            "file_path": str(self.file_path)
        }
        
        if self.data:
            result["data"] = self.data
        
        if self.validation:
            result["validation"] = self.validation
        
        if self.error:
            result["error"] = self.error
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), indent=indent, default=str)


class BankStatementProcessorGroq:
    """
    Bank statement extraction processor using Groq API.
    Alternative to Gemini-based processor with higher rate limits.
    """
    
    def __init__(self):
        """Initialize processor with Groq LLM service"""
        self.llm = get_llm_service()  # Uses Groq by default
        self.validator = get_validator()
        logger.info("Bank Statement Processor (Groq) initialized")
    
    def process_excel(self, file_path: str):
        """
        Process bank statement Excel file to structured JSON.
        
        Args:
            file_path: Absolute path to Excel file
            
        Returns:
            ProcessingResult with extracted data and validation status
        """
        file_path = Path(file_path)
        
        # Validate file exists
        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                error=error_msg
            )
        
        # Validate file format
        if file_path.suffix.lower() not in ['.xlsx', '.xls', '.xlsm']:
            error_msg = f"Unsupported file format: {file_path.suffix}"
            logger.error(error_msg)
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                error=error_msg
            )
        
        try:
            logger.info(f"Processing: {file_path.name}")
            
            # Step 1: Parse Excel to DataFrame
            df = self._parse_excel_to_dataframe(str(file_path))
            
            if df is None or df.empty:
                return ProcessingResult(
                    success=False,
                    file_path=str(file_path),
                    error="Excel file is empty or could not be parsed"
                )
            
            logger.info(f"Parsed Excel: {df.shape[0]} rows, {df.shape[1]} columns")
            
            # Step 2: Extract structured data with Groq
            extracted_data = self._extract_with_groq(df)
            
            if not extracted_data:
                return ProcessingResult(
                    success=False,
                    file_path=str(file_path),
                    error="Groq extraction failed - returned no data"
                )
            
            logger.info(f"Extraction successful: {len(extracted_data.get('transactions', []))} transactions")
            
            # Step 3: Validate extracted data
            validation_result = self._validate_extraction(extracted_data)
            
            # Prepare metadata
            metadata = {
                "excel_rows": df.shape[0],
                "excel_columns": df.shape[1],
                "transactions_extracted": len(extracted_data.get("transactions", [])),
                "validation_level": validation_result.validation_level.value,
                "issues_found": len(validation_result.issues),
                "llm_provider": "groq"
            }
            
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
            
            return ProcessingResult(
                success=True,
                file_path=str(file_path),
                data=extracted_data,
                validation=validation_summary,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Processing failed for {file_path.name}: {e}", exc_info=True)
            return ProcessingResult(
                success=False,
                file_path=str(file_path),
                error=str(e)
            )
    
    def _parse_excel_to_dataframe(self, file_path: str) -> Optional[pd.DataFrame]:
        """Parse Excel file to pandas DataFrame"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Clean DataFrame
            df = df.dropna(how='all')
            df = df.dropna(axis=1, how='all')
            df = df.fillna('')
            
            # Strip whitespace
            for col in df.columns:
                if df[col].dtype == 'object':
                    df[col] = df[col].astype(str).str.strip()
            
            df = df.reset_index(drop=True)
            return df
            
        except Exception as e:
            logger.error(f"Excel parsing failed: {e}")
            return None
    
    def _extract_with_groq(self, df: pd.DataFrame) -> Optional[Dict]:
        """Extract structured data using Groq API"""
        try:
            # Generate extraction prompt
            prompt = generate_bank_statement_prompt(df)
            
            logger.info("Sending extraction request to Groq...")
            
            # Call Groq API
            extracted_data = self.llm.structure_data(prompt)
            
            if not extracted_data:
                logger.error("Groq returned None")
                return None
            
            # Ensure transactions is a list
            if "transactions" not in extracted_data:
                extracted_data["transactions"] = []
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Groq extraction failed: {e}", exc_info=True)
            return None
    
    def _validate_extraction(self, data: Dict):
        """Validate extracted data"""
        return self.validator.validate(data)


# Singleton instance
_processor_groq = None

def get_processor_groq():
    """Get or create Groq-based processor instance"""
    global _processor_groq
    if _processor_groq is None:
        _processor_groq = BankStatementProcessorGroq()
    return _processor_groq
