"""Budget use case: month and amount are validated together before anything is written."""

import sqlite3
from datetime import datetime, timezone

from app.core.errors import ValidationFailure
from app.repositories import budget_repository
from app.repositories.budget_repository import BudgetRecord
from app.schemas.budget import BudgetIn
from app.services import validation


def save_budget(conn: sqlite3.Connection, month: str, payload: BudgetIn) -> BudgetRecord:
    errors: list[tuple[str, str]] = []
    valid_month: str | None = None
    cents: int | None = None
    try:
        valid_month = validation.parse_month(month)
    except ValidationFailure as failure:
        errors.extend((e.field, e.message) for e in failure.errors)
    try:
        cents = validation.parse_budget(payload.amount)
    except ValidationFailure as failure:
        errors.extend((e.field, e.message) for e in failure.errors)
    if errors or valid_month is None or cents is None:
        raise ValidationFailure(errors)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return budget_repository.upsert(conn, valid_month, cents, stamp)
