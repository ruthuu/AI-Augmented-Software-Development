"""T054: base figures of GET /api/summary (budget status and month boundaries)."""

import pytest
from fastapi.testclient import TestClient


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


def test_summary_with_a_budget_below_it(client: TestClient) -> None:
    put_budget(client, "2026-11", "10000.00")
    add_expense(client, "2500.75", "2026-11-05")
    result = summary(client)
    assert result["month"] == "2026-11"
    assert result["total_spent"] == "2500.75"
    assert result["expense_count"] == 1
    assert result["remaining"] == "7499.25"
    assert (result["over_budget"], result["over_budget_by"]) == (False, None)


def test_summary_exactly_at_the_budget(client: TestClient) -> None:
    put_budget(client, "2026-11", "10000.00")
    add_expense(client, "10000.00", "2026-11-05")
    result = summary(client)
    assert (result["remaining"], result["over_budget"], result["over_budget_by"]) == (
        "0.00",
        False,
        None,
    )


def test_summary_one_paisa_over_the_budget(client: TestClient) -> None:
    put_budget(client, "2026-11", "10000.00")
    add_expense(client, "10000.01", "2026-11-05")
    result = summary(client)
    assert (result["remaining"], result["over_budget"], result["over_budget_by"]) == (
        "0.00",
        True,
        "0.01",
    )


def test_summary_without_a_budget(client: TestClient) -> None:
    add_expense(client, "100.00", "2026-11-05")
    result = summary(client)
    assert result["total_spent"] == "100.00"
    assert result["budget"] is None
    assert result["remaining"] is None
    assert (result["over_budget"], result["over_budget_by"]) == (False, None)


def test_an_expense_in_another_month_is_not_counted(client: TestClient) -> None:
    put_budget(client, "2026-11", "10000.00")
    add_expense(client, "5000.00", "2026-10-31")
    result = summary(client)
    assert result["total_spent"] == "0.00"
    assert result["expense_count"] == 0
    assert result["remaining"] == "10000.00"
    assert summary(client, "2026-10")["total_spent"] == "5000.00"


def test_deleting_an_expense_lowers_spent_and_clears_the_warning(client: TestClient) -> None:
    put_budget(client, "2026-11", "5000.00")
    add_expense(client, "4000.00", "2026-11-02")
    big = add_expense(client, "2000.00", "2026-11-03")
    over = summary(client)
    assert (over["total_spent"], over["over_budget"], over["over_budget_by"]) == (
        "6000.00",
        True,
        "1000.00",
    )
    assert client.delete(f"/api/expenses/{big}").status_code == 204
    after = summary(client)
    assert (after["total_spent"], after["remaining"], after["over_budget"]) == (
        "4000.00",
        "1000.00",
        False,
    )


def test_a_budget_belongs_to_one_month(client: TestClient) -> None:
    put_budget(client, "2026-11", "10000.00")
    assert summary(client, "2026-10")["budget"] is None


def test_summary_defaults_to_the_month_of_today(client: TestClient) -> None:
    add_expense(client, "10.00", "2026-11-12")
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json()["month"] == "2026-11"
    assert response.json()["total_spent"] == "10.00"


@pytest.mark.parametrize("month", ["2026-13", "abc", "2026-1"])
def test_summary_rejects_an_invalid_month(client: TestClient, month: str) -> None:
    response = client.get(f"/api/summary?month={month}")
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": "month", "message": "Enter a valid month"}]


def test_summary_for_a_month_far_in_the_future(client: TestClient) -> None:
    result = summary(client, "9999-12")
    assert (result["total_spent"], result["expense_count"]) == ("0.00", 0)


def expense_body(amount: str, day: str, category: str) -> dict[str, str]:
    return {
        "amount": amount,
        "description": "x",
        "category": category,
        "payment_method": "Cash",
        "expense_date": day,
    }


def rows(result: dict[str, object]) -> list[tuple[str, str, int]]:
    by_category = result["by_category"]
    assert isinstance(by_category, list)
    return [(r["category"], r["total"], r["count"]) for r in by_category]


def test_worked_example_total_count_and_category_rows(client: TestClient) -> None:
    for amount, category in (("100.10", "Food"), ("200.20", "Food"), ("50.00", "Transport")):
        add_expense(client, amount, "2026-11-10", category)
    result = summary(client)
    assert result["total_spent"] == "350.30"
    assert result["expense_count"] == 3
    assert rows(result) == [("Food", "300.30", 2), ("Transport", "50.00", 1)]


def test_point_ten_plus_point_twenty_is_point_thirty(client: TestClient) -> None:
    add_expense(client, "0.10", "2026-11-01")
    add_expense(client, "0.20", "2026-11-12")
    assert summary(client)["total_spent"] == "0.30"


def test_categories_without_spending_are_omitted(client: TestClient) -> None:
    add_expense(client, "10.00", "2026-11-10", "Bills")
    assert [r[0] for r in rows(summary(client))] == ["Bills"]


def test_rows_are_ordered_by_total_then_name(client: TestClient) -> None:
    for category, amount in (("Transport", "50.00"), ("Bills", "50.00"), ("Food", "75.00")):
        add_expense(client, amount, "2026-11-10", category)
    assert [r[0] for r in rows(summary(client))] == ["Food", "Bills", "Transport"]


def test_an_empty_month_has_zero_figures(client: TestClient) -> None:
    result = summary(client, "2026-05")
    assert (result["total_spent"], result["expense_count"], result["by_category"]) == (
        "0.00",
        0,
        [],
    )


def test_the_all_time_count_includes_every_month(client: TestClient) -> None:
    add_expense(client, "1.00", "2026-11-10")
    add_expense(client, "1.00", "2026-10-10")
    add_expense(client, "1.00", "2025-01-10")
    assert summary(client)["total_recorded_count"] == 3
    assert summary(client)["expense_count"] == 1
    assert summary(client, "2026-05")["total_recorded_count"] == 3


def test_editing_the_date_moves_the_amount_between_months(client: TestClient) -> None:
    expense_id = add_expense(client, "40.00", "2026-11-05", "Food")
    add_expense(client, "10.00", "2026-10-05", "Food")
    assert summary(client)["total_spent"] == "40.00"
    assert summary(client, "2026-10")["total_spent"] == "10.00"
    edited = client.put(
        f"/api/expenses/{expense_id}", json=expense_body("40.00", "2026-10-20", "Food")
    )
    assert edited.status_code == 200
    november, october = summary(client), summary(client, "2026-10")
    assert (november["total_spent"], november["expense_count"]) == ("0.00", 0)
    assert (october["total_spent"], october["expense_count"]) == ("50.00", 2)


def test_editing_the_amount_or_category_updates_the_summary(client: TestClient) -> None:
    expense_id = add_expense(client, "40.00", "2026-11-05", "Food")
    client.put(f"/api/expenses/{expense_id}", json=expense_body("55.50", "2026-11-05", "Bills"))
    assert rows(summary(client)) == [("Bills", "55.50", 1)]


def test_repeated_calls_return_identical_output(client: TestClient) -> None:
    add_expense(client, "12.34", "2026-11-05", "Food")
    add_expense(client, "56.78", "2026-11-06", "Bills")
    first = client.get("/api/summary?month=2026-11").json()
    assert all(client.get("/api/summary?month=2026-11").json() == first for _ in range(5))


def test_the_list_category_filter_does_not_change_the_summary(client: TestClient) -> None:
    add_expense(client, "10.00", "2026-11-05", "Food")
    add_expense(client, "20.00", "2026-11-05", "Bills")
    before = summary(client)
    client.get("/api/expenses?category=Food&month=2026-11")
    assert summary(client) == before
    assert len(rows(before)) == 2
