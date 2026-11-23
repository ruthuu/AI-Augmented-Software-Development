"""Builds harness/cases/*.json from the written specification.

Expected values come from spec.md, data-model.md, and contracts/api.md only. This script contains a
small reference model of those documents (the "oracle"): it never imports from backend/ and never
reads application output. It uses Decimal and integer cents only (no float).

Run from the repository root:  python harness\\tools\\build_cases.py
It rewrites every file in harness/cases/. Review the generated JSON against the spec, not against
the application.
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "harness" / "cases"

TODAY = "2026-11-12"
CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
]
PAYMENT_METHODS = ["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking", "Other"]

VALIDATION_ERROR = "validation_error"
ERR_MSG = "$str"


def to_cents(text: str) -> int:
    value = Decimal(text) * 100
    if value != value.to_integral_value():
        raise ValueError(f"not exact cents: {text}")
    return int(value)


def fmt(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def clean_description(text: str) -> str:
    """FR-042 in the written order."""
    out = []
    for ch in text:
        if ch in "\t\n\r":
            out.append(" ")
        elif ord(ch) < 32 or 127 <= ord(ch) <= 159:
            continue
        else:
            out.append(ch)
    return "".join(out).strip(" ")


class Oracle:
    """In-memory reference model of the stored data, built from the specification."""

    def __init__(self) -> None:
        self.seq = 0
        self.rows: list[dict] = []
        self.budgets: dict[str, int] = {}

    def add(self, body: dict) -> dict:
        self.seq += 1
        row = {
            "seq": self.seq,
            "cents": to_cents(body["amount"]),
            "description": clean_description(body["description"]),
            "category": body["category"],
            "payment_method": body["payment_method"],
            "expense_date": body["expense_date"],
        }
        self.rows.append(row)
        return row

    def remove(self, row: dict) -> None:
        self.rows.remove(row)

    def update(self, row: dict, body: dict) -> None:
        row["cents"] = to_cents(body["amount"])
        row["description"] = clean_description(body["description"])
        row["category"] = body["category"]
        row["payment_method"] = body["payment_method"]
        row["expense_date"] = body["expense_date"]

    def listing(self, month: str | None = None, category: str | None = None) -> list[dict]:
        rows = [
            r
            for r in self.rows
            if (month is None or r["expense_date"][:7] == month)
            and (category is None or r["category"] == category)
        ]
        return sorted(rows, key=lambda r: (r["expense_date"], r["seq"]), reverse=True)

    def summary(self, month: str) -> dict:
        rows = self.listing(month=month)
        total = sum(r["cents"] for r in rows)
        per: dict[str, list[int]] = {}
        for r in rows:
            per.setdefault(r["category"], []).append(r["cents"])
        by_category = sorted(
            ({"category": c, "total": sum(v), "count": len(v)} for c, v in per.items()),
            key=lambda d: (-d["total"], d["category"]),
        )
        budget = self.budgets.get(month)
        over = budget is not None and total > budget
        return {
            "month": month,
            "total_spent": fmt(total),
            "expense_count": len(rows),
            "total_recorded_count": len(self.rows),
            "by_category": [
                {"category": d["category"], "total": fmt(d["total"]), "count": d["count"]}
                for d in by_category
            ],
            "budget": None if budget is None else {"month": month, "amount": fmt(budget)},
            "remaining": None if budget is None else fmt(max(budget - total, 0)),
            "over_budget": over,
            "over_budget_by": fmt(total - budget) if over else None,
        }


def expense_expected(row: dict, id_marker: str = "$int") -> dict:
    return {
        "id": id_marker,
        "amount": fmt(row["cents"]),
        "description": row["description"],
        "category": row["category"],
        "payment_method": row["payment_method"],
        "expense_date": row["expense_date"],
        "created_at": "$utc",
        "updated_at": "$utc",
    }


def error_body(*pairs: tuple[str, str], unordered: bool = False) -> dict:
    errors: object = [{"field": f, "message": m} for f, m in pairs]
    if unordered:
        errors = {"$unordered": errors}
    return {"code": VALIDATION_ERROR, "message": ERR_MSG, "errors": errors}


NOT_FOUND = {"code": "not_found", "message": "This expense no longer exists", "errors": []}


class Suite:
    def __init__(self, filename: str, suite: str, description: str, prefix: str) -> None:
        self.filename = filename
        self.suite = suite
        self.description = description
        self.prefix = prefix
        self.cases: list[dict] = []

    def add(
        self,
        suffix: str,
        spec_ref: str,
        method: str,
        path: str,
        status: int,
        expected: object,
        body: object = None,
        raw_body: str | None = None,
        phase: str = "write",
        save: dict | None = None,
        derivation: str | None = None,
        note: str | None = None,
        kind: str = "required",
    ) -> None:
        request: dict = {"method": method, "path": path}
        if body is not None:
            request["body"] = body
        if raw_body is not None:
            request["raw_body"] = raw_body
        case: dict = {
            "id": f"{self.prefix}-{suffix}",
            "spec_ref": spec_ref,
            "phase": phase,
            "kind": kind,
            "request": request,
            "expected_status": status,
            "expected_body_or_fields": expected,
        }
        if note:
            case["note"] = note
        if save:
            case["save"] = save
        if derivation:
            case["derivation"] = derivation
        self.cases.append(case)

    def write(self) -> None:
        ids = [c["id"] for c in self.cases]
        if len(ids) != len(set(ids)):
            raise SystemExit(f"duplicate case id in {self.filename}")
        doc = {"suite": self.suite, "description": self.description, "cases": self.cases}
        (OUT / self.filename).write_text(
            json.dumps(doc, indent=1, ensure_ascii=True) + "\n", encoding="utf-8"
        )


O = Oracle()
SUITES: list[Suite] = []

BASE = {
    "amount": "250.50",
    "description": "Lunch",
    "category": "Food",
    "payment_method": "UPI",
    "expense_date": "2026-02-10",
}


def with_(**changes: object) -> dict:
    body = dict(BASE)
    body.update(changes)
    return body


def create(s: Suite, suffix: str, spec_ref: str, body: dict, **kw: object) -> dict:
    row = O.add(body)
    s.add(suffix, spec_ref, "POST", "/api/expenses", 201, expense_expected(row), body=body, **kw)
    return row


def summary_case(s: Suite, suffix: str, spec_ref: str, month: str, **kw: object) -> None:
    s.add(suffix, spec_ref, "GET", f"/api/summary?month={month}", 200, O.summary(month), **kw)


def list_case(
    s: Suite,
    suffix: str,
    spec_ref: str,
    month: str | None = None,
    category: str | None = None,
    **kw: object,
) -> None:
    query = []
    if month is not None:
        query.append(f"month={month}")
    if category is not None:
        query.append(f"category={category.replace(' ', '%20')}")
    path = "/api/expenses" + ("?" + "&".join(query) if query else "")
    expected = [expense_expected(r) for r in O.listing(month, category)]
    s.add(suffix, spec_ref, "GET", path, 200, expected, **kw)


# ---------------------------------------------------------------- 01 configuration
s = Suite("01_config.json", "config", "GET /api/config exact lists, limits, and today", "CFG")
s.add(
    "001",
    "FR-016, FR-017, FR-041, contracts/api.md GET /api/config",
    "GET",
    "/api/config",
    200,
    {
        "today": TODAY,
        "currency": "INR",
        "categories": CATEGORIES,
        "payment_methods": PAYMENT_METHODS,
        "limits": {
            "max_expense": "9999999.99",
            "max_budget": "99999999.99",
            "max_description_length": 200,
            "min_date": "2000-01-01",
        },
    },
    note="The harness starts the server with SPENDWISE_TODAY=2026-11-12.",
)
SUITES.append(s)

# ---------------------------------------------------------------- 02 hand-calculated dataset
DATASET = [
    # September 2026
    ("S01", "2026-09-01", "Food", "Cash", "120.50"),
    ("S02", "2026-09-01", "Transport", "UPI", "45.00"),
    ("S03", "2026-09-03", "Shopping", "Credit Card", "2499.99"),
    ("S04", "2026-09-05", "Bills", "Net Banking", "1850.00"),
    ("S05", "2026-09-07", "Entertainment", "UPI", "650.00"),
    ("S06", "2026-09-09", "Healthcare", "Debit Card", "320.75"),
    ("S07", "2026-09-11", "Education", "Net Banking", "4999.00"),
    ("S08", "2026-09-13", "Other", "Cash", "15.25"),
    ("S09", "2026-09-15", "Food", "UPI", "210.40"),
    ("S10", "2026-09-17", "Transport", "Cash", "80.00"),
    ("S11", "2026-09-19", "Shopping", "Debit Card", "1299.50"),
    ("S12", "2026-09-21", "Bills", "Credit Card", "999.01"),
    ("S13", "2026-09-23", "Entertainment", "Cash", "300.00"),
    ("S14", "2026-09-25", "Healthcare", "UPI", "75.30"),
    ("S15", "2026-09-27", "Education", "Credit Card", "1200.00"),
    ("S16", "2026-09-29", "Food", "Other", "99.99"),
    ("S17", "2026-09-30", "Transport", "Net Banking", "60.10"),
    ("S18", "2026-09-30", "Other", "UPI", "0.01"),
    # October 2026 (created in a mixed date order on purpose)
    ("T01", "2026-10-31", "Food", "UPI", "350.20"),
    ("T02", "2026-10-01", "Transport", "Cash", "120.00"),
    ("T03", "2026-10-02", "Shopping", "Credit Card", "3999.00"),
    ("T04", "2026-10-04", "Bills", "UPI", "1450.75"),
    ("T05", "2026-10-06", "Entertainment", "Debit Card", "499.00"),
    ("T06", "2026-10-08", "Healthcare", "Cash", "1200.00"),
    ("T07", "2026-10-10", "Education", "UPI", "2500.00"),
    ("T08", "2026-10-12", "Other", "Net Banking", "89.90"),
    ("T09", "2026-10-14", "Food", "Cash", "175.35"),
    ("T10", "2026-10-16", "Transport", "UPI", "230.00"),
    ("T11", "2026-10-18", "Shopping", "Cash", "799.99"),
    ("T12", "2026-10-20", "Bills", "Net Banking", "2200.00"),
    ("T13", "2026-10-22", "Entertainment", "UPI", "150.50"),
    ("T14", "2026-10-24", "Healthcare", "Credit Card", "640.00"),
    ("T15", "2026-10-26", "Education", "Cash", "800.00"),
    ("T16", "2026-10-28", "Other", "UPI", "20.00"),
    ("T17", "2026-10-31", "Transport", "Debit Card", "15.00"),
    ("T18", "2026-10-01", "Food", "Credit Card", "64.99"),
    # November 2026 (up to and including today, 2026-11-12)
    ("N01", "2026-11-01", "Food", "Cash", "310.00"),
    ("N02", "2026-11-02", "Transport", "UPI", "55.50"),
    ("N03", "2026-11-03", "Shopping", "UPI", "1599.00"),
    ("N04", "2026-11-04", "Bills", "Net Banking", "1750.00"),
    ("N05", "2026-11-05", "Entertainment", "Credit Card", "899.00"),
    ("N06", "2026-11-06", "Healthcare", "UPI", "450.00"),
    ("N07", "2026-11-07", "Education", "Cash", "3000.00"),
    ("N08", "2026-11-08", "Other", "Debit Card", "42.42"),
    ("N09", "2026-11-09", "Food", "UPI", "188.88"),
    ("N10", "2026-11-10", "Transport", "Cash", "95.05"),
    ("N11", "2026-11-10", "Shopping", "Other", "249.50"),
    ("N12", "2026-11-11", "Bills", "UPI", "600.00"),
    ("N13", "2026-11-11", "Entertainment", "Cash", "120.00"),
    ("N14", "2026-11-12", "Healthcare", "Credit Card", "1000.00"),
    ("N15", "2026-11-12", "Education", "UPI", "1000.00"),
    ("N16", "2026-11-12", "Food", "Cash", "25.00"),
    ("N17", "2026-11-12", "Other", "UPI", "5.55"),
    ("N18", "2026-11-12", "Transport", "Net Banking", "70.00"),
    # One expense just outside the three months (last day of August)
    ("A01", "2026-08-31", "Food", "Cash", "11.11"),
]


def derivation_for(month: str) -> str:
    items = [d for d in DATASET if d[1][:7] == month]
    parts = []
    per: dict[str, list[str]] = {}
    for _, _, cat, _, amt in items:
        per.setdefault(cat, []).append(amt)
    for cat in sorted(per, key=lambda c: (-sum(to_cents(a) for a in per[c]), c)):
        total = sum(to_cents(a) for a in per[cat])
        parts.append(f"{cat}: {' + '.join(per[cat])} = {fmt(total)} ({len(per[cat])})")
    grand = sum(to_cents(d[4]) for d in items)
    return (
        f"Month {month}, {len(items)} expenses. "
        + "; ".join(parts)
        + f". Total = sum of category totals = {fmt(grand)}."
    )


s = Suite(
    "02_dataset.json",
    "dataset",
    "55 hand-calculated expenses over Sep-Nov 2026 (plus one on 2026-08-31), all 8 categories",
    "DS",
)
for code, date, cat, pm, amt in DATASET:
    create(
        s,
        f"C-{code}",
        "FR-001, FR-016, FR-017, SC-003",
        {
            "amount": amt,
            "description": f"Dataset {code}",
            "category": cat,
            "payment_method": pm,
            "expense_date": date,
        },
    )
assert len(O.rows) == 55
for month, name in (("2026-09", "SEP"), ("2026-10", "OCT"), ("2026-11", "NOV")):
    summary_case(
        s,
        f"SUM-{name}",
        "FR-025, FR-029, FR-030, FR-031, FR-034, FR-035, SC-003",
        month,
        derivation=derivation_for(month),
        note="Budget is not set for this month; total_recorded_count is the all-time count, 55.",
    )
    list_case(
        s,
        f"LIST-{name}",
        "FR-002, FR-019, FR-035, SC-007",
        month=month,
        note="Order: expense_date descending, then id descending (later created first).",
    )
summary_case(
    s,
    "SUM-AUG",
    "FR-035",
    "2026-08",
    derivation="Month 2026-08 holds only A01 (2026-08-31, Food 11.11): total 11.11, count 1.",
)
s.add(
    "SUM-DEFAULT",
    "FR-028, FR-041",
    "GET",
    "/api/summary",
    200,
    O.summary("2026-11"),
    note="No month parameter: defaults to the month of today (2026-11).",
)
s.add(
    "LIST-ALL",
    "FR-002, FR-021",
    "GET",
    "/api/expenses",
    200,
    {"$expense_order": True, "$length": 55},
    derivation="18 (Sep) + 18 (Oct) + 18 (Nov) + 1 (Aug 31) = 55.",
)
SUITES.append(s)

# ---------------------------------------------------------------- 03 validation matrix
s = Suite(
    "03_validation.json",
    "validation",
    "Accepted and rejected values with the exact messages from data-model.md",
    "VAL",
)

AMOUNT_OK = [
    ("0.01", "0.01"),
    ("12", "12.00"),
    ("12.5", "12.50"),
    ("12.50", "12.50"),
    ("9999999.99", "9999999.99"),
    ("1000000", "1000000.00"),
]
for i, (given, shown) in enumerate(AMOUNT_OK, 1):
    create(
        s,
        f"AMT-OK{i:02d}",
        "FR-007, FR-008, FR-009",
        with_(amount=given, description=f"Amount accepted {given}"),
        note=f"Accepted; returned amount is {shown}.",
    )
    assert fmt(to_cents(given)) == shown

REQ = "Amount is required"
BAD = "Enter a valid amount"
ZERO = "Amount must be greater than zero"
DEC = "Amount can have at most 2 decimal places"
CAP = "Amount cannot exceed 9,999,999.99"
AMOUNT_BAD = [
    ("", REQ),
    ("abc", BAD),
    ("12.", BAD),
    (".5", BAD),
    ("1,000", BAD),
    ("1e3", BAD),
    ("12abc", BAD),
    ("--5", BAD),
    ("0", ZERO),
    ("0.00", ZERO),
    ("-5", ZERO),
    ("-0.01", ZERO),
    ("-0.001", ZERO),
    ("12.345", DEC),
    ("12.999", DEC),
    ("0.005", DEC),
    ("0.001", DEC),
    ("9999999.995", DEC),
    ("10000000.005", DEC),
    ("10000000.00", CAP),
    ("10000000.01", CAP),
    ("99999999999999999999.99", CAP),
]
for i, (given, message) in enumerate(AMOUNT_BAD, 1):
    s.add(
        f"AMT-BAD{i:02d}",
        "FR-007, FR-008, FR-009, FR-014",
        "POST",
        "/api/expenses",
        422,
        error_body(("amount", message)),
        body=with_(amount=given),
        note=f"amount {given!r}: rejected, never rounded, nothing stored.",
    )

DESC_OK = [
    ("Lunch", "Lunch"),
    ("  Lunch with spaces  ", "Lunch with spaces"),
    ("Tom\tJerry", "Tom Jerry"),
    ("Tom\nJerry", "Tom Jerry"),
    ("Tom\r\nJerry", "Tom  Jerry"),
    ("ab\u0000c", "abc"),
    ("a\u007fb", "ab"),
    ("\u0007bell", "bell"),
    ('<b>Tom & "Jerry\'s"</b>', '<b>Tom & "Jerry\'s"</b>'),
    ("x'); DROP TABLE expenses;--", "x'); DROP TABLE expenses;--"),
    ("Caf\u00e9 \u20b9 \u65e5\u672c\u8a9e \U0001f600", "Caf\u00e9 \u20b9 \u65e5\u672c\u8a9e \U0001f600"),
    ("a" * 200, "a" * 200),
    ("a" * 200 + " ", "a" * 200),
    ("\U0001f600" * 200, "\U0001f600" * 200),
]
for i, (given, shown) in enumerate(DESC_OK, 1):
    create(
        s,
        f"DESC-OK{i:02d}",
        "FR-010, FR-042",
        with_(description=given),
        note="Accepted; the response description is the cleaned text.",
    )
    assert clean_description(given) == shown

DESC_REQ = "Description is required"
DESC_LONG = "Description cannot exceed 200 characters"
DESC_BAD = [
    ("", DESC_REQ),
    ("   ", DESC_REQ),
    ("\t\n", DESC_REQ),
    ("\u0000", DESC_REQ),
    ("\u0007 \u007f", DESC_REQ),
    ("a" * 201, DESC_LONG),
    ("a" * 200 + "\u0007x", DESC_LONG),
    ("\U0001f600" * 201, DESC_LONG),
]
for i, (given, message) in enumerate(DESC_BAD, 1):
    s.add(
        f"DESC-BAD{i:02d}",
        "FR-010, FR-042",
        "POST",
        "/api/expenses",
        422,
        error_body(("description", message)),
        body=with_(description=given),
    )

for i, given in enumerate(["food", "FOOD", "Groceries", "Other2", "Food,Bills"], 1):
    s.add(
        f"CAT-BAD{i:02d}",
        "FR-012",
        "POST",
        "/api/expenses",
        422,
        error_body(("category", "Select a valid category")),
        body=with_(category=given),
    )

PM_BAD = [
    ("", "Payment method is required"),
    ("upi", "Select a valid payment method"),
    ("Wallet", "Select a valid payment method"),
    ("Credit  Card", "Select a valid payment method"),
    ("Debit card", "Select a valid payment method"),
]
for i, (given, message) in enumerate(PM_BAD, 1):
    s.add(
        f"PM-BAD{i:02d}",
        "FR-013",
        "POST",
        "/api/expenses",
        422,
        error_body(("payment_method", message)),
        body=with_(payment_method=given),
    )

for i, (given, shown) in enumerate([("2000-01-01", "2000-01-01"), ("2024-02-29", "2024-02-29")], 1):
    create(
        s,
        f"DATE-OK{i:02d}",
        "FR-011",
        with_(expense_date=given, description=f"Date accepted {given}"),
        note="Earliest allowed date and a real leap day.",
    )

DATE_INVALID = [
    "2026-02-30",
    "2026-13-01",
    "2026-00-10",
    "26-11-10",
    "2026/11/10",
    "abc",
    "10-11-2026",
    "2025-02-29",
    "2026-11-31",
    "2026-1-5",
]
for i, given in enumerate(DATE_INVALID, 1):
    s.add(
        f"DATE-BAD{i:02d}",
        "FR-011",
        "POST",
        "/api/expenses",
        422,
        error_body(("expense_date", "Enter a valid date")),
        body=with_(expense_date=given),
    )
for i, given in enumerate(["1999-12-31", "1900-01-01"], 1):
    s.add(
        f"DATE-OLD{i:02d}",
        "FR-011",
        "POST",
        "/api/expenses",
        422,
        error_body(("expense_date", "Date cannot be before 01 Jan 2000")),
        body=with_(expense_date=given),
    )
for i, given in enumerate(["2026-11-13", "2026-12-01", "2999-01-01"], 1):
    s.add(
        f"DATE-FUT{i:02d}",
        "FR-011, FR-041",
        "POST",
        "/api/expenses",
        422,
        error_body(("expense_date", "Date cannot be in the future")),
        body=with_(expense_date=given),
        note="Today is 2026-11-12; 2026-11-12 itself is accepted in the dataset (DS-C-N14).",
    )

s.add(
    "MULTI-EMPTY",
    "FR-014, US1 scenario 8",
    "POST",
    "/api/expenses",
    422,
    error_body(
        ("amount", "Amount is required"),
        ("description", "Description is required"),
        ("category", "Category is required"),
        ("payment_method", "Payment method is required"),
        ("expense_date", "Date is required"),
        unordered=True,
    ),
    body={},
    note="One error per missing field, all returned together.",
)
s.add(
    "MULTI-ALL-BAD",
    "FR-014",
    "POST",
    "/api/expenses",
    422,
    error_body(
        ("amount", "Enter a valid amount"),
        ("description", "Description is required"),
        ("category", "Select a valid category"),
        ("payment_method", "Select a valid payment method"),
        ("expense_date", "Enter a valid date"),
        unordered=True,
    ),
    body={
        "amount": "abc",
        "description": "  ",
        "category": "X",
        "payment_method": "Y",
        "expense_date": "2026-02-30",
    },
)
s.add(
    "MULTI-TWO",
    "FR-014",
    "POST",
    "/api/expenses",
    422,
    error_body(
        ("amount", "Amount must be greater than zero"),
        ("category", "Select a valid category"),
        unordered=True,
    ),
    body=with_(amount="0", category="Nope"),
    note="Only the failing fields are reported.",
)
s.add(
    "BODY-MALFORMED",
    "contracts/api.md Conventions, data-model.md request body",
    "POST",
    "/api/expenses",
    422,
    error_body(("body", "Request body must be valid JSON")),
    raw_body="{not json",
)
s.add(
    "BODY-UNKNOWN",
    "contracts/api.md Conventions, data-model.md request body",
    "POST",
    "/api/expenses",
    422,
    error_body(("color", "Unknown field")),
    body=with_(color="red"),
)
SUITES.append(s)

# ---------------------------------------------------------------- 04 create, update, delete
s = Suite(
    "04_crud.json",
    "crud",
    "Create, list order, update, delete, 404, and updates across two months",
    "CRUD",
)
body_e1 = {
    "amount": "100.00",
    "description": "E1 original",
    "category": "Food",
    "payment_method": "Cash",
    "expense_date": "2026-03-05",
}
body_e2 = {
    "amount": "50.00",
    "description": "E2 original",
    "category": "Transport",
    "payment_method": "UPI",
    "expense_date": "2026-03-06",
}
r1 = create(s, "001-E1", "FR-001", body_e1, save={"e1": "id", "e1_created": "created_at"})
r2 = create(s, "002-E2", "FR-001", body_e2, save={"e2": "id"})
s.add(
    "003-LIST-MARCH",
    "FR-002",
    "GET",
    "/api/expenses?month=2026-03",
    200,
    [expense_expected(r2, "$var:e2"), expense_expected(r1, "$var:e1")],
    note="Newest date first.",
)
summary_case(
    s,
    "004-SUM-MARCH",
    "FR-025, FR-029, FR-034",
    "2026-03",
    derivation="E1 100.00 (Food) + E2 50.00 (Transport) = 150.00, count 2; Food 100.00 then Transport 50.00.",
)
s.add(
    "005-PUT-INVALID",
    "FR-003, FR-014, contracts/api.md PUT",
    "PUT",
    "/api/expenses/{{e1}}",
    422,
    error_body(("amount", "Amount must be greater than zero")),
    body=dict(body_e1, amount="0"),
    note="A rejected update leaves the stored expense unchanged.",
)
s.add(
    "006-LIST-UNCHANGED",
    "FR-014",
    "GET",
    "/api/expenses?month=2026-03",
    200,
    [expense_expected(r2, "$var:e2"), expense_expected(r1, "$var:e1")],
)
body_e1b = {
    "amount": "300.00",
    "description": "E1 edited",
    "category": "Food",
    "payment_method": "UPI",
    "expense_date": "2026-04-02",
}
O.update(r1, body_e1b)
expected_put = expense_expected(r1, "$var:e1")
expected_put["created_at"] = "$var:e1_created"
s.add(
    "007-PUT-OK",
    "FR-003, FR-036, contracts/api.md PUT",
    "PUT",
    "/api/expenses/{{e1}}",
    200,
    expected_put,
    body=body_e1b,
    note="Same id and created_at; amount and date changed (moves from March to April).",
)
summary_case(
    s,
    "008-SUM-MARCH-AFTER",
    "FR-036",
    "2026-03",
    derivation="Only E2 remains in March: total 50.00, count 1, Transport 50.00.",
)
summary_case(
    s,
    "009-SUM-APRIL-AFTER",
    "FR-036",
    "2026-04",
    derivation="E1 moved to 2026-04-02 with amount 300.00: total 300.00, count 1, Food 300.00.",
)
s.add(
    "010-PUT-MISSING",
    "FR-003, contracts/api.md 404",
    "PUT",
    "/api/expenses/9999999",
    404,
    NOT_FOUND,
    body=body_e1b,
)
s.add("011-DELETE-E2", "FR-004, contracts/api.md DELETE", "DELETE", "/api/expenses/{{e2}}", 204, "$empty")
O.remove(r2)
s.add("012-DELETE-AGAIN", "contracts/api.md DELETE", "DELETE", "/api/expenses/{{e2}}", 404, NOT_FOUND)
s.add(
    "013-PUT-DELETED",
    "contracts/api.md PUT",
    "PUT",
    "/api/expenses/{{e2}}",
    404,
    NOT_FOUND,
    body=body_e2,
)
summary_case(
    s,
    "014-SUM-MARCH-EMPTY",
    "FR-036",
    "2026-03",
    derivation="E2 deleted: March is empty: total 0.00, count 0, by_category [].",
)
list_case(s, "015-LIST-MARCH-EMPTY", "FR-022", month="2026-03")
dup = {
    "amount": "10.00",
    "description": "Duplicate",
    "category": "Other",
    "payment_method": "Cash",
    "expense_date": "2026-03-20",
}
create(s, "016-DUP-1", "Edge case: identical expenses are allowed", dup)
create(s, "017-DUP-2", "Edge case: identical expenses are allowed", dup)
list_case(
    s,
    "018-LIST-DUPS",
    "Edge case, FR-006",
    month="2026-03",
    note="Exactly two rows: one POST creates at most one expense.",
)
summary_case(
    s,
    "019-SUM-DUPS",
    "FR-034",
    "2026-03",
    derivation="Two identical expenses of 10.00 (Other): total 20.00, count 2.",
)
SUITES.append(s)

# ---------------------------------------------------------------- 05 filters
s = Suite(
    "05_filters.json",
    "filters",
    "Month and category filters, month boundaries, empty results, and category ordering",
    "FIL",
)
f1 = create(s, "C-F1", "FR-035", {
    "amount": "10.00", "description": "F1 last day of Dec 2025", "category": "Food",
    "payment_method": "Cash", "expense_date": "2025-12-31",
})
f2 = create(s, "C-F2", "FR-035", {
    "amount": "20.00", "description": "F2 first day of Jan 2026", "category": "Transport",
    "payment_method": "UPI", "expense_date": "2026-01-01",
})
f3 = create(s, "C-F3", "FR-035", {
    "amount": "30.00", "description": "F3 last day of Jan 2026", "category": "Food",
    "payment_method": "Cash", "expense_date": "2026-01-31",
})
list_case(s, "L-DEC", "FR-019, FR-035, SC-007", month="2025-12",
          note="2025-12-31 belongs to December 2025 only.")
list_case(s, "L-JAN", "FR-019, FR-035, SC-007", month="2026-01",
          note="2026-01-01 and 2026-01-31 are both inside January; 2025-12-31 is not.")
list_case(s, "L-JAN-FOOD", "FR-020", month="2026-01", category="Food")
list_case(s, "L-JAN-TRANSPORT", "FR-020", month="2026-01", category="Transport")
list_case(s, "L-JAN-EDU", "FR-020, FR-022", month="2026-01", category="Education",
          note="No match: empty array.")
list_case(s, "L-NONE", "FR-022", month="2020-01", note="A valid month without data returns [].")
list_case(s, "L-SEP-FOOD", "FR-018, FR-020, SC-007", month="2026-09", category="Food")
list_case(s, "L-HEALTH", "FR-018, SC-007", category="Healthcare",
          note="Only the dataset uses Healthcare, so this is every Healthcare expense in the database.")
list_case(s, "L-ALL", "FR-021", note="No filter: every expense, expense_date descending then id descending.")
s.cases[-1]["expected_body_or_fields"] = {"$expense_order": True, "$length": len(O.rows)}
s.cases[-1]["derivation"] = f"Ledger of stored expenses at this point: {len(O.rows)}."
summary_case(
    s,
    "SUM-JAN",
    "FR-035",
    "2026-01",
    derivation="F2 20.00 (Transport) + F3 30.00 (Food) = 50.00, count 2; Food 30.00 (1) comes before Transport 20.00 (1) because 30.00 > 20.00. 2025-12-31 is excluded.",
)
summary_case(
    s,
    "SUM-DEC",
    "FR-035",
    "2025-12",
    derivation="F1 10.00 (Food) only: total 10.00, count 1.",
)
s.add("Q-MONTH-13", "contracts/api.md GET /api/expenses", "GET", "/api/expenses?month=2026-13", 422,
      error_body(("month", "Enter a valid month")))
s.add("Q-MONTH-ABC", "contracts/api.md GET /api/expenses", "GET", "/api/expenses?month=abc", 422,
      error_body(("month", "Enter a valid month")))
s.add("Q-MONTH-SHORT", "contracts/api.md GET /api/expenses", "GET", "/api/expenses?month=2026-1", 422,
      error_body(("month", "Enter a valid month")))
s.add("Q-CAT-BAD", "contracts/api.md GET /api/expenses", "GET", "/api/expenses?category=Nope", 422,
      error_body(("category", "Select a valid category")))
s.add("Q-BOTH-BAD", "contracts/api.md GET /api/expenses", "GET",
      "/api/expenses?month=2026-13&category=Nope", 422,
      error_body(("month", "Enter a valid month"), ("category", "Select a valid category"),
                 unordered=True))
s.add("Q-SUM-BAD", "contracts/api.md GET /api/summary", "GET", "/api/summary?month=abc", 422,
      error_body(("month", "Enter a valid month")))
s.add("Q-SUM-13", "contracts/api.md GET /api/summary", "GET", "/api/summary?month=2026-13", 422,
      error_body(("month", "Enter a valid month")))
tie = [
    ("TIE-FOOD", "75.00", "Food"),
    ("TIE-TRANSPORT", "50.00", "Transport"),
    ("TIE-BILLS", "50.00", "Bills"),
    ("TIE-EDU", "50.00", "Education"),
]
for code, amt, cat in tie:
    create(s, f"C-{code}", "FR-031", {
        "amount": amt, "description": code, "category": cat,
        "payment_method": "Cash", "expense_date": "2025-11-15",
    })
summary_case(
    s,
    "SUM-TIE",
    "FR-031",
    "2025-11",
    derivation="Food 75.00 first (highest); Bills, Education, Transport all 50.00, so by name: Bills, Education, Transport. Total 75.00 + 50.00 + 50.00 + 50.00 = 225.00, count 4.",
)
SUITES.append(s)

# ---------------------------------------------------------------- 06 budgets
s = Suite(
    "06_budgets.json",
    "budgets",
    "Budget create, replace, rejection, month rules, and remaining/over-budget arithmetic",
    "BUD",
)
summary_case(s, "001-NO-BUDGET", "FR-027", "2026-07",
             derivation="No budget and no expenses: total 0.00, count 0, budget null, remaining null, over_budget false.")
s.add("002-SET", "FR-023", "PUT", "/api/budgets/2026-07", 200,
      {"month": "2026-07", "amount": "10000.00", "updated_at": "$utc"}, body={"amount": "10000.00"})
O.budgets["2026-07"] = to_cents("10000.00")
s.add("003-REPLACE", "FR-023", "PUT", "/api/budgets/2026-07", 200,
      {"month": "2026-07", "amount": "12000.00", "updated_at": "$utc"}, body={"amount": "12000.00"})
O.budgets["2026-07"] = to_cents("12000.00")
summary_case(s, "004-AFTER-REPLACE", "FR-023, FR-025", "2026-07",
             derivation="Budget replaced by 12000.00; no expenses: remaining 12000.00.")
s.add("005-RESET", "FR-023", "PUT", "/api/budgets/2026-07", 200,
      {"month": "2026-07", "amount": "10000.00", "updated_at": "$utc"}, body={"amount": "10000.00"})
O.budgets["2026-07"] = to_cents("10000.00")

BUD_NUM = "Budget must be a number greater than zero"
BUD_DEC = "Budget can have at most 2 decimal places"
BUD_CAP = "Budget cannot exceed 99,999,999.99"
BUD_BAD = [
    ("0", BUD_NUM), ("0.00", BUD_NUM), ("-100", BUD_NUM), ("", BUD_NUM), ("abc", BUD_NUM),
    ("1,000", BUD_NUM), ("-0.001", BUD_NUM),
    ("12000.999", BUD_DEC), ("0.005", BUD_DEC), ("99999999.995", BUD_DEC),
    ("100000000.00", BUD_CAP), ("100000000.01", BUD_CAP),
]
for i, (given, message) in enumerate(BUD_BAD, 1):
    s.add(f"BAD{i:02d}", "FR-024, FR-014", "PUT", "/api/budgets/2026-07", 422,
          error_body(("amount", message)), body={"amount": given},
          note=f"budget {given!r}: rejected, never rounded; the saved 10000.00 stays.")
s.add("BAD-JSON", "contracts/api.md PUT /api/budgets", "PUT", "/api/budgets/2026-07", 422,
      error_body(("body", "Request body must be valid JSON")), raw_body="{bad")
s.add("BAD-UNKNOWN", "contracts/api.md PUT /api/budgets", "PUT", "/api/budgets/2026-07", 422,
      error_body(("x", "Unknown field")), body={"amount": "500.00", "x": 1})
summary_case(s, "UNCHANGED", "FR-024", "2026-07",
             derivation="After every rejected request the budget is still 10000.00; remaining 10000.00.")

for i, month in enumerate(["2026-13", "abc", "2026-1", "2026-00", "26-07"], 1):
    s.add(f"MONTH-BAD{i:02d}", "contracts/api.md PUT /api/budgets", "PUT", f"/api/budgets/{month}", 422,
          error_body(("month", "Enter a valid month")), body={"amount": "100.00"})
for i, month in enumerate(["1999-12", "2099-01", "0001-01", "9999-12"], 1):
    s.add(f"MONTH-OK{i:02d}", "FR-023, data-model.md Monthly Budget", "PUT", f"/api/budgets/{month}", 200,
          {"month": month, "amount": "100.00", "updated_at": "$utc"}, body={"amount": "100.00"},
          note="Any real month is valid, including months before 2000 and future months.")
    O.budgets[month] = to_cents("100.00")

for i, (given, shown) in enumerate([("0.01", "0.01"), ("12000", "12000.00"), ("99999999.99", "99999999.99")], 1):
    s.add(f"LIMIT-OK{i:02d}", "FR-024", "PUT", "/api/budgets/2026-06", 200,
          {"month": "2026-06", "amount": shown, "updated_at": "$utc"}, body={"amount": given})
    O.budgets["2026-06"] = to_cents(shown)
summary_case(s, "LIMIT-SUM", "FR-024", "2026-06",
             derivation="Last accepted budget for 2026-06 is 99999999.99; no expenses: remaining 99999999.99.")

x1 = create(s, "X1", "FR-025", {"amount": "6000.00", "description": "Budget X1", "category": "Food",
                                 "payment_method": "Cash", "expense_date": "2026-07-01"})
x2 = create(s, "X2", "FR-025", {"amount": "3999.99", "description": "Budget X2", "category": "Transport",
                                 "payment_method": "UPI", "expense_date": "2026-07-31"})
summary_case(s, "SUM-9999-99", "FR-025, FR-026, SC-006", "2026-07",
             derivation="6000.00 + 3999.99 = 9999.99; remaining = 10000.00 - 9999.99 = 0.01; not over budget.")
create(s, "X3", "FR-026", {"amount": "0.01", "description": "Budget X3", "category": "Transport",
                            "payment_method": "UPI", "expense_date": "2026-07-15"})
summary_case(s, "SUM-EQUAL", "FR-026, SC-006", "2026-07",
             derivation="9999.99 + 0.01 = 10000.00 equals the budget: remaining 0.00, over_budget false, over_budget_by null.")
create(s, "X4", "FR-026", {"amount": "0.01", "description": "Budget X4", "category": "Transport",
                            "payment_method": "UPI", "expense_date": "2026-07-16"})
summary_case(s, "SUM-OVER", "FR-026, SC-006", "2026-07",
             derivation="10000.00 + 0.01 = 10000.01 exceeds 10000.00 by 0.01: remaining 0.00, over_budget true, over_budget_by 0.01. Transport 3999.99 + 0.01 + 0.01 = 4000.01 (3), Food 6000.00 (1).")
s.add("RAISE", "FR-023, FR-026", "PUT", "/api/budgets/2026-07", 200,
      {"month": "2026-07", "amount": "10000.01", "updated_at": "$utc"}, body={"amount": "10000.01"})
O.budgets["2026-07"] = to_cents("10000.01")
summary_case(s, "SUM-RAISED", "FR-026",
             "2026-07", derivation="Budget 10000.01 equals spent 10000.01: remaining 0.00, over_budget false.")
s.add("BACK", "FR-023", "PUT", "/api/budgets/2026-07", 200,
      {"month": "2026-07", "amount": "10000.00", "updated_at": "$utc"}, body={"amount": "10000.00"})
O.budgets["2026-07"] = to_cents("10000.00")
summary_case(s, "SUM-BACK", "FR-026", "2026-07",
             derivation="Budget back to 10000.00; spent 10000.01: over by 0.01.")
summary_case(s, "OTHER-MONTH", "FR-023", "2026-09",
             derivation="A budget belongs to one month only: September 2026 still has no budget.")

s.add("W-SET", "FR-025", "PUT", "/api/budgets/2026-05", 200,
      {"month": "2026-05", "amount": "10000.00", "updated_at": "$utc"}, body={"amount": "10000.00"})
O.budgets["2026-05"] = to_cents("10000.00")
for code, amt, cat, date in [("W1", "100.10", "Food", "2026-05-10"), ("W2", "200.20", "Food", "2026-05-11"),
                              ("W3", "50.00", "Transport", "2026-05-12")]:
    create(s, code, "FR-034", {"amount": amt, "description": f"Worked example {code}",
                                "category": cat, "payment_method": "Cash", "expense_date": date})
summary_case(s, "W-SUM", "FR-034, data-model.md worked example", "2026-05",
             derivation="100.10 + 200.20 + 50.00 = 350.30; remaining 10000.00 - 350.30 = 9649.70; Food 100.10 + 200.20 = 300.30 (2), Transport 50.00 (1).")
SUITES.append(s)

# ---------------------------------------------------------------- 07 persistence (verify phase)
s = Suite(
    "07_persistence.json",
    "persistence",
    "After the server was stopped and restarted on the same database file",
    "PER",
)
s.add("CONFIG", "FR-041", "GET", "/api/config", 200, {
    "today": TODAY, "currency": "INR", "categories": CATEGORIES, "payment_methods": PAYMENT_METHODS,
    "limits": {"max_expense": "9999999.99", "max_budget": "99999999.99",
               "max_description_length": 200, "min_date": "2000-01-01"},
}, phase="verify")
for month, name in (("2026-09", "SEP"), ("2026-10", "OCT"), ("2026-11", "NOV")):
    summary_case(s, f"SUM-{name}", "FR-005, SC-008", month, phase="verify",
                 derivation=derivation_for(month))
    list_case(s, f"LIST-{name}", "FR-005, SC-008", month=month, phase="verify")
for month in ("2026-02", "2026-03", "2026-04", "2026-01", "2025-12", "2025-11", "2026-05", "2026-07", "2026-08"):
    list_case(s, f"LIST-{month}", "FR-005, SC-008", month=month, phase="verify")
for month in ("2026-07", "2026-06", "2026-05", "2026-03", "2026-04", "1999-12", "9999-12", "2025-11"):
    summary_case(s, f"SUM-{month}", "FR-005, SC-008", month, phase="verify")
s.add("LIST-ALL", "FR-005, SC-008", "GET", "/api/expenses", 200,
      {"$expense_order": True, "$length": len(O.rows)}, phase="verify",
      derivation=f"Every expense stored in the write phase, minus the deleted one: {len(O.rows)}.")
SUITES.append(s)

TOTAL_AFTER_WRITE = len(O.rows)

# ---------------------------------------------------------------- 08 timing (supplementary)
s = Suite(
    "08_timing.json",
    "timing",
    "Supplementary HTTP timing with 1,000 expenses; correctness is checked, time is only recorded",
    "TIM",
)
s.cases.append({
    "id": "TIM-001",
    "spec_ref": "SC-005 (informational only; SC-005a is measured by a person, SC-005b in process)",
    "phase": "timing",
    "kind": "supplementary",
    "type": "timing",
    "params": {
        "count": 1000,
        "amount": "1.00",
        "expense_date": "2025-02-15",
        "month": "2025-02",
        "baseline_total": TOTAL_AFTER_WRITE,
        "expected_month_total": "1000.00",
    },
    "note": "Creates 1,000 expenses in 2025-02, then lists all and loads the 2025-02 summary. Records elapsed_ms only; no time limit decides a status.",
})
SUITES.append(s)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    total = 0
    for suite in SUITES:
        suite.write()
        total += len(suite.cases)
        print(f"{suite.filename}: {len(suite.cases)} cases")
    print(f"total cases: {total}; expenses stored after the write phase: {TOTAL_AFTER_WRITE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
