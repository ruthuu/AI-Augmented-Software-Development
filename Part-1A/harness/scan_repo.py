#!/usr/bin/env python3
"""Repository scans for the SpendWise harness (Python standard library only).

Usage:
    python harness/scan_repo.py float
    python harness/scan_repo.py tracked-files
    python harness/scan_repo.py secret-patterns [--path <folder>]

Sub-checks:
    float            Gate G7. Fails on any `float` name, call, annotation, or float literal in
                     backend/app/core/money.py, backend/app/services/, backend/app/repositories/,
                     and backend/app/schemas/.
    tracked-files    Gate G9. Reports tracked `.env`, `.env.*` (except `.env.example`), and `*.db`
                     files, using `git ls-files`. Depends only on git state, so it is valid on an
                     empty project.
    secret-patterns  Aid for the manual G9 working-tree review. Scans every file under backend/ and
                     frontend/src/ (including local .env and .env.* files) for obvious secret
                     patterns. With --path it scans that folder instead (used for evidence folders
                     and snapshots).

Output never contains matched text: each finding is printed as file path, line number, and pattern
or rule name only, so this scanner cannot copy a real secret into evidence.

Exit codes: 0 scanned and clean, 1 findings, 2 the scan itself failed, 3 nothing to scan (zero
files examined; the harness reports this as NOT RUN, never as PASS).
The last line printed is "FILES_EXAMINED=<n> FINDINGS=<m>".
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FLOAT_TARGETS = [
    "backend/app/core/money.py",
    "backend/app/services",
    "backend/app/repositories",
    "backend/app/schemas",
]

EXCLUDED_DIRS = {
    "node_modules",
    "dist",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "coverage",
    "htmlcov",
    "data",
}
EXCLUDED_FILE_PATTERNS = ["*.db", "*.log", ".coverage", ".coverage.*", "yarn-error.log", "*.pyc"]
MAX_FILE_BYTES = 5 * 1024 * 1024

SECRET_PATTERNS = {
    "private-key-block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "password-assignment": re.compile(
        r"(?i)\b(?:password|passwd|pwd)\b\s*[=:]\s*(?:'[^'\s]{4,}'|\"[^\"\s]{4,}\")"
    ),
    "api-key-assignment": re.compile(
        r"(?i)\bapi[_-]?key\b\s*[=:]\s*['\"]?[A-Za-z0-9._\-]{8,}"
    ),
    "secret-env-line": re.compile(
        r"(?im)^\s*[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|API_?KEY|TOKEN)[A-Z0-9_]*\s*=\s*[^\s#]+"
    ),
    "bearer-token": re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{16,}=*"),
    "aws-access-key-id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
}


def excluded(path: Path, base: Path) -> bool:
    relative = path.relative_to(base)
    if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
        return True
    return any(fnmatch.fnmatch(path.name, pattern) for pattern in EXCLUDED_FILE_PATTERNS)


def iter_files(folder: Path):
    for path in sorted(folder.rglob("*")):
        if path.is_file() and not excluded(path, folder):
            yield path


def display(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def scan_float() -> int:
    files: list[Path] = []
    for target in FLOAT_TARGETS:
        path = ROOT / target
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    examined = 0
    findings = 0
    failed = False
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            if not source.strip():
                continue  # an empty __init__.py has nothing to examine
            tree = ast.parse(source, filename=str(path))
        except (SyntaxError, UnicodeDecodeError, OSError):
            print(f"ERROR {display(path)}: cannot be parsed")
            failed = True
            continue
        examined += 1
        for node in ast.walk(tree):
            rule = None
            if isinstance(node, ast.Name) and node.id == "float":
                rule = "float-name"
            elif isinstance(node, ast.Constant) and isinstance(node.value, float):
                rule = "float-literal"
            elif isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.strip() == "float":
                rule = "float-string-annotation"
            elif isinstance(node, ast.Attribute) and node.attr == "float":
                rule = "float-attribute"
            if rule:
                print(f"FINDING {display(path)}:{node.lineno} {rule}")
                findings += 1
    print(f"FILES_EXAMINED={examined} FINDINGS={findings}")
    if failed:
        return 2
    if examined == 0:
        return 3
    return 1 if findings else 0


def scan_tracked() -> int:
    try:
        completed = subprocess.run(  # noqa: S603
            ["git", "ls-files"],  # noqa: S607
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        print("ERROR git could not be started")
        print("FILES_EXAMINED=0 FINDINGS=0")
        return 2
    if completed.returncode != 0:
        print("ERROR git ls-files failed")
        print("FILES_EXAMINED=0 FINDINGS=0")
        return 2
    tracked = [line for line in completed.stdout.splitlines() if line.strip()]
    findings = 0
    for name in tracked:
        base = name.rsplit("/", 1)[-1]
        is_env = base == ".env" or (base.startswith(".env.") and base != ".env.example")
        if is_env:
            print(f"FINDING {name} tracked-env-file")
            findings += 1
        elif base.endswith(".db"):
            print(f"FINDING {name} tracked-database-file")
            findings += 1
    print(f"FILES_EXAMINED={len(tracked)} FINDINGS={findings}")
    return 1 if findings else 0


def secret_targets(path_arg: str | None) -> list[Path]:
    if path_arg:
        folder = Path(path_arg)
        if not folder.is_absolute():
            folder = Path.cwd() / folder
        if not folder.is_dir():
            return []
        return list(iter_files(folder.resolve()))
    files: list[Path] = []
    for relative in ("backend", "frontend/src"):
        folder = ROOT / relative
        if folder.is_dir():
            files.extend(iter_files(folder))
    return files


def scan_secrets(path_arg: str | None) -> int:
    if path_arg and not Path(path_arg).exists():
        print("ERROR the --path folder does not exist")
        print("FILES_EXAMINED=0 FINDINGS=0")
        return 2
    examined = 0
    findings = 0
    for path in secret_targets(path_arg):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data:
            continue
        text = data.decode("utf-8", errors="replace")
        examined += 1
        for name, pattern in SECRET_PATTERNS.items():
            for found in pattern.finditer(text):
                line = text.count("\n", 0, found.start()) + 1
                print(f"FINDING {display(path)}:{line} {name}")
                findings += 1
    print(f"FILES_EXAMINED={examined} FINDINGS={findings}")
    if examined == 0:
        return 3
    return 1 if findings else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("check", choices=["float", "tracked-files", "secret-patterns"])
    parser.add_argument("--path", default=None)
    args = parser.parse_args()
    if args.path and args.check != "secret-patterns":
        parser.error("--path is only valid with secret-patterns")
    try:
        if args.check == "float":
            return scan_float()
        if args.check == "tracked-files":
            return scan_tracked()
        return scan_secrets(args.path)
    except Exception as error:  # noqa: BLE001 - a scanner crash is an ERROR, never a verdict
        print(f"ERROR {type(error).__name__}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
