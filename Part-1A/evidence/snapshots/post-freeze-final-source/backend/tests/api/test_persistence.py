"""T036 (expense part): data survives an application restart (US1 #13, SC-008)."""

import sqlite3
from pathlib import Path

from tests.support import AppFactory, ClientFactory


def test_expense_survives_a_second_app_instance(
    make_app: AppFactory, make_client: ClientFactory, db_path: Path
) -> None:
    first = make_client(make_app())
    created = first.post(
        "/api/expenses",
        json={
            "amount": "250.50",
            "description": "Lunch",
            "category": "Food",
            "payment_method": "UPI",
            "expense_date": "2026-11-10",
        },
    ).json()
    edited = first.put(
        f"/api/expenses/{created['id']}",
        json={
            "amount": "300.00",
            "description": "Lunch edited",
            "category": "Food",
            "payment_method": "Cash",
            "expense_date": "2026-11-09",
        },
    ).json()
    gone = first.post(
        "/api/expenses",
        json={
            "amount": "1.00",
            "description": "Gone",
            "category": "Other",
            "payment_method": "Other",
            "expense_date": "2026-11-01",
        },
    ).json()
    first.delete(f"/api/expenses/{gone['id']}")

    second = make_client(make_app())
    assert second.get("/api/expenses").json() == [edited]


def test_restart_does_not_reapply_or_change_the_schema(
    make_app: AppFactory, make_client: ClientFactory, db_path: Path
) -> None:
    make_client(make_app())
    make_client(make_app())
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    finally:
        connection.close()
    assert rows == [("001_initial",)]


def test_budget_survives_a_second_app_instance(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    first = make_client(make_app())
    first.put("/api/budgets/2026-11", json={"amount": "10000.00"})
    first.put("/api/budgets/2026-11", json={"amount": "12000.00"})
    first.put("/api/budgets/2026-11", json={"amount": "10000.00"})
    first.post(
        "/api/expenses",
        json={
            "amount": "2500.75",
            "description": "x",
            "category": "Food",
            "payment_method": "Cash",
            "expense_date": "2026-11-05",
        },
    )
    second = make_client(make_app())
    result = second.get("/api/summary?month=2026-11").json()
    assert result["budget"] == {"month": "2026-11", "amount": "10000.00"}
    assert result["total_spent"] == "2500.75"
    assert result["remaining"] == "7499.25"
    assert result["over_budget"] is False
