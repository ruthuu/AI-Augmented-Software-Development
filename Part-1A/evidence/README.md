# Evidence folders

Raw output of the independent harness (`harness/run-harness.ps1`). Evidence is written only by the harness runner or by the human running the named commands, never by the coding agent. Initial evidence is never overwritten or deleted.

| Folder | What it holds |
|--------|---------------|
| `initial-generation/` | The first complete harness run on the first complete generation of the application, before any repair. |
| `repairs/` | Run 0 (`run-0-selftest`, `run-0-baseline`) and one folder per repair round (prompt, summary, change list, diff, and the rerun results). |
| `snapshots/` | Copies of the source tree at the generation freeze and after each repair, so changes can be compared without a Git commit. |
| `final-generation/` | The same checks run again after the repairs. |

Files in a run folder, per check `<check>`: `<check>.stdout.txt`, `<check>.stderr.txt`, `<check>.exitcode.txt`, `<check>.meta.json` (command, start, end, status). Per run: `results.json`, `results.md`, `api-results.json` (each black-box case with expected and observed values), `environment.txt` (tool versions only), `manifest.sha256.txt`, `git-state.txt`.

A check status is exactly `PASS`, `FAIL`, `ERROR`, or `NOT RUN`; see `harness-log.md` for the rules. A run folder is marked read-only after its run. Snapshots, manifests, diffs, and run folders never include `.env` files, `*.log` files, `*.db` files, `node_modules`, `dist`, `.venv`, `__pycache__`, `.pytest_cache`, or coverage output.
