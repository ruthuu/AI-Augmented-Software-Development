#!/usr/bin/env python3
"""Black-box API checks for SpendWise (Python standard library only).

Runs the expected-case files in harness/cases/ against a running server over HTTP and writes the
observed results next to the expected values. It never imports anything from backend/.

Usage:
    python harness/run_api_checks.py --base-url http://127.0.0.1:8000 --phase write|verify|timing|all
        [--cases harness/cases] [--out api-results.json] [--append]

Phases:
    write   cases that create and change data (run against a fresh database)
    verify  cases that read the same data after the server was restarted on the same database
    timing  supplementary: loads 1,000 expenses and records elapsed milliseconds (no time limit)
    all     write, then verify, then timing, against the one running server (no restart)

Exit code: 0 when every selected case is PASS, 1 when at least one case is FAIL and none is ERROR,
2 when at least one case is ERROR (for example the server is not reachable).
The last line printed is "compared=N passed=P failed=F error=E".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")
REQUEST_TIMEOUT_SECONDS = 30
EXPENSE_KEYS = {
    "id",
    "amount",
    "description",
    "category",
    "payment_method",
    "expense_date",
    "created_at",
    "updated_at",
}


class Unreachable(Exception):
    """The server did not answer."""


class MissingVariable(Exception):
    """A case needs a value saved by an earlier case that did not provide it."""


def http(base_url: str, method: str, path: str, body: bytes | None) -> tuple[int, bytes]:
    request = urllib.request.Request(base_url + path, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as error:
        raise Unreachable(f"{type(error).__name__}: {error}") from error


def parse_body(raw: bytes) -> object:
    if not raw:
        return None
    text = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text[:2000]


def substitute(text: str, variables: dict) -> str:
    def replace(found: re.Match) -> str:
        name = found.group(1)
        if name not in variables:
            raise MissingVariable(name)
        return str(variables[name])

    return re.sub(r"\{\{(\w+)\}\}", replace, text)


def same_type(expected: object, observed: object) -> bool:
    if isinstance(expected, bool) or isinstance(observed, bool):
        return isinstance(expected, bool) and isinstance(observed, bool)
    return True


def match(expected: object, observed: object, path: str, variables: dict, diffs: list) -> None:
    if isinstance(expected, str) and expected.startswith("$"):
        if expected == "$any":
            return
        if expected == "$int":
            if not (isinstance(observed, int) and not isinstance(observed, bool)):
                diffs.append(f"{path}: expected an integer, got {observed!r}")
            return
        if expected == "$str":
            if not (isinstance(observed, str) and observed):
                diffs.append(f"{path}: expected a non-empty string, got {observed!r}")
            return
        if expected == "$utc":
            if not (isinstance(observed, str) and UTC_RE.match(observed)):
                diffs.append(f"{path}: expected a UTC ISO 8601 timestamp, got {observed!r}")
            return
        if expected.startswith("$var:"):
            name = expected[5:]
            if name not in variables:
                raise MissingVariable(name)
            if observed != variables[name]:
                diffs.append(f"{path}: expected saved value {variables[name]!r}, got {observed!r}")
            return
    if isinstance(expected, dict):
        if "$unordered" in expected:
            match_unordered(expected["$unordered"], observed, path, variables, diffs)
            return
        if expected.get("$expense_order"):
            match_expense_order(expected, observed, path, diffs)
            return
        if not isinstance(observed, dict):
            diffs.append(f"{path}: expected an object, got {type(observed).__name__}")
            return
        partial = bool(expected.get("$partial"))
        wanted = {k: v for k, v in expected.items() if k != "$partial"}
        if not partial:
            extra = sorted(set(observed) - set(wanted))
            if extra:
                diffs.append(f"{path}: unexpected fields {extra}")
        for key, value in wanted.items():
            if key not in observed:
                diffs.append(f"{path}.{key}: missing")
            else:
                match(value, observed[key], f"{path}.{key}", variables, diffs)
        return
    if isinstance(expected, list):
        if not isinstance(observed, list):
            diffs.append(f"{path}: expected a list, got {type(observed).__name__}")
            return
        if len(expected) != len(observed):
            diffs.append(f"{path}: expected {len(expected)} items, got {len(observed)}")
            return
        for index, (e, o) in enumerate(zip(expected, observed)):
            match(e, o, f"{path}[{index}]", variables, diffs)
        return
    if not same_type(expected, observed) or expected != observed:
        diffs.append(f"{path}: expected {expected!r}, got {observed!r}")


def match_unordered(expected: list, observed: object, path: str, variables: dict, diffs: list) -> None:
    if not isinstance(observed, list):
        diffs.append(f"{path}: expected a list, got {type(observed).__name__}")
        return
    if len(expected) != len(observed):
        diffs.append(f"{path}: expected {len(expected)} items, got {len(observed)}")
        return
    unused = list(range(len(observed)))
    for index, item in enumerate(expected):
        for position in unused:
            trial: list = []
            match(item, observed[position], path, variables, trial)
            if not trial:
                unused.remove(position)
                break
        else:
            diffs.append(f"{path}: no observed item matches expected item {index}: {item!r}")


def match_expense_order(expected: dict, observed: object, path: str, diffs: list) -> None:
    if not isinstance(observed, list):
        diffs.append(f"{path}: expected a list, got {type(observed).__name__}")
        return
    if "$length" in expected and len(observed) != expected["$length"]:
        diffs.append(f"{path}: expected {expected['$length']} items, got {len(observed)}")
    ids: set = set()
    previous = None
    for index, item in enumerate(observed):
        if not isinstance(item, dict) or set(item) != EXPENSE_KEYS:
            diffs.append(f"{path}[{index}]: not an expense object with exactly the 8 contract fields")
            return
        if item["id"] in ids:
            diffs.append(f"{path}[{index}]: duplicate id {item['id']!r}")
        ids.add(item["id"])
        key = (item["expense_date"], item["id"])
        if previous is not None and not key < previous:
            diffs.append(
                f"{path}[{index}]: order is not expense_date descending then id descending"
            )
            return
        previous = key


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_case(base_url: str, case: dict, variables: dict) -> dict:
    entry = {
        "id": case["id"],
        "spec_ref": case.get("spec_ref", ""),
        "phase": case.get("phase", "write"),
        "request": case.get("request"),
        "expected": {
            "status": case.get("expected_status"),
            "body": case.get("expected_body_or_fields"),
        },
        "observed": None,
        "status": "ERROR",
        "kind": case.get("kind", "required"),
        "elapsed_ms": None,
    }
    if case.get("derivation"):
        entry["derivation"] = case["derivation"]
    try:
        request = case["request"]
        path = substitute(request["path"], variables)
        payload = None
        if "raw_body" in request:
            payload = request["raw_body"].encode("utf-8")
        elif "body" in request:
            payload = json.dumps(request["body"], ensure_ascii=False).encode("utf-8")
        started = time.perf_counter()
        status, raw = http(base_url, request["method"], path, payload)
        entry["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
        body = parse_body(raw)
        entry["observed"] = {"status": status, "body": body}
        diffs: list = []
        if status != case["expected_status"]:
            diffs.append(f"status: expected {case['expected_status']}, got {status}")
        expected_body = case.get("expected_body_or_fields")
        if expected_body == "$empty":
            if raw:
                diffs.append("body: expected an empty body")
        else:
            match(expected_body, body, "body", variables, diffs)
        for name, field in case.get("save", {}).items():
            if isinstance(body, dict) and field in body:
                variables[name] = body[field]
        entry["status"] = "FAIL" if diffs else "PASS"
        if diffs:
            entry["differences"] = diffs[:20]
    except MissingVariable as error:
        entry["status"] = "FAIL"
        entry["differences"] = [f"depends on saved value '{error}' that an earlier case did not provide"]
    except Unreachable as error:
        entry["observed"] = {"error": str(error)}
        entry["status"] = "ERROR"
    except Exception as error:  # noqa: BLE001 - any harness exception is an ERROR, never a verdict
        entry["observed"] = {"error": f"{type(error).__name__}: {error}"}
        entry["status"] = "ERROR"
    return entry


def run_timing(base_url: str, case: dict) -> dict:
    params = case["params"]
    count = params["count"]
    baseline = params["baseline_total"]
    entry = {
        "id": case["id"],
        "spec_ref": case.get("spec_ref", ""),
        "phase": "timing",
        "request": {"description": f"create {count} expenses, then list all and load the summary"},
        "expected": {
            "created": count,
            "list_all_count": baseline + count,
            "summary_expense_count": count,
            "summary_total_spent": params["expected_month_total"],
            "summary_total_recorded_count": baseline + count,
            "time_limit": "none (recorded only)",
        },
        "observed": None,
        "status": "ERROR",
        "kind": "supplementary",
        "elapsed_ms": None,
    }
    observed: dict = {}
    try:
        created = 0
        for index in range(count):
            body = {
                "amount": params["amount"],
                "description": f"Timing {index + 1}",
                "category": "Food",
                "payment_method": "Cash",
                "expense_date": params["expense_date"],
            }
            status, _ = http(base_url, "POST", "/api/expenses", json.dumps(body).encode("utf-8"))
            if status != 201:
                observed["first_failed_create"] = {"index": index + 1, "status": status}
                break
            created += 1
        observed["created"] = created
        started = time.perf_counter()
        list_status, list_raw = http(base_url, "GET", "/api/expenses", None)
        list_ms = round((time.perf_counter() - started) * 1000, 1)
        listed = parse_body(list_raw)
        started = time.perf_counter()
        sum_status, sum_raw = http(base_url, "GET", f"/api/summary?month={params['month']}", None)
        sum_ms = round((time.perf_counter() - started) * 1000, 1)
        summary = parse_body(sum_raw)
        observed.update(
            {
                "list_all_status": list_status,
                "list_all_count": len(listed) if isinstance(listed, list) else None,
                "list_all_ms": list_ms,
                "summary_status": sum_status,
                "summary_expense_count": summary.get("expense_count") if isinstance(summary, dict) else None,
                "summary_total_spent": summary.get("total_spent") if isinstance(summary, dict) else None,
                "summary_total_recorded_count": summary.get("total_recorded_count") if isinstance(summary, dict) else None,
                "summary_ms": sum_ms,
            }
        )
        entry["elapsed_ms"] = round(list_ms + sum_ms, 1)
        correct = (
            created == count
            and list_status == 200
            and observed["list_all_count"] == baseline + count
            and sum_status == 200
            and observed["summary_expense_count"] == count
            and observed["summary_total_spent"] == params["expected_month_total"]
            and observed["summary_total_recorded_count"] == baseline + count
        )
        entry["status"] = "PASS" if correct else "FAIL"
    except Unreachable as error:
        observed["error"] = str(error)
        entry["status"] = "ERROR"
    except Exception as error:  # noqa: BLE001
        observed["error"] = f"{type(error).__name__}: {error}"
        entry["status"] = "ERROR"
    entry["observed"] = observed
    return entry


def load_cases(folder: Path) -> list:
    cases = []
    for path in sorted(folder.glob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        for case in document["cases"]:
            case["_suite"] = document.get("suite", path.stem)
            cases.append(case)
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--phase", choices=["write", "verify", "timing", "all"], required=True)
    parser.add_argument("--cases", default=str(Path(__file__).resolve().parent / "cases"))
    parser.add_argument("--out", default="api-results.json")
    parser.add_argument("--append", action="store_true")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    wanted = {"write", "verify", "timing"} if args.phase == "all" else {args.phase}
    cases = [c for c in load_cases(Path(args.cases)) if c.get("phase", "write") in wanted]
    if not cases:
        print("No cases selected.")
        print("compared=0 passed=0 failed=0 error=0")
        return 2

    reachable = True
    try:
        http(base_url, "GET", "/api/config", None)
    except Unreachable as error:
        reachable = False
        unreachable_text = str(error)

    results: list = []
    variables: dict = {}
    for case in cases:
        if not reachable:
            results.append(
                {
                    "id": case["id"],
                    "spec_ref": case.get("spec_ref", ""),
                    "phase": case.get("phase", "write"),
                    "request": case.get("request"),
                    "expected": {
                        "status": case.get("expected_status"),
                        "body": case.get("expected_body_or_fields"),
                    },
                    "observed": {"error": unreachable_text},
                    "status": "ERROR",
                    "kind": case.get("kind", "required"),
                    "elapsed_ms": None,
                }
            )
        elif case.get("type") == "timing":
            results.append(run_timing(base_url, case))
        else:
            results.append(run_case(base_url, case, variables))

    out_path = Path(args.out)
    entries: list = []
    if args.append and out_path.exists():
        entries = json.loads(out_path.read_text(encoding="utf-8"))
    entries.extend(results)
    out_path.write_text(json.dumps(entries, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")

    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    for r in results:
        if r["status"] != "PASS":
            print(f"{r['status']} {r['id']} ({r['kind']}): {'; '.join(r.get('differences', [])[:3])}")
    print(f"started={now_iso()} phase={args.phase} base_url={base_url}")
    print(f"compared={passed + failed} passed={passed} failed={failed} error={errors}")
    if errors:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
