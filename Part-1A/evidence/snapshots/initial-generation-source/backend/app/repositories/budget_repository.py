"""Parameterized SQL for monthly budgets (one row per month)."""

import sqlite3
from dataclasses import dataclass

from app.core.money import cents_to_text


@dataclass(frozen=True)
class BudgetRecord:
    month: str
    amount: str
    updated_at: str


def upsert(conn: sqlite3.Connection, month: str, amount_cents: int, stamp: str) -> BudgetRecord:
    with conn:
        conn.execute(
            "INSERT INTO monthly_budgets (month, amount_cents, updated_at) VALUES (?, ?, ?)"
            " ON CONFLICT(month) DO UPDATE SET amount_cents = excluded.amount_cents,"
            " updated_at = excluded.updated_at",
            (month, amount_cents, stamp),
        )
    return BudgetRecord(month=month, amount=cents_to_text(amount_cents), updated_at=stamp)


def get_cents(conn: sqlite3.Connection, month: str) -> int | None:
    row = conn.execute(
        "SELECT amount_cents FROM monthly_budgets WHERE month = ?", (month,)
    ).fetchone()
    return int(row["amount_cents"]) if row else None
