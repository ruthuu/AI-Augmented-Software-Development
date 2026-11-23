# Quickstart and Validation Guide: SpendWise

**Feature**: `001-spendwise-expense-tracker` | **Date**: 2026-11-13

How to set up, run, and verify the application once implemented. Commands are for Windows
PowerShell, run from the repository root (`Part-1A`) unless stated. Contracts:
[contracts/api.md](contracts/api.md). Data rules: [data-model.md](data-model.md).

## Prerequisites

- Python 3.12 or later
- Node.js 24 and Yarn 1.22 (classic). Check with `yarn --version`; the package manager for the
  frontend is Yarn, and `yarn.lock` is committed

## Setup

```powershell
# Backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements-dev.txt

# Frontend
cd frontend
yarn install --frozen-lockfile
cd ..
```

Configuration uses real environment variables only. The application reads `SPENDWISE_DB_PATH`,
`SPENDWISE_CORS_ORIGINS`, and `SPENDWISE_TODAY` from the process environment when it starts. It does
not read any `.env` file and uses no dotenv package. `backend/.env.example` is only a reference
list of the available variables and example values; do not copy it to `.env` expecting it to take
effect. Set the variables you need in the PowerShell terminal that starts the backend:

```powershell
$env:SPENDWISE_DB_PATH = "backend\data\spendwise.db"                         # optional, this is the default
$env:SPENDWISE_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"  # optional, this is the default
$env:SPENDWISE_TODAY = "2026-11-12"                                          # optional, demos and walkthroughs only

# Return a variable to its default:
Remove-Item Env:SPENDWISE_TODAY -ErrorAction SilentlyContinue
```

A variable set this way lasts only for that terminal session, and the backend reads it at start, so
restart the backend after changing it. A relative `SPENDWISE_DB_PATH` is resolved against the
repository root (`Part-1A`), not the folder the server is started from.

| Variable | Default | Purpose |
|----------|---------|---------|
| `SPENDWISE_DB_PATH` | `backend/data/spendwise.db` | SQLite file location (git-ignored) |
| `SPENDWISE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed browser origins |
| `SPENDWISE_TODAY` | unset (real local date) | Pins "today" (`YYYY-MM-DD`) for demos and walkthroughs only; automated tests override it with `2026-11-12` (FR-041) |

## Run

```powershell
# Terminal 1: backend on http://127.0.0.1:8000
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2: frontend on http://localhost:5173
cd frontend
yarn dev
```

The database file and tables are created automatically on first start. `app.main:app` is the module-level `app = create_app()` in `backend/app/main.py`; the independent harness starts the server with the same `uvicorn app.main:app --app-dir backend` entry point.

## Quality gates (constitution G1 to G10)

```powershell
ruff check backend                              # G1
ruff format --check backend                     # G2
bandit -r backend/app -ll                       # G3
pytest backend                                  # G4, G7 (float-ban test), G10
pytest backend --cov=app --cov-fail-under=80    # G5
# G6: coverage report for app/services and app/core must show >= 90%
cd frontend; yarn build; yarn lint; yarn test; cd ..   # G8 and frontend lint/tests
# G9: review the complete working tree (every file, not only `git diff`, because new files are untracked) together with the output of the scanner:
#   python harness\scan_repo.py tracked-files ; python harness\scan_repo.py secret-patterns
#   (findings show file, line, and pattern only, never the matched text); confirm .env and *.db are not tracked
```

The frontend package manager is Yarn and `yarn.lock` is retained, as required by constitution v1.1.0.

## Independent harness and evidence

The harness is separate from the application and its own tests. It is written from the spec
before the application exists, runs the same checks every time, and stores raw evidence. See
[tasks.md](tasks.md) Phases 2 and 9 and `harness-log.md`.

```powershell
.\harness\run-harness.ps1 -OutDir evidence\initial-generation   # first run, before any repair
.\harness\run-harness.ps1 -OutDir evidence\final-generation     # same checks, after repairs
```

Each run writes, per check: `<check>.stdout.txt`, `<check>.stderr.txt`, `<check>.exitcode.txt`,
`<check>.meta.json` (command, start, end), plus `api-results.json` (each black-box case with
expected and observed values), `results.json`, `results.md`, `environment.txt`,
`manifest.sha256.txt`. A check is PASS only when it was executed and its exit code and comparisons
say so; otherwise it is FAIL, ERROR, or NOT RUN. Initial evidence is never overwritten.

Repairs are traced without requiring a Git commit: the source tree is copied to
`evidence\snapshots\initial-generation-source\` at the generation freeze (and to
`after-repair-NN-source\` after each repair), and each repair is recorded as a SHA-256 manifest
comparison (added, removed, and modified files, including new untracked files) plus a text diff
of the snapshot against the repaired tree.

All evidence is generated by the independent operator (the harness runner or the human running the
commands), never by the coding agent. Snapshots, manifests, diffs, change lists, and run folders
exclude `.env`, `.env.*` (except `.env.example`), `*.log`, `yarn-error.log`, and `*.db` files, and
the environment record lists tool versions only, never environment variable values. The secret
scanner still scans `.env*` files in the working tree, but prints only file, line, and pattern
name, never the matched text, and it is also run over every snapshot and run folder before the
folder is marked read-only.

## Validation scenarios

Each scenario lists the spec items it proves. "Seed" means the deterministic seed script, which
fills a separate database file and never touches the default application database:

```powershell
python backend/scripts/seed.py --count 50 --db backend\data\seed-50.db      # 50 expenses, September to November 2026 (dates up to 2026-11-12), all 8 categories
python backend/scripts/seed.py --count 1000 --db backend\data\seed-1000.db  # 1,000 expenses, same date range
$env:SPENDWISE_TODAY = "2026-11-12"                    # so the dashboard opens on November 2026
$env:SPENDWISE_DB_PATH = "backend\data\seed-50.db"   # then start the backend against that file
```

Run these commands from the repository root (`Part-1A`). The script adds the `backend` folder to
its own import path, so no `PYTHONPATH` or `cd` is needed.

`--count N` and `--db PATH` are both required. The script refuses to run without `--db` or when
`--db` is the default application database in any spelling (a path with `..` segments such as
`.\backend\..\backend\data\spendwise.db`, the absolute path, or different letter casing on
Windows), is a directory, or is an existing file that is not empty; when it refuses it creates and
changes nothing. It accepts a new path or an existing empty file, and a relative `--db` is relative
to the current folder. Running it again with the same `--db` is therefore refused: rename or delete
the seed file (it is only test data) or pick a new name.

| # | Scenario | Steps | Expected result | Spec items |
|---|----------|-------|-----------------|-----------|
| V1 | Add and list | Add `250.50`, `Lunch`, Food, `2026-11-10`, UPI | Row shows `₹250.50`, `Lunch`, `Food`, `10 Nov 2026`, `UPI`; no other rows created | US1 #1, FR-001, FR-002 |
| V2 | Edit and delete | Edit amount to `300.00`; then delete and cancel; then delete and confirm | `₹300.00` on the same row; cancel keeps row; confirm removes it | US1 #2 to #4 |
| V3 | Validation | Submit empty form; then amounts `0`, `-5`, `12.345`; date `2026-02-30`; a future date | A message beside each invalid field; list unchanged | US1 #5 to #12, SC-002 |
| V4 | Persistence | Add an expense, set a budget, stop and restart both servers | Expense and budget are unchanged | US1 #13, US3 #10, SC-008 |
| V5 | Filters | With the 50-expense seed database, filter by month (September, October, or November 2026), by category, by both, and clear | Only matching rows; empty-state message when none | US2, SC-007 |
| V6 | Budget | Set November budget `10000.00`; add expenses to reach `9999.99`, `10000.00`, `10000.01` | No warning, no warning (`₹0.00` remaining), warning "exceeded by ₹0.01" | US3 #2 to #4, SC-006 |
| V7 | Budget validation | Try `0`, `-100`, empty, `abc`, `12000.999`, `100000000.00`; then `0.01`, `99999999.99` | Specific messages for the first six; the last two are saved; prior budget never changes on failure | US3 #8, #11 to #15 |
| V8 | Dashboard | Select November 2026 on the 50-expense seed database; edit an expense dated in November into an October 2026 date | Total, count, category rows match hand calculation; both months update without reload | US4, SC-003, SC-004 |
| V9 | Responsive | Browser dev tools at 360, 768, and 1440 px wide | No horizontal scrolling; all controls reachable | FR-038 |
| V10 | Performance (SC-005a, manual) | Use the 1,000-expense seed database (`--count 1000`); with the browser cache disabled, load the main screen 5 times; for each run record the time from the start of navigation until both the expense list and the dashboard figures are visible | Every one of the 5 runs is within 2 seconds; record the median too. Measures browser rendering, local network, and server work together | SC-005a |
| V10b | Performance (SC-005b, automated) | `pytest backend/tests/api/test_performance.py` | After one warm-up call, listing all 1,000 expenses and computing a monthly summary each finish in under 500 ms. Measures server work only, in process, with no browser or network | SC-005b |
| V11 | Interaction count | From the main screen with no form or dialog open, count interactions per FR-043 (one click, tap, or form submission; typing and choosing values inside an open form do not count) for add, edit, delete, filter, and set budget | Add 2, edit 2, delete 2, filter 1 per control, set budget 1; each at most 3 | FR-039, FR-043, SC-001 |
| V12 | Description handling | Add `<b>Tom & "Jerry's"</b>`; add a description with a tab or line break between words; add one made only of spaces | First is shown exactly as typed as plain text; second is shown with single spaces; third is rejected with "Description is required" | FR-042, US1 #23 to #26 |
| V13 | Amount strictly above zero | Try `0`, `0.00`, `-5`, then `0.01` | First three rejected; `0.01` saved. Automated `test_db_constraints.py` also confirms the database itself refuses `0` and negative cents | FR-007, FR-015, US1 #5, #6, #27 |
| V14 | Add expense timing (SC-001, manual) | From the main screen with nothing open, a person holding the values on a card (`450.00`, `Groceries`, Food, `2026-11-05`, Cash) starts a stopwatch at the first click on Add expense and stops it when the new expense is visible in the list; repeat 3 times, deleting the expense between attempts; an observer counts interactions per FR-043 | Every one of the 3 attempts is under 30 seconds, and the interaction count is 2 (never more than 3) | SC-001, FR-039 |
| V15 | Update timing (SC-004, manual) | Start the backend on the 50-expense seed database with `SPENDWISE_TODAY=2026-11-12` and a budget set for November 2026 (the month shown); for each of add, edit amount, and delete, perform 3 runs and measure from the click on Save or Confirm until the list and every affected figure (Total, expense count, category row, Remaining or the over-budget warning) show the new values, using the browser Performance panel or a frame-by-frame screen recording; do not refresh the page | Every one of the 9 runs is within 1 second, with no manual refresh | SC-004, FR-036 |

## SC-010 scripted walkthrough

SC-010 is a single scripted pass/fail walkthrough, not a usability study. It does not measure a
percentage of users and must not be reported as evidence of any usability percentage target.

Rules for a valid run:

- It is performed by someone other than the author of the code (or by an automated end-to-end UI
  test that drives the real UI against the real backend). A React Testing Library test that mocks
  the API is not an end-to-end test and does not satisfy SC-010.
- The reviewer uses only the README and the on-screen labels. Any help given is written down. A run
  in which help was needed is `FAILED`, not passed.
- Start from a clean, empty database and `SPENDWISE_TODAY=2026-11-12`, set up and confirmed as in
  "Clean start" below. The walkthrough must never run against a seeded database.
- Interactions are counted by an observer using FR-043 and written down per operation.

Clean start (PowerShell, from `Part-1A`, in the same terminal that starts the backend):

```powershell
# 1. Use the default database or a brand-new empty file, never a seeded one.
Remove-Item Env:SPENDWISE_DB_PATH -ErrorAction SilentlyContinue   # option A: unset, so the default backend\data\spendwise.db is used
# $env:SPENDWISE_DB_PATH = "backend\data\sc010-$(Get-Date -Format yyyyMMdd-HHmmss).db"   # option B: a new file that does not exist yet

# 2. Pin today's date.
$env:SPENDWISE_TODAY = "2026-11-12"

# 3. Confirm the setup; each check stops the script if it fails.
"SPENDWISE_DB_PATH = '$env:SPENDWISE_DB_PATH'   SPENDWISE_TODAY = '$env:SPENDWISE_TODAY'"
if ($env:SPENDWISE_TODAY -ne "2026-11-12") { throw "SPENDWISE_TODAY is not 2026-11-12" }
if ($env:SPENDWISE_DB_PATH -match "seed") { throw "A seeded database is selected" }
$db = if ($env:SPENDWISE_DB_PATH) { $env:SPENDWISE_DB_PATH } else { "backend\data\spendwise.db" }
if (Test-Path $db) { throw "$db already exists; rename it or use option B so the database starts empty" }
```

Then start the backend and the frontend. `Remove-Item Env:...` only unsets the variable in the
current terminal. Before step 1, confirm in the browser that the expense list is empty, the
dashboard shows Total `₹0.00` and 0 expenses, and no budget is set; if any of these is not true,
stop, because an old or seeded database is in use. Keep the confirmation output for
`harness-log.md`.

Steps and expected values:

- [ ] Add expense `450.00`, `Groceries`, Food, `2026-11-05`, Cash. It appears in the list.
- [ ] Set the November 2026 budget to `1000.00`. The page shows Spent `₹450.00`, Remaining
      `₹550.00`, no warning.
- [ ] Open the dashboard for November 2026. It shows Total `₹450.00`, Expenses this month `1`,
      Food `₹450.00`.

Record in `harness-log.md`: reviewer name and whether independent, date, steps passed or failed,
interactions counted per operation (add must be 2, set budget 1, open dashboard at most 1),
observed Total, count, Spent, and Remaining next to the expected values, any help given, and the
result. The three results are mutually exclusive:

- `PASSED`: completed without help by a qualifying performer, every interaction limit met, and every
  expected figure matched.
- `FAILED`: attempted by a qualifying performer, but one or more requirements were not met (a step
  failed, help was needed, an interaction limit was exceeded, or a figure did not match).
- `NOT DEMONSTRATED`: no independent performer or qualifying end-to-end test was available, so the
  walkthrough could not be evaluated.

An automated Playwright run of the same steps is an optional stretch goal (decision D-17).
