"""G10: POST /api/expenses rejects a date that is not YYYY-MM-DD with 422 and writes nothing."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _expense_count(db_path: Path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0])
    finally:
        connection.close()


@pytest.mark.parametrize(
    "date_text",
    ["abc", "2026-1-5", "20261112", "10-11-2026", "2026/11/10", "2026-11-10T00:00:00"],
)
def test_a_date_that_is_not_iso_8601_is_rejected_and_nothing_is_stored(
    client: TestClient, db_path: Path, date_text: str
) -> None:
    response = client.post(
        "/api/expenses",
        json={
            "amount": "250.50",
            "description": "Lunch",
            "category": "Food",
            "payment_method": "UPI",
            "expense_date": date_text,
        },
    )
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "expense_date", "message": "Enter a valid date"}]
    assert _expense_count(db_path) == 0
