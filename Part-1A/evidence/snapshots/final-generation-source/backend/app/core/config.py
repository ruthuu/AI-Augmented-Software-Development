"""Settings from real environment variables only (no .env loading) and shared path helpers."""

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path

# backend/app/core/config.py -> repository root; never derived from the working directory.
DEFAULT_BASE_FOLDER = Path(__file__).resolve().parents[3]
DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def resolve_db_path(path: str | Path, base_folder: Path) -> Path:
    """Absolute, normalized path; a relative path is resolved against the base folder."""
    return Path(os.path.normpath(os.path.join(os.path.abspath(base_folder), path)))


def same_path(first: str | Path, second: str | Path) -> bool:
    """Compare normalized absolute paths; letter casing is ignored on Windows only."""
    normalized = [os.path.normcase(os.path.normpath(os.path.abspath(p))) for p in (first, second)]
    return normalized[0] == normalized[1]


@dataclass(frozen=True)
class Settings:
    base_folder: Path
    db_path: Path
    cors_origins: tuple[str, ...]
    today: date | None

    @property
    def default_db_path(self) -> Path:
        return self.base_folder / "backend" / "data" / "spendwise.db"

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, base_folder: Path | None = None
    ) -> "Settings":
        values = os.environ if env is None else env
        base = Path(os.path.abspath(base_folder or DEFAULT_BASE_FOLDER))
        default_db = base / "backend" / "data" / "spendwise.db"
        raw_db = values.get("SPENDWISE_DB_PATH", "").strip()
        db_path = resolve_db_path(raw_db, base) if raw_db else default_db
        raw_origins = values.get("SPENDWISE_CORS_ORIGINS", "").strip() or DEFAULT_CORS_ORIGINS
        origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())
        return cls(base, db_path, origins, _parse_today(values.get("SPENDWISE_TODAY", "")))


def _parse_today(raw: str) -> date | None:
    text = raw.strip()
    if not text:
        return None
    if _ISO_DATE.fullmatch(text) is None:
        raise ValueError("SPENDWISE_TODAY must be a date in the form YYYY-MM-DD")
    try:
        return date.fromisoformat(text)
    except ValueError as error:
        raise ValueError("SPENDWISE_TODAY must be a real calendar date") from error
