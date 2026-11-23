"""T064 (SC-005b): server-side work for list-all and the monthly summary with 1,000 expenses.

Measured in process with the test client: no browser and no network. SC-005a (the 2-second
user-facing requirement, measured by a person) is a separate manual check.
"""

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from scripts import seed
from tests.support import AppFactory, ClientFactory

LIMIT_SECONDS = 0.5


@pytest.fixture
def thousand(
    db_path: Path, make_app: AppFactory, make_client: ClientFactory, tmp_path: Path
) -> TestClient:
    settings = Settings.from_env({}, tmp_path)
    assert seed.main(["--count", "1000", "--db", str(db_path)], settings) == 0
    return make_client(make_app())


def elapsed(client: TestClient, path: str) -> float:
    client.get(path)  # one warm-up call
    started = time.perf_counter()
    response = client.get(path)
    duration = time.perf_counter() - started
    assert response.status_code == 200
    return duration


def test_list_all_1000_expenses_is_under_500_ms(thousand: TestClient) -> None:
    assert len(thousand.get("/api/expenses").json()) == 1000
    assert elapsed(thousand, "/api/expenses") < LIMIT_SECONDS


def test_monthly_summary_with_1000_expenses_is_under_500_ms(thousand: TestClient) -> None:
    result = thousand.get("/api/summary?month=2026-10").json()
    assert result["expense_count"] > 0
    assert result["total_recorded_count"] == 1000
    assert elapsed(thousand, "/api/summary?month=2026-10") < LIMIT_SECONDS
