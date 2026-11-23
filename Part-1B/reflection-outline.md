# Reflection report outline (facts for the author to build on)

This outline lists what actually happened in the project, with pointers to evidence. It contains no first-person reflection. The final reflection, its wording and any claim about personal experience, judgement or approval must be written by the author.

## 1. Scope and approach
- Assignment part: Part 1B, a Natural-Language Reminder Agent with three intents (`CREATE`, `RESCHEDULE`, `CLARIFY`); no auth, notifications, database, calendar or multiple agents.
- Workflow: Spec Kit (`specify init`), then constitution, spec, plan, tasks, implementation (`.specify/memory/constitution.md`, `specs/001-nl-reminder-agent/`).
- Stack reused from Part-1A: FastAPI, Pydantic, pytest, ruff, React + Vite + Yarn, PowerShell harness, hashed evidence folders, `harness-log.md`. Part-1A was not modified.
- Tasks were completed in order T001 to T024 (`tasks.md`); tests were written before the code they cover.

## 2. Key design decisions (with the reason recorded in the spec/plan)
- One Gemini call per request, no retries (FR-010); temperature 0, JSON mode; strict Pydantic schema with `extra="forbid"` and per-intent field rules, validated locally.
- `CLARIFY` instead of guessing for missing, vague, ambiguous, past, unsupported and multiple-reminder requests.
- Past times: a normal `CLARIFY` through a past-time guard, not an error (a change requested during planning; the constitution was amended to v1.1.0).
- No reminder store: `RESCHEDULE` is interpretation only; responses carry `persisted: false` and the UI says "NOT SAVED".
- Model choice: `gemini-3.5-flash-lite`, chosen after listing the models available to the key and making one compatibility call (plan.md, "Verified Gemini model").
- Evaluation: three layers, 33 cases written from the spec before any model run, deterministic scoring, per-run evidence with SHA-256 manifest.

## 3. Defects found and fixed (from the project record)
- Schema accepted Unix timestamps (`1700000000`, `"1700000000"`) as datetimes. Found by a new test during T013; fixed with an ISO-8601-only datetime type; 7 tests added.
- Run 1: `TC-14-missing-date` ("at 5pm") was answered with CREATE (assumed today). Prompt repair 1.
- Run 2: `TC-15-missing-time-of-day` ("on Friday") was answered with CREATE (assumed 09:00). Prompt repair 2.
- Details: `harness-log.md` (manual entries), raw replies in `evidence/run-*/raw/`.

## 4. Results (copy numbers only from `evidence/run-*/results.json`)
| Run | structural | property | semantic | verdict |
|---|---|---|---|---|
| run-20261123T081644Z | 33/33 | 32/33 | 32/33 | FAIL |
| run-20261123T082259Z | 33/33 | 32/33 | 32/33 | FAIL |
| run-20261123T082957Z | 33/33 | 33/33 | 33/33 | PASS |
| run-20261123T083731Z | 32/33 | 32/33 | 32/33 | FAIL (provider `ServerError` on TC-08) |

Offline checks at the last run: ruff clean; backend 111 tests and harness 155 tests passed; frontend lint and build exit 0; secret scans clean.

## 5. Honest caveats to carry into the report
- The only PASS followed two prompt changes made on the same 33 cases (not held out).
- Output varies between runs; the latest run failed because of a provider error that the one-call rule does not retry.
- The semantic threshold (0.9) is declared by the harness; the spec sets none.
- The past-time guard never fired in real runs; it is covered by unit tests only.
- Keyword-based semantic scoring; two injection cases; English only; no frontend automated tests; loading state not seen by eye.

## 6. AI-assisted workflow: material to discuss (author to complete)
- Where the assistant's output was checked or corrected, with evidence: the schema leniency above; tests failing first (red) before each implementation step; the key never stored in source (secret scan: `harness/scan_secrets.py`).
- What was decided by the author versus proposed by the assistant: [author to write].
- What the author would change next (for example a held-out case set, a retry policy for provider errors, a persistence layer): [author to write].

## 7. Items only the author can supply
- Reflection text and any statements about personal learning or effort.
- The recorded demo and its link; the public GitHub URL in `README.md`.
- Any instructor or reviewer feedback and approvals.
