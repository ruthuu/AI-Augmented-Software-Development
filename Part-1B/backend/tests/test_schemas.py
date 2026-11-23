import pytest
from pydantic import ValidationError

from app.schemas import AgentResult, InterpretRequest

WHEN = "2026-11-24T18:00:00+05:30"


def test_valid_create() -> None:
    r = AgentResult.model_validate({"intent": "CREATE", "title": "call mom", "scheduled_at": WHEN})
    assert r.intent == "CREATE"
    assert r.title == "call mom"
    assert r.scheduled_at is not None and r.scheduled_at.utcoffset() is not None
    assert r.reminder_reference is None and r.clarification is None


def test_valid_reschedule() -> None:
    r = AgentResult.model_validate(
        {"intent": "RESCHEDULE", "reminder_reference": "dentist", "scheduled_at": WHEN}
    )
    assert r.reminder_reference == "dentist"
    assert r.title is None and r.clarification is None


def test_valid_clarify() -> None:
    r = AgentResult.model_validate({"intent": "CLARIFY", "clarification": "When?"})
    assert r.clarification == "When?"
    assert r.title is None and r.reminder_reference is None and r.scheduled_at is None


def test_explicit_nulls_are_accepted() -> None:
    raw = (
        '{"intent":"CLARIFY","title":null,"reminder_reference":null,'
        '"scheduled_at":null,"clarification":"When?"}'
    )
    assert AgentResult.model_validate_json(raw).intent == "CLARIFY"


def test_json_datetime_string_parsed() -> None:
    raw = f'{{"intent":"CREATE","title":"x","scheduled_at":"{WHEN}"}}'
    assert AgentResult.model_validate_json(raw).scheduled_at.isoformat() == WHEN


def test_text_is_trimmed() -> None:
    r = AgentResult.model_validate(
        {"intent": "CREATE", "title": "  call mom  ", "scheduled_at": WHEN}
    )
    assert r.title == "call mom"


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"intent": "DELETE", "clarification": "x"}, id="unknown-intent"),
        pytest.param(
            {"intent": "create", "title": "x", "scheduled_at": WHEN}, id="lowercase-intent"
        ),
        pytest.param({"title": "x", "scheduled_at": WHEN}, id="missing-intent"),
        pytest.param(
            {"intent": "CREATE", "title": "x", "scheduled_at": WHEN, "priority": "high"},
            id="extra-field",
        ),
        pytest.param({"intent": "CREATE", "scheduled_at": WHEN}, id="create-missing-title"),
        pytest.param({"intent": "CREATE", "title": "x"}, id="create-missing-time"),
        pytest.param(
            {"intent": "CREATE", "title": "x", "scheduled_at": WHEN, "clarification": "q"},
            id="create-with-clarification",
        ),
        pytest.param(
            {"intent": "CREATE", "title": "x", "scheduled_at": WHEN, "reminder_reference": "r"},
            id="create-with-reference",
        ),
        pytest.param(
            {"intent": "RESCHEDULE", "scheduled_at": WHEN}, id="reschedule-missing-reference"
        ),
        pytest.param(
            {"intent": "RESCHEDULE", "reminder_reference": "r"}, id="reschedule-missing-time"
        ),
        pytest.param(
            {"intent": "RESCHEDULE", "reminder_reference": "r", "scheduled_at": WHEN, "title": "t"},
            id="reschedule-with-title",
        ),
        pytest.param(
            {
                "intent": "RESCHEDULE",
                "reminder_reference": "r",
                "scheduled_at": WHEN,
                "clarification": "q",
            },
            id="reschedule-with-clarification",
        ),
        pytest.param({"intent": "CLARIFY"}, id="clarify-missing-question"),
        pytest.param({"intent": "CLARIFY", "clarification": "  "}, id="clarify-blank-question"),
        pytest.param(
            {"intent": "CLARIFY", "clarification": "q", "scheduled_at": WHEN},
            id="clarify-with-time",
        ),
        pytest.param(
            {"intent": "CLARIFY", "clarification": "q", "title": "t"}, id="clarify-with-title"
        ),
        pytest.param(
            {"intent": "CLARIFY", "clarification": "q", "reminder_reference": "r"},
            id="clarify-with-reference",
        ),
        pytest.param({"intent": "CLARIFY", "clarification": ""}, id="clarify-empty-string"),
        pytest.param(
            {"intent": "CREATE", "title": "x", "scheduled_at": "2026-11-24T18:00:00"},
            id="naive-datetime",
        ),
        pytest.param(
            {"intent": "CREATE", "title": "x", "scheduled_at": "tomorrow 6pm"},
            id="non-iso-datetime",
        ),
        pytest.param({"intent": "CREATE", "title": "  ", "scheduled_at": WHEN}, id="blank-title"),
        pytest.param(
            {"intent": "CREATE", "title": "x" * 201, "scheduled_at": WHEN}, id="overlong-title"
        ),
        pytest.param({"intent": "CLARIFY", "clarification": "q" * 301}, id="overlong-question"),
    ],
)
def test_invalid_results_are_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate(payload)


def test_non_json_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate_json("Sure! Here is your reminder")


def test_request_valid() -> None:
    r = InterpretRequest.model_validate({"text": " Remind me ", "now": "2026-11-23T10:00:00+05:30"})
    assert r.text == "Remind me"
    assert r.now.utcoffset() is not None


def test_request_text_limit_boundary() -> None:
    now = "2026-11-23T10:00:00+05:30"
    assert InterpretRequest.model_validate({"text": "a" * 500, "now": now})
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "a" * 501, "now": now})


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": "", "now": "2026-11-23T10:00:00+05:30"}, id="empty-text"),
        pytest.param({"text": "   ", "now": "2026-11-23T10:00:00+05:30"}, id="blank-text"),
        pytest.param({"now": "2026-11-23T10:00:00+05:30"}, id="missing-text"),
        pytest.param({"text": "x"}, id="missing-now"),
        pytest.param({"text": "x", "now": "2026-11-23T10:00:00"}, id="naive-now"),
        pytest.param({"text": "x", "now": "not a date"}, id="invalid-now"),
        pytest.param(
            {"text": "x", "now": "2026-11-23T10:00:00+05:30", "extra": 1}, id="extra-field"
        ),
    ],
)
def test_invalid_requests_are_rejected(payload: dict) -> None:
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate(payload)


@pytest.mark.parametrize("value", [1700000000, 1700000000.5, "1700000000", "1700000000.5", True])
def test_epoch_numbers_are_not_accepted_as_datetimes(value: object) -> None:
    with pytest.raises(ValidationError):
        AgentResult.model_validate({"intent": "CREATE", "title": "x", "scheduled_at": value})
    with pytest.raises(ValidationError):
        InterpretRequest.model_validate({"text": "x", "now": value})


@pytest.mark.parametrize("value", ["2026-11-24T18:00:00Z", "2026-11-24T18:00:00+05:30"])
def test_iso_datetimes_with_an_offset_are_accepted(value: str) -> None:
    r = AgentResult.model_validate({"intent": "CREATE", "title": "x", "scheduled_at": value})
    assert r.scheduled_at is not None and r.scheduled_at.utcoffset() is not None
