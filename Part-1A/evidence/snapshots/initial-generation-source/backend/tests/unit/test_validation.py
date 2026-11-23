"""T034: expense validation rules and messages (data-model.md), values from the spec."""

from collections.abc import Callable
from datetime import date

import pytest

from app.core.errors import ValidationFailure
from app.services import validation

TODAY = date(2026, 11, 12)


def failure(call: Callable[[], object]) -> tuple[str, str]:
    with pytest.raises(ValidationFailure) as caught:
        call()
    assert len(caught.value.errors) == 1
    error = caught.value.errors[0]
    return error.field, error.message


@pytest.mark.parametrize(
    ("text", "cents"),
    [("0.01", 1), ("12", 1200), ("12.5", 1250), ("12.50", 1250), ("9999999.99", 999999999)],
)
def test_accepted_amounts(text: str, cents: int) -> None:
    assert validation.parse_amount(text) == cents


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "Amount is required"),
        (None, "Amount is required"),
        ("abc", "Enter a valid amount"),
        ("12.", "Enter a valid amount"),
        (".5", "Enter a valid amount"),
        ("1,000", "Enter a valid amount"),
        ("1e3", "Enter a valid amount"),
        ("   ", "Enter a valid amount"),
        ("0", "Amount must be greater than zero"),
        ("0.00", "Amount must be greater than zero"),
        ("-5", "Amount must be greater than zero"),
        ("-0.001", "Amount must be greater than zero"),
        ("12.345", "Amount can have at most 2 decimal places"),
        ("12.500", "Amount can have at most 2 decimal places"),
        ("0.005", "Amount can have at most 2 decimal places"),
        ("12.999", "Amount can have at most 2 decimal places"),
        ("9999999.995", "Amount can have at most 2 decimal places"),
        ("10000000.005", "Amount can have at most 2 decimal places"),
        ("10000000.00", "Amount cannot exceed 9,999,999.99"),
        ("10000000.01", "Amount cannot exceed 9,999,999.99"),
        ("99999999999999999999.99", "Amount cannot exceed 9,999,999.99"),
    ],
)
def test_rejected_amounts(text: str | None, message: str) -> None:
    assert failure(lambda: validation.parse_amount(text)) == ("amount", message)


@pytest.mark.parametrize(
    ("text", "cleaned"),
    [
        ("Lunch", "Lunch"),
        ("  Lunch  ", "Lunch"),
        ("Tea\tSnacks", "Tea Snacks"),
        ("Tea\nSnacks", "Tea Snacks"),
        ("Tea\rSnacks", "Tea Snacks"),
        ("Tea\r\nSnacks", "Tea  Snacks"),
        ("A\u0000b", "Ab"),
        ("A\u007fb", "Ab"),
        ('<b>Tom & "Jerry\'s"</b>', '<b>Tom & "Jerry\'s"</b>'),
        ("back\\slash", "back\\slash"),
        ("Caf\u00e9 \u65e5\u672c\u8a9e \U0001f600", "Caf\u00e9 \u65e5\u672c\u8a9e \U0001f600"),
        ("a" * 200, "a" * 200),
        ("a" * 200 + "  ", "a" * 200),
        ("a" * 200 + "\u0007", "a" * 200),
    ],
)
def test_accepted_descriptions_are_cleaned(text: str, cleaned: str) -> None:
    assert validation.clean_description(text) == cleaned


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("", "Description is required"),
        (None, "Description is required"),
        ("   ", "Description is required"),
        ("\t\n\r", "Description is required"),
        ("\u0000\u0007 \u007f", "Description is required"),
        ("a" * 201, "Description cannot exceed 200 characters"),
        ("a" * 200 + "\u0007b", "Description cannot exceed 200 characters"),
    ],
)
def test_rejected_descriptions(text: str | None, message: str) -> None:
    assert failure(lambda: validation.clean_description(text)) == ("description", message)


@pytest.mark.parametrize(
    ("text", "parsed"),
    [
        ("2024-02-29", date(2024, 2, 29)),
        ("2000-01-01", date(2000, 1, 1)),
        ("2026-11-12", TODAY),
        ("1999-12-31", date(1999, 12, 31)),
        ("2026-11-13", date(2026, 11, 13)),
    ],
)
def test_real_calendar_dates_are_parsed(text: str, parsed: date) -> None:
    assert validation.parse_expense_date(text) == parsed


@pytest.mark.parametrize(
    "text",
    [
        "2025-02-29",
        "2026-02-29",
        "2026-02-30",
        "2026-13-01",
        "2026-00-10",
        "abc",
        "2026-1-5",
        "20261112",
    ],
)
def test_impossible_or_misshaped_dates(text: str) -> None:
    assert failure(lambda: validation.parse_expense_date(text)) == (
        "expense_date",
        "Enter a valid date",
    )


@pytest.mark.parametrize("text", ["", None])
def test_missing_date(text: str | None) -> None:
    assert failure(lambda: validation.parse_expense_date(text)) == (
        "expense_date",
        "Date is required",
    )


@pytest.mark.parametrize("text", ["2024-02-29", "2000-01-01", "2026-11-12"])
def test_dates_in_range_are_accepted(text: str) -> None:
    validation.check_date_range(date.fromisoformat(text), TODAY)


def test_date_before_2000_is_rejected() -> None:
    assert failure(lambda: validation.check_date_range(date(1999, 12, 31), TODAY)) == (
        "expense_date",
        "Date cannot be before 01 Jan 2000",
    )


@pytest.mark.parametrize("text", ["2026-11-13", "2999-01-01"])
def test_date_after_today_is_rejected(text: str) -> None:
    assert failure(lambda: validation.check_date_range(date.fromisoformat(text), TODAY)) == (
        "expense_date",
        "Date cannot be in the future",
    )


def test_the_future_check_follows_the_given_today() -> None:
    validation.check_date_range(date(2026, 11, 13), date(2026, 11, 13))
    assert failure(lambda: validation.check_date_range(date(2026, 11, 13), TODAY))[1] == (
        "Date cannot be in the future"
    )


@pytest.mark.parametrize(
    "category",
    ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Healthcare", "Education", "Other"],
)
def test_each_category_is_accepted(category: str) -> None:
    assert validation.validate_category(category) == category


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (None, "Category is required"),
        ("", "Category is required"),
        ("food", "Select a valid category"),
        ("Groceries", "Select a valid category"),
        ("Food ", "Select a valid category"),
    ],
)
def test_rejected_categories(text: str | None, message: str) -> None:
    assert failure(lambda: validation.validate_category(text)) == ("category", message)


@pytest.mark.parametrize(
    "method", ["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking", "Other"]
)
def test_each_payment_method_is_accepted(method: str) -> None:
    assert validation.validate_payment_method(method) == method


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (None, "Payment method is required"),
        ("", "Payment method is required"),
        ("Bitcoin", "Select a valid payment method"),
        ("upi", "Select a valid payment method"),
        ("Credit  Card", "Select a valid payment method"),
    ],
)
def test_rejected_payment_methods(text: str | None, message: str) -> None:
    assert failure(lambda: validation.validate_payment_method(text)) == (
        "payment_method",
        message,
    )


@pytest.mark.parametrize("text", ["2026-11", "1999-12", "0001-01", "9999-12", "2024-02"])
def test_real_months_are_accepted(text: str) -> None:
    assert validation.parse_month(text) == text


@pytest.mark.parametrize(
    "text", ["2026-13", "2026-00", "0000-01", "26-11", "2026-1", "abc", "", "2026-11-01"]
)
def test_malformed_months_are_rejected(text: str) -> None:
    assert failure(lambda: validation.parse_month(text)) == ("month", "Enter a valid month")


@pytest.mark.parametrize(
    ("month", "first", "last"),
    [
        ("2026-11", "2026-11-01", "2026-11-30"),
        ("2025-12", "2025-12-01", "2025-12-31"),
        ("2024-02", "2024-02-01", "2024-02-29"),
        ("2025-02", "2025-02-01", "2025-02-28"),
        ("9999-12", "9999-12-01", "9999-12-31"),
        ("0001-01", "0001-01-01", "0001-01-31"),
    ],
)
def test_month_range_is_inclusive_and_never_overflows(month: str, first: str, last: str) -> None:
    assert validation.month_range(month) == (first, last)


@pytest.mark.parametrize(
    ("text", "cents"),
    [
        ("0.01", 1),
        ("99999999.99", 9999999999),
        ("12000", 1200000),
        ("12000.5", 1200050),
        ("10000.00", 1000000),
    ],
)
def test_accepted_budgets(text: str, cents: int) -> None:
    assert validation.parse_budget(text) == cents


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("0", "Budget must be a number greater than zero"),
        ("0.00", "Budget must be a number greater than zero"),
        ("-100", "Budget must be a number greater than zero"),
        ("", "Budget must be a number greater than zero"),
        (None, "Budget must be a number greater than zero"),
        ("   ", "Budget must be a number greater than zero"),
        ("abc", "Budget must be a number greater than zero"),
        ("1,000", "Budget must be a number greater than zero"),
        ("12000.999", "Budget can have at most 2 decimal places"),
        ("0.005", "Budget can have at most 2 decimal places"),
        ("99999999.995", "Budget can have at most 2 decimal places"),
        ("100000000.00", "Budget cannot exceed 99,999,999.99"),
        ("100000000.01", "Budget cannot exceed 99,999,999.99"),
    ],
)
def test_rejected_budgets(text: str | None, message: str) -> None:
    assert failure(lambda: validation.parse_budget(text)) == ("amount", message)
