"""Evaluation harness for the reminder agent: three layers, reporting and evidence."""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = HARNESS_DIR.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.agent import InvalidOutputError, interpret  # noqa: E402
from app.llm import DEFAULT_MODEL, GeminiClient, LLMClient, LLMUnavailableError  # noqa: E402
from app.schemas import AgentResult, Intent  # noqa: E402
from dotenv import load_dotenv  # noqa: E402
from pydantic import (  # noqa: E402
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)

CASES_PATH = HARNESS_DIR / "cases" / "cases.json"
MIN_CASES = 15

HARNESS_VERSION = "1.0"
PART_DIR = HARNESS_DIR.parent
EVIDENCE_DIR = PART_DIR / "evidence"
LOG_PATH = PART_DIR / "harness-log.md"
MANIFEST_NAME = "manifest.sha256.txt"

# Pass rule for the overall verdict. The spec (SC-003, SC-004, SC-005) fixes the structural,
# property and invented-detail limits; it sets no semantic threshold, so semantic_min is a
# harness-declared value, fixed before the first real run.
THRESHOLDS = {
    "structural_min": 1.0,
    "property_min": 1.0,
    "semantic_min": 0.9,
    "invented_details_max": 0,
}

_SECRET_PATTERNS = [
    re.compile(r"AQ\.[A-Za-z0-9_\-]{16,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{20,}"),
]


class CaseFileError(Exception):
    """The evaluation case file is missing or invalid."""


# --- evaluation cases -----------------------------------------------------------------------


class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Intent
    title_keywords: list[str] | None = None
    reference_keywords: list[str] | None = None
    scheduled_at: AwareDatetime | None = None
    tolerance_minutes: int | None = Field(default=None, ge=0)
    clarification_keywords_any: list[str] | None = None

    @model_validator(mode="after")
    def _check_intent_fields(self) -> "Expected":
        needed = {
            "CREATE": ("title_keywords", "scheduled_at", "tolerance_minutes"),
            "RESCHEDULE": ("reference_keywords", "scheduled_at", "tolerance_minutes"),
            "CLARIFY": ("clarification_keywords_any",),
        }[self.intent]
        missing = [f for f in needed if getattr(self, f) in (None, [])]
        if missing:
            raise ValueError(f"{self.intent} requires: {', '.join(missing)}")
        if self.intent == "CLARIFY" and self.scheduled_at is not None:
            raise ValueError("CLARIFY must not expect scheduled_at")
        for name in ("title_keywords", "reference_keywords", "clarification_keywords_any"):
            words = getattr(self, name)
            if words is not None and any(not w.strip() for w in words):
                raise ValueError(f"{name} must not contain blank entries")
        return self


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    group: str = Field(min_length=1)
    category: str = Field(min_length=1)
    tags: list[str]
    requirements: list[str] = Field(min_length=1)
    spec_ref: str
    text: str
    now: AwareDatetime
    expected: Expected
    properties: list[str]
    rubric: str
    forbidden_terms: list[str] = []

    @model_validator(mode="after")
    def _check_text(self) -> "Case":
        if not self.text.strip():
            raise ValueError("text must not be blank")
        return self


class Dataset(BaseModel):
    # Header keys (description, layers, ...) are documentation only.
    model_config = ConfigDict(extra="ignore")

    property_vocabulary: dict[str, str]
    cases: list[Case]

    @model_validator(mode="after")
    def _check_cases(self) -> "Dataset":
        if len(self.cases) < MIN_CASES:
            raise ValueError(f"at least {MIN_CASES} cases are required, found {len(self.cases)}")
        duplicates = sorted(i for i, n in Counter(c.id for c in self.cases).items() if n > 1)
        if duplicates:
            raise ValueError(f"duplicate case ids: {', '.join(duplicates)}")
        for case in self.cases:
            unknown = sorted(set(case.properties) - set(self.property_vocabulary))
            if unknown:
                raise ValueError(f"{case.id}: unknown properties: {', '.join(unknown)}")
            if "title_excludes_forbidden_terms" in case.properties and not case.forbidden_terms:
                raise ValueError(f"{case.id}: forbidden_terms is required for that property")
        return self


def _summarise(exc: ValidationError) -> list[str]:
    # Location and message only: pydantic's `input` would echo the model's reply.
    return [f"{'.'.join(str(p) for p in e['loc']) or 'reply'}: {e['msg']}" for e in exc.errors()]


def load_cases(path: Path = CASES_PATH) -> list[Case]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise CaseFileError(f"case file not found: {path}") from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CaseFileError(f"case file is not valid JSON: {exc.msg} (line {exc.lineno})") from None
    try:
        return Dataset.model_validate(data).cases
    except ValidationError as exc:
        raise CaseFileError("invalid case file: " + "; ".join(_summarise(exc))) from None


# --- structural layer -----------------------------------------------------------------------


def redact(text: str) -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if len(key) >= 8:
        text = text.replace(key, "[REDACTED]")
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


@dataclass(frozen=True)
class LayerRecord:
    case_id: str
    layer: str
    passed: bool
    details: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_structural(case_id: str, raw_text: str | None) -> LayerRecord:
    """Judge the raw model reply only; the past-time guard and final result play no part."""
    if raw_text is None:
        return LayerRecord(case_id, "structural", False, ["no model reply was received"])
    try:
        AgentResult.model_validate_json(raw_text)
    except ValidationError as exc:
        details = [redact(d) for d in _summarise(exc)]
        return LayerRecord(case_id, "structural", False, details)
    return LayerRecord(case_id, "structural", True, [])


# --- one case run ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaseRun:
    """What happened when one case went through the agent."""

    case_id: str
    raw_text: str | None
    result: AgentResult | None
    guard_applied: bool
    llm_calls: int
    error_code: str | None = None
    error_detail: str | None = None


# --- property / invariant layer -------------------------------------------------------------

_INTENTS = ("CREATE", "RESCHEDULE", "CLARIFY")
# (required, must be null) per intent. Written out here, not read from the schema.
_FIELD_RULES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "CREATE": (("title", "scheduled_at"), ("reminder_reference", "clarification")),
    "RESCHEDULE": (("reminder_reference", "scheduled_at"), ("title", "clarification")),
    "CLARIFY": (("clarification",), ("title", "reminder_reference", "scheduled_at")),
}


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _general_checks(case: Case, run: CaseRun) -> list[str]:
    failures: list[str] = []
    if run.llm_calls != 1:
        failures.append(f"expected exactly 1 LLM call, observed {run.llm_calls}")
    result = run.result
    if result is None:
        failures.append(f"no final result (error: {run.error_code or 'unknown'})")
        return failures

    if result.intent not in _INTENTS:
        failures.append(f"intent {result.intent!r} is not one of {', '.join(_INTENTS)}")
    else:
        required, forbidden = _FIELD_RULES[result.intent]
        failures += [
            f"{result.intent} requires a non-empty {f}"
            for f in required
            if _blank(getattr(result, f))
        ]
        failures += [
            f"{result.intent} must not set {f}" for f in forbidden if getattr(result, f) is not None
        ]

    when = result.scheduled_at
    if when is not None:
        if when.utcoffset() is None:
            failures.append("scheduled_at has no UTC offset")
        elif when < case.now:
            failures.append(f"scheduled_at {when.isoformat()} is earlier than now")

    if run.guard_applied and (result.intent != "CLARIFY" or when is not None):
        failures.append("past-time guard was applied but the final result is not a plain CLARIFY")
    return failures


def _check_property(name: str, case: Case, result: AgentResult) -> str | None:
    if name == "scheduled_at_null":
        return "scheduled_at must be null" if result.scheduled_at is not None else None
    if name == "title_null":
        return "title must be null" if result.title is not None else None
    if name == "reference_null":
        return "reminder_reference must be null" if result.reminder_reference is not None else None
    if name == "clarification_null":
        return "clarification must be null" if result.clarification is not None else None
    if name == "clarification_present":
        return "clarification must be a non-empty string" if _blank(result.clarification) else None
    if name == "scheduled_at_not_before_now":
        when = result.scheduled_at
        if when is not None and when.utcoffset() is not None and when < case.now:
            return "scheduled_at must not be earlier than now"
        return None
    if name == "title_excludes_forbidden_terms":
        title = (result.title or "").casefold()
        hits = [t for t in case.forbidden_terms if t.casefold() in title]
        return f"title contains forbidden term(s): {', '.join(hits)}" if hits else None
    return f"unknown property {name!r}"


def evaluate_property(case: Case, run: CaseRun) -> LayerRecord:
    """Deterministic checks on the final result; no expected answer is consulted."""
    failures = _general_checks(case, run)
    if run.result is not None:
        for name in case.properties:
            message = _check_property(name, case, run.result)
            if message:
                failures.append(message)
    return LayerRecord(case.id, "property", not failures, [redact(f) for f in failures])


# --- semantic layer -------------------------------------------------------------------------


@dataclass(frozen=True)
class SemanticRecord:
    case_id: str
    passed: bool
    score: float
    checks: list[dict]
    details: list[str]
    invented_details: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _check(name: str, passed: bool, detail: str = "") -> dict:
    return {"name": name, "passed": passed, "detail": "" if passed else detail}


def _keywords_all(name: str, text: str | None, words: list[str]) -> dict:
    haystack = (text or "").casefold()
    missing = [w for w in words if w.casefold() not in haystack]
    return _check(name, not missing, f"{name}: missing keyword(s): {', '.join(missing)}")


def _time_check(case: Case, result: AgentResult) -> dict:
    expected = case.expected
    when = result.scheduled_at
    if when is None:
        return _check("scheduled_at", False, "scheduled_at: no datetime was returned")
    if when.utcoffset() is None:
        return _check("scheduled_at", False, "scheduled_at: no UTC offset")
    if expected.scheduled_at is None or expected.tolerance_minutes is None:
        return _check("scheduled_at", False, "scheduled_at: the case defines no expected time")
    diff = abs((when - expected.scheduled_at).total_seconds()) / 60
    ok = diff <= expected.tolerance_minutes
    return _check(
        "scheduled_at",
        ok,
        f"scheduled_at: differs from the expected instant by {diff:.1f} minute(s) "
        f"(tolerance {expected.tolerance_minutes})",
    )


def _expected_checks(case: Case, result: AgentResult) -> list[dict]:
    expected = case.expected
    if expected.intent == "CREATE":
        return [
            _keywords_all("title_keywords", result.title, expected.title_keywords or []),
            _time_check(case, result),
        ]
    if expected.intent == "RESCHEDULE":
        return [
            _keywords_all(
                "reference_keywords", result.reminder_reference, expected.reference_keywords or []
            ),
            _time_check(case, result),
        ]
    text = (result.clarification or "").casefold()
    words = expected.clarification_keywords_any or []
    found = any(w.casefold() in text for w in words)
    return [
        _check(
            "clarification_keywords_any",
            found,
            f"clarification_keywords_any: none of [{', '.join(words)}] found in the question",
        )
    ]


_CHECK_NAMES = {
    "CREATE": ("title_keywords", "scheduled_at"),
    "RESCHEDULE": ("reference_keywords", "scheduled_at"),
    "CLARIFY": ("clarification_keywords_any",),
}


def evaluate_semantic(case: Case, run: CaseRun) -> SemanticRecord:
    """Does the final result satisfy the request? Uses the case's expected values only."""
    expected = case.expected
    names = _CHECK_NAMES[expected.intent]
    result = run.result

    if result is None:
        reason = f"no final result (error: {run.error_code or 'unknown'})"
        checks = [_check("intent", False, reason)] + [
            _check(n, False, f"{n}: not evaluated") for n in names
        ]
        return SemanticRecord(case.id, False, 0.0, checks, [reason], False)

    intent_ok = result.intent == expected.intent
    checks = [
        _check("intent", intent_ok, f"intent: expected {expected.intent}, got {result.intent}")
    ]
    if intent_ok:
        checks += _expected_checks(case, result)
    else:
        checks += [
            _check(n, False, f"{n}: not evaluated because the intent differs") for n in names
        ]

    score = sum(c["passed"] for c in checks) / len(checks)
    details = [redact(c["detail"]) for c in checks if not c["passed"]]
    invented = expected.intent == "CLARIFY" and result.intent in ("CREATE", "RESCHEDULE")
    return SemanticRecord(
        case.id, all(c["passed"] for c in checks), score, checks, details, invented
    )


# --- running cases --------------------------------------------------------------------------


class CountingClient:
    """Counts calls independently of the agent, so the one-call rule is observed, not assumed."""

    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self.calls = 0

    def generate(self, system_prompt: str, user_message: str) -> str:
        self.calls += 1
        return self._inner.generate(system_prompt, user_message)


def run_case(case: Case, client: LLMClient) -> CaseRun:
    """One request through the same `interpret` entry point the API uses. Never retried."""
    counting = CountingClient(client)
    try:
        outcome = interpret(case.text, case.now, counting)
    except InvalidOutputError as exc:
        return CaseRun(
            case.id, exc.raw_text, None, False, counting.calls, "llm_invalid_output", exc.detail
        )
    except LLMUnavailableError as exc:
        return CaseRun(case.id, None, None, False, counting.calls, "llm_unavailable", str(exc))
    return CaseRun(
        case.id,
        outcome.raw_text,
        outcome.result,
        outcome.past_time_guard_applied,
        counting.calls,
    )


def evaluate_case(case: Case, run: CaseRun) -> dict:
    structural = evaluate_structural(case.id, run.raw_text)
    prop = evaluate_property(case, run)
    semantic = evaluate_semantic(case, run)
    final = json.loads(redact(run.result.model_dump_json())) if run.result is not None else None
    return {
        "case_id": case.id,
        "group": case.group,
        "category": case.category,
        "text": case.text,
        "now": case.now.isoformat(),
        "expected_intent": case.expected.intent,
        "actual_intent": run.result.intent if run.result is not None else None,
        "final_result": final,
        "past_time_guard_applied": run.guard_applied,
        "llm_calls": run.llm_calls,
        "error_code": run.error_code,
        "error_detail": redact(run.error_detail) if run.error_detail else None,
        "structural": structural.to_dict(),
        "property": prop.to_dict(),
        "semantic": semantic.to_dict(),
        "passed_all": structural.passed and prop.passed and semantic.passed,
    }


# --- scores and verdict ---------------------------------------------------------------------

_LAYERS = ("structural", "property", "semantic")


def _rate(passed: int, total: int) -> float:
    return passed / total if total else 0.0


def aggregate(results: list[dict]) -> dict:
    n = len(results)

    def layer(name: str) -> dict:
        passed = sum(1 for r in results if r[name]["passed"])
        return {"passed": passed, "total": n, "rate": _rate(passed, n)}

    semantic = layer("semantic")
    semantic["mean_score"] = sum(r["semantic"]["score"] for r in results) / n if n else 0.0
    invented = [r["case_id"] for r in results if r["semantic"]["invented_details"]]
    guarded = [r["case_id"] for r in results if r["past_time_guard_applied"]]
    return {
        "cases": n,
        "structural": layer("structural"),
        "property": layer("property"),
        "semantic": semantic,
        "invented_details": {"count": len(invented), "case_ids": invented},
        "past_time_guard_applied": {"count": len(guarded), "case_ids": guarded},
        "errors": sum(1 for r in results if r["error_code"] is not None),
        "llm_calls_total": sum(r["llm_calls"] for r in results),
    }


def build_verdict(agg: dict, results: list[dict], expected_cases: int) -> dict:
    t = THRESHOLDS
    criteria = [
        {
            "name": "all cases executed",
            "source": "spec SC-002",
            "required": expected_cases,
            "actual": agg["cases"],
            "met": agg["cases"] == expected_cases,
        },
        {
            "name": "structural pass rate",
            "source": "spec SC-003",
            "required": f">= {t['structural_min']}",
            "actual": agg["structural"]["rate"],
            "met": agg["structural"]["rate"] >= t["structural_min"],
        },
        {
            "name": "property pass rate",
            "source": "spec SC-004",
            "required": f">= {t['property_min']}",
            "actual": agg["property"]["rate"],
            "met": agg["property"]["rate"] >= t["property_min"],
        },
        {
            "name": "cases with invented details",
            "source": "spec SC-005",
            "required": f"<= {t['invented_details_max']}",
            "actual": agg["invented_details"]["count"],
            "met": agg["invented_details"]["count"] <= t["invented_details_max"],
        },
        {
            "name": "semantic pass rate",
            "source": "harness-declared (the spec sets no semantic threshold)",
            "required": f">= {t['semantic_min']}",
            "actual": agg["semantic"]["rate"],
            "met": agg["semantic"]["rate"] >= t["semantic_min"],
        },
    ]
    failed = []
    for r in results:
        layers = [name for name in _LAYERS if not r[name]["passed"]]
        if layers:
            failed.append(
                {
                    "case_id": r["case_id"],
                    "failed_layers": layers,
                    "reasons": {name: r[name]["details"] for name in layers},
                }
            )
    overall = "PASS" if all(c["met"] for c in criteria) else "FAIL"
    return {"overall": overall, "criteria": criteria, "failed_cases": failed}


# --- evidence -------------------------------------------------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _evidence_files(run_dir: Path) -> list[Path]:
    manifest = run_dir / MANIFEST_NAME
    return sorted(p for p in run_dir.rglob("*") if p.is_file() and p != manifest)


def write_manifest(run_dir: Path) -> None:
    lines = [f"{_sha256(p)}  {p.relative_to(run_dir).as_posix()}" for p in _evidence_files(run_dir)]
    (run_dir / MANIFEST_NAME).write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_manifest(run_dir: Path) -> list[str]:
    manifest = run_dir / MANIFEST_NAME
    if not manifest.is_file():
        return [f"{MANIFEST_NAME} is missing"]
    listed: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, _, rel = line.partition("  ")
        listed[rel] = digest
    problems = []
    for rel, digest in listed.items():
        path = run_dir / rel
        if not path.is_file():
            problems.append(f"missing: {rel}")
        elif _sha256(path) != digest:
            problems.append(f"changed: {rel}")
    actual = {p.relative_to(run_dir).as_posix() for p in _evidence_files(run_dir)}
    problems += [f"not in manifest: {rel}" for rel in sorted(actual - set(listed))]
    return problems


_LOG_HEADER = (
    "# Harness Log\n\n"
    "Entries headed `Run` are generated by `harness/run_eval.py` from the computed results and "
    "are never edited by hand. Entries headed `Manual entry` record observations, repairs and "
    "decisions made by a person or an assistant; they contain no score that is not in a "
    "`results.json`.\n"
)


def _pct(layer: dict) -> str:
    return f"{layer['passed']}/{layer['total']} ({layer['rate'] * 100:.1f}%)"


def format_log_entry(results: dict, command: str, run_dir: Path) -> str:
    meta, agg, verdict = results["meta"], results["aggregate"], results["verdict"]
    try:
        evidence = run_dir.relative_to(PART_DIR).as_posix()
    except ValueError:
        evidence = run_dir.name
    lines = [
        f"\n## Run {meta['run_id']}\n",
        f"- Started (UTC): {meta['started_utc']}; finished (UTC): {meta['finished_utc']}",
        f"- Command: `{command}`",
        f"- Model: {meta['model']}",
        f"- Cases: {agg['cases']}; LLM calls: {agg['llm_calls_total']}; "
        f"cases with no usable reply: {agg['errors']}",
        f"- structural: {_pct(agg['structural'])}",
        f"- property: {_pct(agg['property'])}",
        f"- semantic: {_pct(agg['semantic'])}, mean score {agg['semantic']['mean_score']:.3f}",
        f"- Past-time guard applied: {agg['past_time_guard_applied']['count']} "
        f"{agg['past_time_guard_applied']['case_ids']}",
        f"- Cases with invented details: {agg['invented_details']['count']} "
        f"{agg['invented_details']['case_ids']}",
        "- Criteria:",
    ]
    for c in verdict["criteria"]:
        lines.append(
            f"  - {c['name']} ({c['source']}): required {c['required']}, "
            f"actual {c['actual']} - {'met' if c['met'] else 'NOT met'}"
        )
    lines.append(f"- Overall: {verdict['overall']}")
    if verdict["failed_cases"]:
        lines.append("- Failed cases:")
        for f in verdict["failed_cases"]:
            lines.append(f"  - {f['case_id']} [{', '.join(f['failed_layers'])}]")
            for layer, reasons in f["reasons"].items():
                for reason in reasons[:3]:
                    lines.append(f"    - {layer}: {reason[:200]}")
    lines.append(f"- Evidence: `{evidence}/results.json`\n")
    return "\n".join(lines)


def append_log(log_path: Path, entry: str) -> None:
    if not log_path.exists():
        log_path.write_text(_LOG_HEADER, encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(entry)


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_evaluation(
    cases: list[Case],
    client: LLMClient,
    run_dir: Path,
    *,
    delay: float = 0.0,
    command: str = "",
    log_path: Path | None = LOG_PATH,
    sleep: Callable[[float], None] = time.sleep,
    model: str | None = None,
) -> dict:
    run_dir.mkdir(parents=True)  # FileExistsError if present: evidence is never overwritten
    (run_dir / "raw").mkdir()
    started = _utc_now()
    results: list[dict] = []

    for index, case in enumerate(cases):
        if index and delay:
            sleep(delay)
        run = run_case(case, client)
        result = evaluate_case(case, run)
        results.append(result)
        raw = (
            redact(run.raw_text)
            if run.raw_text is not None
            else (f"<no reply: {run.error_code}: {redact(run.error_detail or '')}>")
        )
        (run_dir / "raw" / f"{case.id}.txt").write_text(raw, encoding="utf-8")
        marks = " ".join(f"{n[:4]}={'pass' if result[n]['passed'] else 'FAIL'}" for n in _LAYERS)
        print(f"{case.id}: {marks}", flush=True)

    agg = aggregate(results)
    report = {
        "meta": {
            "run_id": run_dir.name,
            "started_utc": started,
            "finished_utc": _utc_now(),
            "model": model or os.environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL,
            "harness_version": HARNESS_VERSION,
            "case_count": len(cases),
            "case_ids": [c.id for c in cases],
            "delay_seconds": delay,
            "thresholds": THRESHOLDS,
        },
        "aggregate": agg,
        "verdict": build_verdict(agg, results, expected_cases=len(cases)),
        "cases": results,
    }
    (run_dir / "results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_manifest(run_dir)
    if log_path is not None:
        append_log(log_path, format_log_entry(report, command, run_dir))
    return report


# --- command line ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reminder agent evaluation harness")
    parser.add_argument("--check-cases", action="store_true", help="validate cases.json and exit")
    parser.add_argument("--verify-manifest", type=Path, metavar="DIR")
    parser.add_argument("--write-manifest", type=Path, metavar="DIR")
    parser.add_argument(
        "--run-dir", type=Path, help="evidence folder (default: evidence/run-<UTC>)"
    )
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between model calls")
    parser.add_argument("--env-file", type=Path, default=BACKEND_DIR / ".env")
    args = parser.parse_args(argv)

    if args.verify_manifest:
        problems = verify_manifest(args.verify_manifest)
        for problem in problems:
            print(problem)
        print("manifest OK" if not problems else f"{len(problems)} manifest problem(s)")
        return 1 if problems else 0
    if args.write_manifest:
        write_manifest(args.write_manifest)
        return 0

    try:
        cases = load_cases()
    except CaseFileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.check_cases:
        print(f"{len(cases)} cases loaded and valid")
        for group, n in sorted(Counter(c.group for c in cases).items()):
            print(f"  {group}: {n}")
        return 0

    load_dotenv(args.env_file)  # does not override variables already set
    if not os.environ.get("GEMINI_API_KEY", "").strip():
        print("ERROR: GEMINI_API_KEY is not set (see backend/.env.example)", file=sys.stderr)
        return 2

    run_dir = args.run_dir or EVIDENCE_DIR / f"run-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    command = "python harness/run_eval.py " + " ".join(argv if argv is not None else sys.argv[1:])
    report = run_evaluation(
        cases, GeminiClient(), run_dir, delay=args.delay, command=command.strip()
    )
    agg = report["aggregate"]
    print(
        f"structural {_pct(agg['structural'])}; property {_pct(agg['property'])}; "
        f"semantic {_pct(agg['semantic'])}; overall {report['verdict']['overall']}"
    )
    print(f"results: {run_dir / 'results.json'}")
    return 0 if report["verdict"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
