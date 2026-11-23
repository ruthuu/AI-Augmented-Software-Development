"""Fail if an API key (or a key-like value) appears in the repository or its evidence."""

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

PART_DIR = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "__pycache__", ".pytest_cache", ".ruff_cache"}
# Harmless values that tests use to exercise redaction and scanning.
ALLOWED_PLACEHOLDERS = {"AQ.SyntheticValue1234567890", "AIzaSyA1234567890abcdefghij"}
MIN_SECRET_LENGTH = 6

_PATTERNS = [
    ("key-like value (AQ.)", re.compile(r"AQ\.[A-Za-z0-9_\-]{16,}")),
    ("key-like value (AIza)", re.compile(r"AIza[A-Za-z0-9_\-]{20,}")),
    (
        "GEMINI_API_KEY assigned a value",
        re.compile(r"GEMINI_API_KEY\s*[=:]\s*[\"']?[A-Za-z0-9_\-.]{20,}"),
    ),
]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str


def format_finding(finding: Finding) -> str:
    # Location and kind only; the matched text is never printed.
    return f"{finding.path}:{finding.line}: {finding.kind}"


def _is_ignored_file(path: Path) -> bool:
    name = path.name
    return name == ".env" or (name.startswith(".env.") and name != ".env.example")


def _files(root: Path) -> list[Path]:
    found = []
    for path in sorted(root.rglob("*")):
        relative_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in relative_parts):
            continue
        if path.is_file() and not _is_ignored_file(path):
            found.append(path)
    return found


def scan(root: Path, known_secrets: list[str] | None = None) -> list[Finding]:
    secrets = [s for s in (known_secrets or []) if len(s) >= MIN_SECRET_LENGTH]
    findings: list[Finding] = []
    for path in _files(root):
        data = path.read_bytes()
        if b"\x00" in data[:4096]:
            continue
        rel = path.relative_to(root).as_posix()
        for number, line in enumerate(data.decode("utf-8", errors="ignore").splitlines(), start=1):
            for kind, pattern in _PATTERNS:
                matches = [m.group(0) for m in pattern.finditer(line)]
                if any(m not in ALLOWED_PLACEHOLDERS for m in matches):
                    findings.append(Finding(rel, number, kind))
            if any(secret in line for secret in secrets):
                findings.append(Finding(rel, number, "value of the configured API key"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Secret scan for Part-1B")
    parser.add_argument("--root", type=Path, default=PART_DIR)
    parser.add_argument("--env-file", type=Path, default=PART_DIR / "backend" / ".env")
    args = parser.parse_args(argv)

    known = [os.environ.get("GEMINI_API_KEY", "").strip()]
    if args.env_file.is_file():
        known.append((dotenv_values(args.env_file).get("GEMINI_API_KEY") or "").strip())

    findings = scan(args.root, [k for k in known if k])
    for finding in findings:
        print(format_finding(finding))
    print("no secrets found" if not findings else f"{len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
