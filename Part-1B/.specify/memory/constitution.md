# Reminder Agent Constitution

## Core Principles

### I. Minimal Scope
- The agent supports exactly three intents: `CREATE`, `RESCHEDULE`, `CLARIFY`. No other intent may be added.
- The following are out of scope and MUST NOT be built: authentication, notifications or scheduling
  of real alerts, databases or persistence, calendar integration, multiple agents, and any
  feature not required by the current specification.
- The frontend is a minimal React page: one text input, one submit action, and a display of the
  returned structured result plus loading and error states.

### II. Single LLM Call, Strict Schema
- Each user request MUST result in exactly one LLM call (Gemini). No retries that issue a second
  call, no chains, no tool loops.
- The LLM output MUST be parsed into one Pydantic model with `extra="forbid"`. Output that fails
  validation MUST be returned as a typed error, never repaired or guessed. The single permitted
  exception is the past-time guard: a CREATE or RESCHEDULE whose datetime is earlier than the
  supplied current time MUST be replaced with a CLARIFY asking for a future time, and the
  replacement MUST be recorded in evaluation reports.
- The schema MUST enforce cross-field invariants: `CREATE` requires a title and a datetime;
  `RESCHEDULE` requires a reference to the existing reminder and a new datetime; `CLARIFY`
  requires a question and MUST NOT carry a datetime.
- Datetimes MUST be ISO 8601. The "current date/time" used to resolve relative expressions MUST be
  passed in as an input, never read implicitly inside the schema or evaluators.

### III. Clarify, Never Invent
- If a required value is missing or ambiguous (e.g. no time, "later", "next week" with no day,
  unspecified reminder to reschedule), the agent MUST return `CLARIFY` with a question.
- The agent MUST NOT fabricate titles, dates, times, or reminder references.

### IV. Evaluation Is Mandatory and Honest
- The evaluation set MUST contain at least 15 meaningful cases covering all three intents,
  including missing-information and ambiguous inputs.
- All three layers MUST be implemented and reported separately:
  1. Structural: output parses against the Pydantic schema.
  2. Property/invariant: intent-specific rules hold (see Principle II), no invented fields,
     datetimes are valid ISO 8601 and not in the past relative to the supplied current time.
  3. Semantic: the intent and extracted values match the expected values in the case file.
- Results MUST be recorded exactly as produced by real runs. Results, scores, and evidence MUST NOT
  be invented, edited by hand, or back-filled. Failures MUST be reported as failures.
- Each run stores raw outputs, exit codes, and a SHA-256 manifest under `evidence/`.

### V. Security and Secrets
- The Gemini API key MUST be read from the `GEMINI_API_KEY` environment variable (or a git-ignored
  `.env`). It MUST NOT appear in source, specs, logs, evidence, or commits.
- An evidence/secret scan MUST pass before a run is considered final.
- User text is untrusted: it MUST be length-limited and treated as data in the prompt, and the
  model output MUST NOT be executed or rendered as HTML.

### VI. Simplicity of Stack
- Backend: Python, FastAPI, Pydantic, pytest, ruff. Frontend: React, TypeScript, Vite, Yarn.
- Unit tests MUST run without network access by using a stubbed LLM client. Real-LLM evaluation is
  run separately by the harness.

## Quality Gates
- G1 `ruff check` passes. G2 backend tests pass. G3 frontend lint and build pass.
- G4 evaluation harness runs all cases through all three layers and records actual results.
- G5 secret scan passes.

## Governance
This constitution governs the Part-1B project only and does not apply to Part-1A. Amendments
require updating this file with a version bump.

**Version**: 1.1.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
