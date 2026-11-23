"""T047 (API part): month and category filters on GET /api/expenses."""

from fastapi.testclient import TestClient


def add(client: TestClient, description: str, day: str, category: str = "Food") -> int:
    response = client.post(
        "/api/expenses",
        json={
            "amount": "10.00",
            "description": description,
            "category": category,
            "payment_method": "Cash",
            "expense_date": day,
        },
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def names(client: TestClient, query: str = "") -> list[str]:
    response = client.get(f"/api/expenses{query}")
    assert response.status_code == 200
    return [row["description"] for row in response.json()]


def seed(client: TestClient) -> None:
    add(client, "oct-last", "2025-10-31", "Food")
    add(client, "nov-first", "2025-11-01", "Transport")
    add(client, "nov-food", "2025-11-15", "Food")
    add(client, "dec-last", "2025-12-31", "Food")
    add(client, "jan-first", "2026-01-01", "Bills")
    add(client, "old", "2000-01-01", "Other")


def test_no_filter_lists_everything(client: TestClient) -> None:
    seed(client)
    assert names(client) == ["jan-first", "dec-last", "nov-food", "nov-first", "oct-last", "old"]


def test_category_only(client: TestClient) -> None:
    seed(client)
    assert names(client, "?category=Food") == ["dec-last", "nov-food", "oct-last"]
    assert names(client, "?category=Bills") == ["jan-first"]


def test_month_only(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=2025-11") == ["nov-food", "nov-first"]


def test_month_and_category_must_both_match(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=2025-11&category=Food") == ["nov-food"]
    assert names(client, "?month=2025-11&category=Transport") == ["nov-first"]


def test_no_match_returns_an_empty_list(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=2025-11&category=Education") == []
    assert names(client, "?month=2020-05") == []


def test_october_31_and_november_1_belong_to_their_own_months(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=2025-10") == ["oct-last"]
    assert names(client, "?month=2025-11")[-1] == "nov-first"


def test_december_31_and_january_1_belong_to_their_own_months(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=2025-12") == ["dec-last"]
    assert names(client, "?month=2026-01") == ["jan-first"]


def test_a_valid_month_before_2000_is_empty_not_an_error(client: TestClient) -> None:
    seed(client)
    assert names(client, "?month=1999-12") == []


def test_filtered_list_keeps_the_date_then_id_order(client: TestClient) -> None:
    add(client, "first", "2025-11-10")
    add(client, "second", "2025-11-10")
    add(client, "later", "2025-11-20")
    assert names(client, "?month=2025-11") == ["later", "second", "first"]


def test_empty_filter_values_mean_no_filter(client: TestClient) -> None:
    seed(client)
    assert len(names(client, "?month=&category=")) == 6


def test_invalid_month_is_rejected(client: TestClient) -> None:
    for month in ("2026-13", "2026-00", "abc", "2026-1", "26-11"):
        response = client.get(f"/api/expenses?month={month}")
        assert response.status_code == 422
        assert response.json()["errors"] == [{"field": "month", "message": "Enter a valid month"}]


def test_invalid_category_is_rejected(client: TestClient) -> None:
    for category in ("Nope", "food"):
        response = client.get(f"/api/expenses?category={category}")
        assert response.status_code == 422
        assert response.json()["errors"] == [
            {"field": "category", "message": "Select a valid category"}
        ]


def test_both_invalid_filters_are_reported_together(client: TestClient) -> None:
    response = client.get("/api/expenses?month=2026-13&category=Nope")
    assert response.status_code == 422
    assert {e["field"] for e in response.json()["errors"]} == {"month", "category"}


def test_filters_do_not_allow_sql_injection(client: TestClient) -> None:
    seed(client)
    response = client.get("/api/expenses?category=Food' OR '1'='1")
    assert response.status_code == 422
    assert len(names(client)) == 6
