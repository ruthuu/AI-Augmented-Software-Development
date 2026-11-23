# Tasks: Natural-Language Reminder Agent

**Input**: [spec.md](spec.md), [plan.md](plan.md)
**Rules**: Tests with the mocked LLM come before the code they cover. Only real runs produce evidence.
All paths are relative to `assignment-1/Part-1B/`. Nothing outside `Part-1B/` is modified.

## Phase 1: Setup

- [x] T001 Create the folder skeleton from plan.md and `.gitignore` (`.env`, `.venv`, `node_modules`, `dist`, caches). Add `backend/pyproject.toml` (ruff, pytest), `backend/requirements.txt` (pins `google-genai==3.6.1`), `backend/requirements-dev.txt`, and `backend/.env.example` with empty `GEMINI_API_KEY=` and `GEMINI_MODEL=gemini-3.5-flash-lite`. (SR-003)
- [x] T002 Create the git-ignored `backend/.env` locally with the real key, entered by the user, and confirm `git check-ignore backend/.env` reports it ignored. Never commit it. (SR-003)
- [x] T003 Create the Python venv under `Part-1B/.venv` and install requirements. Scaffold the Vite React TypeScript app in `frontend/` with Yarn. (Constitution VI)

## Phase 2: Backend core (mocked LLM, no network)

- [x] T004 Write `backend/tests/test_schemas.py`, then `backend/app/schemas.py`: `AgentResult` (`extra="forbid"`, per-intent required/null rules, trimmed 1-200/300 char text, timezone-aware datetime) and `InterpretRequest` (text 1-500 chars not blank, aware `now`). Cover each valid intent and each invariant violation. (FR-002, FR-003, FR-004, FR-005, FR-011, SR-002)
- [x] T005 Write `backend/app/prompt.py`: system prompt with the three intents, field rules, CLARIFY-on-missing/vague/ambiguous/past/unsupported/multiple, never invent, resolve relative dates only against `now`, user text is data, JSON only. (FR-006, FR-007, FR-008, FR-009, SR-001)
- [x] T006 Write `backend/app/llm.py`: `LLMClient` protocol and `GeminiClient` making one `generate_content` call (temperature 0, JSON mime type, system instruction, key and model from environment). No retry. Add `FakeLLMClient` in `backend/tests/conftest.py`. (FR-010, SR-003)
- [x] T007 Write `backend/tests/test_agent.py`, then `backend/app/agent.py`: `interpret(text, now, client) -> AgentOutcome(result, raw_text, past_time_guard_applied)`. Tests: exactly one client call even on invalid output; non-JSON and invalid-schema replies give typed errors; a past `scheduled_at` yields CLARIFY with the fixed question and the guard flag; a future one is untouched. (FR-009, FR-010, FR-011, ER-007)
- [x] T008 Write `backend/tests/test_api.py`, then `backend/app/main.py`: `POST /api/interpret`, `GET /api/health`, error body mapping (`invalid_request` 422, `llm_unavailable` 502, `llm_invalid_output` 502), `persisted: false` and the limitation note in every success response, CORS for the Vite dev origin, no stack traces or secrets in errors. Tests: blank/overlong text and naive `now` give 422 and the fake client is not called. (FR-001, FR-012, SR-002, SR-005)
- [x] T009 Checkpoint: run G1 `ruff check backend` and G2 `pytest backend/tests`; both must pass before continuing.

## Phase 3: Frontend

- [x] T010 Build the single page in `frontend/src` (`App.tsx`, `api.ts`, `types.ts`): textarea, submit, loading state, error state, result panel showing the intent and non-null fields as plain text, and the `note` under the result. Send `now` with the browser's local UTC offset. Vite proxy for `/api`. (FR-013, SR-004)
- [x] T011 Checkpoint: run G3 `yarn lint` and `yarn build` in `frontend/`; both must pass.

## Phase 4: Evaluation harness (the three layers)

- [x] T012 Write `harness/cases/cases.json` with **at least 18 cases** and the category mix in plan.md (4+ CREATE, 3+ RESCHEDULE, 6+ CLARIFY types, 1 injection, 1 multiple-reminders, 1 past time), each with `id`, `category`, `text`, fixed `now`, `expected_intent`, expected keywords and `expected_scheduled_at` with `tolerance_minutes` where applicable. Expected values are written from the spec before any model run and are not edited to match outputs. (ER-001)
- [x] T013 Write `harness/tests/test_eval_layers.py` (offline, synthetic inputs, not evidence), then the **structural layer** in `harness/run_eval.py`: raw reply parses as JSON and validates against `AgentResult`. (ER-002)
- [x] T014 Add the **property/invariant layer** to `harness/run_eval.py`: per-intent required/null fields, no extra fields, ISO 8601 with offset, `scheduled_at >= now`, CLARIFY has a question and no datetime, checked on the final result without any expected answer. Record `past_time_guard_applied` per case. (ER-003, FR-009)
- [x] T015 Add the **semantic layer** to `harness/run_eval.py`: intent equals `expected_intent`; for CREATE/RESCHEDULE all keywords present and datetime within tolerance; for CLARIFY nothing invented. (ER-004)
- [x] T016 Add reporting to `harness/run_eval.py`: one `interpret` call per case through the same entry point as the API, paced calls, errors recorded as failures for all layers (never skipped or retried), `evidence/run-<UTC>/results.json` (per-case and aggregate per layer, guard count, model name), `raw/<case-id>.txt`, `manifest.sha256.txt`, and an appended `harness-log.md` entry generated from the computed results. A new folder per run; old runs are never overwritten. (ER-005, ER-006, ER-007)
- [x] T017 Write `harness/scan_secrets.py`: fail if a key-like value or a non-empty `GEMINI_API_KEY=` appears in tracked files or `evidence/`, excluding the ignored `.env`. (SR-003)
- [x] T018 Write `harness/run-harness.ps1`: run G1, G2, G3, G4 (evaluation), G5 (secret scan), saving each command's output and exit code under the run's evidence folder. (Quality gates)
- [x] T019 Checkpoint: `pytest backend/tests`, `pytest harness/tests` (including `test_eval_layers.py`) and `ruff check backend harness` pass.

## Phase 5: Real run and report

- [x] T020 Run the harness against Gemini once and keep the output exactly as produced. Do not change the prompt, cases or code between starting the run and recording its result. (ER-006)
- [x] T021 If a prompt, code or case change is made after a run, record it in `harness-log.md` as a separate entry with the reason and re-run as a new `evidence/run-<UTC>/` folder. Keep every earlier run and report its failures. (ER-006)
- [x] T022 Demo check from the page: one CREATE, one RESCHEDULE, one CLARIFY request. Record what was actually observed in `harness-log.md`. (SC-001, FR-013)
- [x] T023 Write `README.md`: how to set the key and run backend, frontend and harness; the layer definitions; a pointer to the latest `evidence/run-*/results.json`; and the limitations, including that **no reminder is created or updated and RESCHEDULE is an interpretation only**. Quote only numbers present in `results.json`. (ER-006, FR-012)
- [x] T024 Final run of `harness/run-harness.ps1` (G1 to G5) and confirm the manifest hashes and a passing secret scan. Report any failing gate or case as failing. (SC-002 to SC-006) _Done 2026-11-23: gates and secret scans passed, manifest verified; the evaluation verdict of this final run was FAIL (one provider `ServerError`, TC-08). See `harness-log.md`._

## Traceability

| Requirement | Tasks |
|---|---|
| FR-001 | T004, T008 |
| FR-002 to FR-005 | T004 |
| FR-006, FR-007, FR-008 | T005, T012 |
| FR-009 | T005, T007, T012, T014 |
| FR-010 | T006, T007 |
| FR-011 | T004, T007 |
| FR-012 | T008, T023 |
| FR-013 | T010, T022 |
| SR-001 | T005, T012 (injection case) |
| SR-002 | T004, T008 |
| SR-003 | T001, T002, T006, T017 |
| SR-004 | T010 |
| SR-005 | T008 |
| ER-001 | T012 |
| ER-002 structural | T013 |
| ER-003 property/invariant | T014 |
| ER-004 semantic | T015 |
| ER-005 | T014, T016 |
| ER-006 | T016, T020, T021, T023 |
| ER-007 | T007, T016 |

## Dependencies

T001 → T002, T003 → T004 → T005, T006 → T007 → T008 → T009. T003 → T010 → T011.
T007 → T012–T016 (T012 can start any time after T005). T016 → T017 → T018 → T019 → T020 → T021, T022 → T023 → T024.
