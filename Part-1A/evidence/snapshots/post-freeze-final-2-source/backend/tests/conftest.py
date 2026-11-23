"""Shared fixtures: fixed "today", a fresh temporary database per test, and a client factory."""

from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import create_app
from tests.support import AppFactory, ClientFactory

FIXED_TODAY = date(2026, 11, 12)


@pytest.fixture(autouse=True)
def _isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("SPENDWISE_DB_PATH", "SPENDWISE_CORS_ORIGINS", "SPENDWISE_TODAY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "spendwise.db"


@pytest.fixture
def make_app(db_path: Path) -> AppFactory:
    def factory(db: Path | None = None, today: date | None = FIXED_TODAY) -> FastAPI:
        return create_app(db_path=db or db_path, today_override=today)

    return factory


@pytest.fixture
def make_client() -> Iterator[ClientFactory]:
    opened: list[TestClient] = []

    def factory(app: FastAPI) -> TestClient:
        test_client = TestClient(app, raise_server_exceptions=False)
        test_client.__enter__()
        opened.append(test_client)
        return test_client

    yield factory
    for test_client in opened:
        test_client.__exit__(None, None, None)


@pytest.fixture
def client(make_app: AppFactory, make_client: ClientFactory) -> TestClient:
    return make_client(make_app())
