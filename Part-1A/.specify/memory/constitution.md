<!--
Sync Impact Report
- Version change: 1.0.0 -> 1.1.0
- Modified principles:
  - I Reliability and Correctness: the mandatory ROUND_HALF_UP quantization rule is replaced by
    exact Decimal parsing, integer-cent representation, and rejection (never rounding) of amounts
    with more than two decimal places
  - IV Security: `package-lock.json` replaced by `yarn.lock` for dependency pinning
  - VI Maintainability: Yarn named as the frontend package manager
- Modified quality gates: G8 `npm run build` -> `yarn build`
- Modified testing rule: the `0.005` money edge case is now rejected, not rounded
- Added sections: none
- Removed sections: none
- Version bump rationale: MINOR. No principle was removed. The money rule became stricter
  (amounts that quantizing would have accepted are now rejected), and the tooling wording changed.
- Follow-up TODOs: none
- Remove this comment before committing.
-->

# SpendWise Constitution

## Core Principles

### I. Reliability and Correctness

All monetary values MUST be handled so that results are exact and repeatable.

- Backend currency parsing MUST use Python `decimal.Decimal`. `float` MUST NOT be used for any
  monetary value in the backend (models, services, tests, fixtures).
- Amounts entered by users MUST be parsed exactly from text. Parsed amounts MUST be represented as
  integer cents (minor units) in all backend calculations and MUST be persisted as SQLite
  `INTEGER`, never `REAL`. The API MUST serialize amounts as decimal strings with exactly two
  fractional digits (e.g. `"12.50"`).
- An expense or budget amount with more than two decimal places MUST be rejected with a validation
  error. User-provided amounts MUST NOT be rounded, quantized, or otherwise altered to fit two
  decimal places, and no rounding mode may be used to turn an invalid amount into an accepted one.
  Parsing and conversion MUST live in one shared money utility.
- Budget calculations and monthly summaries MUST be deterministic: the same stored data MUST always
  produce the same output. Results MUST NOT depend on wall-clock time, locale, row ordering, or
  randomness. "Current date" MUST be an injectable parameter, not read inline.
- Summaries MUST be sorted by an explicit, documented key (e.g. category, then date, then id).

Rationale: a finance tool that is off by one cent, or that changes its answer between runs, is
not trustworthy.

### II. Simplicity and Usability

- The frontend MUST be a React single-page interface that is usable from 360 px to 1440 px viewport
  width without horizontal scrolling.
- Add, edit, delete, and list expense MUST each be completable in at most 3 user interactions
  (clicks or form submissions) from the main screen.
- Form errors MUST be shown next to the offending field in plain language, using the message
  returned by the backend validation.
- Every asynchronous operation MUST show a loading state, and every failure MUST show an error
  state; silent failures are prohibited.
- Interactive elements MUST be keyboard reachable and have accessible labels.
- Features not required by the current specification MUST NOT be built (YAGNI): no authentication,
  multi-currency, or sync unless a spec explicitly adds them.

### III. Data Integrity

- The backend is the sole authority for validation. Frontend validation is a convenience and MUST
  NOT be relied upon.
- The backend MUST reject with HTTP 422 (and a structured error body) any request that has:
  - a negative amount, or an amount of zero unless the spec explicitly allows it;
  - an amount with more than two decimal places or a value above the documented maximum;
  - a missing required field;
  - an invalid or non-ISO-8601 date, or a calendar-invalid date (e.g. `2026-02-30`);
  - a category outside the supported category list.
- The supported category list MUST be defined in exactly one backend location and exposed via the
  API so the frontend never hard-codes it.
- Valid expense records MUST be persisted in SQLite. Writes spanning more than one statement MUST
  run in a transaction, and a rejected request MUST leave the database unchanged.
- Schema changes MUST be applied through versioned, repeatable scripts checked into the repository.
- Database constraints (`NOT NULL`, `CHECK (amount_cents >= 0)`) MUST back up application
  validation.

### IV. Security

- All user input MUST be validated by Pydantic models and sanitized before use. Free-text fields
  MUST have a documented maximum length and MUST be stored as plain text.
- SQL MUST use parameterized queries or an ORM; string-built SQL is prohibited.
- The frontend MUST NOT render user content as raw HTML (`dangerouslySetInnerHTML` is prohibited
  unless sanitized and justified in the plan).
- Secrets, credentials, tokens, and keys MUST NOT appear in source code, tests, or committed
  files. Configuration MUST come from environment variables; `.env` files MUST be git-ignored and
  an `.env.example` with placeholder values MUST be committed.
- CORS MUST allow only explicitly configured origins (no `*` outside local development).
- Error responses MUST NOT leak stack traces, SQL, or file paths.
- The SQLite database file MUST be git-ignored.
- Dependencies MUST be pinned in `requirements.txt` and `yarn.lock`.

### V. Testability

- Business logic (money handling, validation rules, budget and summary calculations) MUST be
  implemented in functions or services independent of FastAPI and the database, so it can be unit
  tested directly.
- Every business rule MUST have at least one automated unit test.
- Every API endpoint MUST have tests for the success path and for each validation failure class
  listed in Principle III.
- Tests MUST be deterministic and independent: each test uses its own temporary or in-memory
  SQLite database, a fixed clock, and no network access.
- Bug fixes MUST include a regression test that fails before the fix.
- Coverage thresholds are defined in the Quality Gates section.

### VI. Maintainability

- The technology stack is fixed: React with Vite (frontend), Python with FastAPI (backend), and
  SQLite (persistence). Changing any of these requires a constitution amendment.
- The frontend package manager is Yarn (classic 1.x). `yarn.lock` MUST be retained in the
  repository and never git-ignored; `package-lock.json` MUST NOT be created.
- The backend MUST be layered, with dependencies pointing inward only:
  `routers` (HTTP) -> `services` (business logic) -> `repositories` (SQLite access), with
  `schemas` (Pydantic) and `core` (config, money utilities) shared. Routers MUST NOT contain
  business logic or SQL.
- The frontend MUST separate API access (`api/` client module), state/hooks, and presentational
  components. Components MUST NOT call `fetch` directly.
- UI elements used in more than one place (form fields, buttons, expense row, error message) MUST
  be reusable components.
- Backend and frontend MUST live in separate top-level directories (`backend/`, `frontend/`).
- Modules SHOULD stay under 300 lines; longer modules need a split or a stated reason.

### VII. Development Standards

- All Python function signatures MUST have type hints, enforced by `ruff` (`ANN` rules).
- All API request and response bodies MUST be Pydantic models; endpoints MUST declare
  `response_model`.
- `ruff check` and `ruff format --check` MUST pass with zero violations.
- `bandit` MUST report zero medium or high severity findings. Any `# nosec` MUST carry a one-line
  justification.
- `pytest` MUST be the only backend test runner.
- Commands for setup, run, lint, security check, and test MUST be documented in the project
  `README.md` so a new contributor can run them without guidance.

## Quality Gates

A change is mergeable only when ALL of the following pass. Each gate is binary and verifiable by a
command.

| # | Gate | Command | Pass criterion |
|---|------|---------|----------------|
| G1 | Lint | `ruff check backend` | 0 violations |
| G2 | Format | `ruff format --check backend` | 0 files would change |
| G3 | Security scan | `bandit -r backend/app -ll` | 0 medium/high findings |
| G4 | Tests | `pytest backend` | 100% pass; 0 skips without a documented reason |
| G5 | Coverage (overall) | `pytest backend --cov=app --cov-fail-under=80` | >= 80% line coverage |
| G6 | Coverage (business logic) | coverage report for `services/` and `core/` | >= 90% line coverage |
| G7 | Float ban | unit test scanning money modules for `float` | 0 occurrences |
| G8 | Frontend build | `yarn build` in `frontend/` | exits 0 |
| G9 | Secrets | review of the diff | 0 secrets or credentials committed |
| G10 | Validation matrix | API tests | every rule in Principle III has a passing rejection test |

## Rules for Specifications, Implementation, and Testing

### Specifications (`/speckit-specify`, `/speckit-clarify`)

- Every functional requirement MUST be testable and use MUST/MUST NOT wording.
- Every spec MUST list, for each input field: type, required/optional, allowed range or values,
  and the error returned on violation.
- Every spec MUST state acceptance scenarios in Given/When/Then form, including at least one
  failure scenario per input field.
- Any calculation (budget remaining, monthly total, per-category total) MUST be specified with an
  explicit formula and a worked numeric example using decimal values.
- Success criteria MUST be measurable (e.g. "a list of 1,000 expenses loads in under 1 second").
- Out-of-scope items MUST be listed so scope stays within the deadline.

### Plans and Tasks (`/speckit-plan`, `/speckit-tasks`)

- The Constitution Check in every plan MUST evaluate gates G1-G10 and Principles I-VII; any
  violation MUST be recorded with a justification in Complexity Tracking.
- Tasks MUST be ordered so that tests for a unit are written before or together with the unit.
- The task list MUST be split into independently demonstrable user stories, ordered by priority,
  so a working subset exists at every milestone.
- Each task MUST name the file(s) it changes.

### Implementation (`/speckit-implement`)

- Implementation MUST NOT begin before a spec, plan, and task list exist for the feature.
- Money values MUST pass through the shared money utility at every input and output boundary.
- New dependencies MUST be justified in the plan; the standard library is preferred.
- Gates G1-G4 MUST be run locally before each commit that touches backend code.

### Testing

- Test layout: `backend/tests/unit/` for business logic, `backend/tests/api/` for endpoints.
- Test names MUST describe behavior (e.g. `test_rejects_negative_amount`).
- Money tests MUST include edge values: `0.00`, `0.01`, `0.005` (more than two decimals: rejected,
  never rounded), `999999.99`, and a sum
  that is wrong under binary floating point (`0.10 + 0.20 == 0.30` with `Decimal`).
- Date tests MUST include a leap day, a month boundary, and a calendar-invalid date.
- Frontend SHOULD have component tests (Vitest and React Testing Library) for the expense form and
  list; frontend coverage is not gated.

## Delivery Constraints

- Deadline: **2026-11-15**. The initial implementation MUST be scoped so that all gates pass by
  that date.
- Priority order when time is short: (1) backend create/list with validation and SQLite
  persistence, (2) monthly summary and budget calculation, (3) React UI for add and list,
  (4) edit and delete, (5) polish.
- Scope MUST NOT grow once planning completes; new ideas go to a backlog and are specified after
  the deadline.
- A single local user is assumed; authentication, multi-user support, and deployment automation
  are out of scope for the initial release.

## Governance

- This constitution supersedes all other project practices. Where a spec, plan, or task conflicts
  with it, the constitution wins and the conflicting artifact MUST be corrected.
- Amendments MUST be made by editing this file, stating the rationale, bumping the version, and
  updating any affected plan check in the same change.
- Versioning follows semantic versioning: MAJOR for removed or redefined principles or gates,
  MINOR for added principles, sections, or gates, PATCH for clarifications and wording.
- Compliance MUST be reviewed when a plan is written (Constitution Check), when a change is
  reviewed (Quality Gates), and before submission (all gates G1-G10 re-run).
- Deviation from a rule MUST be justified in writing in the plan; unjustified deviations MUST
  block merge.

**Version**: 1.1.0 | **Ratified**: 2026-11-12 | **Last Amended**: 2026-11-13
