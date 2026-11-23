"""T020 (part 2): migrations and the database CHECK constraints (FR-015, US1 #27)."""

import re
import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.constants import LIMITS
from app.db.connection import connect
from app.db.migrate import apply_migrations, initialize_database

EXPENSE_SQL = (
    "INSERT INTO expenses (amount_cents, description, category, payment_method, expense_date,"
    " created_at, updated_at) VALUES (?, ?, 'Food', 'Cash', ?, 't', 't')"
)
BUDGET_SQL = "INSERT INTO monthly_budgets (month, amount_cents, updated_at) VALUES (?, ?, 't')"


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    path = tmp_path / "t.db"
    initialize_database(path)
    connection = connect(path)
    yield connection
    connection.close()


def _count(conn: sqlite3.Connection, table: str) -> int:
    row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()  # noqa: S608
    return int(row[0])


def _insert_expense(
    conn: sqlite3.Connection,
    cents: int = 100,
    description: str = "x",
    date_text: str = "2026-11-10",
) -> None:
    conn.execute(EXPENSE_SQL, (cents, description, date_text))
    conn.commit()


def test_applying_migrations_twice_is_safe(tmp_path: Path) -> None:
    path = tmp_path / "t.db"
    initialize_database(path)
    initialize_database(path)
    connection = connect(path)
    try:
        assert apply_migrations(connection) == []
        versions = [r[0] for r in connection.execute("SELECT version FROM schema_migrations")]
        assert versions == ["001_initial"]
    finally:
        connection.close()


def test_initializing_the_default_layout_creates_folder_and_file(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    assert not (tmp_path / "backend" / "data").exists()
    initialize_database(settings.default_db_path)
    assert (tmp_path / "backend" / "data").is_dir()
    assert settings.default_db_path.is_file()


def test_connection_enables_foreign_keys(conn: sqlite3.Connection) -> None:
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_check_limits_equal_the_constants(conn: sqlite3.Connection) -> None:
    pattern = re.compile(r"amount_cents\s*>\s*(\d+)\s+AND\s+amount_cents\s*<=\s*(\d+)")
    found: dict[str, tuple[int, int]] = {}
    for name, sql in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN"
        " ('expenses','monthly_budgets')"
    ):
        match = pattern.search(sql)
        assert match is not None, name
        found[name] = (int(match.group(1)), int(match.group(2)))
    assert found["expenses"] == (LIMITS.min_amount_cents - 1, LIMITS.max_expense_cents)
    assert found["monthly_budgets"] == (LIMITS.min_amount_cents - 1, LIMITS.max_budget_cents)
    assert (LIMITS.min_amount_cents, LIMITS.max_expense_cents, LIMITS.max_budget_cents) == (
        1,
        999999999,
        9999999999,
    )


@pytest.mark.parametrize("cents", [1, 999999999])
def test_expense_limits_are_accepted(conn: sqlite3.Connection, cents: int) -> None:
    _insert_expense(conn, cents)
    assert _count(conn, "expenses") == 1


@pytest.mark.parametrize("cents", [1, 9999999999])
def test_budget_limits_are_accepted(conn: sqlite3.Connection, cents: int) -> None:
    conn.execute(BUDGET_SQL, ("2026-11", cents))
    conn.commit()
    assert _count(conn, "monthly_budgets") == 1


@pytest.mark.parametrize("cents", [0, -1, 1000000000])
def test_expense_amounts_outside_the_limits_are_refused(
    conn: sqlite3.Connection, cents: int
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert_expense(conn, cents)
    assert _count(conn, "expenses") == 0


@pytest.mark.parametrize("cents", [0, -1, 10000000000])
def test_budget_amounts_outside_the_limits_are_refused(
    conn: sqlite3.Connection, cents: int
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BUDGET_SQL, ("2026-11", cents))
        conn.commit()
    assert _count(conn, "monthly_budgets") == 0


@pytest.mark.parametrize("date_text", ["2026/11/10", "2026-1-5", "10-11-2026", "abcd-ef-gh", ""])
def test_expense_date_without_the_iso_shape_is_refused(
    conn: sqlite3.Connection, date_text: str
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert_expense(conn, date_text=date_text)
    assert _count(conn, "expenses") == 0


@pytest.mark.parametrize("month", ["2026-1", "2026/11", "26-11", "abcd-ef", ""])
def test_budget_month_without_the_iso_shape_is_refused(
    conn: sqlite3.Connection, month: str
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(BUDGET_SQL, (month, 100))
        conn.commit()
    assert _count(conn, "monthly_budgets") == 0


@pytest.mark.parametrize("length", [0, 201])
def test_description_length_outside_1_to_200_is_refused(
    conn: sqlite3.Connection, length: int
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        _insert_expense(conn, description="a" * length)
    assert _count(conn, "expenses") == 0


@pytest.mark.parametrize("length", [1, 200])
def test_description_length_1_and_200_are_accepted(conn: sqlite3.Connection, length: int) -> None:
    _insert_expense(conn, description="a" * length)
    assert _count(conn, "expenses") == 1
