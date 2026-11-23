import json
from pathlib import Path

import pytest
from app.llm import LLMUnavailableError
from helpers import WHEN, make_case

from run_eval import (
    THRESHOLDS,
    CountingClient,
    aggregate,
    build_verdict,
    evaluate_case,
    main,
    run_case,
    run_evaluation,
    verify_manifest,
    write_manifest,
)

CREATE_REPLY = json.dumps(
    {
        "intent": "CREATE",
        "title": "call mom",
        "reminder_reference": None,
        "scheduled_at": WHEN,
        "clarification": None,
    }
)
CLARIFY_REPLY = json.dumps(
    {
        "intent": "CLARIFY",
        "title": None,
        "reminder_reference": None,
        "scheduled_at": None,
        "clarification": "What time should I remind you?",
    }
)
PAST_REPLY = json.dumps(
    {
        "intent": "CREATE",
        "title": "call bank",
        "reminder_reference": None,
        "scheduled_at": "2026-11-22T15:00:00+05:30",
        "clarification": None,
    }
)


class ScriptedClient:
    """Returns the scripted reply for whichever case text appears in the user message."""

    def __init__(self, replies: dict[str, str], error: Exception | None = None) -> None:
        self.replies = replies
        self.error = error
        self.calls = 0

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        for text, reply in self.replies.items():
            if f"<request>\n{text}\n</request>" in user_message:
                return reply
        raise AssertionError("no scripted reply")


def create_case(i: int = 1):  # noqa: ANN201
    return make_case("CREATE", id=f"TC-{i:02d}", text=f"call mom tomorrow {i}")


def clarify_case(i: int = 2):  # noqa: ANN201
    return make_case("CLARIFY", id=f"TC-{i:02d}", text=f"remind me {i}")


def scripted(cases: list) -> ScriptedClient:  # noqa: ANN001
    return ScriptedClient(
        {c.text: CREATE_REPLY if c.expected.intent == "CREATE" else CLARIFY_REPLY for c in cases}
    )


# --- one case --------------------------------------------------------------------------------


def test_counting_client_counts_each_call() -> None:
    inner = ScriptedClient({"x": CLARIFY_REPLY})
    client = CountingClient(inner)
    assert client.calls == 0
    client.generate("s", "<request>\nx\n</request>")
    assert client.calls == 1 and inner.calls == 1


def test_run_case_success_makes_one_call_and_keeps_the_raw_reply() -> None:
    case = create_case()
    run = run_case(case, scripted([case]))
    assert run.llm_calls == 1
    assert run.raw_text == CREATE_REPLY
    assert run.result is not None and run.result.intent == "CREATE"
    assert run.guard_applied is False
    assert run.error_code is None


def test_run_case_invalid_output_keeps_raw_text_and_an_error_code() -> None:
    case = clarify_case()
    run = run_case(case, ScriptedClient({case.text: "not json at all"}))
    assert run.result is None
    assert run.raw_text == "not json at all"
    assert run.error_code == "llm_invalid_output"
    assert run.llm_calls == 1


def test_run_case_llm_failure_is_recorded_not_raised_and_not_retried() -> None:
    case = clarify_case()
    client = ScriptedClient({}, error=LLMUnavailableError("Gemini request failed (ClientError)"))
    run = run_case(case, client)
    assert run.result is None and run.raw_text is None
    assert run.error_code == "llm_unavailable"
    assert run.error_detail == "Gemini request failed (ClientError)"
    assert run.llm_calls == 1 and client.calls == 1


def test_past_time_guard_is_recorded() -> None:
    case = make_case("CLARIFY", text="call the bank yesterday")
    object.__setattr__(case.expected, "clarification_keywords_any", ["past", "future"])
    run = run_case(case, ScriptedClient({case.text: PAST_REPLY}))
    assert run.guard_applied is True
    assert run.raw_text == PAST_REPLY
    result = evaluate_case(case, run)
    assert result["past_time_guard_applied"] is True
    assert result["structural"]["passed"] is True
    assert result["semantic"]["passed"] is True


def test_evaluate_case_combines_the_three_layers() -> None:
    case = create_case()
    result = evaluate_case(case, run_case(case, scripted([case])))
    assert result["case_id"] == case.id
    assert result["structural"]["passed"] and result["property"]["passed"]
    assert result["semantic"]["passed"] and result["passed_all"] is True
    assert result["actual_intent"] == "CREATE"
    assert result["llm_calls"] == 1
    json.dumps(result)


# --- aggregation and verdict -----------------------------------------------------------------


def results_for(cases: list, client: ScriptedClient) -> list[dict]:  # noqa: ANN001
    return [evaluate_case(c, run_case(c, client)) for c in cases]


def test_aggregate_counts_each_layer() -> None:
    cases = [create_case(1), clarify_case(2), clarify_case(3)]
    client = scripted(cases)
    client.replies[cases[2].text] = "not json"
    agg = aggregate(results_for(cases, client))

    assert agg["cases"] == 3
    assert agg["structural"] == {"passed": 2, "total": 3, "rate": pytest.approx(2 / 3)}
    assert agg["property"]["passed"] == 2
    assert agg["semantic"]["passed"] == 2
    assert agg["semantic"]["mean_score"] == pytest.approx(2 / 3)
    assert agg["errors"] == 1
    assert agg["llm_calls_total"] == 3
    assert agg["past_time_guard_applied"] == {"count": 0, "case_ids": []}


def test_verdict_passes_when_every_criterion_is_met() -> None:
    cases = [create_case(1), clarify_case(2)]
    results = results_for(cases, scripted(cases))
    verdict = build_verdict(aggregate(results), results, expected_cases=2)
    assert verdict["overall"] == "PASS"
    assert verdict["failed_cases"] == []
    assert all(c["met"] for c in verdict["criteria"])
    assert {c["name"] for c in verdict["criteria"]} >= {
        "all cases executed",
        "structural pass rate",
        "property pass rate",
        "semantic pass rate",
        "cases with invented details",
    }


def test_verdict_fails_and_lists_failed_cases_with_reasons() -> None:
    cases = [create_case(1), clarify_case(2)]
    client = scripted(cases)
    client.replies[cases[1].text] = "not json"
    results = results_for(cases, client)
    verdict = build_verdict(aggregate(results), results, expected_cases=2)

    assert verdict["overall"] == "FAIL"
    [failed] = verdict["failed_cases"]
    assert failed["case_id"] == "TC-02"
    assert failed["failed_layers"] == ["structural", "property", "semantic"]
    assert failed["reasons"]["structural"]


def test_an_invented_detail_fails_overall_even_if_the_semantic_rate_is_high() -> None:
    cases = [create_case(i) for i in range(1, 11)] + [clarify_case(11)]
    client = scripted(cases)
    client.replies[cases[-1].text] = CREATE_REPLY  # CLARIFY expected, reminder returned
    results = results_for(cases, client)
    agg = aggregate(results)
    verdict = build_verdict(agg, results, expected_cases=11)

    assert agg["semantic"]["rate"] >= THRESHOLDS["semantic_min"]
    assert agg["invented_details"]["case_ids"] == ["TC-11"]
    assert verdict["overall"] == "FAIL"
    [unmet] = [c for c in verdict["criteria"] if not c["met"]]
    assert unmet["name"] == "cases with invented details"


def test_a_missing_case_result_fails_the_completeness_criterion() -> None:
    cases = [create_case(1)]
    results = results_for(cases, scripted(cases))
    verdict = build_verdict(aggregate(results), results, expected_cases=2)
    assert verdict["overall"] == "FAIL"
    assert any(c["name"] == "all cases executed" and not c["met"] for c in verdict["criteria"])


# --- full run and evidence -------------------------------------------------------------------


def test_run_evaluation_writes_results_raw_outputs_manifest_and_log(tmp_path: Path) -> None:
    cases = [create_case(1), clarify_case(2), clarify_case(3)]
    client = scripted(cases)
    client.replies[cases[2].text] = "not json"
    run_dir = tmp_path / "run-test"
    log = tmp_path / "harness-log.md"

    results = run_evaluation(
        cases, client, run_dir, command="python harness/run_eval.py", log_path=log, model="m-1"
    )

    on_disk = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(results))
    assert on_disk["meta"]["model"] == "m-1"
    assert on_disk["meta"]["case_count"] == 3
    assert on_disk["meta"]["thresholds"] == THRESHOLDS
    assert on_disk["verdict"]["overall"] == "FAIL"
    assert [c["case_id"] for c in on_disk["cases"]] == ["TC-01", "TC-02", "TC-03"]
    assert (run_dir / "raw" / "TC-01.txt").read_text(encoding="utf-8") == CREATE_REPLY
    assert (run_dir / "raw" / "TC-03.txt").read_text(encoding="utf-8") == "not json"
    assert verify_manifest(run_dir) == []
    assert client.calls == 3

    text = log.read_text(encoding="utf-8")
    assert "# Harness Log" in text
    assert "structural: 2/3" in text and "property: 2/3" in text and "semantic: 2/3" in text
    assert "Overall: FAIL" in text
    assert "TC-03" in text
    assert "python harness/run_eval.py" in text


def test_log_entries_are_appended_not_replaced(tmp_path: Path) -> None:
    cases = [create_case(1)]
    log = tmp_path / "harness-log.md"
    run_evaluation(cases, scripted(cases), tmp_path / "run-a", log_path=log)
    run_evaluation(cases, scripted(cases), tmp_path / "run-b", log_path=log)
    text = log.read_text(encoding="utf-8")
    assert text.count("# Harness Log") == 1
    assert "run-a" in text and "run-b" in text
    assert text.count("Overall: PASS") == 2


def test_an_existing_run_folder_is_never_overwritten(tmp_path: Path) -> None:
    cases = [create_case(1)]
    run_dir = tmp_path / "run-x"
    run_dir.mkdir()
    (run_dir / "keep.txt").write_text("old evidence", encoding="utf-8")
    log = tmp_path / "harness-log.md"
    client = scripted(cases)

    with pytest.raises(FileExistsError):
        run_evaluation(cases, client, run_dir, log_path=log)

    assert (run_dir / "keep.txt").read_text(encoding="utf-8") == "old evidence"
    assert client.calls == 0
    assert not log.exists()


def test_calls_are_paced_between_cases_only(tmp_path: Path) -> None:
    cases = [create_case(1), clarify_case(2), clarify_case(3)]
    sleeps: list[float] = []
    run_evaluation(
        cases, scripted(cases), tmp_path / "run", delay=2.5, sleep=sleeps.append, log_path=None
    )
    assert sleeps == [2.5, 2.5]


def test_an_llm_failure_is_recorded_as_a_failure_on_every_layer(tmp_path: Path) -> None:
    cases = [create_case(1)]
    client = ScriptedClient({}, error=LLMUnavailableError("Gemini request failed (ClientError)"))
    results = run_evaluation(cases, client, tmp_path / "run", log_path=None)
    [case] = results["cases"]
    assert case["error_code"] == "llm_unavailable"
    assert not case["structural"]["passed"]
    assert not case["property"]["passed"]
    assert not case["semantic"]["passed"]
    assert results["verdict"]["overall"] == "FAIL"
    assert (
        (tmp_path / "run" / "raw" / "TC-01.txt").read_text(encoding="utf-8").startswith("<no reply")
    )
    assert client.calls == 1


def test_key_like_text_is_redacted_everywhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-env-key-123456")
    case = clarify_case(1)
    reply = CLARIFY_REPLY.replace("What time", "dummy-env-key-123456 What time")
    run_dir = tmp_path / "run"
    run_evaluation([case], ScriptedClient({case.text: reply}), run_dir, log_path=None)

    for path in run_dir.rglob("*"):
        if path.is_file():
            assert "dummy-env-key-123456" not in path.read_text(encoding="utf-8")


def test_guard_cases_are_listed_in_the_aggregate(tmp_path: Path) -> None:
    case = make_case("CLARIFY", id="TC-21", text="call the bank yesterday")
    object.__setattr__(case.expected, "clarification_keywords_any", ["past"])
    results = run_evaluation(
        [case], ScriptedClient({case.text: PAST_REPLY}), tmp_path / "run", log_path=None
    )
    assert results["aggregate"]["past_time_guard_applied"] == {"count": 1, "case_ids": ["TC-21"]}


# --- manifest --------------------------------------------------------------------------------


def test_manifest_detects_changed_missing_and_extra_files(tmp_path: Path) -> None:
    (tmp_path / "raw").mkdir()
    (tmp_path / "results.json").write_text("{}", encoding="utf-8")
    (tmp_path / "raw" / "a.txt").write_text("a", encoding="utf-8")
    write_manifest(tmp_path)
    assert verify_manifest(tmp_path) == []

    (tmp_path / "raw" / "a.txt").write_text("changed", encoding="utf-8")
    (tmp_path / "extra.txt").write_text("x", encoding="utf-8")
    (tmp_path / "results.json").unlink()
    problems = " ".join(verify_manifest(tmp_path))
    assert "a.txt" in problems and "extra.txt" in problems and "results.json" in problems


def test_manifest_uses_forward_slashes_and_excludes_itself(tmp_path: Path) -> None:
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "a.txt").write_text("a", encoding="utf-8")
    write_manifest(tmp_path)
    lines = (tmp_path / "manifest.sha256.txt").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert lines[0].endswith("  raw/a.txt") and len(lines[0].split()[0]) == 64


# --- command line ----------------------------------------------------------------------------


def test_main_refuses_to_run_without_a_key_and_creates_no_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    run_dir = tmp_path / "run"
    code = main(["--env-file", str(tmp_path / "missing.env"), "--run-dir", str(run_dir)])
    assert code == 2
    assert not run_dir.exists()


def test_main_check_cases_succeeds() -> None:
    assert main(["--check-cases"]) == 0


def test_main_verify_manifest(tmp_path: Path) -> None:
    (tmp_path / "f.txt").write_text("f", encoding="utf-8")
    write_manifest(tmp_path)
    assert main(["--verify-manifest", str(tmp_path)]) == 0
    (tmp_path / "f.txt").write_text("tampered", encoding="utf-8")
    assert main(["--verify-manifest", str(tmp_path)]) == 1
