"""Parameterized SQL for expenses. Money is converted between cents and text only here."""

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.money import cents_to_text
from app.schemas.expense import ValidExpense

_COLUMNS = (
    "id, amount_cents, description, category, payment_method, expense_date, created_at, updated_at"
)


@dataclass(frozen=True)
class ExpenseRecord:
    id: int
    amount: str
    description: str
    category: str
    payment_method: str
    expense_date: str
    created_at: str
    updated_at: str


def _record(row: sqlite3.Row) -> ExpenseRecord:
    return ExpenseRecord(
        id=row["id"],
        amount=cents_to_text(row["amount_cents"]),
        description=row["description"],
        category=row["category"],
        payment_method=row["payment_method"],
        expense_date=row["expense_date"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def insert(conn: sqlite3.Connection, data: ValidExpense, stamp: str) -> ExpenseRecord:
    with conn:
        cursor = conn.execute(
            "INSERT INTO expenses (amount_cents, description, category, payment_method,"
            " expense_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                data.amount_cents,
                data.description,
                data.category,
                data.payment_method,
                data.expense_date.isoformat(),
                stamp,
                stamp,
            ),
        )
    created = get(conn, int(cursor.lastrowid or 0))
    if created is None:
        raise RuntimeError("inserted expense could not be read back")
    return created


def insert_many(conn: sqlite3.Connection, items: Sequence[ValidExpense], stamp: str) -> int:
    """Insert all items in one transaction (used by the seed script)."""
    with conn:
        conn.executemany(
            "INSERT INTO expenses (amount_cents, description, category, payment_method,"
            " expense_date, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    item.amount_cents,
                    item.description,
                    item.category,
                    item.payment_method,
                    item.expense_date.isoformat(),
                    stamp,
                    stamp,
                )
                for item in items
            ],
        )
    return len(items)


def update(
    conn: sqlite3.Connection, expense_id: int, data: ValidExpense, stamp: str
) -> ExpenseRecord | None:
    with conn:
        cursor = conn.execute(
            "UPDATE expenses SET amount_cents = ?, description = ?, category = ?,"
            " payment_method = ?, expense_date = ?, updated_at = ? WHERE id = ?",
            (
                data.amount_cents,
                data.description,
                data.category,
                data.payment_method,
                data.expense_date.isoformat(),
                stamp,
                expense_id,
            ),
        )
    if cursor.rowcount == 0:
        return None
    return get(conn, expense_id)


def delete(conn: sqlite3.Connection, expense_id: int) -> bool:
    with conn:
        cursor = conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    return cursor.rowcount > 0


def get(conn: sqlite3.Connection, expense_id: int) -> ExpenseRecord | None:
    row = conn.execute(
        "SELECT id, amount_cents, description, category, payment_method, expense_date,"
        " created_at, updated_at FROM expenses WHERE id = ?",
        (expense_id,),
    ).fetchone()
    return _record(row) if row else None


def month_rows(conn: sqlite3.Connection, first_day: str, last_day: str) -> list[tuple[str, int]]:
    """(category, amount_cents) of every expense dated within the inclusive range."""
    rows = conn.execute(
        "SELECT category, amount_cents FROM expenses WHERE expense_date >= ? AND expense_date <= ?",
        (first_day, last_day),
    ).fetchall()
    return [(row["category"], int(row["amount_cents"])) for row in rows]


def count_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0])


def list_filtered(
    conn: sqlite3.Connection, month_range: tuple[str, str] | None, category: str | None
) -> list[ExpenseRecord]:
    """Newest first. Each filter combination is a fixed query with `?` placeholders only."""
    if month_range is not None and category is not None:
        rows = conn.execute(
            "SELECT id, amount_cents, description, category, payment_method, expense_date,"
            " created_at, updated_at FROM expenses"
            " WHERE expense_date >= ? AND expense_date <= ? AND category = ?"
            " ORDER BY expense_date DESC, id DESC",
            (month_range[0], month_range[1], category),
        ).fetchall()
    elif month_range is not None:
        rows = conn.execute(
            "SELECT id, amount_cents, description, category, payment_method, expense_date,"
            " created_at, updated_at FROM expenses"
            " WHERE expense_date >= ? AND expense_date <= ?"
            " ORDER BY expense_date DESC, id DESC",
            month_range,
        ).fetchall()
    elif category is not None:
        rows = conn.execute(
            "SELECT id, amount_cents, description, category, payment_method, expense_date,"
            " created_at, updated_at FROM expenses WHERE category = ?"
            " ORDER BY expense_date DESC, id DESC",
            (category,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, amount_cents, description, category, payment_method, expense_date,"
            " created_at, updated_at FROM expenses ORDER BY expense_date DESC, id DESC"
        ).fetchall()
    return [_record(row) for row in rows]
