"""T019: generic 500 body without internals, and CORS limited to the configured origins."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.support import AppFactory, ClientFactory

SECRET_MARKERS = ["SELECT", "secret_table", "Traceback", "RuntimeError", "C:\\", "File ", ".py"]


def _failing_app(make_app: AppFactory) -> FastAPI:
    app = make_app()

    @app.get("/api/_test-boom")
    def boom() -> None:
        raise RuntimeError("SELECT * FROM secret_table; C:\\Users\\someone\\secret.py")

    return app


def test_unexpected_error_returns_generic_500(
    make_app: AppFactory, make_client: ClientFactory
) -> None:
    client = make_client(_failing_app(make_app))
    response = client.get("/api/_test-boom")
    assert response.status_code == 500
    body = response.json()
    assert body["code"] == "internal_error"
    assert isinstance(body["message"], str) and body["message"]
    assert body["errors"] == []
    assert set(body) == {"code", "message", "errors"}
    for marker in SECRET_MARKERS:
        assert marker not in response.text


def test_not_found_route_still_uses_the_error_shape(client: TestClient) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert set(response.json()) == {"code", "message", "errors"}


def _preflight(client: TestClient, origin: str) -> dict[str, str]:
    response = client.options(
        "/api/config",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )
    return {key.lower(): value for key, value in response.headers.items()}


def test_cors_allows_only_configured_origins(
    monkeypatch: pytest.MonkeyPatch, make_app: AppFactory, make_client: ClientFactory
) -> None:
    monkeypatch.setenv("SPENDWISE_CORS_ORIGINS", "http://allowed.example, http://other.example")
    client = make_client(make_app())
    allowed = _preflight(client, "http://allowed.example")
    assert allowed["access-control-allow-origin"] == "http://allowed.example"
    other = _preflight(client, "http://other.example")
    assert other["access-control-allow-origin"] == "http://other.example"
    denied = _preflight(client, "http://evil.example")
    assert "access-control-allow-origin" not in denied
    default_origin = _preflight(client, "http://localhost:5173")
    assert "access-control-allow-origin" not in default_origin


def test_cors_defaults_are_the_two_local_dev_origins(
    monkeypatch: pytest.MonkeyPatch, make_app: AppFactory, make_client: ClientFactory
) -> None:
    monkeypatch.delenv("SPENDWISE_CORS_ORIGINS", raising=False)
    client = make_client(make_app())
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        assert _preflight(client, origin)["access-control-allow-origin"] == origin
    assert "access-control-allow-origin" not in _preflight(client, "http://evil.example")


def test_cors_never_uses_a_wildcard(client: TestClient) -> None:
    for origin in ("http://localhost:5173", "http://evil.example"):
        response = client.get("/api/config", headers={"Origin": origin})
        assert response.headers.get("access-control-allow-origin") != "*"
