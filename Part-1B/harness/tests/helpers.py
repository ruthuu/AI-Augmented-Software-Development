from datetime import datetime

from app.schemas import AgentResult

from run_eval import Case, CaseRun

NOW = "2026-11-23T10:00:00+05:30"
WHEN = "2026-11-24T18:00:00+05:30"


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def make_case(intent: str = "CREATE", **over: object) -> Case:
    expected: dict[str, object] = {"intent": intent}
    if intent == "CREATE":
        expected.update(title_keywords=["mom"], scheduled_at=WHEN, tolerance_minutes=0)
    elif intent == "RESCHEDULE":
        expected.update(reference_keywords=["dentist"], scheduled_at=WHEN, tolerance_minutes=0)
    else:
        expected.update(clarification_keywords_any=["when", "time"])
    case = {
        "id": "TC-X",
        "group": "g",
        "category": "c",
        "tags": [],
        "requirements": ["FR-003"],
        "spec_ref": "synthetic",
        "text": "synthetic request",
        "now": NOW,
        "expected": expected,
        "properties": [],
        "rubric": "synthetic",
    }
    case.update(over)
    return Case.model_validate(case)


def create_result(title: str = "call mom", when: str = WHEN) -> AgentResult:
    return AgentResult(intent="CREATE", title=title, scheduled_at=dt(when))


def reschedule_result(ref: str = "dentist", when: str = WHEN) -> AgentResult:
    return AgentResult(intent="RESCHEDULE", reminder_reference=ref, scheduled_at=dt(when))


def clarify_result(question: str = "What time should I remind you?") -> AgentResult:
    return AgentResult(intent="CLARIFY", clarification=question)


def make_run(
    result: AgentResult | None,
    *,
    raw_text: str | None = "{}",
    guard_applied: bool = False,
    llm_calls: int = 1,
    error_code: str | None = None,
) -> CaseRun:
    return CaseRun(
        case_id="TC-X",
        raw_text=raw_text,
        result=result,
        guard_applied=guard_applied,
        llm_calls=llm_calls,
        error_code=error_code,
    )
