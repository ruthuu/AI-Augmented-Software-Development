import json
from pathlib import Path

import pytest

from run_eval import (
    CASES_PATH,
    MIN_CASES,
    Case,
    CaseFileError,
    evaluate_structural,
    load_cases,
    redact,
)

WHEN = "2026-11-24T18:00:00+05:30"
NOW = "2026-11-23T10:00:00+05:30"


def reply(**fields: object) -> str:
    base = {
        "intent": None,
        "title": None,
        "reminder_reference": None,
        "scheduled_at": None,
        "clarification": None,
    }
    return json.dumps({**base, **fields})


# --- case loading ---------------------------------------------------------------------------


def make_case(i: int, **over: object) -> dict:
    case = {
        "id": f"TC-{i:02d}",
        "group": "missing_information",
        "category": "clarify_missing_time",
        "tags": [],
        "requirements": ["FR-005"],
        "spec_ref": "synthetic",
        "text": f"synthetic request {i}",
        "now": NOW,
        "expected": {"intent": "CLARIFY", "clarification_keywords_any": ["when"]},
        "properties": ["scheduled_at_null"],
        "rubric": "synthetic",
    }
    case.update(over)
    return case


def write_dataset(tmp_path: Path, cases: list[dict], vocab: dict | None = None) -> Path:
    vocab = (
        {"scheduled_at_null": "x", "title_excludes_forbidden_terms": "y"}
        if vocab is None
        else vocab
    )
    path = tmp_path / "cases.json"
    path.write_text(json.dumps({"property_vocabulary": vocab, "cases": cases}), encoding="utf-8")
    return path


def valid_cases(n: int = MIN_CASES) -> list[dict]:
    return [make_case(i) for i in range(1, n + 1)]


def test_real_case_file_loads() -> None:
    cases = load_cases(CASES_PATH)
    assert len(cases) >= MIN_CASES
    assert all(isinstance(c, Case) for c in cases)
    assert len({c.id for c in cases}) == len(cases)


def test_synthetic_dataset_loads(tmp_path: Path) -> None:
    assert len(load_cases(write_dataset(tmp_path, valid_cases()))) == MIN_CASES


def test_missing_file_is_reported(tmp_path: Path) -> None:
    with pytest.raises(CaseFileError, match="not found"):
        load_cases(tmp_path / "nope.json")


def test_invalid_json_file_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "cases.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(CaseFileError, match="not valid JSON"):
        load_cases(path)


def test_too_few_cases_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(CaseFileError, match="at least"):
        load_cases(write_dataset(tmp_path, valid_cases(MIN_CASES - 1)))


def test_duplicate_ids_are_rejected(tmp_path: Path) -> None:
    cases = valid_cases()
    cases[1]["id"] = cases[0]["id"]
    with pytest.raises(CaseFileError, match="duplicate"):
        load_cases(write_dataset(tmp_path, cases))


@pytest.mark.parametrize(
    ("override", "message"),
    [
        pytest.param({"expected": {"intent": "DELETE"}}, "intent", id="bad-intent"),
        pytest.param({"now": "2026-11-23T10:00:00"}, "now", id="naive-now"),
        pytest.param({"text": "   "}, "text", id="blank-text"),
        pytest.param({"properties": ["not_a_property"]}, "unknown propert", id="unknown-property"),
        pytest.param(
            {"properties": ["title_excludes_forbidden_terms"]}, "forbidden_terms", id="no-terms"
        ),
        pytest.param({"unexpected": 1}, "unexpected", id="extra-key"),
        pytest.param(
            {"expected": {"intent": "CREATE", "title_keywords": ["x"]}},
            "CREATE",
            id="create-incomplete",
        ),
        pytest.param(
            {"expected": {"intent": "CLARIFY", "clarification_keywords_any": []}},
            "clarification_keywords_any",
            id="clarify-no-keywords",
        ),
        pytest.param(
            {
                "expected": {
                    "intent": "CLARIFY",
                    "clarification_keywords_any": ["when"],
                    "scheduled_at": WHEN,
                }
            },
            "CLARIFY",
            id="clarify-with-time",
        ),
    ],
)
def test_invalid_case_is_rejected(tmp_path: Path, override: dict, message: str) -> None:
    cases = valid_cases()
    cases[0] = make_case(1, **override)
    with pytest.raises(CaseFileError, match=message):
        load_cases(write_dataset(tmp_path, cases))


# --- structural layer: valid output ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(reply(intent="CREATE", title="call mom", scheduled_at=WHEN), id="create"),
        pytest.param(
            reply(intent="RESCHEDULE", reminder_reference="dentist", scheduled_at=WHEN),
            id="reschedule",
        ),
        pytest.param(reply(intent="CLARIFY", clarification="When?"), id="clarify"),
        pytest.param('{"intent":"CLARIFY","clarification":"When?"}', id="omitted-nulls"),
    ],
)
def test_valid_output_passes(raw: str) -> None:
    record = evaluate_structural("TC-01", raw)
    assert record.passed is True
    assert record.details == []
    assert record.case_id == "TC-01"
    assert record.layer == "structural"


def test_structural_ignores_the_past_time_guard() -> None:
    # A past datetime is a property/semantic matter; the raw reply is still well-formed.
    raw = reply(intent="CREATE", title="call bank", scheduled_at="2020-01-01T09:00:00+05:30")
    assert evaluate_structural("TC-21", raw).passed is True


# --- structural layer: malformed JSON --------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param("Sure! Here is your reminder", id="prose"),
        pytest.param("", id="empty"),
        pytest.param('{"intent":"CLARIFY"', id="truncated"),
        pytest.param('```json\n{"intent":"CLARIFY","clarification":"x"}\n```', id="fenced"),
        pytest.param("[]", id="array"),
        pytest.param("null", id="null"),
        pytest.param("42", id="number"),
    ],
)
def test_malformed_json_fails(raw: str) -> None:
    record = evaluate_structural("TC-01", raw)
    assert record.passed is False
    assert record.details


def test_no_reply_fails_with_a_reason() -> None:
    record = evaluate_structural("TC-01", None)
    assert record.passed is False
    assert record.details == ["no model reply was received"]


# --- structural layer: missing fields --------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "field"),
    [
        pytest.param('{"title":"x","scheduled_at":"' + WHEN + '"}', "intent", id="no-intent"),
        pytest.param(reply(intent="CREATE", scheduled_at=WHEN), "title", id="create-no-title"),
        pytest.param(reply(intent="CREATE", title="x"), "scheduled_at", id="create-no-time"),
        pytest.param(
            reply(intent="RESCHEDULE", scheduled_at=WHEN), "reminder_reference", id="resched-no-ref"
        ),
        pytest.param(
            reply(intent="RESCHEDULE", reminder_reference="x"), "scheduled_at", id="resched-no-time"
        ),
        pytest.param(reply(intent="CLARIFY"), "clarification", id="clarify-no-question"),
    ],
)
def test_missing_required_field_fails_and_names_it(raw: str, field: str) -> None:
    record = evaluate_structural("TC-01", raw)
    assert record.passed is False
    assert any(field in d for d in record.details)


# --- structural layer: enum values -----------------------------------------------------------


@pytest.mark.parametrize("intent", ["DELETE", "create", "Create", "", None, 5, ["CREATE"]])
def test_invalid_intent_fails(intent: object) -> None:
    record = evaluate_structural("TC-01", reply(intent=intent, clarification="x"))
    assert record.passed is False
    assert any("intent" in d for d in record.details)


# --- structural layer: extra fields ----------------------------------------------------------


def test_extra_field_fails_and_names_it() -> None:
    raw = json.dumps({"intent": "CLARIFY", "clarification": "When?", "confidence": 0.9})
    record = evaluate_structural("TC-01", raw)
    assert record.passed is False
    assert any("confidence" in d for d in record.details)


# --- structural layer: nullability and types -------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(reply(intent="CLARIFY", clarification="q", title="t"), id="clarify-title"),
        pytest.param(
            reply(intent="CLARIFY", clarification="q", scheduled_at=WHEN), id="clarify-time"
        ),
        pytest.param(
            reply(intent="CLARIFY", clarification="q", reminder_reference="r"), id="clarify-ref"
        ),
        pytest.param(
            reply(intent="CREATE", title="t", scheduled_at=WHEN, clarification="q"),
            id="create-clarification",
        ),
        pytest.param(
            reply(intent="CREATE", title="t", scheduled_at=WHEN, reminder_reference="r"),
            id="create-reference",
        ),
        pytest.param(
            reply(intent="RESCHEDULE", reminder_reference="r", scheduled_at=WHEN, title="t"),
            id="reschedule-title",
        ),
        pytest.param(
            reply(intent="CLARIFY", clarification="q", title=""), id="empty-string-instead-of-null"
        ),
    ],
)
def test_incorrect_nullability_fails(raw: str) -> None:
    record = evaluate_structural("TC-01", raw)
    assert record.passed is False
    assert any("must not set" in d for d in record.details) or any(
        "title" in d for d in record.details
    )


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(reply(intent="CREATE", title=5, scheduled_at=WHEN), id="title-int"),
        pytest.param(reply(intent="CREATE", title=["a"], scheduled_at=WHEN), id="title-list"),
        pytest.param(reply(intent="CREATE", title="t", scheduled_at="tomorrow 6pm"), id="non-iso"),
        pytest.param(
            reply(intent="CREATE", title="t", scheduled_at="2026-11-24T18:00:00"), id="naive-time"
        ),
        pytest.param(reply(intent="CREATE", title="t", scheduled_at=1700000000), id="time-int"),
        pytest.param(reply(intent="CREATE", title="x" * 201, scheduled_at=WHEN), id="overlong"),
    ],
)
def test_wrong_types_fail(raw: str) -> None:
    assert evaluate_structural("TC-01", raw).passed is False


# --- details: useful, no raw text, no secrets ------------------------------------------------


def test_details_do_not_echo_the_model_text() -> None:
    marker = "SENSITIVE-MARKER"
    record = evaluate_structural("TC-01", reply(intent="CREATE", title=marker, scheduled_at="bad"))
    assert record.passed is False
    assert all(marker not in d for d in record.details)


def test_redact_masks_key_like_values_and_the_environment_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-env-key-123456")
    text = "a dummy-env-key-123456 b AQ.SyntheticValue1234567890 c AIzaSyA1234567890abcdefghij"
    out = redact(text)
    assert "dummy-env-key-123456" not in out
    assert "AQ.Synthetic" not in out
    assert "AIzaSy" not in out
    assert out.count("[REDACTED]") == 3


def test_redact_leaves_ordinary_text_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert redact("title: Field required") == "title: Field required"


def test_record_is_json_serialisable() -> None:
    record = evaluate_structural("TC-01", "not json")
    assert json.loads(json.dumps(record.to_dict())) == {
        "case_id": "TC-01",
        "layer": "structural",
        "passed": False,
        "details": record.details,
    }
