"""Expense use cases: validate first, write only when everything is valid."""

import sqlite3
from datetime import date, datetime, timezone

from app.core.errors import NotFound, ValidationFailure
from app.repositories import expense_repository as repository
from app.repositories.expense_repository import ExpenseRecord
from app.schemas.expense import ExpenseIn
from app.services import validation

_MAX_SQLITE_INTEGER = 2**63 - 1


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _checked_id(expense_id: int) -> int:
    if expense_id < 1 or expense_id > _MAX_SQLITE_INTEGER:
        raise NotFound()
    return expense_id


def create(conn: sqlite3.Connection, payload: ExpenseIn, today: date) -> ExpenseRecord:
    return repository.insert(conn, payload.to_valid(today), _now())


def update(
    conn: sqlite3.Connection, expense_id: int, payload: ExpenseIn, today: date
) -> ExpenseRecord:
    data = payload.to_valid(today)
    updated = repository.update(conn, _checked_id(expense_id), data, _now())
    if updated is None:
        raise NotFound()
    return updated


def delete(conn: sqlite3.Connection, expense_id: int) -> None:
    if not repository.delete(conn, _checked_id(expense_id)):
        raise NotFound()


def list_expenses(
    conn: sqlite3.Connection, month: str | None = None, category: str | None = None
) -> list[ExpenseRecord]:
    """Optional filters; empty values mean no filter; every invalid filter is reported together."""
    errors: list[tuple[str, str]] = []
    month_range: tuple[str, str] | None = None
    if month:
        try:
            month_range = validation.month_range(validation.parse_month(month))
        except ValidationFailure as failure:
            errors.extend((e.field, e.message) for e in failure.errors)
    if category:
        try:
            validation.validate_category(category)
        except ValidationFailure as failure:
            errors.extend((e.field, e.message) for e in failure.errors)
    if errors:
        raise ValidationFailure(errors)
    return repository.list_filtered(conn, month_range, category or None)
