"""
Balance Continuity Validator
Validates that balances in bank statements are mathematically correct and continuous
"""

import logging
from typing import Dict, List, Optional
from decimal import Decimal, ROUND_HALF_UP

from .validation_models import (
    ValidationResult,
    ValidationError,
    ValidationErrorType,
    ValidationSeverity
)

logger = logging.getLogger(__name__)


class BalanceValidator:
    """
    Validates balance continuity in bank statements
    
    Key validations:
    1. Opening + Credits - Debits = Closing balance
    2. Each transaction balance is correctly calculated
    3. Sequential statements have continuous balances
    """
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize balance validator
        
        Args:
            tolerance: Acceptable difference for rounding errors (default 0.01)
        """
        self.tolerance = Decimal(str(tolerance))
        self.validator_name = "balance_validator"
    
    def validate_statement(self, statement_data: Dict) -> ValidationResult:
        """
        Validate all balance checks for a single statement
        
        Args:
            statement_data: Extracted bank statement data
            
        Returns:
            ValidationResult with all balance validation errors/warnings
        """
        result = ValidationResult(
            validator_name=self.validator_name,
            status="passed",
            passed=True,
            metadata={
                "tolerance": float(self.tolerance)
            }
        )
        
        # Check 1: Validate opening/closing balance calculation
        self._validate_opening_closing(statement_data, result)
        
        # Check 2: Validate individual transaction balances
        self._validate_transaction_balances(statement_data, result)
        
        # Check 3: Validate totals match sum of transactions
        self._validate_totals(statement_data, result)
        
        logger.info(
            f"[BalanceValidator] Validation complete: "
            f"{result.error_count} errors, {result.warning_count} warnings"
        )
        
        return result
    
    def _validate_opening_closing(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate: closing_balance = opening_balance + credits - debits"""
        try:
            opening = self._to_decimal(statement_data.get('opening_balance'))
            closing = self._to_decimal(statement_data.get('closing_balance'))
            total_credits = self._to_decimal(statement_data.get('total_credits', 0))
            total_debits = self._to_decimal(statement_data.get('total_debits', 0))
            
            # Check if required fields are present
            if opening is None or closing is None:
                result.add_error(
                    error_type=ValidationErrorType.MISSING_BALANCE,
                    message="Missing opening or closing balance",
                    severity=ValidationSeverity.ERROR,
                    field="opening_balance/closing_balance"
                )
                return
            
            # Calculate expected closing balance
            expected_closing = opening + total_credits - total_debits
            difference = abs(closing - expected_closing)
            
            if difference > self.tolerance:
                result.add_error(
                    error_type=ValidationErrorType.BALANCE_MISMATCH,
                    message=(
                        f"Closing balance mismatch. "
                        f"Expected: {expected_closing:.2f}, "
                        f"Actual: {closing:.2f}, "
                        f"Difference: {difference:.2f}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field="closing_balance",
                    expected=float(expected_closing),
                    actual=float(closing),
                    context={
                        "opening_balance": float(opening),
                        "total_credits": float(total_credits),
                        "total_debits": float(total_debits),
                        "calculation": f"{opening} + {total_credits} - {total_debits}"
                    }
                )
            elif difference > 0:
                # Small difference within tolerance - add warning
                result.add_warning(
                    warning_type="minor_balance_difference",
                    message=f"Minor rounding difference in closing balance: {difference:.2f}",
                    field="closing_balance",
                    recommendation="Verify rounding rules with bank"
                )
        
        except Exception as e:
            logger.error(f"Error validating opening/closing balance: {e}")
            result.add_error(
                error_type=ValidationErrorType.CALCULATION_ERROR,
                message=f"Failed to validate opening/closing balance: {str(e)}",
                severity=ValidationSeverity.ERROR
            )
    
    def _validate_transaction_balances(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate each transaction's balance calculation"""
        transactions = statement_data.get('transactions', [])
        
        if not transactions:
            result.add_warning(
                warning_type="no_transactions",
                message="No transactions found in statement",
                recommendation="Verify OCR extracted transaction table correctly"
            )
            return
        
        opening_balance = self._to_decimal(statement_data.get('opening_balance'))
        if opening_balance is None:
            return  # Already flagged in previous check
        
        running_balance = opening_balance
        
        for idx, transaction in enumerate(transactions):
            try:
                debit = self._to_decimal(transaction.get('debit', 0))
                credit = self._to_decimal(transaction.get('credit', 0))
                stated_balance = self._to_decimal(transaction.get('balance'))
                
                # Calculate expected balance
                if credit > 0:
                    expected_balance = running_balance + credit
                else:
                    expected_balance = running_balance - debit
                
                # Check if stated balance matches
                if stated_balance is not None:
                    difference = abs(stated_balance - expected_balance)
                    
                    if difference > self.tolerance:
                        result.add_error(
                            error_type=ValidationErrorType.BALANCE_MISMATCH,
                            message=(
                                f"Transaction {idx + 1}: Balance mismatch. "
                                f"Expected: {expected_balance:.2f}, "
                                f"Stated: {stated_balance:.2f}"
                            ),
                            severity=ValidationSeverity.ERROR,
                            field=f"transactions[{idx}].balance",
                            expected=float(expected_balance),
                            actual=float(stated_balance),
                            context={
                                "transaction_index": idx,
                                "transaction_date": transaction.get('date'),
                                "description": transaction.get('description', '')[:50],
                                "debit": float(debit),
                                "credit": float(credit)
                            }
                        )
                    else:
                        # Update running balance with stated balance for next iteration
                        running_balance = stated_balance
                else:
                    # No balance stated in transaction, use calculated
                    running_balance = expected_balance
            
            except Exception as e:
                logger.error(f"Error validating transaction {idx}: {e}")
                result.add_error(
                    error_type=ValidationErrorType.CALCULATION_ERROR,
                    message=f"Transaction {idx + 1}: Validation failed - {str(e)}",
                    severity=ValidationSeverity.WARNING,
                    field=f"transactions[{idx}]"
                )
    
    def _validate_totals(
        self,
        statement_data: Dict,
        result: ValidationResult
    ):
        """Validate that total credits/debits match sum of transactions"""
        transactions = statement_data.get('transactions', [])
        if not transactions:
            return
        
        stated_credits = self._to_decimal(statement_data.get('total_credits'))
        stated_debits = self._to_decimal(statement_data.get('total_debits'))
        
        # Calculate actual totals from transactions
        actual_credits = sum(
            self._to_decimal(t.get('credit', 0))
            for t in transactions
        )
        actual_debits = sum(
            self._to_decimal(t.get('debit', 0))
            for t in transactions
        )
        
        # Check credits
        if stated_credits is not None:
            diff = abs(stated_credits - actual_credits)
            if diff > self.tolerance:
                result.add_error(
                    error_type=ValidationErrorType.CALCULATION_ERROR,
                    message=(
                        f"Total credits mismatch. "
                        f"Stated: {stated_credits:.2f}, "
                        f"Sum of transactions: {actual_credits:.2f}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field="total_credits",
                    expected=float(actual_credits),
                    actual=float(stated_credits)
                )
        
        # Check debits
        if stated_debits is not None:
            diff = abs(stated_debits - actual_debits)
            if diff > self.tolerance:
                result.add_error(
                    error_type=ValidationErrorType.CALCULATION_ERROR,
                    message=(
                        f"Total debits mismatch. "
                        f"Stated: {stated_debits:.2f}, "
                        f"Sum of transactions: {actual_debits:.2f}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    field="total_debits",
                    expected=float(actual_debits),
                    actual=float(stated_debits)
                )
    
    def validate_multi_statement_continuity(
        self,
        statements: List[Dict],
        sort_by_date: bool = True
    ) -> ValidationResult:
        """
        Validate balance continuity across multiple sequential statements
        
        Args:
            statements: List of bank statement data (same account)
            sort_by_date: Whether to sort statements by period_to date
            
        Returns:
            ValidationResult for cross-statement validation
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
            result.add_warning(
                warning_type="insufficient_statements",
                message="Need at least 2 statements to validate continuity",
                recommendation="Upload sequential statements for the same account"
            )
            return result
        
        # Sort statements by end date if requested
        if sort_by_date:
            statements = sorted(
                statements,
                key=lambda s: s.get('statement_period_to', '1900-01-01')
            )
        
        # Check each consecutive pair
        for i in range(len(statements) - 1):
            current = statements[i]
            next_stmt = statements[i + 1]
            
            current_closing = self._to_decimal(current.get('closing_balance'))
            next_opening = self._to_decimal(next_stmt.get('opening_balance'))
            
            if current_closing is None or next_opening is None:
                continue
            
            difference = abs(current_closing - next_opening)
            
            if difference > self.tolerance:
                result.add_error(
                    error_type=ValidationErrorType.CROSS_DOC_INCONSISTENCY,
                    message=(
                        f"Balance discontinuity between statements. "
                        f"Statement {i+1} closing: {current_closing:.2f}, "
                        f"Statement {i+2} opening: {next_opening:.2f}"
                    ),
                    severity=ValidationSeverity.ERROR,
                    context={
                        "statement_1_period": f"{current.get('statement_period_from')} to {current.get('statement_period_to')}",
                        "statement_2_period": f"{next_stmt.get('statement_period_from')} to {next_stmt.get('statement_period_to')}",
                        "difference": float(difference)
                    }
                )
        
        return result
    
    @staticmethod
    def _to_decimal(value) -> Optional[Decimal]:
        """
        Convert value to Decimal for precise calculations
        
        Args:
            value: Number or string to convert
            
        Returns:
            Decimal value or None if invalid
        """
        if value is None:
            return None
        
        try:
            # Handle string or numeric input
            if isinstance(value, str):
                # Remove commas and currency symbols
                value = value.replace(',', '').replace('₹', '').replace('$', '').strip()
            
            decimal_value = Decimal(str(value))
            # Round to 2 decimal places
            return decimal_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert '{value}' to Decimal")
            return None


# Singleton instance
_balance_validator = None

def get_balance_validator(tolerance: float = 0.01) -> BalanceValidator:
    """Get or create balance validator instance"""
    global _balance_validator
    if _balance_validator is None:
        _balance_validator = BalanceValidator(tolerance=tolerance)
    return _balance_validator
