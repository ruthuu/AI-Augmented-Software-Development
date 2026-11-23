import json

import pytest
from fastapi.testclient import TestClient

from app.agent import PAST_TIME_QUESTION
from app.main import app, get_llm_client
from tests.support import FakeLLMClient, unavailable

NOTE = "Interpretation only. No reminder was created, updated, stored or scheduled."
NOW = "2026-11-23T10:00:00+05:30"
FRONTEND_ORIGIN = "http://localhost:5173"


def llm_reply(**fields: object) -> str:
    base = {
        "intent": None,
        "title": None,
        "reminder_reference": None,
        "scheduled_at": None,
        "clarification": None,
    }
    return json.dumps({**base, **fields})


def post(client: TestClient, text: str = "Remind me to call mom tomorrow at 6pm") -> object:
    return client.post("/api/interpret", json={"text": text, "now": NOW})


# --- health ---------------------------------------------------------------------------------


def test_health(client: TestClient, fake_llm: FakeLLMClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert fake_llm.calls == []


# --- success --------------------------------------------------------------------------------


def test_create(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply = llm_reply(
        intent="CREATE", title="call mom", scheduled_at="2026-11-24T18:00:00+05:30"
    )
    response = post(client)

    assert response.status_code == 200
    assert response.json() == {
        "result": {
            "intent": "CREATE",
            "title": "call mom",
            "reminder_reference": None,
            "scheduled_at": "2026-11-24T18:00:00+05:30",
            "clarification": None,
        },
        "persisted": False,
        "note": NOTE,
    }
    assert len(fake_llm.calls) == 1


def test_reschedule(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply = llm_reply(
        intent="RESCHEDULE", reminder_reference="dentist", scheduled_at="2026-11-27T16:00:00+05:30"
    )
    response = post(client, "Move my dentist reminder to Friday at 4pm")

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intent"] == "RESCHEDULE"
    assert body["result"]["reminder_reference"] == "dentist"
    assert body["result"]["scheduled_at"] == "2026-11-27T16:00:00+05:30"
    assert body["persisted"] is False
    assert body["note"] == NOTE
    assert len(fake_llm.calls) == 1


def test_clarify(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.reply = llm_reply(intent="CLARIFY", clarification="What time should I remind you?")
    response = post(client, "Remind me to call the bank")

    assert response.status_code == 200
    body = response.json()
    assert body["result"] == {
        "intent": "CLARIFY",
        "title": None,
        "reminder_reference": None,
        "scheduled_at": None,
        "clarification": "What time should I remind you?",
    }
    assert body["persisted"] is False
    assert body["note"] == NOTE


def test_past_time_is_a_normal_clarify_not_an_error(
    client: TestClient, fake_llm: FakeLLMClient
) -> None:
    fake_llm.reply = llm_reply(
        intent="CREATE", title="call bank", scheduled_at="2026-11-22T15:00:00+05:30"
    )
    response = post(client, "Remind me to call the bank yesterday at 3pm")

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["intent"] == "CLARIFY"
    assert body["result"]["clarification"] == PAST_TIME_QUESTION
    assert body["result"]["scheduled_at"] is None
    assert len(fake_llm.calls) == 1


# --- invalid requests -----------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": "", "now": NOW}, id="empty-text"),
        pytest.param({"text": "   ", "now": NOW}, id="blank-text"),
        pytest.param({"text": "a" * 501, "now": NOW}, id="overlong-text"),
        pytest.param({"now": NOW}, id="missing-text"),
        pytest.param({"text": "x"}, id="missing-now"),
        pytest.param({"text": "x", "now": "2026-11-23T10:00:00"}, id="naive-now"),
        pytest.param({"text": "x", "now": "not a date"}, id="invalid-now"),
        pytest.param({"text": "x", "now": NOW, "extra": 1}, id="unknown-field"),
        pytest.param({"text": 123, "now": NOW}, id="text-not-a-string"),
        pytest.param(["text"], id="body-not-an-object"),
    ],
)
def test_invalid_request_is_422_and_makes_no_model_call(
    client: TestClient, fake_llm: FakeLLMClient, payload: object
) -> None:
    response = client.post("/api/interpret", json=payload)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "invalid_request"
    assert error["message"]
    assert fake_llm.calls == []


def test_malformed_json_body_is_422(client: TestClient, fake_llm: FakeLLMClient) -> None:
    response = client.post(
        "/api/interpret", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert fake_llm.calls == []


def test_422_body_does_not_echo_the_submitted_text(client: TestClient) -> None:
    response = client.post("/api/interpret", json={"text": "a" * 501, "now": NOW})
    assert "aaaaaaaaaa" not in response.text


def test_wrong_method_is_405(client: TestClient) -> None:
    assert client.get("/api/interpret").status_code == 405


# --- model failures -------------------------------------------------------------------------


def test_llm_failure_is_a_safe_502(client: TestClient, fake_llm: FakeLLMClient) -> None:
    fake_llm.error = unavailable()
    response = post(client)

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "llm_unavailable",
            "message": "The language model could not be reached. Try again later.",
        }
    }
    assert "FakeError" not in response.text
    assert len(fake_llm.calls) == 1


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("MODEL-SAID-THIS plain text", id="not-json"),
        pytest.param("", id="empty"),
        pytest.param(llm_reply(intent="DELETE", clarification="MODEL-SAID-THIS"), id="bad-intent"),
        pytest.param(llm_reply(intent="CREATE", title="MODEL-SAID-THIS"), id="missing-time"),
    ],
)
def test_invalid_model_output_is_a_safe_502(
    client: TestClient, fake_llm: FakeLLMClient, raw: str
) -> None:
    fake_llm.reply = raw
    response = post(client)

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "llm_invalid_output",
            "message": "The model returned a reply that does not match the required format.",
        }
    }
    assert "MODEL-SAID-THIS" not in response.text
    assert len(fake_llm.calls) == 1


def test_missing_api_key_is_a_safe_502_with_no_network_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_llm_client.cache_clear()
    app.dependency_overrides.clear()

    response = post(TestClient(app))

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "llm_unavailable"
    assert "GEMINI_API_KEY" not in response.text
    get_llm_client.cache_clear()


# --- CORS -----------------------------------------------------------------------------------


@pytest.mark.parametrize("origin", [FRONTEND_ORIGIN, "http://127.0.0.1:5173"])
def test_cors_allows_the_local_frontend(client: TestClient, origin: str) -> None:
    response = client.options(
        "/api/interpret",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_rejects_other_origins(client: TestClient) -> None:
    response = client.options(
        "/api/interpret",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in response.headers
