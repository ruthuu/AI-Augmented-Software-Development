"""T062 (dataset, SC-003): hand-calculated totals for the 50-expense seed dataset.

The constants below were calculated independently of the application code, by adding the 50
generated amounts by hand per month and per category. The generator's rules (documented in
scripts/seed.py): expense i (from 0) has category CATEGORIES[i % 8], date 2026-09-01 plus
(i * 29) % 73 days, and amount 10.00 plus ((i * 7919) % 99000) cents.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from scripts import seed
from tests.support import AppFactory, ClientFactory

# month -> (total, count, [(category, total, count)] ordered by total descending then name)
EXPECTED = {
    "2026-09": (
        "9313.10",
        21,
        [
            ("Food", "1781.68", 4),
            ("Bills", "1573.83", 3),
            ("Other", "1326.26", 2),
            ("Education", "1217.10", 3),
            ("Entertainment", "1128.16", 2),
            ("Transport", "1019.25", 3),
            ("Healthcare", "732.46", 2),
            ("Shopping", "534.36", 2),
        ],
    ),
    "2026-10": (
        "10886.90",
        20,
        [
            ("Transport", "2009.25", 3),
            ("Entertainment", "1811.40", 3),
            ("Food", "1484.64", 2),
            ("Other", "1454.67", 3),
            ("Healthcare", "1286.54", 2),
            ("Shopping", "1256.82", 3),
            ("Education", "890.84", 2),
            ("Bills", "692.74", 2),
        ],
    ),
    "2026-11": (
        "5037.75",
        9,
        [
            ("Healthcare", "1009.50", 2),
            ("Transport", "999.75", 1),
            ("Shopping", "801.90", 1),
            ("Bills", "801.65", 1),
            ("Entertainment", "603.80", 1),
            ("Education", "405.70", 1),
            ("Other", "207.85", 1),
            ("Food", "207.60", 1),
        ],
    ),
}


@pytest.fixture
def seeded(
    db_path: Path, make_app: AppFactory, make_client: ClientFactory, tmp_path: Path
) -> TestClient:
    settings = Settings.from_env({}, tmp_path)
    assert seed.main(["--count", "50", "--db", str(db_path)], settings) == 0
    return make_client(make_app())


@pytest.mark.parametrize("month", sorted(EXPECTED))
def test_monthly_total_count_and_category_totals(seeded: TestClient, month: str) -> None:
    total, count, categories = EXPECTED[month]
    result = seeded.get(f"/api/summary?month={month}").json()
    assert result["total_spent"] == total
    assert result["expense_count"] == count
    assert [(c["category"], c["total"], c["count"]) for c in result["by_category"]] == categories


def test_the_all_time_count_is_fifty(seeded: TestClient) -> None:
    assert seeded.get("/api/summary?month=2026-10").json()["total_recorded_count"] == 50
    assert len(seeded.get("/api/expenses").json()) == 50


@pytest.mark.parametrize(
    ("month", "budget", "remaining", "over_by"),
    [
        ("2026-09", "10000.00", "686.90", None),
        ("2026-10", "10000.00", "0.00", "886.90"),
        ("2026-11", "5037.75", "0.00", None),
        ("2026-11", "5037.74", "0.00", "0.01"),
    ],
)
def test_remaining_budget_and_overage(
    seeded: TestClient, month: str, budget: str, remaining: str, over_by: str | None
) -> None:
    assert seeded.put(f"/api/budgets/{month}", json={"amount": budget}).status_code == 200
    result = seeded.get(f"/api/summary?month={month}").json()
    assert result["remaining"] == remaining
    assert result["over_budget_by"] == over_by
    assert result["over_budget"] is (over_by is not None)


def test_filters_match_the_dataset(seeded: TestClient) -> None:
    listed = seeded.get("/api/expenses?month=2026-11").json()
    assert len(listed) == 9
    food_october = seeded.get("/api/expenses?month=2026-10&category=Food").json()
    assert len(food_october) == 2
    assert sum(int(r["amount"].replace(".", "")) for r in food_october) == 148464
