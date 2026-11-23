# Harness results

Mode: full. Started 2026-11-21T07:04:41Z UTC, finished 2026-11-21T07:07:43Z UTC.

| Kind | PASS | FAIL | ERROR | NOT RUN |
|------|------|------|-------|---------|
| required | 13 | 1 | 0 | 0 |
| supplementary | 1 | 1 | 0 | 0 |

A supplementary result never offsets a required one.

| Check | Kind | Status | Exit code | Reason | Evidence files |
|-------|------|--------|-----------|--------|----------------|
| G1-ruff-check | required | PASS | 0 | exit code 0 | G1-ruff-check.stdout.txt, G1-ruff-check.stderr.txt, G1-ruff-check.exitcode.txt, G1-ruff-check.meta.json |
| G2-ruff-format | required | PASS | 0 | exit code 0 | G2-ruff-format.stdout.txt, G2-ruff-format.stderr.txt, G2-ruff-format.exitcode.txt, G2-ruff-format.meta.json |
| G3-bandit | required | PASS | 0 | exit code 0 | G3-bandit.stdout.txt, G3-bandit.stderr.txt, G3-bandit.exitcode.txt, G3-bandit.meta.json |
| G4-pytest | required | PASS | 0 | 430 tests passed | G4-pytest.stdout.txt, G4-pytest.stderr.txt, G4-pytest.exitcode.txt, G4-pytest.meta.json |
| G5-coverage | required | PASS | 0 | 430 tests passed and a coverage percentage was reported | G5-coverage.stdout.txt, G5-coverage.stderr.txt, G5-coverage.exitcode.txt, G5-coverage.meta.json |
| G6-core-services-coverage | required | PASS | 0 | coverage percentage reported and threshold met | G6-core-services-coverage.stdout.txt, G6-core-services-coverage.stderr.txt, G6-core-services-coverage.exitcode.txt, G6-core-services-coverage.meta.json |
| G7-float-scan | required | PASS | 0 | 13 files scanned, no findings | G7-float-scan.stdout.txt, G7-float-scan.stderr.txt, G7-float-scan.exitcode.txt, G7-float-scan.meta.json |
| G9-tracked-files | required | PASS | 0 | no tracked .env or *.db file | G9-tracked-files.stdout.txt, G9-tracked-files.stderr.txt, G9-tracked-files.exitcode.txt, G9-tracked-files.meta.json |
| G9-secret-patterns | supplementary | FAIL | 1 | the scan reported findings (file, line, and rule only; see stdout) | G9-secret-patterns.stdout.txt, G9-secret-patterns.stderr.txt, G9-secret-patterns.exitcode.txt, G9-secret-patterns.meta.json |
| G8-yarn-build | required | PASS | 0 | exit code 0 | G8-yarn-build.stdout.txt, G8-yarn-build.stderr.txt, G8-yarn-build.exitcode.txt, G8-yarn-build.meta.json |
| FE-yarn-lint | required | PASS | 0 | exit code 0 | FE-yarn-lint.stdout.txt, FE-yarn-lint.stderr.txt, FE-yarn-lint.exitcode.txt, FE-yarn-lint.meta.json |
| FE-yarn-test | required | FAIL | 1 | exit code 1 | FE-yarn-test.stdout.txt, FE-yarn-test.stderr.txt, FE-yarn-test.exitcode.txt, FE-yarn-test.meta.json |
| API-write | required | PASS | 0 | 242 cases compared and all matched | API-write.stdout.txt, API-write.stderr.txt, API-write.exitcode.txt, API-write.meta.json |
| API-verify | required | PASS | 0 | 25 cases compared and all matched | API-verify.stdout.txt, API-verify.stderr.txt, API-verify.exitcode.txt, API-verify.meta.json |
| API-timing | supplementary | PASS | 0 | 1 cases compared and all matched | API-timing.stdout.txt, API-timing.stderr.txt, API-timing.exitcode.txt, API-timing.meta.json |
| evidence-secret-scan | required | PASS | 0 | 68 files scanned, no findings | evidence-secret-scan.stdout.txt, evidence-secret-scan.stderr.txt, evidence-secret-scan.exitcode.txt, evidence-secret-scan.meta.json |
