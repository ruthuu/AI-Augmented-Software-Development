"""Pure validation rules: check order and messages come from data-model.md."""

import calendar
import re
import unicodedata
from datetime import date

from app.core import money
from app.core.constants import CATEGORIES, LIMITS, PAYMENT_METHODS
from app.core.errors import ValidationFailure

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ISO_MONTH = re.compile(r"\d{4}-\d{2}")


def _fail(field: str, message: str) -> ValidationFailure:
    return ValidationFailure([(field, message)])


def parse_amount(text: str | None) -> int:
    """Return the amount in cents, or raise with the first failing rule (never rounds)."""
    if text is None or text == "":
        raise _fail("amount", "Amount is required")
    result = money.analyze_amount_text(text)
    if result.kind != "valid":
        raise _fail("amount", "Enter a valid amount")
    if not result.is_positive:
        raise _fail("amount", "Amount must be greater than zero")
    if result.cents is None:
        raise _fail("amount", "Amount can have at most 2 decimal places")
    if result.cents < LIMITS.min_amount_cents:
        raise _fail("amount", "Amount must be greater than zero")
    if result.cents > LIMITS.max_expense_cents:
        raise _fail("amount", "Amount cannot exceed 9,999,999.99")
    return result.cents


def clean_description(text: str | None) -> str:
    """FR-042: tab, LF, CR become one space; other control characters are removed; then trim."""
    spaced = "".join(" " if ch in "\t\n\r" else ch for ch in text or "")
    kept = "".join(ch for ch in spaced if unicodedata.category(ch) != "Cc")
    cleaned = kept.strip(" ")
    if not cleaned:
        raise _fail("description", "Description is required")
    if len(cleaned) > LIMITS.max_description_length:
        raise _fail("description", "Description cannot exceed 200 characters")
    return cleaned


def parse_expense_date(text: str | None) -> date:
    """A real calendar date written as YYYY-MM-DD (the database only checks the shape)."""
    if text is None or text == "":
        raise _fail("expense_date", "Date is required")
    if _ISO_DATE.fullmatch(text) is None:
        raise _fail("expense_date", "Enter a valid date")
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise _fail("expense_date", "Enter a valid date") from None


def check_date_range(value: date, today: date) -> None:
    if value < LIMITS.min_date:
        raise _fail("expense_date", "Date cannot be before 01 Jan 2000")
    if value > today:
        raise _fail("expense_date", "Date cannot be in the future")


def validate_category(text: str | None) -> str:
    if text is None or text == "":
        raise _fail("category", "Category is required")
    if text not in CATEGORIES:
        raise _fail("category", "Select a valid category")
    return text


def validate_payment_method(text: str | None) -> str:
    if text is None or text == "":
        raise _fail("payment_method", "Payment method is required")
    if text not in PAYMENT_METHODS:
        raise _fail("payment_method", "Select a valid payment method")
    return text


def parse_budget(text: str | None) -> int:
    """Budget in cents: above zero, at most 99,999,999.99, at most two decimals; never rounds."""
    message = "Budget must be a number greater than zero"
    result = money.analyze_amount_text(text)
    if result.kind != "valid" or not result.is_positive:
        raise _fail("amount", message)
    if result.cents is None:
        raise _fail("amount", "Budget can have at most 2 decimal places")
    if result.cents < LIMITS.min_amount_cents:
        raise _fail("amount", message)
    if result.cents > LIMITS.max_budget_cents:
        raise _fail("amount", "Budget cannot exceed 99,999,999.99")
    return result.cents


def parse_month(text: str) -> str:
    """A real calendar month written as YYYY-MM (year 0001 to 9999); any real month is valid."""
    if _ISO_MONTH.fullmatch(text or "") is None:
        raise _fail("month", "Enter a valid month")
    year, month = int(text[:4]), int(text[5:])
    if year < 1 or not 1 <= month <= 12:
        raise _fail("month", "Enter a valid month")
    return text


def month_range(month: str) -> tuple[str, str]:
    """First and last day of the month, both inclusive, so December 9999 needs no next month."""
    year, number = int(month[:4]), int(month[5:])
    last_day = calendar.monthrange(year, number)[1]
    return date(year, number, 1).isoformat(), date(year, number, last_day).isoformat()
