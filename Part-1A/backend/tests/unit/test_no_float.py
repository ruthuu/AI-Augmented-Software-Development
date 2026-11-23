"""T018 (G7): no float name, call, annotation, or literal in the money-handling modules."""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"
TARGETS = [APP / "core" / "money.py", APP / "services", APP / "repositories", APP / "schemas"]


def _python_files() -> list[Path]:
    files: list[Path] = []
    for target in TARGETS:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(sorted(target.rglob("*.py")))
    return files


def _float_findings(source: str) -> list[str]:
    findings: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name) and node.id == "float":
            findings.append(f"line {node.lineno}: name 'float'")
        elif isinstance(node, ast.Attribute) and node.attr == "float":
            findings.append(f"line {node.lineno}: attribute 'float'")
        elif isinstance(node, ast.Constant) and isinstance(node.value, float):
            findings.append(f"line {node.lineno}: float literal")
        elif isinstance(node, ast.Constant) and node.value == "float":
            findings.append(f"line {node.lineno}: string annotation 'float'")
    return findings


def test_money_module_exists() -> None:
    assert (APP / "core" / "money.py").is_file()


@pytest.mark.parametrize("path", _python_files(), ids=lambda p: p.relative_to(APP).as_posix())
def test_no_float_in_module(path: Path) -> None:
    assert _float_findings(path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "source",
    ["x: float = 1", "y = float('1')", "z = 1.5", "w = 1e3", "def f(a: 'float') -> None: ..."],
)
def test_detector_catches_float_usage(source: str) -> None:
    assert _float_findings(source) != []


def test_detector_ignores_clean_code() -> None:
    assert _float_findings("def f(a: int) -> int:\n    return a + 1\n") == []
