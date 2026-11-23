"""G10: POST /api/expenses rejects a negative amount with 422 and writes nothing (Principle III)."""

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


@pytest.mark.parametrize("amount", ["-5", "-100", "-0.01", "-0.001"])
def test_a_negative_amount_is_rejected_and_nothing_is_stored(
    client: TestClient, db_path: Path, amount: str
) -> None:
    response = client.post(
        "/api/expenses",
        json={
            "amount": amount,
            "description": "Lunch",
            "category": "Food",
            "payment_method": "UPI",
            "expense_date": "2026-11-10",
        },
    )
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "amount", "message": "Amount must be greater than zero"}
    ]
    assert _expense_count(db_path) == 0
