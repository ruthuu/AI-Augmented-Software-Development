import json

import pytest
from app.agent import PAST_TIME_QUESTION
from app.schemas import AgentResult
from helpers import (
    WHEN,
    clarify_result,
    create_result,
    dt,
    make_case,
    make_run,
    reschedule_result,
)

from run_eval import evaluate_semantic

# --- CREATE and RESCHEDULE -------------------------------------------------------------------


def test_create_matching_expectation_scores_one() -> None:
    record = evaluate_semantic(make_case("CREATE"), make_run(create_result()))
    assert record.passed is True
    assert record.score == 1.0
    assert [c["name"] for c in record.checks] == ["intent", "title_keywords", "scheduled_at"]
    assert all(c["passed"] for c in record.checks)
    assert record.details == []
    assert record.invented_details is False


def test_keywords_are_case_insensitive() -> None:
    record = evaluate_semantic(make_case("CREATE"), make_run(create_result(title="Call MOM")))
    assert record.passed is True


def test_every_keyword_is_required() -> None:
    case = make_case("CREATE")
    object.__setattr__(case.expected, "title_keywords", ["mom", "bank"])
    record = evaluate_semantic(case, make_run(create_result(title="call mom")))
    assert record.passed is False
    assert any("bank" in d for d in record.details)


def test_missing_keyword_fails_and_gives_a_partial_score() -> None:
    record = evaluate_semantic(make_case("CREATE"), make_run(create_result(title="phone dad")))
    assert record.passed is False
    assert record.score == pytest.approx(2 / 3)
    assert any("title_keywords" in d and "mom" in d for d in record.details)


def test_exact_tolerance_zero_rejects_a_one_minute_difference() -> None:
    record = evaluate_semantic(
        make_case("CREATE"), make_run(create_result(when="2026-11-24T18:01:00+05:30"))
    )
    assert record.passed is False
    assert any("scheduled_at" in d and "1.0 minute" in d for d in record.details)


def test_tolerance_allows_small_differences_only() -> None:
    case = make_case("CREATE")
    object.__setattr__(case.expected, "tolerance_minutes", 5)
    assert evaluate_semantic(case, make_run(create_result(when="2026-11-24T18:03:00+05:30"))).passed
    assert evaluate_semantic(case, make_run(create_result(when="2026-11-24T18:05:00+05:30"))).passed
    late = evaluate_semantic(case, make_run(create_result(when="2026-11-24T18:06:00+05:30")))
    assert late.passed is False


def test_the_same_instant_in_another_offset_matches() -> None:
    # 12:30 UTC is 18:00 at +05:30.
    record = evaluate_semantic(
        make_case("CREATE"), make_run(create_result(when="2026-11-24T12:30:00+00:00"))
    )
    assert record.passed is True


def test_reschedule_checks_the_reference_field() -> None:
    case = make_case("RESCHEDULE")
    ok = evaluate_semantic(case, make_run(reschedule_result(ref="my dentist appointment")))
    assert ok.passed is True
    assert [c["name"] for c in ok.checks] == ["intent", "reference_keywords", "scheduled_at"]
    wrong = evaluate_semantic(case, make_run(reschedule_result(ref="gym")))
    assert wrong.passed is False


def test_missing_datetime_fails_the_time_check() -> None:
    result = AgentResult.model_construct(intent="CREATE", title="call mom", scheduled_at=None)
    record = evaluate_semantic(make_case("CREATE"), make_run(result))
    assert record.passed is False
    assert any("scheduled_at" in d for d in record.details)


# --- intent mismatches -----------------------------------------------------------------------


def test_intent_mismatch_fails_everything_and_is_explained() -> None:
    record = evaluate_semantic(make_case("CREATE"), make_run(clarify_result()))
    assert record.passed is False
    assert record.score == 0.0
    assert any("intent" in d and "CREATE" in d and "CLARIFY" in d for d in record.details)
    assert len(record.checks) == 3
    assert not any(c["passed"] for c in record.checks)


@pytest.mark.parametrize("actual", [create_result(), reschedule_result()])
def test_clarify_expected_but_reminder_returned_counts_as_invented(actual: AgentResult) -> None:
    record = evaluate_semantic(make_case("CLARIFY"), make_run(actual))
    assert record.passed is False
    assert record.invented_details is True


def test_other_mismatches_are_not_counted_as_invented() -> None:
    assert (
        evaluate_semantic(make_case("CREATE"), make_run(reschedule_result())).invented_details
        is False
    )
    assert (
        evaluate_semantic(make_case("CREATE"), make_run(clarify_result())).invented_details is False
    )


# --- CLARIFY ---------------------------------------------------------------------------------


def test_clarify_needs_one_of_the_keywords() -> None:
    case = make_case("CLARIFY")
    assert evaluate_semantic(case, make_run(clarify_result("When should I remind you?"))).passed
    assert evaluate_semantic(case, make_run(clarify_result("WHAT TIME?"))).passed
    miss = evaluate_semantic(case, make_run(clarify_result("Tell me more please.")))
    assert miss.passed is False
    assert any("clarification_keywords_any" in d for d in miss.details)
    assert miss.invented_details is False


def test_guard_produced_clarify_is_scored_on_the_final_result() -> None:
    case = make_case("CLARIFY")
    object.__setattr__(case.expected, "clarification_keywords_any", ["past", "future"])
    guarded = AgentResult(intent="CLARIFY", clarification=PAST_TIME_QUESTION)
    record = evaluate_semantic(case, make_run(guarded, guard_applied=True))
    assert record.passed is True


# --- failed runs and serialisation -----------------------------------------------------------


def test_no_final_result_scores_zero_with_the_reason() -> None:
    record = evaluate_semantic(
        make_case("CLARIFY"), make_run(None, error_code="llm_invalid_output", raw_text="x")
    )
    assert record.passed is False
    assert record.score == 0.0
    assert record.invented_details is False
    assert any("no final result" in d and "llm_invalid_output" in d for d in record.details)


def test_record_is_json_serialisable() -> None:
    record = evaluate_semantic(make_case("CREATE"), make_run(create_result(when=WHEN)))
    data = json.loads(json.dumps(record.to_dict()))
    assert data["case_id"] == "TC-X"
    assert data["passed"] is True
    assert data["score"] == 1.0
    assert data["invented_details"] is False
    assert dt(WHEN) is not None
