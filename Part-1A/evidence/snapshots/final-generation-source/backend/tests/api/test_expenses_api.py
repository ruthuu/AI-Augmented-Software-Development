"""T035: expenses API (create, list, update, delete, validation, no side effects)."""

import sqlite3
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.support import AppFactory, ClientFactory

NOT_FOUND = {"code": "not_found", "message": "This expense no longer exists", "errors": []}


def body(**changes: str) -> dict[str, str]:
    base = {
        "amount": "250.50",
        "description": "Lunch",
        "category": "Food",
        "payment_method": "UPI",
        "expense_date": "2026-11-10",
    }
    base.update(changes)
    return base


def row_count(db_path: Path) -> int:
    connection = sqlite3.connect(db_path)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM expenses").fetchone()[0])
    finally:
        connection.close()


def test_create_returns_201_with_the_expense(client: TestClient) -> None:
    response = client.post("/api/expenses", json=body())
    assert response.status_code == 201
    created = response.json()
    assert created["id"] >= 1
    assert {k: created[k] for k in body()} == body()
    assert created["created_at"].endswith("Z") and created["updated_at"].endswith("Z")
    assert set(created) == {*body(), "id", "created_at", "updated_at"}


def test_amount_is_returned_with_two_decimals(client: TestClient) -> None:
    for sent, shown in (("12", "12.00"), ("12.5", "12.50"), ("0.01", "0.01")):
        assert client.post("/api/expenses", json=body(amount=sent)).json()["amount"] == shown


def test_list_is_ordered_by_date_then_id_descending(client: TestClient) -> None:
    ids = {}
    for name, day in (
        ("a", "2026-11-10"),
        ("b", "2026-11-12"),
        ("c", "2026-11-10"),
        ("d", "2026-11-01"),
    ):
        ids[name] = client.post(
            "/api/expenses", json=body(description=name, expense_date=day)
        ).json()["id"]
    listed = client.get("/api/expenses").json()
    assert [row["id"] for row in listed] == [ids["b"], ids["c"], ids["a"], ids["d"]]


def test_list_is_empty_when_nothing_is_recorded(client: TestClient) -> None:
    assert client.get("/api/expenses").json() == []


def test_update_keeps_id_and_row_count(client: TestClient, db_path: Path) -> None:
    created = client.post("/api/expenses", json=body()).json()
    response = client.put(f"/api/expenses/{created['id']}", json=body(amount="300.00"))
    assert response.status_code == 200
    updated = response.json()
    assert updated["id"] == created["id"]
    assert updated["amount"] == "300.00"
    assert updated["created_at"] == created["created_at"]
    assert row_count(db_path) == 1
    assert client.get("/api/expenses").json()[0]["amount"] == "300.00"


def test_delete_returns_204_then_404(client: TestClient) -> None:
    created = client.post("/api/expenses", json=body()).json()
    first = client.delete(f"/api/expenses/{created['id']}")
    assert first.status_code == 204 and first.content == b""
    assert client.get("/api/expenses").json() == []
    second = client.delete(f"/api/expenses/{created['id']}")
    assert (second.status_code, second.json()) == (404, NOT_FOUND)
    update = client.put(f"/api/expenses/{created['id']}", json=body())
    assert (update.status_code, update.json()) == (404, NOT_FOUND)


def test_unknown_or_non_numeric_id_is_a_404(client: TestClient) -> None:
    assert client.delete("/api/expenses/999999").json() == NOT_FOUND
    assert client.put("/api/expenses/abc", json=body()).status_code == 404


def test_empty_body_returns_one_error_per_field(client: TestClient, db_path: Path) -> None:
    response = client.post("/api/expenses", json={})
    assert response.status_code == 422
    payload = response.json()
    assert payload["code"] == "validation_error"
    assert sorted(payload["errors"], key=lambda e: e["field"]) == [
        {"field": "amount", "message": "Amount is required"},
        {"field": "category", "message": "Category is required"},
        {"field": "description", "message": "Description is required"},
        {"field": "expense_date", "message": "Date is required"},
        {"field": "payment_method", "message": "Payment method is required"},
    ]
    assert row_count(db_path) == 0


def test_all_failing_fields_are_reported_together(client: TestClient) -> None:
    response = client.post(
        "/api/expenses",
        json={
            "amount": "abc",
            "description": "  ",
            "category": "X",
            "payment_method": "Y",
            "expense_date": "2026-11-13",
        },
    )
    assert response.status_code == 422
    assert {e["field"]: e["message"] for e in response.json()["errors"]} == {
        "amount": "Enter a valid amount",
        "description": "Description is required",
        "category": "Select a valid category",
        "payment_method": "Select a valid payment method",
        "expense_date": "Date cannot be in the future",
    }


@pytest.mark.parametrize(
    ("changes", "field", "message"),
    [
        ({"amount": "0"}, "amount", "Amount must be greater than zero"),
        ({"amount": "12.345"}, "amount", "Amount can have at most 2 decimal places"),
        ({"amount": "10000000.00"}, "amount", "Amount cannot exceed 9,999,999.99"),
        ({"description": ""}, "description", "Description is required"),
        ({"description": "a" * 201}, "description", "Description cannot exceed 200 characters"),
        ({"category": "Bitcoin"}, "category", "Select a valid category"),
        ({"payment_method": "upi"}, "payment_method", "Select a valid payment method"),
        ({"payment_method": ""}, "payment_method", "Payment method is required"),
        ({"expense_date": "2026-02-30"}, "expense_date", "Enter a valid date"),
        ({"expense_date": "1999-12-31"}, "expense_date", "Date cannot be before 01 Jan 2000"),
        ({"expense_date": "2026-11-13"}, "expense_date", "Date cannot be in the future"),
    ],
)
def test_a_rejected_create_leaves_the_database_unchanged(
    client: TestClient, db_path: Path, changes: dict[str, str], field: str, message: str
) -> None:
    response = client.post("/api/expenses", json=body(**changes))
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": field, "message": message}]
    assert row_count(db_path) == 0


def test_a_rejected_update_keeps_the_stored_expense(client: TestClient) -> None:
    created = client.post("/api/expenses", json=body()).json()
    response = client.put(f"/api/expenses/{created['id']}", json=body(payment_method="Bitcoin"))
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "payment_method", "message": "Select a valid payment method"}
    ]
    assert client.get("/api/expenses").json() == [created]


def test_unknown_field_is_rejected(client: TestClient, db_path: Path) -> None:
    response = client.post("/api/expenses", json={**body(), "color": "red"})
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "color", "message": "Unknown field"}]
    assert row_count(db_path) == 0


def test_unknown_field_is_rejected_on_update(client: TestClient) -> None:
    created = client.post("/api/expenses", json=body()).json()
    response = client.put(f"/api/expenses/{created['id']}", json={**body(), "color": "red"})
    assert response.status_code == 422
    assert client.get("/api/expenses").json() == [created]


def test_malformed_json_is_rejected_and_writes_nothing(client: TestClient, db_path: Path) -> None:
    response = client.post(
        "/api/expenses", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["errors"] == [
        {"field": "body", "message": "Request body must be valid JSON"}
    ]
    assert row_count(db_path) == 0


def test_non_string_amount_is_rejected_not_converted(client: TestClient, db_path: Path) -> None:
    response = client.post("/api/expenses", json={**body(), "amount": 12.5})
    assert response.status_code == 422
    assert row_count(db_path) == 0


@pytest.mark.parametrize(
    "text",
    [
        '<b>Tom & "Jerry\'s"</b>',
        "<script>alert(1)</script>",
        "x'); DROP TABLE expenses;--",
        "Caf\u00e9 \u20b9 \u65e5\u672c\u8a9e \U0001f600",
        "back\\slash",
    ],
)
def test_special_characters_round_trip_unchanged(client: TestClient, text: str) -> None:
    created = client.post("/api/expenses", json=body(description=text))
    assert created.status_code == 201
    assert created.json()["description"] == text
    assert client.get("/api/expenses").json()[0]["description"] == text


def test_control_characters_are_cleaned_before_storing(client: TestClient) -> None:
    created = client.post("/api/expenses", json=body(description="Tea\tSnacks\u0000"))
    assert created.json()["description"] == "Tea Snacks"


def test_today_is_accepted_and_tomorrow_is_not(client: TestClient) -> None:
    assert client.post("/api/expenses", json=body(expense_date="2026-11-12")).status_code == 201
    assert client.post("/api/expenses", json=body(expense_date="2026-11-13")).status_code == 422


def test_the_future_check_follows_the_backend_date(
    make_app: AppFactory, make_client: ClientFactory, db_path: Path
) -> None:
    later = make_client(make_app(today=date(2026, 11, 13)))
    assert later.post("/api/expenses", json=body(expense_date="2026-11-13")).status_code == 201
    assert later.post("/api/expenses", json=body(expense_date="2026-11-14")).status_code == 422
    assert row_count(db_path) == 1


def test_startup_and_get_requests_create_no_rows(client: TestClient, db_path: Path) -> None:
    assert row_count(db_path) == 0
    for path in ("/api/expenses", "/api/config", "/api/expenses"):
        client.get(path)
    assert row_count(db_path) == 0


def test_one_post_creates_exactly_one_row(client: TestClient, db_path: Path) -> None:
    client.post("/api/expenses", json=body())
    assert row_count(db_path) == 1


def test_identical_expenses_are_allowed_when_added_deliberately(client: TestClient) -> None:
    first = client.post("/api/expenses", json=body()).json()
    second = client.post("/api/expenses", json=body()).json()
    assert first["id"] != second["id"]
    assert len(client.get("/api/expenses").json()) == 2
