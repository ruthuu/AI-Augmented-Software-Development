"""Expense request and response models."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.errors import ValidationFailure
from app.services import validation

T = TypeVar("T")


@dataclass(frozen=True)
class ValidExpense:
    amount_cents: int
    description: str
    category: str
    payment_method: str
    expense_date: date


def _attempt(
    parser: Callable[[str | None], T], value: str | None, errors: list[tuple[str, str]]
) -> T | None:
    try:
        return parser(value)
    except ValidationFailure as failure:
        errors.extend((e.field, e.message) for e in failure.errors)
        return None


class ExpenseIn(BaseModel):
    """Shape only: unknown fields are refused; every rule lives in services/validation.py."""

    model_config = ConfigDict(extra="forbid", strict=True)

    amount: str | None = None
    description: str | None = None
    category: str | None = None
    payment_method: str | None = None
    expense_date: str | None = None

    def to_valid(self, today: date) -> ValidExpense:
        """Run every parser, report all failing fields together, then check the date range."""
        errors: list[tuple[str, str]] = []
        amount = _attempt(validation.parse_amount, self.amount, errors)
        description = _attempt(validation.clean_description, self.description, errors)
        category = _attempt(validation.validate_category, self.category, errors)
        method = _attempt(validation.validate_payment_method, self.payment_method, errors)
        day = _attempt(validation.parse_expense_date, self.expense_date, errors)
        if day is not None:
            _attempt(lambda _: validation.check_date_range(day, today), None, errors)
        if (
            errors
            or amount is None
            or description is None
            or category is None
            or method is None
            or day is None
        ):
            raise ValidationFailure(errors)
        return ValidExpense(amount, description, category, method, day)


class ExpenseOut(BaseModel):
    id: int
    amount: str
    description: str
    category: str
    payment_method: str
    expense_date: str
    created_at: str
    updated_at: str
