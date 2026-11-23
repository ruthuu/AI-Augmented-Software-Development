# Harness results

Mode: full. Started 2026-11-19T05:10:56Z UTC, finished 2026-11-19T05:11:05Z UTC.

| Kind | PASS | FAIL | ERROR | NOT RUN |
|------|------|------|-------|---------|
| required | 2 | 0 | 0 | 12 |
| supplementary | 0 | 0 | 0 | 2 |

A supplementary result never offsets a required one.

| Check | Kind | Status | Exit code | Reason | Evidence files |
|-------|------|--------|-----------|--------|----------------|
| G1-ruff-check | required | NOT RUN | n/a | precondition not met: no SpendWise Python source under backend/app (only empty __init__.py files) | G1-ruff-check.stdout.txt, G1-ruff-check.stderr.txt, G1-ruff-check.exitcode.txt, G1-ruff-check.meta.json |
| G2-ruff-format | required | NOT RUN | n/a | precondition not met: no SpendWise Python source under backend/app (only empty __init__.py files) | G2-ruff-format.stdout.txt, G2-ruff-format.stderr.txt, G2-ruff-format.exitcode.txt, G2-ruff-format.meta.json |
| G3-bandit | required | NOT RUN | n/a | precondition not met: no SpendWise Python source under backend/app (only empty __init__.py files) | G3-bandit.stdout.txt, G3-bandit.stderr.txt, G3-bandit.exitcode.txt, G3-bandit.meta.json |
| G4-pytest | required | NOT RUN | n/a | precondition not met: no test_*.py under backend/tests | G4-pytest.stdout.txt, G4-pytest.stderr.txt, G4-pytest.exitcode.txt, G4-pytest.meta.json |
| G5-coverage | required | NOT RUN | n/a | precondition not met: no test_*.py under backend/tests | G5-coverage.stdout.txt, G5-coverage.stderr.txt, G5-coverage.exitcode.txt, G5-coverage.meta.json |
| G6-core-services-coverage | required | NOT RUN | n/a | precondition not met: G5 did not run, so there is no coverage data | G6-core-services-coverage.stdout.txt, G6-core-services-coverage.stderr.txt, G6-core-services-coverage.exitcode.txt, G6-core-services-coverage.meta.json |
| G7-float-scan | required | NOT RUN | 3 | nothing to scan (zero files examined) | G7-float-scan.stdout.txt, G7-float-scan.stderr.txt, G7-float-scan.exitcode.txt, G7-float-scan.meta.json |
| G9-tracked-files | required | PASS | 0 | no tracked .env or *.db file | G9-tracked-files.stdout.txt, G9-tracked-files.stderr.txt, G9-tracked-files.exitcode.txt, G9-tracked-files.meta.json |
| G9-secret-patterns | supplementary | NOT RUN | n/a | precondition not met: no SpendWise application files exist yet to scan | G9-secret-patterns.stdout.txt, G9-secret-patterns.stderr.txt, G9-secret-patterns.exitcode.txt, G9-secret-patterns.meta.json |
| G8-yarn-build | required | NOT RUN | n/a | precondition not met: frontend/src/api/client.ts does not exist (the stock Vite template alone does not count) | G8-yarn-build.stdout.txt, G8-yarn-build.stderr.txt, G8-yarn-build.exitcode.txt, G8-yarn-build.meta.json |
| FE-yarn-lint | required | NOT RUN | n/a | precondition not met: frontend/src/api/client.ts does not exist (the stock Vite template alone does not count) | FE-yarn-lint.stdout.txt, FE-yarn-lint.stderr.txt, FE-yarn-lint.exitcode.txt, FE-yarn-lint.meta.json |
| FE-yarn-test | required | NOT RUN | n/a | precondition not met: frontend/src/api/client.ts does not exist (the stock Vite template alone does not count) | FE-yarn-test.stdout.txt, FE-yarn-test.stderr.txt, FE-yarn-test.exitcode.txt, FE-yarn-test.meta.json |
| API-write | required | NOT RUN | n/a | precondition not met: backend/app/main.py does not exist | API-write.stdout.txt, API-write.stderr.txt, API-write.exitcode.txt, API-write.meta.json |
| API-verify | required | NOT RUN | n/a | precondition not met: backend/app/main.py does not exist | API-verify.stdout.txt, API-verify.stderr.txt, API-verify.exitcode.txt, API-verify.meta.json |
| API-timing | supplementary | NOT RUN | n/a | precondition not met: backend/app/main.py does not exist | API-timing.stdout.txt, API-timing.stderr.txt, API-timing.exitcode.txt, API-timing.meta.json |
| evidence-secret-scan | required | PASS | 0 | 63 files scanned, no findings | evidence-secret-scan.stdout.txt, evidence-secret-scan.stderr.txt, evidence-secret-scan.exitcode.txt, evidence-secret-scan.meta.json |
