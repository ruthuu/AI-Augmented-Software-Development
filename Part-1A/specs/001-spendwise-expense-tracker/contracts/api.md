# API Contract: SpendWise

**Feature**: `001-spendwise-expense-tracker` | **Date**: 2026-11-13

Base path `/api`. JSON only. FastAPI also serves the generated OpenAPI document at
`/openapi.json` and `/docs`; this file is the human-readable contract and the source for contract
tests.

## Conventions

- Money: JSON **strings** with exactly two decimals (`"250.50"`). Requests MUST send strings.
- Dates: `YYYY-MM-DD`. Months: `YYYY-MM`. Timestamps: UTC ISO 8601.
- Currency is always INR; there is no currency field.
- Unknown request fields are rejected with 422; `errors[].field` is the unknown field's name and the
  message is "Unknown field". A body that is not valid JSON is rejected with 422, field `body`,
  message "Request body must be valid JSON".
- `description` is cleaned before validation (FR-042): tab, line feed, and carriage return become one
  space, other control characters are removed, then it is trimmed. Responses return the cleaned
  text.
- "Today" is the backend's local date (FR-041). `GET /api/config` returns it as `today`; the
  future-date check on `expense_date` and the default month of `GET /api/summary` use the same
  value.

### Error body (all non-2xx responses)

```json
{
  "code": "validation_error",
  "message": "Please correct the highlighted fields.",
  "errors": [
    { "field": "amount", "message": "Amount must be greater than zero" }
  ]
}
```

| Status | `code` | When |
|--------|--------|------|
| 404 | `not_found` | Expense does not exist; `message` is "This expense no longer exists"; `errors` is `[]` |
| 422 | `validation_error` | Any invalid input; `errors` lists one entry per failing field |
| 500 | `internal_error` | Unexpected failure; generic `message`, no internals |

Field names in `errors[].field`: `amount`, `description`, `category`, `payment_method`,
`expense_date`, `month`, and `body` (for malformed JSON). Messages are listed in
[data-model.md](../data-model.md#validation-rules-and-messages).

## Endpoints

| Method | Path | Responsibility | Success |
|--------|------|----------------|---------|
| GET | `/api/config` | Static lists, limits, and "today" for the UI | 200 |
| GET | `/api/expenses` | List expenses, optionally filtered by month and category | 200 |
| POST | `/api/expenses` | Validate and create one expense | 201 |
| PUT | `/api/expenses/{id}` | Validate and replace all editable fields of an expense | 200 |
| DELETE | `/api/expenses/{id}` | Permanently delete an expense | 204 |
| PUT | `/api/budgets/{month}` | Validate and create or replace the budget for a month | 200 |
| GET | `/api/summary` | Monthly dashboard and budget status | 200 |

### GET /api/config

Response 200:

```json
{
  "today": "2026-11-12",
  "currency": "INR",
  "categories": ["Food", "Transport", "Shopping", "Bills", "Entertainment", "Healthcare", "Education", "Other"],
  "payment_methods": ["Cash", "Credit Card", "Debit Card", "UPI", "Net Banking", "Other"],
  "limits": {
    "max_expense": "9999999.99",
    "max_budget": "99999999.99",
    "max_description_length": 200,
    "min_date": "2000-01-01"
  }
}
```

### GET /api/expenses

Query (all optional): `month=YYYY-MM`, `category=<category>`. Both given means both must match.
Invalid values return 422 ("Enter a valid month" / "Select a valid category"). Order: `expense_date`
descending, then `id` descending (FR-002). Response 200: array of Expense; `[]` when nothing
matches.

```json
[
  {
    "id": 7,
    "amount": "250.50",
    "description": "Lunch",
    "category": "Food",
    "payment_method": "UPI",
    "expense_date": "2026-11-10",
    "created_at": "2026-11-12T08:15:00Z",
    "updated_at": "2026-11-12T08:15:00Z"
  }
]
```

### POST /api/expenses and PUT /api/expenses/{id}

Request (all five fields required):

```json
{
  "amount": "250.50",
  "description": "Lunch",
  "category": "Food",
  "payment_method": "UPI",
  "expense_date": "2026-11-10"
}
```

- POST: 201 with the created Expense. Always creates exactly one row.
- PUT: 200 with the updated Expense; the `id` and `created_at` do not change. 404 if the id does
  not exist. A rejected request leaves the stored expense unchanged.
- 422 example for an empty body: one error per missing field, e.g.
  `{"field": "amount", "message": "Amount is required"}` and the same for the other four fields
  (US1 scenario 8).

### DELETE /api/expenses/{id}

204 with no body. 404 "This expense no longer exists" if missing. The confirmation step (FR-004) is
a UI concern; the API deletes when called.

### PUT /api/budgets/{month}

Request:

```json
{ "amount": "10000.00" }
```

Response 200:

```json
{ "month": "2026-11", "amount": "10000.00", "updated_at": "2026-11-12T08:20:00Z" }
```

Setting again replaces the value. A 422 leaves any existing budget unchanged, including a 422 for a
malformed JSON body (field `body`) or an unknown field in the request. Any valid calendar month is
allowed, including future months and months before 2000; only a malformed month (not `YYYY-MM` or
not a real month) returns "Enter a valid month".

### GET /api/summary

Query: `month=YYYY-MM` (optional; defaults to the month of "today"). Response 200:

```json
{
  "month": "2026-11",
  "total_spent": "350.30",
  "expense_count": 3,
  "total_recorded_count": 57,
  "by_category": [
    { "category": "Food", "total": "300.30", "count": 2 },
    { "category": "Transport", "total": "50.00", "count": 1 }
  ],
  "budget": { "month": "2026-11", "amount": "10000.00" },
  "remaining": "9649.70",
  "over_budget": false,
  "over_budget_by": null
}
```

- No budget set: `budget`, `remaining` are `null`, `over_budget` is `false`.
- Over budget by `0.01`: `remaining` is `"0.00"`, `over_budget` is `true`,
  `over_budget_by` is `"0.01"`.
- `by_category` lists only categories with spending in the month, sorted by total descending, then
  name. It ignores the expense list's category filter (FR-032).
- Month with no expenses: `total_spent` `"0.00"`, `expense_count` `0`, `by_category` `[]`.

## Responsibilities

| Layer | Owns |
|-------|------|
| Router | Parse path/query/body, call one service function, shape the response. No SQL, no business rules. |
| Schema (Pydantic) | Field shape, required fields, calling pure parsers, response models. |
| Service | Context rules (date range against "today"), orchestration, error mapping, summary calculations (pure helpers). |
| Repository | Parameterized SQL, cents conversion at the boundary, transactions. |
