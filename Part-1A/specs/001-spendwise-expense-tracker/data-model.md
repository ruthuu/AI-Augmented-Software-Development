# Data Model: SpendWise

**Feature**: `001-spendwise-expense-tracker` | **Date**: 2026-11-13

## Entities

### Expense (stored)

| Field | Type (API) | Type (SQLite) | Rules |
|-------|-----------|---------------|-------|
| `id` | integer | `INTEGER PRIMARY KEY AUTOINCREMENT` | Assigned by the system; never reused. |
| `amount` | string, e.g. `"250.50"` | `amount_cents INTEGER` | > 0, <= 9,999,999.99, at most 2 decimals. Stored as cents. |
| `description` | string | `TEXT` | Cleaned per FR-042 (tab, line feed, carriage return become one space; other control characters removed; trimmed), then 1 to 200 characters. |
| `category` | string | `TEXT` | One of the eight categories in `core/constants.py`. |
| `payment_method` | string | `TEXT` | One of the six payment methods in `core/constants.py`, exact match. |
| `expense_date` | string `YYYY-MM-DD` | `TEXT` | Real calendar date, `2000-01-01` to today inclusive, where today is the backend date (FR-041). |
| `created_at` | string (UTC ISO 8601) | `TEXT` | Set once on insert. |
| `updated_at` | string (UTC ISO 8601) | `TEXT` | Set on insert and on every edit. |

Identity: `id` only. No uniqueness constraint on content, so deliberately identical expenses are
allowed (spec Edge Cases). The system never inserts rows except in response to an explicit
`POST /api/expenses`.

### Monthly Budget (stored)

| Field | Type (API) | Type (SQLite) | Rules |
|-------|-----------|---------------|-------|
| `month` | string `YYYY-MM` | `TEXT PRIMARY KEY` | Any real calendar month (year 0001 to 9999, month 01 to 12), including months before 2000 and future months. One row per month. |
| `amount` | string, e.g. `"10000.00"` | `amount_cents INTEGER` | > 0, <= 99,999,999.99, at most 2 decimals. |
| `updated_at` | string (UTC ISO 8601) | `TEXT` | Set on every save. Saving again replaces the row (upsert). |

### Category and Payment Method (constants, not tables)

- Categories: Food, Transport, Shopping, Bills, Entertainment, Healthcare, Education, Other.
- Payment methods: Cash, Credit Card, Debit Card, UPI, Net Banking, Other.
- Defined once in `backend/app/core/constants.py` and served by `GET /api/config`.

### Monthly Summary (derived, never stored)

| Field | Definition |
|-------|-----------|
| `month` | Requested month, or the month of "today" when omitted. |
| `total_spent` | Sum of `amount_cents` of expenses whose date is in the month (first and last day inclusive). |
| `expense_count` | Number of expenses in the month. |
| `total_recorded_count` | Number of all expenses ever recorded (FR-030). |
| `by_category` | One row `{category, total, count}` per category with at least one expense in the month, sorted by `total` descending, then `category` ascending. |
| `budget` | `{month, amount}` or `null` when none is set. |
| `remaining` | `max(budget - total_spent, 0)`; `null` when no budget. |
| `over_budget` | `total_spent > budget`; `false` when no budget. |
| `over_budget_by` | `total_spent - budget` when over budget, otherwise `null`. |

Worked example (budget `10000.00`; November expenses `100.10`, `200.20`, `50.00`):
`total_spent = 35030 cents -> "350.30"`, `expense_count = 3`, `remaining = "9649.70"`,
`over_budget = false`, `by_category = [Food 300.30 (2), Transport 50.00 (1)]`.

Boundary example (budget `10000.00`, spent `10000.01`): `remaining = "0.00"`, `over_budget = true`,
`over_budget_by = "0.01"`. Spent exactly `10000.00`: `remaining = "0.00"`, `over_budget = false`,
`over_budget_by = null`.

## Schema (migration `001_initial.sql`)

```sql
CREATE TABLE expenses (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    amount_cents   INTEGER NOT NULL CHECK (amount_cents > 0 AND amount_cents <= 999999999),
    description    TEXT    NOT NULL CHECK (length(description) BETWEEN 1 AND 200),
    category       TEXT    NOT NULL,
    payment_method TEXT    NOT NULL,
    expense_date   TEXT    NOT NULL
        CHECK (expense_date GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]-[0-3][0-9]'),
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);

CREATE INDEX idx_expenses_date ON expenses (expense_date DESC, id DESC);
CREATE INDEX idx_expenses_category ON expenses (category);

CREATE TABLE monthly_budgets (
    month        TEXT PRIMARY KEY CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0 AND amount_cents <= 9999999999),
    updated_at   TEXT NOT NULL
);
```

Notes:

- The `CHECK` constraints are stricter than the constitution's `amount_cents >= 0` because the spec
  forbids zero: `amount_cents > 0` means at least 1 cent (`0.01`) in both tables, so a zero or
  negative amount cannot be stored even if request validation is bypassed (FR-007, FR-015). The
  upper limits (999,999,999 and 9,999,999,999 cents) mirror FR-009 and FR-024.
- There is no `CHECK ... IN (...)` for category or payment method; see decision D-11.
- A runner table `schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)` is
  created by the migration runner itself.
- Month queries use an inclusive range on the ISO date text between the first and last day of the
  month: `expense_date >= '2026-11-01' AND expense_date <= '2026-11-30'` (no next-month value is
  needed, so December 9999 cannot overflow). ISO dates sort correctly as text.

## Validation Rules and Messages

Evaluated in the order listed for each field; the first failure is reported for that field. All
failures are returned together, one per field. Amount text parsing and every digit and
decimal-places check are done by `core/money.py` (`analyze_amount_text`); `services/validation.py`
applies the order below and maps each outcome to its message.

| Field | Order of checks | Message |
|-------|-----------------|---------|
| amount | missing or empty | Amount is required |
| | not matching `^[+-]?\d+(\.\d+)?$` (e.g. `abc`, `12.`, `.5`, `1,000`, `1e3`) | Enter a valid amount |
| | value <= 0 | Amount must be greater than zero |
| | more than 2 decimal places | Amount can have at most 2 decimal places |
| | above 9,999,999.99 | Amount cannot exceed 9,999,999.99 |
| description | empty or whitespace-only after cleaning (FR-042) | Description is required |
| | longer than 200 characters after cleaning | Description cannot exceed 200 characters |
| category | missing | Category is required |
| | not one of the eight | Select a valid category |
| payment_method | missing or empty | Payment method is required |
| | not an exact match of the six | Select a valid payment method |
| expense_date | missing | Date is required |
| | not `YYYY-MM-DD` or not a real calendar date | Enter a valid date |
| | before 2000-01-01 | Date cannot be before 01 Jan 2000 |
| | after today (backend date from the injected clock, FR-041) | Date cannot be in the future |
| budget amount | empty, non-numeric, zero, or negative | Budget must be a number greater than zero |
| | more than 2 decimal places | Budget can have at most 2 decimal places |
| | above 99,999,999.99 | Budget cannot exceed 99,999,999.99 |
| month (path or query) | not `YYYY-MM` or not a real month (year 0001 to 9999, month 01 to 12); every real month is valid, including months before 2000 and future months | Enter a valid month |
| request body (any write endpoint) | not valid JSON | Request body must be valid JSON (field `body`) |
| request body (any write endpoint) | contains a field that is not part of the request | Unknown field (field is the unknown field's name) |

Other messages: update or delete of a missing expense returns 404 "This expense no longer exists".

## State Transitions

Expenses have no status. The only lifecycle is create -> update (any number of times, same `id`) ->
delete (permanent). Every transition changes the derived summary for the month of the old date and,
if the date changed months, for the month of the new date (FR-036). Summaries are recomputed from
the stored rows on every request, so totals cannot go stale.
