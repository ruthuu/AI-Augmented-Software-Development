"""T053: budget status arithmetic in integer cents (FR-025, FR-026, FR-027)."""

import pytest

from app.core.money import cents_to_text, sum_cents, text_to_cents
from app.services.calculations import budget_status, summarize_by_category


def cents(text: str) -> int:
    return text_to_cents(text)


def test_spent_below_the_budget() -> None:
    status = budget_status(cents("2500.75"), cents("10000.00"))
    assert status.remaining_cents == cents("7499.25")
    assert status.over_budget is False
    assert status.over_budget_by_cents is None


def test_spent_exactly_equal_to_the_budget_is_not_an_overage() -> None:
    status = budget_status(cents("10000.00"), cents("10000.00"))
    assert status.remaining_cents == 0
    assert status.over_budget is False
    assert status.over_budget_by_cents is None


def test_one_paisa_over_is_an_overage() -> None:
    status = budget_status(cents("10000.01"), cents("10000.00"))
    assert status.remaining_cents == 0
    assert status.over_budget is True
    assert status.over_budget_by_cents == 1


def test_one_paisa_under_leaves_one_paisa() -> None:
    status = budget_status(cents("9999.99"), cents("10000.00"))
    assert status.remaining_cents == 1
    assert status.over_budget is False


def test_no_budget() -> None:
    status = budget_status(cents("500.00"), None)
    assert status.remaining_cents is None
    assert status.over_budget is False
    assert status.over_budget_by_cents is None


def test_no_spending_leaves_the_whole_budget() -> None:
    status = budget_status(0, cents("100.00"))
    assert status.remaining_cents == 10000
    assert status.over_budget is False


@pytest.mark.parametrize(
    ("spent", "budget", "by"),
    [("6000.00", "5000.00", "1000.00"), ("99999999.99", "0.01", "99999999.98")],
)
def test_overage_amount_is_exact(spent: str, budget: str, by: str) -> None:
    status = budget_status(cents(spent), cents(budget))
    assert status.over_budget is True
    assert status.over_budget_by_cents == cents(by)
    assert status.remaining_cents == 0


def test_category_rows_are_summed_in_integer_cents() -> None:
    rows = [("Food", cents("100.10")), ("Food", cents("200.20")), ("Transport", cents("50.00"))]
    result = summarize_by_category(rows)
    assert [(r.category, cents_to_text(r.total_cents), r.count) for r in result] == [
        ("Food", "300.30", 2),
        ("Transport", "50.00", 1),
    ]


def test_point_ten_plus_point_twenty_is_exactly_point_thirty() -> None:
    result = summarize_by_category([("Other", cents("0.10")), ("Other", cents("0.20"))])
    assert [(r.category, r.total_cents, r.count) for r in result] == [("Other", 30, 2)]
    assert cents_to_text(sum_cents(r.total_cents for r in result)) == "0.30"


def test_categories_are_ordered_by_total_descending_then_name() -> None:
    rows = [("Transport", 5000), ("Bills", 5000), ("Education", 5000), ("Food", 7500)]
    assert [r.category for r in summarize_by_category(rows)] == [
        "Food",
        "Bills",
        "Education",
        "Transport",
    ]


def test_no_rows_give_no_categories() -> None:
    assert summarize_by_category([]) == []


def test_many_small_amounts_do_not_drift() -> None:
    rows = [("Food", cents("0.10"))] * 1000
    (only,) = summarize_by_category(rows)
    assert (cents_to_text(only.total_cents), only.count) == ("100.00", 1000)
