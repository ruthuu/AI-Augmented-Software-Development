"""T054: PUT /api/budgets/{month}."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def stored_budgets(db_path: Path) -> dict[str, int]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT month, amount_cents FROM monthly_budgets").fetchall()
    finally:
        connection.close()
    return {month: cents for month, cents in rows}


def put_budget(client: TestClient, month: str, amount: str) -> int:
    return client.put(f"/api/budgets/{month}", json={"amount": amount}).status_code


def add_expense(client: TestClient, amount: str, day: str, category: str = "Food") -> int:
    response = client.post(
        "/api/expenses",
        json={
            "amount": amount,
            "description": "x",
            "category": category,
            "payment_method": "Cash",
            "expense_date": day,
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def summary(client: TestClient, month: str = "2026-11") -> dict[str, object]:
    response = client.get(f"/api/summary?month={month}")
    assert response.status_code == 200
    return dict(response.json())


def test_put_creates_a_budget(client: TestClient, db_path: Path) -> None:
    response = client.put("/api/budgets/2026-11", json={"amount": "10000.00"})
    assert response.status_code == 200
    body = response.json()
    assert (body["month"], body["amount"]) == ("2026-11", "10000.00")
    assert body["updated_at"].endswith("Z")
    assert set(body) == {"month", "amount", "updated_at"}
    assert stored_budgets(db_path) == {"2026-11": 1000000}


def test_put_again_replaces_the_budget(client: TestClient, db_path: Path) -> None:
    put_budget(client, "2026-11", "10000.00")
    response = client.put("/api/budgets/2026-11", json={"amount": "12000.00"})
    assert response.json()["amount"] == "12000.00"
    assert stored_budgets(db_path) == {"2026-11": 1200000}


@pytest.mark.parametrize(
    ("sent", "shown"),
    [
        ("0.01", "0.01"),
        ("99999999.99", "99999999.99"),
        ("12000", "12000.00"),
        ("12000.5", "12000.50"),
    ],
)
def test_accepted_budget_amounts(client: TestClient, sent: str, shown: str) -> None:
    assert client.put("/api/budgets/2026-11", json={"amount": sent}).json()["amount"] == shown


@pytest.mark.parametrize(
    ("sent", "message"),
    [
        ("0", "Budget must be a number greater than zero"),
        ("-100", "Budget must be a number greater than zero"),
        ("", "Budget must be a number greater than zero"),
        ("abc", "Budget must be a number greater than zero"),
        ("12000.999", "Budget can have at most 2 decimal places"),
        ("0.005", "Budget can have at most 2 decimal places"),
        ("100000000.00", "Budget cannot exceed 99,999,999.99"),
    ],
)
def test_a_rejected_budget_leaves_the_existing_budget_unchanged(
    client: TestClient, db_path: Path, sent: str, message: str
) -> None:
    put_budget(client, "2026-11", "10000.00")
    response = client.put("/api/budgets/2026-11", json={"amount": sent})
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "amount", "message": message}]
    assert stored_budgets(db_path) == {"2026-11": 1000000}
    assert summary(client)["budget"] == {"month": "2026-11", "amount": "10000.00"}


@pytest.mark.parametrize("month", ["2026-13", "2026-00", "abc", "2026-1", "26-11", "0000-01"])
def test_an_invalid_month_is_rejected(client: TestClient, db_path: Path, month: str) -> None:
    response = client.put(f"/api/budgets/{month}", json={"amount": "100.00"})
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "month", "message": "Enter a valid month"}]
    assert stored_budgets(db_path) == {}


@pytest.mark.parametrize("month", ["1999-12", "2099-01", "0001-01", "9999-12"])
def test_any_real_month_is_accepted(client: TestClient, db_path: Path, month: str) -> None:
    assert put_budget(client, month, "100.00") == 200
    assert stored_budgets(db_path) == {month: 10000}


def test_an_invalid_month_and_amount_are_reported_together(client: TestClient) -> None:
    response = client.put("/api/budgets/2026-13", json={"amount": "abc"})
    assert response.status_code == 422
    assert {e["field"] for e in response.json()["errors"]} == {"month", "amount"}


def test_malformed_json_leaves_the_budget_unchanged(client: TestClient, db_path: Path) -> None:
    put_budget(client, "2026-11", "10000.00")
    response = client.put(
        "/api/budgets/2026-11", content="{bad", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "body", "message": "Request body must be valid JSON"}
    ]
    assert stored_budgets(db_path) == {"2026-11": 1000000}


def test_an_unknown_field_leaves_the_budget_unchanged(client: TestClient, db_path: Path) -> None:
    put_budget(client, "2026-11", "10000.00")
    response = client.put("/api/budgets/2026-11", json={"amount": "500.00", "extra": 1})
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "extra", "message": "Unknown field"}]
    assert stored_budgets(db_path) == {"2026-11": 1000000}


def test_a_missing_amount_is_rejected(client: TestClient, db_path: Path) -> None:
    response = client.put("/api/budgets/2026-11", json={})
    assert response.status_code == 422
    assert stored_budgets(db_path) == {}


def test_a_json_number_amount_is_rejected_not_converted(client: TestClient, db_path: Path) -> None:
    response = client.put("/api/budgets/2026-11", json={"amount": 12000.5})
    assert response.status_code == 422
    assert stored_budgets(db_path) == {}
