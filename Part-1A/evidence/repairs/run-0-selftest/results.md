# Harness results

Mode: self-test. Started 2026-11-19T05:11:26Z UTC, finished 2026-11-19T05:11:31Z UTC.

| Kind | PASS | FAIL | ERROR | NOT RUN |
|------|------|------|-------|---------|
| required | 1 | 1 | 1 | 1 |
| supplementary | 0 | 0 | 0 | 0 |

A supplementary result never offsets a required one.

| Check | Kind | Status | Exit code | Reason | Evidence files |
|-------|------|--------|-----------|--------|----------------|
| selftest-pass | required | PASS | 0 | 1 tests passed | selftest-pass.stdout.txt, selftest-pass.stderr.txt, selftest-pass.exitcode.txt, selftest-pass.meta.json |
| selftest-fail | required | FAIL | 1 | exit code 1 | selftest-fail.stdout.txt, selftest-fail.stderr.txt, selftest-fail.exitcode.txt, selftest-fail.meta.json |
| selftest-error | required | ERROR | n/a | the command could not be started: Exception calling "Start" with "1" argument(s): "The system cannot find the file specified" | selftest-error.stdout.txt, selftest-error.stderr.txt, selftest-error.exitcode.txt, selftest-error.meta.json |
| selftest-not-run | required | NOT RUN | n/a | precondition not met: synthetic subject that does not exist | selftest-not-run.stdout.txt, selftest-not-run.stderr.txt, selftest-not-run.exitcode.txt, selftest-not-run.meta.json |

Self-test: the four synthetic checks produced exactly PASS, FAIL, ERROR, and NOT RUN
