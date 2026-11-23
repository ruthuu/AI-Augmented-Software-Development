r"""Deterministic seed data for manual checks (V5, V8, V10) and tests.

    python backend/scripts/seed.py --count 50 --db backend\data\seed-50.db

Expense i (counting from 0) gets category CATEGORIES[i % 8], payment method
PAYMENT_METHODS[(i * 5) % 6], date 2026-09-01 plus (i * 29) % 73 days (so September 1 to
November 12, 2026), and an amount of 10.00 plus ((i * 7919) % 99000) cents. Timestamps are fixed.
The script writes only to the file named by --db and never to the application's default database.
"""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

# Lets `python backend/scripts/seed.py` import the app package without PYTHONPATH or cd.
_BACKEND_FOLDER = Path(__file__).resolve().parents[1]
if str(_BACKEND_FOLDER) not in sys.path:
    sys.path.insert(0, str(_BACKEND_FOLDER))

from app.core import money  # noqa: E402
from app.core.config import Settings, resolve_db_path, same_path  # noqa: E402
from app.core.constants import CATEGORIES, PAYMENT_METHODS  # noqa: E402
from app.db.connection import connect  # noqa: E402
from app.db.migrate import initialize_database  # noqa: E402
from app.repositories import expense_repository  # noqa: E402
from app.schemas.expense import ValidExpense  # noqa: E402

FIRST_DAY = date(2026, 9, 1)
DAY_SPAN = 73  # September 1 to November 12, 2026 inclusive
FIXED_STAMP = "2026-11-12T00:00:00Z"


@dataclass(frozen=True)
class SeedExpense:
    amount_text: str
    amount_cents: int
    description: str
    category: str
    payment_method: str
    expense_date: date


class _UsageError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise _UsageError(message)


def generate(count: int) -> list[SeedExpense]:
    expenses: list[SeedExpense] = []
    for i in range(count):
        amount_text = money.cents_to_text(1000 + (i * 7919) % 99000)
        expenses.append(
            SeedExpense(
                amount_text=amount_text,
                amount_cents=money.text_to_cents(amount_text),
                description=f"Seed expense {i + 1}",
                category=CATEGORIES[i % len(CATEGORIES)],
                payment_method=PAYMENT_METHODS[(i * 5) % len(PAYMENT_METHODS)],
                expense_date=FIRST_DAY + timedelta(days=(i * 29) % DAY_SPAN),
            )
        )
    return expenses


def _refuse(message: str) -> int:
    print(f"error: {message}", file=sys.stderr)
    return 2


def _parse_count(text: str | None) -> int | None:
    if text is None or not text.isdigit() or int(text) < 1:
        return None
    return int(text)


def main(argv: Sequence[str] | None = None, settings: Settings | None = None) -> int:
    parser = _Parser(description="Fill a NEW database file with deterministic expenses.")
    parser.add_argument("--count", help="number of expenses to create (required, at least 1)")
    parser.add_argument("--db", help="path of the database file to create (required)")
    try:
        args = parser.parse_args(argv)
    except _UsageError as problem:
        return _refuse(str(problem))
    if not args.db:
        return _refuse("--db is required: give the path of a new database file")
    count = _parse_count(args.count)
    if count is None:
        return _refuse("--count is required and must be a whole number of at least 1")

    active = settings or Settings.from_env()
    target = resolve_db_path(args.db, Path.cwd())
    if same_path(target, active.default_db_path):
        return _refuse("refusing to write to the application's default database; pick another --db")
    if target.is_dir():
        return _refuse(f"--db {target} is a directory, not a database file")
    if target.exists() and target.stat().st_size > 0:
        return _refuse(f"--db {target} already exists and is not empty; it is never overwritten")

    try:
        initialize_database(target)
        conn = connect(target)
        try:
            valid = [
                ValidExpense(
                    e.amount_cents, e.description, e.category, e.payment_method, e.expense_date
                )
                for e in generate(count)
            ]
            expense_repository.insert_many(conn, valid, FIXED_STAMP)
        finally:
            conn.close()
    except OSError as problem:
        print(f"error: could not write {target}: {problem}", file=sys.stderr)
        return 1
    print(f"Created {count} expenses in {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
