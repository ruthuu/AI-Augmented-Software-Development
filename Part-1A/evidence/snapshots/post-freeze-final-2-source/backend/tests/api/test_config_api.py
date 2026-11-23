"""T021: constants, GET /api/config, and the app entry point."""

import hashlib
import importlib
import sqlite3
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.constants import CATEGORIES, LIMITS, PAYMENT_METHODS
from app.db.migrate import initialize_database
from tests.support import AppFactory, ClientFactory

CATEGORY_LIST = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
]
PAYMENT_LIST = ["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking", "Other"]


def test_categories_are_exact() -> None:
    assert list(CATEGORIES) == CATEGORY_LIST


def test_payment_methods_are_exact() -> None:
    assert list(PAYMENT_METHODS) == PAYMENT_LIST


def test_limits_are_integer_cents() -> None:
    assert LIMITS.max_expense_cents == 999999999
    assert LIMITS.max_budget_cents == 9999999999
    assert LIMITS.min_amount_cents == 1
    assert LIMITS.max_description_length == 200
    assert LIMITS.min_date == date(2000, 1, 1)
    for value in (LIMITS.max_expense_cents, LIMITS.max_budget_cents, LIMITS.min_amount_cents):
        assert type(value) is int


def test_config_endpoint_returns_the_contract(client: TestClient) -> None:
    response = client.get("/api/config")
    assert response.status_code == 200
    assert response.json() == {
        "today": "2026-11-12",
        "currency": "INR",
        "categories": CATEGORY_LIST,
        "payment_methods": PAYMENT_LIST,
        "limits": {
            "max_expense": "9999999.99",
            "max_budget": "99999999.99",
            "max_description_length": 200,
            "min_date": "2000-01-01",
        },
    }


def test_today_in_config_equals_the_override(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    other = make_client(make_app(today=date(2027, 1, 31)))
    assert other.get("/api/config").json()["today"] == "2027-01-31"


def _fresh_import(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.delitem(sys.modules, "app.main", raising=False)
    return importlib.import_module("app.main")


def test_importing_app_main_creates_no_database_or_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "does-not-exist-yet" / "spendwise.db"
    monkeypatch.setenv("SPENDWISE_DB_PATH", str(db))
    monkeypatch.setenv("SPENDWISE_TODAY", "2026-11-12")
    module = _fresh_import(monkeypatch)
    assert isinstance(module.app, FastAPI)
    assert not db.parent.exists()
    assert not db.exists()


def test_importing_app_main_does_not_modify_an_existing_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "existing.db"
    initialize_database(db)
    before = hashlib.sha256(db.read_bytes()).hexdigest()
    monkeypatch.setenv("SPENDWISE_DB_PATH", str(db))
    monkeypatch.setenv("SPENDWISE_TODAY", "2026-11-12")
    _fresh_import(monkeypatch)
    assert hashlib.sha256(db.read_bytes()).hexdigest() == before


def test_starting_the_app_creates_folder_file_and_serves_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "does-not-exist-yet" / "spendwise.db"
    monkeypatch.setenv("SPENDWISE_DB_PATH", str(db))
    monkeypatch.setenv("SPENDWISE_TODAY", "2026-11-12")
    module = _fresh_import(monkeypatch)
    assert not db.parent.exists()
    with TestClient(module.app) as started:
        assert db.parent.is_dir()
        assert db.is_file()
        response = started.get("/api/config")
        assert response.status_code == 200
        assert response.json()["today"] == "2026-11-12"
    check = sqlite3.connect(db)
    try:
        versions = [r[0] for r in check.execute("SELECT version FROM schema_migrations")]
    finally:
        check.close()
    assert versions == ["001_initial"]
