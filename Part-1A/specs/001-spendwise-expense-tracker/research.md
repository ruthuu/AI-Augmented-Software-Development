# Research and Technical Decisions: SpendWise

**Feature**: `001-spendwise-expense-tracker` | **Date**: 2026-11-13

Each entry: Decision, Rationale, Alternatives considered. IDs (D-nn) are referenced from
[plan.md](plan.md).

## Resolved planning decisions (formerly provisional)

These three items were open after `/speckit-clarify` and are now decided. They are written into the
spec (FR-041, FR-043, SC-005) and the Clarifications log.

| ID | Decision | Spec reference | Artifacts |
|----|----------|----------------|-----------|
| P-1 | The backend determines "today" at runtime from the local date of the machine it runs on and exposes it in `GET /api/config`. The interface uses it for the default month and the latest selectable date. Future-date validation uses the same backend date. Automated tests use the fixed date `2026-11-12`. | FR-011, FR-028, FR-041, Assumptions | `core/clock.py`, `contracts/api.md`, frontend default month and date `max`, `tests/conftest.py` |
| P-2 | SC-005 has two checks. SC-005a (manual): database seeded with 1,000 expenses; 5 cold-cache page loads; time from navigation start until list and dashboard are both visible; every run within 2 s; median recorded. SC-005b (automated, in process): 1,000 seeded expenses, fixed date, one warm-up call; list-all and monthly summary each timed separately; each under 500 ms. SC-005b measures server work only, not rendering or network. | SC-005 | `tests/api/test_performance.py`, `backend/scripts/seed.py`, `quickstart.md` V10 |
| P-3 | One click, tap, or form submission is one interaction; typing is not. Choosing values inside an open form is data entry and is not counted; choosing a filter or month value as the operation itself is one interaction. Counted from the main screen with nothing open. | FR-039, FR-043, SC-001, SC-010 | UI layout, `quickstart.md` V11, frontend tests |

## Decisions

### D-01 Frontend language: TypeScript

- **Decision**: Vite `react-ts` template with `strict` enabled.
- **Rationale**: Same setup cost as JavaScript. Typed API responses catch field-name mistakes
  between backend and UI, which is the most likely source of bugs in a 3-day build.
- **Alternatives**: JavaScript (less typing, but silent mismatches); TypeScript with a code
  generator from OpenAPI (extra tooling, rejected as over-engineering).

### D-02 Single-page UI, no router, no state library, plain CSS

- **Decision**: One screen with a dashboard section and an expenses section. React hooks for state.
  A single stylesheet with CSS Grid/Flexbox and media queries.
- **Rationale**: The spec has one screen's worth of features. Fewer dependencies means less to
  install, configure, and debug before the deadline.
- **Alternatives**: React Router (no multiple pages needed); TanStack Query or Redux (more concepts
  than the app needs); Tailwind or a component library (setup time, no benefit here).

### D-03 Frontend does no money arithmetic

- **Decision**: The backend returns every money value as a two-decimal string. The frontend only
  formats strings for display (`₹10,000.00`) by inserting thousands separators into the string. It
  never converts money to `number`.
- **Rationale**: Satisfies the constitution's exactness rule end to end and removes any chance of
  float drift on the screen.
- **Alternatives**: Convert to cents as `number` in the UI (still exact for the allowed range, but
  duplicates backend logic and invites mistakes).

### D-04 Backend: `sqlite3` from the standard library, hand-written SQL

- **Decision**: Repositories use parameterized SQL through `sqlite3`. No ORM.
- **Rationale**: Two tables and about eight queries. No extra dependency, no mapping layer, and
  Bandit has nothing to flag as long as SQL contains only placeholders.
- **Alternatives**: SQLAlchemy or SQLModel (more setup, learning cost, and hidden queries for no
  gain at this size).

### D-05 Money storage: integer cents

- **Decision**: Store `amount_cents INTEGER`. Convert with `Decimal` in one module
  (`core/money.py`): string to cents on input, cents to two-decimal string on output.
- **Rationale**: Integers are exact, `SUM()` in SQL is exact, and range checks are simple
  `CHECK` constraints.
- **Alternatives**: `TEXT` decimal strings (SQL cannot sum them exactly); `REAL` (prohibited).

### D-06 Money parsing is strict and string-only

- **Decision**: Request amounts MUST be JSON strings. `core/money.py` is the single owner of amount-text parsing and every digit and
  decimal-places check (`analyze_amount_text` trims, applies `^[+-]?\d+(\.\d+)?$`, and reports the
  sign, the decimal places, and the exact cents). `services/validation.py` `parse_amount` applies, in order:
  empty -> "Amount is required"; not matching `^[+-]?\d+(\.\d+)?$` -> "Enter a valid amount"; value
  <= 0 -> "Amount must be greater than zero"; more than two decimals -> "Amount can have at most 2
  decimal places"; above `9,999,999.99` -> "Amount cannot exceed 9,999,999.99". `parse_budget` uses
  the same order with the budget messages from FR-024 and limit `99,999,999.99`.
- **Rationale**: Covers every accepted and rejected form in the spec's Edge Cases (`12.`, `.5`,
  `1,000`, `1e3`, `abc`, `12.345`, `-5`). Because it works on strings, no value ever passes
  through `float`. Trailing zeros beyond two places (`12.500`) are rejected, never silently
  rounded.
- **Alternatives**: Let Pydantic coerce `Decimal` (accepts `1e3`, `NaN`, `Infinity`; messages not
  controllable); accept JSON numbers (a float risk at the boundary).

### D-07 Validation layering

- **Decision**: Three layers, all on the backend:
  1. Pydantic request models check shape: required fields, string types, no extra fields, and call
     the pure parsers in `services/validation.py` (amount, budget, date format, month format,
     description, category, payment method).
  2. The service layer checks rules that need context: date not after "today" and not before
     `2000-01-01`.
  3. SQLite `CHECK` constraints are the last line of defense for amount range, month and date
     format, and description length.
- **Rationale**: The parsers are plain functions, so unit tests do not need FastAPI or SQLite. The
  context-dependent rule uses the injected clock, which keeps results deterministic.
- **Alternatives**: Pydantic `date` type (accepts more formats than the spec allows, and cannot see
  the injected clock).

### D-08 One error format

- **Decision**: All errors return
  `{"code": "...", "message": "...", "errors": [{"field": "...", "message": "..."}]}`. Codes:
  `validation_error` (422), `not_found` (404), `internal_error` (500). A global handler converts
  Pydantic and service errors into this shape and returns generic text for unexpected errors.
- **Rationale**: The UI can map `errors[].field` to the form field and show `message` verbatim,
  which meets FR-014. Nothing about SQL, stack traces, or file paths reaches the client.
- **Alternatives**: FastAPI's default 422 body (nested, English technical messages, includes
  "Value error," prefixes).

### D-09 "Today" comes from an injectable clock (P-1)

- **Decision**: `core/clock.py` provides `get_today()` as a FastAPI dependency. It returns the
  local date of the machine running the backend, read at request time. `GET /api/config` returns it
  as `today`, and the service layer uses the same dependency for the future-date check, so the
  interface and the validation can never disagree. Tests override the dependency with `2026-11-12`.
  An optional environment variable `SPENDWISE_TODAY` pins the date for demos and manual
  walkthroughs; it is documented as test and demo only.
- **Rationale**: Constitution I requires an injectable current date. A single source of truth
  avoids browser/server disagreement around midnight or across time zones.
- **Alternatives**: Browser sends its date (two sources of truth); freeze time with a library
  (extra dependency).

### D-10 Schema changes through versioned SQL files

- **Decision**: `backend/app/db/migrations/NNN_name.sql`, applied in order at startup by a small
  runner that records applied versions in `schema_migrations`.
- **Rationale**: Meets constitution III ("versioned, repeatable scripts") with about 30 lines of
  code and no new dependency.
- **Alternatives**: Alembic (heavy for two tables); `CREATE TABLE IF NOT EXISTS` in code (not
  versioned).

### D-11 Category and payment method lists live in one place

- **Decision**: Constants in `core/constants.py`, exposed through `GET /api/config`. The frontend
  reads them from there. The database has no `CHECK ... IN (...)` for them.
- **Rationale**: Constitution III requires exactly one definition. A SQL copy would be a second.
  The service layer validates before any write, and no other code path writes expenses.
- **Alternatives**: Enum `CHECK` in SQL (second source of truth); lookup tables with foreign keys
  (more joins for fixed lists).

### D-12 Connections and test databases

- **Decision**: One SQLite connection per request through a FastAPI dependency, with
  `PRAGMA foreign_keys = ON`. Writes use a transaction (`with conn:`). Tests create a temporary
  file database per test through `tmp_path`.
- **Rationale**: Simple and safe for a single-user app. A file database lets persistence tests
  reopen the same data with a second application instance, which an in-memory database cannot do.
- **Alternatives**: Shared global connection (thread-safety problems); in-memory databases (cannot
  test restart persistence).

### D-13 Summary computation

- **Decision**: The repository returns month rows as `(amount_cents, category)` pairs and counts;
  `services/calculations.py` (pure functions) sums them with integers and builds the response:
  `remaining = max(budget - spent, 0)`, `over_budget = spent > budget`,
  `over_budget_by = spent - budget` when over, else `null`. Category rows are sorted by total
  descending, then category name.
- **Rationale**: Keeps the business rules in pure, directly testable functions. Returning
  `remaining` clamped at `0.00` plus `over_budget_by` matches the spec ("not as a negative
  remaining value"). The ordering rule satisfies FR-031 and determinism (FR-037).
- **Alternatives**: SQL `GROUP BY` for everything (rules would hide in SQL strings and be harder to
  unit test).

### D-14 Description sanitization

- **Decision**: Apply FR-042 in `services/validation.py` (`clean_description`), in this order:
  (1) replace each tab, line feed, and carriage return with one space; (2) remove every other
  Unicode control character (`unicodedata.category(ch) == "Cc"`, e.g. NUL, DEL, C1 controls);
  (3) trim leading and trailing spaces; then check the cleaned text is 1 to 200 characters. Nothing
  else is changed: `<`, `>`, `&`, quotes, backslashes, accented letters, non-Latin scripts, and
  emoji are kept. Zero-width format characters (category `Cf`) are also kept because they are not
  control characters. The cleaned text is stored as plain text; React escapes it on output and
  `dangerouslySetInnerHTML` is not used.
- **Rationale**: Meets constitution IV ("validate and sanitize") without altering visible text.
  Turning line breaks and tabs into spaces keeps pasted multi-line text readable ("Tea" + newline
  + "Snacks" becomes "Tea Snacks") instead of gluing words together. Dangerous characters are made
  harmless by safe output encoding, not by stripping them.
- **Alternatives**: Remove all control characters including line breaks (glues words together);
  HTML-escaping on write (corrupts stored data, double-escapes in React); no cleaning (violates the
  constitution and lets NUL and similar characters reach the database).

### D-15 Local development networking

- **Decision**: Vite dev server proxies `/api` to `http://127.0.0.1:8000`. The backend also allows
  CORS only for origins listed in `SPENDWISE_CORS_ORIGINS` (default
  `http://localhost:5173,http://127.0.0.1:5173`). Uvicorn binds to `127.0.0.1`.
- **Rationale**: No CORS problems in development, no wildcard origins (constitution IV), and no
  network exposure.
- **Alternatives**: `allow_origins=["*"]` (prohibited); serving the built frontend from FastAPI
  (extra work, not needed for the assignment).

### D-16 Frontend testing stack

- **Decision**: Vitest, React Testing Library, `@testing-library/user-event`, `jsdom`. Tests mock
  the `api/` module (one place), never `fetch` calls spread across components.
- **Rationale**: Native to Vite, no extra bundler config, and fast. Constitution VI already forces
  all network calls into `api/`, so mocking one module is enough.
- **Alternatives**: Jest (needs transform config for Vite/TS); Playwright for every flow (slower to
  set up; kept as an optional stretch for SC-010).

### D-17 SC-010 verification

- **Decision**: SC-010 is verified by one scripted pass/fail walkthrough (add expense, set budget,
  open dashboard; expected figures listed in `quickstart.md`), run by a reviewer other than the
  author or by an automated end-to-end UI test against the real backend. Steps, interaction counts
  (FR-043), expected versus observed figures, and any help given are recorded in `harness-log.md`.
  If no independent reviewer or qualifying end-to-end test was available, the result is
  `NOT DEMONSTRATED`; if it was attempted but help was needed or any requirement was not met, the
  result is `FAILED`; `PASSED` requires completion without help, all interaction limits met, and all
  expected figures matched. A
  component test with a mocked API is not an end-to-end test. Playwright is an optional stretch.
- **Rationale**: This matches the current SC-010 wording: a scripted walkthrough with 0 failed
  steps, no verbal help, interaction limits, and expected figures. It is not a usability study, so
  no percentage of users is claimed.
- **Alternatives**: Playwright as mandatory (extra dependency and browser download; risk to the
  deadline); a multi-user usability study (impractical for this assignment and not what SC-010
  requires).

### D-18 Dependency policy

- **Decision**: Backend runtime: `fastapi`, `uvicorn`. Backend dev: `pytest`, `pytest-cov`, `httpx`
  (needed by FastAPI's `TestClient`), `ruff`, `bandit`. Frontend: `react`, `react-dom`, plus the
  Vite template tooling, `vitest`, and the Testing Library packages. Exact versions are pinned from
  the first successful install (`requirements*.txt` with `==`; `yarn.lock` committed). The frontend
  package manager is Yarn 1.22 (classic): `yarn install --frozen-lockfile`, `yarn dev`,
  `yarn build`, `yarn lint`, `yarn test`.
- **Rationale**: Smallest set that meets the constitution. Pydantic v2 comes with FastAPI. Yarn is
  the project's chosen package manager; constitution v1.1.0 (amended 2026-11-13) names `yarn build` and `yarn.lock`.
- **Alternatives**: `pydantic-settings` (not needed for three environment variables); npm (not
  chosen).

### D-19 Independent harness and evidence

- **Decision**: A harness in `harness/` (outside `backend/` and `frontend/`) runs the quality gates
  and black-box HTTP checks whose expected values are derived from the spec before implementation.
  Each run stores stdout, stderr, exit codes, and expected-versus-observed results in
  `evidence/initial-generation/` (first run, before any repair) or `evidence/final-generation/`
  (same checks after repairs). `harness-log.md` records rules, runs, failures, repairs, and human
  decisions. The coding agent may not edit `harness/` or `evidence/`.
- **Rationale**: Checks written by the same agent that wrote the code, after the code, can be bent
  to pass. Fixed expected values and preserved raw output let a human judge what really happened.
- **Alternatives**: Rely only on the application's own tests (not independent); use a browser
  automation suite for the whole harness (heavier, and not needed for the API rules).
