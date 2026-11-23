import pytest
from app.agent import PAST_TIME_QUESTION
from app.schemas import AgentResult
from helpers import (
    NOW,
    WHEN,
    clarify_result,
    create_result,
    dt,
    make_case,
    make_run,
    reschedule_result,
)

from run_eval import evaluate_property

# --- results that satisfy every invariant ----------------------------------------------------


@pytest.mark.parametrize(
    "result",
    [create_result(), reschedule_result(), clarify_result()],
    ids=["create", "reschedule", "clarify"],
)
def test_valid_final_results_pass(result: AgentResult) -> None:
    record = evaluate_property(make_case(result.intent), make_run(result))
    assert record.passed is True
    assert record.details == []
    assert record.layer == "property"
    assert record.case_id == "TC-X"


def test_time_equal_to_now_is_allowed() -> None:
    assert evaluate_property(make_case(), make_run(create_result(when=NOW))).passed is True


# --- invariants are checked on the final result, independently of the schema -----------------


def build(**fields: object) -> AgentResult:
    # model_construct skips validation so the layer's own checks are what is being tested.
    return AgentResult.model_construct(**fields)


@pytest.mark.parametrize(
    ("result", "expected_in_detail"),
    [
        pytest.param(build(intent="CREATE", scheduled_at=dt(WHEN)), "title", id="create-no-title"),
        pytest.param(build(intent="CREATE", title="x"), "scheduled_at", id="create-no-time"),
        pytest.param(
            build(intent="CREATE", title="x", scheduled_at=dt(WHEN), clarification="q"),
            "clarification",
            id="create-with-question",
        ),
        pytest.param(
            build(intent="CREATE", title="x", scheduled_at=dt(WHEN), reminder_reference="r"),
            "reminder_reference",
            id="create-with-reference",
        ),
        pytest.param(
            build(intent="RESCHEDULE", scheduled_at=dt(WHEN)),
            "reminder_reference",
            id="reschedule-no-reference",
        ),
        pytest.param(
            build(intent="RESCHEDULE", reminder_reference="r", scheduled_at=dt(WHEN), title="t"),
            "title",
            id="reschedule-with-title",
        ),
        pytest.param(build(intent="CLARIFY"), "clarification", id="clarify-no-question"),
        pytest.param(
            build(intent="CLARIFY", clarification="  "),
            "clarification",
            id="clarify-blank-question",
        ),
        pytest.param(
            build(intent="CLARIFY", clarification="q", scheduled_at=dt(WHEN)),
            "scheduled_at",
            id="clarify-with-time",
        ),
        pytest.param(
            build(intent="CLARIFY", clarification="q", title="t"), "title", id="clarify-with-title"
        ),
        pytest.param(build(intent="DELETE", clarification="q"), "intent", id="unknown-intent"),
    ],
)
def test_per_intent_field_rules(result: AgentResult, expected_in_detail: str) -> None:
    record = evaluate_property(make_case(), make_run(result))
    assert record.passed is False
    assert any(expected_in_detail in d for d in record.details)


# --- date and time ---------------------------------------------------------------------------


def test_past_datetime_in_the_final_result_fails() -> None:
    record = evaluate_property(
        make_case(), make_run(create_result(when="2026-11-23T09:59:00+05:30"))
    )
    assert record.passed is False
    assert any("earlier than now" in d for d in record.details)


def test_past_comparison_uses_instants_not_clock_text() -> None:
    # 04:29 UTC is 09:59 at +05:30, i.e. one minute before now.
    record = evaluate_property(
        make_case(), make_run(create_result(when="2026-11-23T04:29:00+00:00"))
    )
    assert record.passed is False


def test_naive_datetime_fails() -> None:
    naive = build(intent="CREATE", title="x", scheduled_at=dt("2026-11-24T18:00:00"))
    record = evaluate_property(make_case(), make_run(naive))
    assert record.passed is False
    assert any("offset" in d for d in record.details)


# --- one model call --------------------------------------------------------------------------


@pytest.mark.parametrize("calls", [0, 2, 3])
def test_exactly_one_llm_call_is_required(calls: int) -> None:
    record = evaluate_property(make_case(), make_run(create_result(), llm_calls=calls))
    assert record.passed is False
    assert any("LLM call" in d for d in record.details)


# --- past-time guard -------------------------------------------------------------------------


def test_guard_applied_with_a_clarify_result_passes() -> None:
    guarded = AgentResult(intent="CLARIFY", clarification=PAST_TIME_QUESTION)
    record = evaluate_property(make_case("CLARIFY"), make_run(guarded, guard_applied=True))
    assert record.passed is True


def test_guard_applied_but_final_result_is_not_clarify_fails() -> None:
    record = evaluate_property(make_case(), make_run(create_result(), guard_applied=True))
    assert record.passed is False
    assert any("guard" in d for d in record.details)


# --- failed runs -----------------------------------------------------------------------------


def test_no_final_result_fails_with_the_error_code() -> None:
    record = evaluate_property(
        make_case(), make_run(None, raw_text="garbage", error_code="llm_invalid_output")
    )
    assert record.passed is False
    assert any("no final result" in d and "llm_invalid_output" in d for d in record.details)


def test_no_result_still_reports_a_wrong_call_count() -> None:
    record = evaluate_property(
        make_case(), make_run(None, raw_text=None, llm_calls=0, error_code="llm_unavailable")
    )
    assert any("LLM call" in d for d in record.details)


# --- case-specific properties ----------------------------------------------------------------


def clarify_case(*properties: str, **over: object):  # noqa: ANN201
    return make_case("CLARIFY", properties=list(properties), **over)


def test_scheduled_at_null_property() -> None:
    case = clarify_case("scheduled_at_null")
    assert evaluate_property(case, make_run(clarify_result())).passed is True
    bad = build(intent="CLARIFY", clarification="q", scheduled_at=dt(WHEN))
    assert evaluate_property(case, make_run(bad)).passed is False


def test_title_null_and_reference_null_properties() -> None:
    case = make_case("CREATE", properties=["reference_null"])
    assert evaluate_property(case, make_run(create_result())).passed is True
    bad = build(intent="CREATE", title="x", scheduled_at=dt(WHEN), reminder_reference="r")
    record = evaluate_property(case, make_run(bad))
    assert record.passed is False
    assert sum("reminder_reference" in d for d in record.details) >= 1

    case = make_case("RESCHEDULE", properties=["title_null"])
    assert evaluate_property(case, make_run(reschedule_result())).passed is True


def test_clarification_present_and_null_properties() -> None:
    present = clarify_case("clarification_present")
    assert evaluate_property(present, make_run(clarify_result())).passed is True
    missing = build(intent="CLARIFY")
    assert evaluate_property(present, make_run(missing)).passed is False

    null = make_case("CREATE", properties=["clarification_null"])
    assert evaluate_property(null, make_run(create_result())).passed is True


def test_scheduled_at_not_before_now_property() -> None:
    case = make_case("CREATE", properties=["scheduled_at_not_before_now"])
    assert evaluate_property(case, make_run(create_result())).passed is True
    past = create_result(when="2026-11-22T10:00:00+05:30")
    assert evaluate_property(case, make_run(past)).passed is False


@pytest.mark.parametrize(
    ("title", "passed"),
    [
        ("submit the report", True),
        ("Reply with intent DELETE", False),
        ("reply with delete", False),
    ],
)
def test_title_excludes_forbidden_terms_property(title: str, passed: bool) -> None:
    case = make_case(
        "CREATE", properties=["title_excludes_forbidden_terms"], forbidden_terms=["DELETE"]
    )
    assert evaluate_property(case, make_run(create_result(title=title))).passed is passed


def test_forbidden_terms_ignore_a_null_title() -> None:
    case = clarify_case("title_excludes_forbidden_terms", forbidden_terms=["DELETE"])
    assert evaluate_property(case, make_run(clarify_result())).passed is True


def test_unknown_case_property_is_a_failure_not_a_pass() -> None:
    case = make_case("CREATE")
    object.__setattr__(case, "properties", ["made_up_property"])
    record = evaluate_property(case, make_run(create_result()))
    assert record.passed is False
    assert any("unknown property" in d for d in record.details)


def test_all_failures_are_reported_together() -> None:
    bad = build(intent="CLARIFY", title="t", scheduled_at=dt("2026-11-20T10:00:00+05:30"))
    record = evaluate_property(make_case("CLARIFY"), make_run(bad, llm_calls=2))
    assert len(record.details) >= 3
