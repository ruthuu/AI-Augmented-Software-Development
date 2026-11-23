# Natural-Language Reminder Agent (BITS SEZG534, Part 1B)

A small agent that turns one natural-language reminder request into a structured result with one of three intents: `CREATE`, `RESCHEDULE` or `CLARIFY`. If required information is missing or ambiguous it returns `CLARIFY` with a question instead of guessing.

- Backend: FastAPI + Pydantic (strict schema). One Gemini call per request, no retries.
- Frontend: one React + Vite page.
- Evaluation: 33 cases, three layers (structural, property/invariant, semantic), JSON results and a hashed evidence folder per run.
- Spec Kit artifacts: `.specify/memory/constitution.md`, `specs/001-nl-reminder-agent/` (`spec.md`, `plan.md`, `tasks.md`).
- Repository: `https://github.com/ruthuu/AI-Augmented-Software-Development`

## Important limitation: nothing is saved or rescheduled

There is no reminder database, scheduler, notification, calendar or login. The agent only **interprets** text. A `CREATE` result does not create a reminder. A `RESCHEDULE` result does **not** update any reminder: the "reminder to reschedule" is only the user's own words from that request and is never checked against anything. Every API response carries `persisted: false` and a note saying so, and the page shows "NOT SAVED (persisted: false)".

## Setup

Requires Python 3.12, Node.js and Yarn.

```powershell
cd assignment-1\Part-1B
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
cd frontend; yarn install; cd ..
```

Create `backend\.env` (git-ignored; `backend\.env.example` is the template):

```
GEMINI_API_KEY=<your key>
GEMINI_MODEL=gemini-3.5-flash-lite
```

The key is read only from the environment. Never commit `.env`, and never paste a key into source, logs or evidence.

## Run the application

```powershell
# terminal 1: backend on http://127.0.0.1:8000
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# terminal 2: frontend on http://127.0.0.1:5173 (proxies /api to the backend)
cd frontend; yarn dev --host 127.0.0.1 --port 5173
```

API contract:

- `GET /api/health` returns `{"status":"ok"}`.
- `POST /api/interpret` with `{"text": "...", "now": "<ISO 8601 with UTC offset>"}` returns `{"result": {intent, title, reminder_reference, scheduled_at, clarification}, "persisted": false, "note": "..."}`.
- Errors use `{"error": {"code", "message"}}`: `422 invalid_request`, `502 llm_unavailable`, `502 llm_invalid_output`. Messages never include the key or the model's raw text.
- A request that resolves to a past date and time returns a normal 200 `CLARIFY` (past-time guard), not an error.

## Tests and quality gates

| Gate | Command (from `Part-1B`) |
|---|---|
| G1 | `.\.venv\Scripts\python.exe -m ruff check backend harness` |
| G2 | `.\.venv\Scripts\python.exe -m pytest backend/tests` and `.\.venv\Scripts\python.exe -m pytest harness/tests` (mock or synthetic data only, no network) |
| G3 | `cd frontend; yarn lint; yarn build` (the frontend has no automated tests) |
| G4 | `.\.venv\Scripts\python.exe harness\run_eval.py` (calls Gemini) |
| G5 | `.\.venv\Scripts\python.exe harness\scan_secrets.py` |

`harness\run-harness.ps1` runs G1 to G5, stores each command's output and exit code under `evidence\run-<UTC>\gates\`, and verifies the manifest. Use `-SkipEvaluation` to skip the Gemini calls. `harness\run_eval.py --check-cases` validates the case file without calling Gemini; `--verify-manifest <dir>` re-checks an evidence folder's hashes.

## Evaluation layers

Each of the 33 cases in `harness/cases/cases.json` has a fixed `now` (2026-11-23T10:00:00+05:30), expected values written from the spec before any model run, deterministic properties and a rubric.

1. **Structural**: the raw model reply parses as JSON and validates against the strict `AgentResult` schema (known fields only, valid intent, correct types and nullability). Judged before the past-time guard.
2. **Property/invariant**: checks on the final result that need no expected answer: per-intent field rules, ISO 8601 with offset, `scheduled_at` not earlier than `now`, exactly one LLM call (counted independently of the agent), guard consistency, plus per-case properties (for example `scheduled_at_null`, `title_excludes_forbidden_terms`).
3. **Semantic**: the final result matches the case's expectation: same intent; all keywords present and `scheduled_at` within tolerance for CREATE/RESCHEDULE; at least one expected keyword in the question for CLARIFY. A case that expects CLARIFY but gets CREATE/RESCHEDULE is counted as "invented details". Scoring is deterministic; no LLM judge is used.

Overall PASS requires: all cases executed (spec SC-002), structural pass rate 1.0 (SC-003), property pass rate 1.0 (SC-004), zero invented-detail cases (SC-005), and a semantic pass rate of at least 0.9. The spec sets no semantic threshold; 0.9 was declared by the harness before the first run.

## Evidence and results

Every real run is kept in `evidence/run-<UTC>/` (`results.json`, `raw/<case>.txt`, `gates/`, `manifest.sha256.txt`). `harness-log.md` records configuration, each run's result, failures, repairs and limitations. The table repeats numbers from each run's `results.json`.

| Run | structural | property | semantic | verdict |
|---|---|---|---|---|
| `run-20261123T081644Z` | 33/33 | 32/33 | 32/33 | FAIL (TC-14 invented a date) |
| `run-20261123T082259Z` | 33/33 | 32/33 | 32/33 | FAIL (TC-15 invented a time) |
| `run-20261123T082957Z` | 33/33 | 33/33 | 33/33 | PASS |
| `run-20261123T083731Z` (latest) | 32/33 | 32/33 | 32/33 | FAIL (one provider `ServerError`, TC-08) |

How to read this: the second and third runs followed two prompt changes made after seeing failures on the same 33 cases, so the PASS is not a held-out result. The latest run used the same prompt and failed only because Gemini returned a server error for one call, which the agent does not retry. Results are reported per run and not merged.

## Limitations

- No persistence: nothing is created, stored, scheduled or updated (see above).
- A reschedule reference is free text and cannot be checked against any existing reminder.
- One model (`gemini-3.5-flash-lite`), English only, one request at a time; model output varies between runs and provider errors can occur.
- The past-time guard never fired in the real runs (0 cases each time); it is verified by unit tests only.
- Semantic scoring uses keyword lists, so an unusual but good clarification question could be marked wrong; the case rubrics state the intended meaning.
- The TC-14 expectation ("at 5pm" with no day is CLARIFY) follows the spec's stricter reading; many users would read it as "today".
- The loading state of the page was not observed by eye (calls were too fast); the error state was.
- The frontend has no automated tests.
- Prompt-injection resistance is evaluated on two cases, not proven.

## Demo sequence

1. Start the backend and frontend (see above) and open `http://127.0.0.1:5173`.
2. CREATE: `Remind me to call mom tomorrow at 6pm`. Show the intent, title, date and time, and the "NOT SAVED (persisted: false)" notice.
3. RESCHEDULE: `Move my dentist reminder to Friday at 4pm`. Point out that the reminder is only named in the user's words and that nothing is updated.
4. CLARIFY: `Remind me to call the bank`. Show the question and that no time was invented.
5. Show the harness: `harness\run-harness.ps1` (or open the latest `evidence\run-*\results.json` and `harness-log.md`) and explain the three layers and the PASS/FAIL rule.
6. State the limitation: reminders are not persisted.

Record and upload the demo yourself; this repository does not contain a recording.
