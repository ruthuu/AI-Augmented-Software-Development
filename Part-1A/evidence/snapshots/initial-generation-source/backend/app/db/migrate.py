"""Versioned SQL migrations. Runs only at application start or when called explicitly."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _statements(script: str) -> list[str]:
    statements: list[str] = []
    buffer = ""
    for line in script.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        statements.append(buffer.strip())
    return statements


def apply_migrations(conn: sqlite3.Connection) -> list[str]:
    """Apply every pending migrations/*.sql in order and return the versions applied now."""
    conn.isolation_level = None
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations"
        " (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
    applied: list[str] = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = path.stem
        if version in done:
            continue
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("BEGIN")
        try:
            for statement in _statements(path.read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (version, stamp),
            )
        except sqlite3.Error:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        applied.append(version)
    return applied


def initialize_database(db_path: Path) -> None:
    """Create the parent folder and the database file if needed, then apply migrations."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        apply_migrations(conn)
    finally:
        conn.close()
