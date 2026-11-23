# SpendWise

A single-user personal expense tracker. Money is shown in Indian rupees (INR). The frontend is React, Vite, and TypeScript; the backend is FastAPI with SQLite.

All commands are for Windows PowerShell and are run from the repository root (`Part-1A`) unless stated otherwise. Detailed scenarios are in `specs/001-spendwise-expense-tracker/quickstart.md`.

## Prerequisites

- Python 3.12 or later
- Node.js 24 and Yarn 1.22 (classic). Check with `yarn --version`. The frontend package manager is Yarn and `yarn.lock` is committed.

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

## Configuration

The backend reads real environment variables only (no `.env` file and no dotenv package). `backend/.env.example` is a reference list of the variables; setting it up as `.env` has no effect. Set variables in the terminal that starts the backend, then restart the backend after changing them:

```powershell
$env:SPENDWISE_DB_PATH = "backend\data\spendwise.db"                         # optional, this is the default
$env:SPENDWISE_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"  # optional, this is the default
$env:SPENDWISE_TODAY = "2026-11-12"                                          # optional, demos and walkthroughs only

# Return a variable to its default:
Remove-Item Env:SPENDWISE_TODAY -ErrorAction SilentlyContinue
```

A relative `SPENDWISE_DB_PATH` is resolved against the repository root, not the folder the server is started from.

## Run

```powershell
# Terminal 1: backend on http://127.0.0.1:8000
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000

# Terminal 2: frontend on http://localhost:5173
cd frontend
yarn dev
```

The database file and tables are created automatically on the first start.

## Lint, security check, and tests

```powershell
ruff check backend                              # lint
ruff format --check backend                     # formatting
bandit -r backend/app -ll                       # security check
pytest backend                                  # backend tests
pytest backend --cov=app --cov-fail-under=80    # backend coverage

cd frontend
yarn build                                      # type check and production build
yarn lint
yarn test
cd ..
```

## Independent harness

The harness is separate from the application and its tests. It writes raw evidence for every check into a new, empty folder:

```powershell
.\harness\run-harness.ps1 -OutDir evidence\initial-generation   # first run, before any repair
.\harness\run-harness.ps1 -OutDir evidence\final-generation     # same checks, after repairs
.\harness\run-harness.ps1 -SelfTest -OutDir evidence\repairs\run-0-selftest   # proves the harness reports PASS, FAIL, ERROR, and NOT RUN correctly
```

Repository scans can also be run on their own:

```powershell
python harness\scan_repo.py float
python harness\scan_repo.py tracked-files
python harness\scan_repo.py secret-patterns
```

## Seed data (for manual checks)

```powershell
python backend/scripts/seed.py --count 50 --db backend\data\seed-50.db
python backend/scripts/seed.py --count 1000 --db backend\data\seed-1000.db
```

The seed script refuses to write to the default application database or to a non-empty file. To look at seeded data, start the backend against that file:

```powershell
$env:SPENDWISE_DB_PATH = "backend\data\seed-50.db"
$env:SPENDWISE_TODAY = "2026-11-12"   # so the dashboard opens on November 2026
uvicorn app.main:app --reload --app-dir backend --host 127.0.0.1 --port 8000
```

## Using the app

1. Open `http://localhost:5173`. The dashboard opens on the current month and shows total spent, the number of expenses this month, and the all-time number of expenses.
2. **Add an expense**: choose Add expense, fill in the amount, description, category, payment method, and date, then choose Save. Amounts can have at most two decimal places and are never rounded.
3. **Set a budget**: pick the month in the Dashboard, type the amount in Budget, and choose Save budget. Spent and Remaining update straight away, and a warning states the amount by which the budget is exceeded.
4. **Look at a month**: change Month in the Dashboard. The category breakdown lists only categories with spending.
5. **Filter the list**: use Filter by month and Filter by category above the expense list; Clear filters shows everything again.

## Reading `evidence/`

`evidence/` holds the raw output of the independent harness and is written only by the harness runner or by the person operating it. `initial-generation/` is the first run, `final-generation/` the run after repairs, `repairs/` holds run 0 and one folder per repair round, and `snapshots/` holds copies of the source tree. In a run folder, `results.md` is the summary (each check is `PASS`, `FAIL`, `ERROR`, or `NOT RUN`), `<check>.stdout.txt`, `<check>.stderr.txt`, `<check>.exitcode.txt`, and `<check>.meta.json` are the raw record of each check, and `api-results.json` lists each black-box case with its expected and observed values. `harness-log.md` explains every run, failure, repair, and decision. See `evidence/README.md` for details.
