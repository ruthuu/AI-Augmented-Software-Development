"""G10: the database refuses NULL in every NOT NULL column of expenses (Principle III)."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.db.connection import connect
from app.db.migrate import initialize_database

INSERT_SQL = (
    "INSERT INTO expenses (amount_cents, description, category, payment_method, expense_date,"
    " created_at, updated_at) VALUES (:amount_cents, :description, :category, :payment_method,"
    " :expense_date, :created_at, :updated_at)"
)
VALID_ROW: dict[str, object] = {
    "amount_cents": 100,
    "description": "x",
    "category": "Food",
    "payment_method": "Cash",
    "expense_date": "2026-11-10",
    "created_at": "t",
    "updated_at": "t",
}


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    path = tmp_path / "t.db"
    initialize_database(path)
    connection = connect(path)
    yield connection
    connection.close()


def _expense_count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0])


def test_every_not_null_column_of_expenses_is_covered(conn: sqlite3.Connection) -> None:
    columns = conn.execute("PRAGMA table_info(expenses)").fetchall()
    not_null = {row[1] for row in columns if row[3] == 1 and row[5] == 0}
    assert not_null == set(VALID_ROW)


@pytest.mark.parametrize("column", list(VALID_ROW))
def test_a_null_in_a_required_column_is_refused(conn: sqlite3.Connection, column: str) -> None:
    row = {**VALID_ROW, column: None}
    with pytest.raises(
        sqlite3.IntegrityError, match=f"NOT NULL constraint failed: expenses.{column}"
    ):
        conn.execute(INSERT_SQL, row)
        conn.commit()
    assert _expense_count(conn) == 0
