"""T062 (seed script): deterministic data, path safety, and the documented commands."""

import hashlib
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.constants import CATEGORIES, PAYMENT_METHODS
from app.services import validation
from scripts import seed

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRST_DAY = date(2026, 9, 1)
LAST_DAY = date(2026, 11, 12)

Row = tuple[object, ...]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_of(db: Path) -> list[Row]:
    connection = sqlite3.connect(db)
    try:
        return connection.execute(
            "SELECT id, amount_cents, description, category, payment_method, expense_date,"
            " created_at, updated_at FROM expenses ORDER BY id"
        ).fetchall()
    finally:
        connection.close()


def run_in_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *args: str
) -> tuple[int, Settings]:
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env({}, tmp_path)
    return seed.main(list(args), settings), settings


def test_importing_the_module_has_no_side_effects(tmp_path: Path) -> None:
    assert callable(seed.main)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("count", [7, 50, 1000])
def test_creates_exactly_the_requested_number_of_expenses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    db = tmp_path / "out" / "seed.db"
    code, _ = run_in_process(tmp_path, monkeypatch, "--count", str(count), "--db", str(db))
    assert code == 0
    assert len(rows_of(db)) == count


def test_the_50_expense_dataset_covers_all_categories_and_the_three_months(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "seed.db"
    run_in_process(tmp_path, monkeypatch, "--count", "50", "--db", str(db))
    rows = rows_of(db)
    assert {r[3] for r in rows} == set(CATEGORIES)
    assert {str(r[5])[:7] for r in rows} == {"2026-09", "2026-10", "2026-11"}
    assert max(str(r[5]) for r in rows) <= "2026-11-12"
    assert min(str(r[5]) for r in rows) >= "2026-09-01"


def test_two_runs_give_identical_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    first, second = tmp_path / "a.db", tmp_path / "b.db"
    run_in_process(tmp_path, monkeypatch, "--count", "50", "--db", str(first))
    run_in_process(tmp_path, monkeypatch, "--count", "50", "--db", str(second))
    assert rows_of(first) == rows_of(second)


def test_every_generated_row_satisfies_the_validation_rules() -> None:
    for expense in seed.generate(1000):
        assert validation.parse_amount(expense.amount_text) == expense.amount_cents
        assert validation.clean_description(expense.description) == expense.description
        assert validation.validate_category(expense.category) == expense.category
        assert validation.validate_payment_method(expense.payment_method) == expense.payment_method
        validation.check_date_range(expense.expense_date, LAST_DAY)
        assert FIRST_DAY <= expense.expense_date <= LAST_DAY
        assert expense.category in CATEGORIES and expense.payment_method in PAYMENT_METHODS


def test_the_database_has_the_migrations_applied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = tmp_path / "seed.db"
    run_in_process(tmp_path, monkeypatch, "--count", "3", "--db", str(db))
    connection = sqlite3.connect(db)
    try:
        versions = [r[0] for r in connection.execute("SELECT version FROM schema_migrations")]
    finally:
        connection.close()
    assert versions == ["001_initial"]


def test_a_new_path_gets_its_parent_folder_and_an_empty_file_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = tmp_path / "x" / "y" / "seed.db"
    assert run_in_process(tmp_path, monkeypatch, "--count", "2", "--db", str(nested))[0] == 0
    assert len(rows_of(nested)) == 2
    empty = tmp_path / "empty.db"
    empty.write_bytes(b"")
    assert run_in_process(tmp_path, monkeypatch, "--count", "2", "--db", str(empty))[0] == 0
    assert len(rows_of(empty)) == 2


def test_an_unrelated_database_is_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other.db"
    other.write_bytes(b"not a real database but not empty")
    before = sha(other)
    run_in_process(tmp_path, monkeypatch, "--count", "2", "--db", str(tmp_path / "seed.db"))
    assert sha(other) == before


def test_a_relative_db_path_is_resolved_against_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    code, _ = run_in_process(tmp_path, monkeypatch, "--count", "2", "--db", "relative.db")
    assert code == 0
    assert len(rows_of(tmp_path / "relative.db")) == 2


def default_spellings(settings: Settings) -> list[str]:
    spelled = os.path.join(".", "backend", "..", "backend", "data", "spendwise.db")
    spellings = [spelled, str(settings.default_db_path)]
    if sys.platform == "win32":
        spellings.append(str(settings.default_db_path).swapcase())
    return spellings


@pytest.mark.parametrize("state", ["absent", "empty", "with-content"])
def test_the_default_database_is_never_touched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, state: str, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env({}, tmp_path)
    default = settings.default_db_path
    if state != "absent":
        default.parent.mkdir(parents=True)
        default.write_bytes(b"" if state == "empty" else b"existing application data")
    before = sha(default) if default.exists() else None
    for spelling in default_spellings(settings):
        code = seed.main(["--count", "5", "--db", spelling], settings)
        assert code != 0
        assert "default" in capsys.readouterr().err.lower()
        if state == "absent":
            assert not default.exists()
            assert not default.parent.exists()
        else:
            assert sha(default) == before


def test_a_missing_db_is_refused_and_creates_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    code, _ = run_in_process(tmp_path, monkeypatch, "--count", "5")
    assert code != 0
    assert "--db" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_a_missing_or_invalid_count_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    db = tmp_path / "seed.db"
    for args in (
        ["--db", str(db)],
        ["--count", "0", "--db", str(db)],
        ["--count", "x", "--db", str(db)],
    ):
        code, _ = run_in_process(tmp_path, monkeypatch, *args)
        assert code != 0
        assert "--count" in capsys.readouterr().err
    assert not db.exists()


def test_a_directory_as_db_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "somefolder"
    folder.mkdir()
    code, _ = run_in_process(tmp_path, monkeypatch, "--count", "5", "--db", str(folder))
    assert code != 0
    assert "directory" in capsys.readouterr().err.lower()
    assert list(folder.iterdir()) == []


def test_an_existing_non_empty_file_is_never_overwritten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    existing = tmp_path / "existing.db"
    existing.write_bytes(b"SQLite format 3\x00 existing rows")
    before = sha(existing)
    code, _ = run_in_process(tmp_path, monkeypatch, "--count", "5", "--db", str(existing))
    assert code != 0
    assert "not empty" in capsys.readouterr().err.lower()
    assert sha(existing) == before


def run_command(cwd: Path, script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


@pytest.mark.parametrize("count", [50, 1000])
def test_the_documented_command_works_from_the_repository_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    db = tmp_path / "documented.db"
    result = run_command(
        REPO_ROOT, Path("backend") / "scripts" / "seed.py", "--count", str(count), "--db", str(db)
    )
    assert result.returncode == 0, result.stderr
    rows = rows_of(db)
    assert len(rows) == count
    if count == 50:
        assert {r[3] for r in rows} == set(CATEGORIES)
        assert {str(r[5])[:7] for r in rows} == {"2026-09", "2026-10", "2026-11"}
        assert max(str(r[5]) for r in rows) <= "2026-11-12"
    in_process = tmp_path / "in-process.db"
    run_in_process(tmp_path, monkeypatch, "--count", str(count), "--db", str(in_process))
    assert rows == rows_of(in_process)


def test_the_documented_command_refuses_the_default_path_of_an_isolated_copy(
    tmp_path: Path,
) -> None:
    layout = tmp_path / "layout"
    for name in ("app", "scripts"):
        shutil.copytree(
            REPO_ROOT / "backend" / name,
            layout / "backend" / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    script = layout / "backend" / "scripts" / "seed.py"
    default = layout / "backend" / "data" / "spendwise.db"
    dotted = os.path.join(".", "backend", "..", "backend", "data", "spendwise.db")
    for spelling in (str(default), dotted):
        result = run_command(layout, script, "--count", "5", "--db", spelling)
        assert result.returncode != 0
        assert not default.parent.exists()
        assert {p.name for p in layout.iterdir()} == {"backend"}
