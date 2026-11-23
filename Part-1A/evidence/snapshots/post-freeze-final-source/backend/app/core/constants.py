"""Single definition of categories, payment methods, and limits (all money in integer cents)."""

from dataclasses import dataclass
from datetime import date

CATEGORIES: tuple[str, ...] = (
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
)

PAYMENT_METHODS: tuple[str, ...] = (
    "Cash",
    "Credit Card",
    "Debit Card",
    "UPI",
    "Net Banking",
    "Other",
)


@dataclass(frozen=True)
class Limits:
    max_expense_cents: int = 999999999
    max_budget_cents: int = 9999999999
    min_amount_cents: int = 1
    max_description_length: int = 200
    min_date: date = date(2000, 1, 1)


LIMITS = Limits()
