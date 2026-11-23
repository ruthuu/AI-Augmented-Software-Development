"""T020 (part 1): configuration and database path helpers."""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

from app.core import config
from app.core.config import Settings, resolve_db_path, same_path

BASE_PARTS = ("backend", "data", "spendwise.db")


def test_resolve_db_path_returns_absolute_normalized_path(tmp_path: Path) -> None:
    result = resolve_db_path(os.path.join(".", "a", "..", "b", "x.db"), tmp_path)
    assert result.is_absolute()
    assert result == tmp_path / "b" / "x.db"
    assert ".." not in result.parts


def test_resolve_db_path_keeps_an_absolute_path(tmp_path: Path) -> None:
    target = tmp_path / "elsewhere" / "x.db"
    assert resolve_db_path(target, tmp_path / "other") == target


def test_relative_env_path_resolves_against_the_base_folder(tmp_path: Path) -> None:
    settings = Settings.from_env({"SPENDWISE_DB_PATH": os.path.join("data", "t.db")}, tmp_path)
    assert settings.db_path == tmp_path / "data" / "t.db"


def test_default_db_path_is_under_the_base_folder(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    assert settings.default_db_path == tmp_path.joinpath(*BASE_PARTS)
    assert settings.db_path == settings.default_db_path


def test_dotted_spelling_of_the_default_path_is_the_default(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    spelled = os.path.join(".", "backend", "..", "backend", "data", "spendwise.db")
    assert same_path(resolve_db_path(spelled, tmp_path), settings.default_db_path)


def test_absolute_default_path_is_the_default(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    assert same_path(str(settings.default_db_path), settings.default_db_path)


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="Letter casing is ignored only on Windows; other file systems are case-sensitive",
)
def test_letter_casing_is_ignored_on_windows(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    assert same_path(str(settings.default_db_path).swapcase(), settings.default_db_path)


def test_a_separate_path_is_not_the_default(tmp_path: Path) -> None:
    settings = Settings.from_env({}, tmp_path)
    assert not same_path(tmp_path / "seed.db", settings.default_db_path)
    assert not same_path(tmp_path / "backend" / "data" / "other.db", settings.default_db_path)


def test_default_base_folder_comes_from_the_location_of_config_py() -> None:
    expected = Path(config.__file__).resolve().parents[3]
    assert expected == config.DEFAULT_BASE_FOLDER
    assert (expected / "backend" / "app" / "core" / "config.py").is_file()


def test_default_base_folder_does_not_depend_on_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = Settings.from_env({}).base_folder
    monkeypatch.chdir(tmp_path)
    after = Settings.from_env({}).base_folder
    assert before == after == config.DEFAULT_BASE_FOLDER


def test_cors_origins_default_and_parsing(tmp_path: Path) -> None:
    assert Settings.from_env({}, tmp_path).cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )
    parsed = Settings.from_env({"SPENDWISE_CORS_ORIGINS": " http://a.example , http://b.example,"})
    assert parsed.cors_origins == ("http://a.example", "http://b.example")


def test_today_override(tmp_path: Path) -> None:
    assert Settings.from_env({}, tmp_path).today is None
    assert Settings.from_env({"SPENDWISE_TODAY": "2026-11-12"}, tmp_path).today == date(
        2026, 11, 12
    )


def test_invalid_today_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="SPENDWISE_TODAY"):
        Settings.from_env({"SPENDWISE_TODAY": "12/11/2026"}, tmp_path)


def test_settings_read_the_process_environment_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SPENDWISE_DB_PATH", str(tmp_path / "env.db"))
    assert Settings.from_env().db_path == tmp_path / "env.db"
