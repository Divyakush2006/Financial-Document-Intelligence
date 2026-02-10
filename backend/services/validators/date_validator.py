"""
Date Sequencing Validator
Validates chronological ordering and date consistency in bank statements
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter

from .validation_models import (
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


class DateSequencingValidator:
    """
    Validates date sequencing and consistency in bank statements
    
    Key validations:
    1. Transactions are in chronological order
    2. All transaction dates within statement period
    3. No duplicate transaction dates with same description
    4. No unrealistic date gaps
    5. Statement periods don't overlap
    """
    
    def __init__(self, max_gap_days: int = 60):
        """
        Initialize date validator
        
        Args:
            max_gap_days: Maximum allowed gap between transactions (default 60)
        """
        self.max_gap_days = max_gap_days
        self.validator_name = "date_sequencing_validator"
    
    def validate_statement(self, statement_data: Dict) -> ValidationResult:
        """
        Validate all date checks for a single statement
        
        Args:
            statement_data: Extracted bank statement data
            
        Returns:
            ValidationResult with all date validation errors/warnings
        """
        result = ValidationResult(
            validator_name=self.validator_name,
            status="passed",
            passed=True,
            metadata={
                "max_gap_days": self.max_gap_days
            }
        )
        
        # Check 1: Validate statement period dates
        self._validate_period_dates(statement_data, result)
        
        # Check 2: Validate transaction date ordering
        self._validate_transaction_ordering(statement_data, result)
        
        # Check 3: Validate transactions within period
        self._validate_dates_in_period(statement_data, result)
        
        # Check 4: Detect date anomalies
        self._detect_date_anomalies(statement_data, result)
        
        # Check 5: Check for large transaction gaps
        self._check_transaction_gaps(statement_data, result)
        
        logger.info(
            f"[DateSequencingValidator] Validation complete: "
            f"{result.error_count} errors, {result.warning_count} warnings"
        )
        
        return result
    
    def _validate_period_dates(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate statement period from/to dates are valid"""
        period_from = self._parse_date(statement_data.get('statement_period_from'))
        period_to = self._parse_date(statement_data.get('statement_period_to'))
        
        if period_from is None or period_to is None:
            result.add_error(
                error_type=ValidationErrorType.DATE_OUT_OF_RANGE,
                message="Missing statement period dates",
                severity=ValidationSeverity.ERROR,
                field="statement_period_from/statement_period_to"
            )
            return
        
        # Check period_to > period_from
        if period_to <= period_from:
            result.add_error(
                error_type=ValidationErrorType.DATE_OUT_OF_ORDER,
                message=(
                    f"Statement period invalid: "
                    f"End date ({period_to.date()}) is before or same as "
                    f"start date ({period_from.date()})"
                ),
                severity=ValidationSeverity.ERROR,
                field="statement_period_to",
                context={
                    "period_from": statement_data.get('statement_period_from'),
                    "period_to": statement_data.get('statement_period_to')
                }
            )
        
        # Check period is not in future
        today = datetime.now()
        if period_to > today:
            result.add_warning(
                warning_type="future_date",
                message=f"Statement period end date ({period_to.date()}) is in the future",
                field="statement_period_to",
                recommendation="Verify this is correct"
            )
        
        # Check period length is reasonable (typically 1-6 months)
        period_days = (period_to - period_from).days
        if period_days > 186:  # > 6 months
            result.add_warning(
                warning_type="long_period",
                message=f"Statement period is unusually long: {period_days} days",
                field="statement_period",
                recommendation="Verify this is a valid statement"
            )
    
    def _validate_transaction_ordering(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate transactions are in chronological order"""
        transactions = statement_data.get('transactions', [])
        
        if not transactions:
            return
        
        prev_date = None
        for idx, transaction in enumerate(transactions):
            current_date = self._parse_date(transaction.get('date'))
            
            if current_date is None:
                result.add_error(
                    error_type=ValidationErrorType.DATE_OUT_OF_RANGE,
                    message=f"Transaction {idx + 1}: Missing or invalid date",
                    severity=ValidationSeverity.ERROR,
                    field=f"transactions[{idx}].date",
                    context={
                        "transaction_index": idx,
                        "description": transaction.get('description', '')[:50]
                    }
                )
                continue
            
            # Check chronological order
            if prev_date is not None and current_date < prev_date:
                result.add_error(
                    error_type=ValidationErrorType.DATE_OUT_OF_ORDER,
                    message=(
                        f"Transaction {idx + 1}: Date out of order. "
                        f"Current: {current_date.date()}, Previous: {prev_date.date()}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field=f"transactions[{idx}].date",
                    context={
                        "current_date": current_date.date().isoformat(),
                        "previous_date": prev_date.date().isoformat(),
                        "current_description": transaction.get('description', '')[:50]
                    }
                )
            
            prev_date = current_date
    
    def _validate_dates_in_period(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate all transaction dates are within statement period"""
        period_from = self._parse_date(statement_data.get('statement_period_from'))
        period_to = self._parse_date(statement_data.get('statement_period_to'))
        
        if period_from is None or period_to is None:
            return  # Already flagged in period validation
        
        transactions = statement_data.get('transactions', [])
        
        for idx, transaction in enumerate(transactions):
            trans_date = self._parse_date(transaction.get('date'))
            
            if trans_date is None:
                continue  # Already flagged
            
            # Check if transaction date is outside period
            if trans_date < period_from or trans_date > period_to:
                result.add_error(
                    error_type=ValidationErrorType.DATE_OUT_OF_RANGE,
                    message=(
                        f"Transaction {idx + 1}: Date {trans_date.date()} "
                        f"outside statement period "
                        f"({period_from.date()} to {period_to.date()})"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field=f"transactions[{idx}].date",
                    context={
                        "transaction_date": trans_date.date().isoformat(),
                        "period_from": period_from.date().isoformat(),
                        "period_to": period_to.date().isoformat(),
                        "description": transaction.get('description', '')[:50]
                    }
                )
    
    def _detect_date_anomalies(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Detect suspicious date patterns"""
        transactions = statement_data.get('transactions', [])
        
        if len(transactions) < 2:
            return
        
        # Check for duplicate dates with same description (potential duplicate entry)
        date_desc_combos = []
        for idx, transaction in enumerate(transactions):
            trans_date = self._parse_date(transaction.get('date'))
            if trans_date:
                desc = transaction.get('description', '').strip().lower()
                date_desc_combos.append((trans_date.date(), desc, idx))
        
        # Count duplicates
        combo_counts = Counter([
            (date, desc) for date, desc, idx in date_desc_combos
        ])
        
        for (date, desc), count in combo_counts.items():
            if count > 1:
                # Find indices of duplicates
                duplicate_indices = [
                    idx for d, dsc, idx in date_desc_combos
                    if d == date and dsc == desc
                ]
                
                result.add_warning(
                    warning_type="possible_duplicate",
                    message=(
                        f"Possible duplicate transactions on {date}: "
                        f"\"{desc[:40]}\" appears {count} times"
                    ),
                    field="transactions",
                    recommendation="Verify these are not duplicate entries",
                    context={
                        "date": date.isoformat(),
                        "description": desc[:100],
                        "indices": duplicate_indices,
                        "count": count
                    }
                )
    
    def _check_transaction_gaps(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Check for unusually large gaps between transactions"""
        transactions = statement_data.get('transactions', [])
        
        if len(transactions) < 2:
            return
        
        # Parse all transaction dates
        dates = []
        for transaction in transactions:
            trans_date = self._parse_date(transaction.get('date'))
            if trans_date:
                dates.append(trans_date)
        
        if len(dates) < 2:
            return
        
        # Sort dates
        dates.sort()
        
        # Check gaps between consecutive transactions
        for i in range(len(dates) - 1):
            gap = (dates[i + 1] - dates[i]).days
            
            if gap > self.max_gap_days:
                result.add_warning(
                    warning_type="large_transaction_gap",
                    message=(
                        f"Large gap ({gap} days) between transactions: "
                        f"{dates[i].date()} to {dates[i + 1].date()}"
                    ),
                    field="transactions",
                    recommendation="Verify no missing transactions in this period",
                    context={
                        "gap_days": gap,
                        "date_from": dates[i].date().isoformat(),
                        "date_to": dates[i + 1].date().isoformat()
                    }
                )
    
    def validate_multi_statement_periods(
        self,
        statements: List[Dict],
        sort_by_date: bool = True
    ) -> ValidationResult:
        """
        Validate statement periods don't overlap and have no large gaps
        
        Args:
            statements: List of bank statement data
            sort_by_date: Whether to sort statements by period_from
            
        Returns:
            ValidationResult for cross-statement period validation
        """
        result = ValidationResult(
            validator_name=f"{self.validator_name}_multi",
            status="passed",
            passed=True,
            metadata={
                "statement_count": len(statements)
            }
        )
        
        if len(statements) < 2:
            return result
        
        # Sort statements by start date if requested
        if sort_by_date:
            statements = sorted(
                statements,
                key=lambda s: s.get('statement_period_from', '1900-01-01')
            )
        
        # Check each consecutive pair
        for i in range(len(statements) - 1):
            current = statements[i]
            next_stmt = statements[i + 1]
            
            current_to = self._parse_date(current.get('statement_period_to'))
            next_from = self._parse_date(next_stmt.get('statement_period_from'))
            
            if current_to is None or next_from is None:
                continue
            
            # Check for overlapping periods
            if current_to >= next_from:
                overlap_days = (current_to - next_from).days + 1
                result.add_error(
                    error_type=ValidationErrorType.CROSS_DOC_INCONSISTENCY,
                    message=(
                        f"Statement periods overlap by {overlap_days} days. "
                        f"Statement {i+1} ends {current_to.date()}, "
                        f"Statement {i+2} starts {next_from.date()}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    context={
                        "statement_1_period": f"{current.get('statement_period_from')} to {current.get('statement_period_to')}",
                        "statement_2_period": f"{next_stmt.get('statement_period_from')} to {next_stmt.get('statement_period_to')}",
                        "overlap_days": overlap_days
                    }
                )
            
            # Check for gaps between statements
            gap_days = (next_from - current_to).days - 1
            if gap_days > 7:  # More than a week gap
                result.add_warning(
                    warning_type="statement_gap",
                    message=(
                        f"Gap of {gap_days} days between statements. "
                        f"Statement {i+1} ends {current_to.date()}, "
                        f"Statement {i+2} starts {next_from.date()}"
                    ),
                    recommendation="Consider uploading missing statement",
                    context={
                        "gap_days": gap_days,
                        "gap_from": current_to.date().isoformat(),
                        "gap_to": next_from.date().isoformat()
                    }
                )
        
        return result
    
    @staticmethod
    def _parse_date(date_value) -> Optional[datetime]:
        """
        Parse date from string or date object
        
        Args:
            date_value: Date string (YYYY-MM-DD) or datetime object
            
        Returns:
            datetime object or None if invalid
        """
        if date_value is None:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            except ValueError:
                # Try other common formats
                for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except ValueError:
                        continue
        
        logger.warning(f"Could not parse date: {date_value}")
        return None


# Singleton instance
_date_validator = None

def get_date_validator(max_gap_days: int = 60) -> DateSequencingValidator:
    """Get or create date validator instance"""
    global _date_validator
    if _date_validator is None:
        _date_validator = DateSequencingValidator(max_gap_days=max_gap_days)
    return _date_validator
