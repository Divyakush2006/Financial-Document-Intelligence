"""
Extraction Validator - Comprehensive validation for bank statement data
Validates balance reconciliation, date consistency, and data completeness
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation result severity levels"""
    PASSED = "PASSED"
    WARNINGS = "WARNINGS"
    CRITICAL_ERRORS = "CRITICAL_ERRORS"


class IssueType(Enum):
    """Types of validation issues"""
    BALANCE_MISMATCH = "balance_mismatch"
    DATE_FORMAT_ERROR = "date_format_error"
    DATE_ORDER_ERROR = "date_chronology_error"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    TRANSACTION_COUNT_MISMATCH = "transaction_count_mismatch"
    FUTURE_DATE = "future_date"
    BALANCE_PROGRESSION = "balance_progression_error"


@dataclass
class ValidationIssue:
    """Represents a single validation issue"""
    issue_type: IssueType
    severity: str  # "ERROR" or "WARNING"
    message: str
    details: Optional[Dict] = None


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    validation_level: ValidationLevel
    balance_check: Dict
    date_check: Dict
    completeness_check: Dict
    issues: List[ValidationIssue]


class ExtractionValidator:
    """
    Validates extracted bank statement data for accuracy and consistency.
    """
    
    # Constants
    BALANCE_TOLERANCE = 0.50  # ±₹0.50 for rounding errors
    REQUIRED_FIELDS = [
        "statement_period_from",
        "statement_period_to",
        "opening_balance",
        "closing_balance",
        "transactions"
    ]
    
    def __init__(self):
        """Initialize validator"""
        self.issues: List[ValidationIssue] = []
    
    def validate(self, data: Dict) -> ValidationResult:
        """
        Run comprehensive validation on extracted data.
        
        Args:
            data: Extracted bank statement data dictionary
            
        Returns:
            ValidationResult with detailed checks and issues
        """
        self.issues = []  # Reset issues
        
        # Run validation checks
        completeness = self._validate_completeness(data)
        balance = self._validate_balance_reconciliation(data)
        dates = self._validate_dates(data)
        
        # Determine overall validation level
        has_errors = any(issue.severity == "ERROR" for issue in self.issues)
        has_warnings = any(issue.severity == "WARNING" for issue in self.issues)
        
        if has_errors:
            level = ValidationLevel.CRITICAL_ERRORS
            is_valid = False
        elif has_warnings:
            level = ValidationLevel.WARNINGS
            is_valid = True
        else:
            level = ValidationLevel.PASSED
            is_valid = True
        
        result = ValidationResult(
            is_valid=is_valid,
            validation_level=level,
            balance_check=balance,
            date_check=dates,
            completeness_check=completeness,
            issues=self.issues
        )
        
        logger.info(f"Validation complete: {level.value} ({len(self.issues)} issues found)")
        return result
    
    def _validate_completeness(self, data: Dict) -> Dict:
        """Check required fields are present"""
        missing_fields = []
        
        for field in self.REQUIRED_FIELDS:
            if field not in data or data[field] is None:
                missing_fields.append(field)
                self.issues.append(ValidationIssue(
                    issue_type=IssueType.MISSING_REQUIRED_FIELD,
                    severity="ERROR",
                    message=f"Required field missing: {field}"
                ))
        
        # Check transaction count
        declared_count = data.get("number_of_transactions", 0)
        actual_count = len(data.get("transactions", []))
        
        if declared_count != actual_count:
            self.issues.append(ValidationIssue(
                issue_type=IssueType.TRANSACTION_COUNT_MISMATCH,
                severity="WARNING",
                message=f"Transaction count mismatch: declared {declared_count}, actual {actual_count}",
                details={"declared": declared_count, "actual": actual_count}
            ))
        
        return {
            "required_fields_present": len(missing_fields) == 0,
            "missing_fields": missing_fields,
            "transaction_count_match": declared_count == actual_count,
            "declared_count": declared_count,
            "actual_count": actual_count
        }
    
    def _validate_balance_reconciliation(self, data: Dict) -> Dict:
        """
        Validate balance calculation: Opening + Credits - Debits = Closing
        """
        try:
            opening = float(data.get("opening_balance", 0))
            closing = float(data.get("closing_balance", 0))
            total_credits = float(data.get("total_credits", 0))
            total_debits = float(data.get("total_debits", 0))
            
            # Calculate expected closing balance
            expected_closing = opening + total_credits - total_debits
            difference = abs(closing - expected_closing)
            
            is_balanced = difference <= self.BALANCE_TOLERANCE
            
            if not is_balanced:
                self.issues.append(ValidationIssue(
                    issue_type=IssueType.BALANCE_MISMATCH,
                    severity="ERROR",
                    message=f"Balance mismatch: Expected ₹{expected_closing:.2f}, Got ₹{closing:.2f} (Diff: ₹{difference:.2f})",
                    details={
                        "opening": opening,
                        "credits": total_credits,
                        "debits": total_debits,
                        "expected_closing": expected_closing,
                        "actual_closing": closing,
                        "difference": difference
                    }
                ))
            
            # Validate transaction-level balance progression
            progression_valid = self._validate_transaction_balances(data)
            
            return {
                "is_balanced": is_balanced,
                "opening_balance": opening,
                "closing_balance": closing,
                "total_credits": total_credits,
                "total_debits": total_debits,
                "expected_closing": expected_closing,
                "difference": difference,
                "tolerance": self.BALANCE_TOLERANCE,
                "progression_valid": progression_valid
            }
            
        except (ValueError, TypeError) as e:
            logger.error(f"Balance validation error: {e}")
            self.issues.append(ValidationIssue(
                issue_type=IssueType.BALANCE_MISMATCH,
                severity="ERROR",
                message=f"Failed to validate balance: {str(e)}"
            ))
            return {"is_balanced": False, "error": str(e)}
    
    def _validate_transaction_balances(self, data: Dict) -> bool:
        """Validate that transaction balances progress correctly"""
        transactions = data.get("transactions", [])
        
        if not transactions:
            return True
        
        valid = True
        prev_balance = data.get("opening_balance", 0)
        
        for i, txn in enumerate(transactions):
            try:
                debit = float(txn.get("debit", 0))
                credit = float(txn.get("credit", 0))
                balance = float(txn.get("balance", 0))
                
                expected_balance = prev_balance + credit - debit
                difference = abs(balance - expected_balance)
                
                if difference > self.BALANCE_TOLERANCE:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.BALANCE_PROGRESSION,
                        severity="WARNING",
                        message=f"Transaction {i+1}: Balance progression error",
                        details={
                            "transaction_index": i,
                            "date": txn.get("date"),
                            "expected_balance": expected_balance,
                            "actual_balance": balance,
                            "difference": difference
                        }
                    ))
                    valid = False
                
                prev_balance = balance
                
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(f"Transaction {i} balance check failed: {e}")
                valid = False
        
        return valid
    
    def _validate_dates(self, data: Dict) -> Dict:
        """Validate date formats and chronological order"""
        try:
            # Validate period dates
            period_from = data.get("statement_period_from")
            period_to = data.get("statement_period_to")
            
            from_date = self._parse_date(period_from)
            to_date = self._parse_date(period_to)
            
            if from_date and to_date:
                if from_date > to_date:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.DATE_ORDER_ERROR,
                        severity="ERROR",
                        message=f"Statement period invalid: from {period_from} is after to {period_to}"
                    ))
            
            # Validate transaction dates
            transactions = data.get("transactions", [])
            prev_date = None
            chronological = True
            future_dates = []
            
            today = datetime.now().date()
            
            for i, txn in enumerate(transactions):
                txn_date_str = txn.get("date")
                txn_date = self._parse_date(txn_date_str)
                
                if not txn_date:
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.DATE_FORMAT_ERROR,
                        severity="WARNING",
                        message=f"Transaction {i+1}: Invalid date format '{txn_date_str}'"
                    ))
                    continue
                
                # Check for future dates
                if txn_date > today:
                    future_dates.append(txn_date_str)
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.FUTURE_DATE,
                        severity="WARNING",
                        message=f"Transaction {i+1}: Future date detected - {txn_date_str}"
                    ))
                
                # Check chronological order
                if prev_date and txn_date < prev_date:
                    chronological = False
                    self.issues.append(ValidationIssue(
                        issue_type=IssueType.DATE_ORDER_ERROR,
                        severity="WARNING",
                        message=f"Transaction {i+1}: Date {txn_date_str} is before previous transaction"
                    ))
                
                prev_date = txn_date
            
            return {
                "period_dates_valid": from_date is not None and to_date is not None,
                "period_from": period_from,
                "period_to": period_to,
                "chronological_order": chronological,
                "future_dates_count": len(future_dates),
                "future_dates": future_dates
            }
            
        except Exception as e:
            logger.error(f"Date validation error: {e}")
            return {"error": str(e)}
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object"""
        if not date_str:
            return None
        
        try:
            # Try YYYY-MM-DD format
            return datetime.strptime(str(date_str), "%Y-%m-%d").date()
        except ValueError:
            try:
                # Try DD-MM-YYYY format
                return datetime.strptime(str(date_str), "%d-%m-%Y").date()
            except ValueError:
                return None


# Singleton instance
_validator = None

def get_validator() -> ExtractionValidator:
    """Get or create validator instance"""
    global _validator
    if _validator is None:
        _validator = ExtractionValidator()
    return _validator
