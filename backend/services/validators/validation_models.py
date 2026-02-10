"""
Pydantic models for validation results
Standardized structure for validation errors, warnings, and results
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    ERROR = "error"      # Critical issue, data may be incorrect
    WARNING = "warning"  # Potential issue, review recommended
    INFO = "info"        # Informational, no action needed


class ValidationErrorType(str, Enum):
    """Types of validation errors"""
    BALANCE_MISMATCH = "balance_mismatch"
    DATE_OUT_OF_ORDER = "date_out_of_order"
    DATE_OUT_OF_RANGE = "date_out_of_range"
    MISSING_BALANCE = "missing_balance"
    DUPLICATE_TRANSACTION = "duplicate_transaction"
    INCOME_IMPLAUSIBLE = "income_implausible"
    CROSS_DOC_INCONSISTENCY = "cross_document_inconsistency"
    CALCULATION_ERROR = "calculation_error"


class ValidationError(BaseModel):
    """Individual validation error"""
    error_type: ValidationErrorType
    severity: ValidationSeverity
    message: str
    field: Optional[str] = None
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    context: Optional[Dict[str, Any]] = None
    
    class Config:
        use_enum_values = True


class ValidationWarning(BaseModel):
    """Individual validation warning"""
    warning_type: str
    message: str
    field: Optional[str] = None
    recommendation: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class ValidationResult(BaseModel):
    """Complete validation result for a document or check"""
    validator_name: str
    status: str = Field(..., description="'passed', 'warnings', or 'failed'")
    passed: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings"""
        return len(self.warnings) > 0
    
    @property
    def error_count(self) -> int:
        """Get count of errors"""
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        """Get count of warnings"""
        return len(self.warnings)
    
    def add_error(
        self,
        error_type: ValidationErrorType,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        **kwargs
    ):
        """Add an error to the result"""
        error = ValidationError(
            error_type=error_type,
            severity=severity,
            message=message,
            **kwargs
        )
        self.errors.append(error)
        self.passed = False
        if self.status == "passed":
            self.status = "failed"
    
    def add_warning(self, warning_type: str, message: str, **kwargs):
        """Add a warning to the result"""
        warning = ValidationWarning(
            warning_type=warning_type,
            message=message,
            **kwargs
        )
        self.warnings.append(warning)
        if self.status == "passed":
            self.status = "warnings"


class AggregatedValidationResult(BaseModel):
    """Aggregated validation results from multiple validators"""
    statement_id: str
    overall_status: str  # 'passed', 'warnings', 'failed'
    validators_run: List[str]
    results: Dict[str, ValidationResult]
    
    total_errors: int = 0
    total_warnings: int = 0
    
    @classmethod
    def from_results(cls, statement_id: str, results: Dict[str, ValidationResult]):
        """Create aggregated result from individual validator results"""
        total_errors = sum(r.error_count for r in results.values())
        total_warnings = sum(r.warning_count for r in results.values())
        
        # Determine overall status
        if total_errors > 0:
            overall_status = "failed"
        elif total_warnings > 0:
            overall_status = "warnings"
        else:
            overall_status = "passed"
        
        return cls(
            statement_id=statement_id,
            overall_status=overall_status,
            validators_run=list(results.keys()),
            results=results,
            total_errors=total_errors,
            total_warnings=total_warnings
        )
    
    @property
    def passed(self) -> bool:
        """Check if all validations passed"""
        return self.overall_status == "passed"
