from pathlib import Path

import pytest

from scan_secrets import Finding, format_finding, main, scan

# Key-like values are built at run time so this file itself holds no key-shaped literal.
AQ_KEY = "AQ." + "Ab" * 16
AIZA_KEY = "AIza" + "Sy" * 15


def write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_tree_has_no_findings(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "Set GEMINI_API_KEY in backend/.env\nGEMINI_API_KEY=\n")
    write(tmp_path, "backend/.env.example", "GEMINI_API_KEY=\nGEMINI_MODEL=gemini-3.5-flash-lite\n")
    assert scan(tmp_path) == []


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        pytest.param(f"key {AQ_KEY} end", "key-like value (AQ.)", id="aq"),
        pytest.param(f"key {AIZA_KEY} end", "key-like value (AIza)", id="aiza"),
        pytest.param(
            "GEMINI_API_KEY=" + "x" * 24, "GEMINI_API_KEY assigned a value", id="assignment"
        ),
        pytest.param(
            'GEMINI_API_KEY: "' + "y" * 24 + '"', "GEMINI_API_KEY assigned a value", id="quoted"
        ),
    ],
)
def test_detects_key_like_values_and_names_the_location_only(
    tmp_path: Path, text: str, kind: str
) -> None:
    write(tmp_path, "evidence/run-1/raw/TC-01.txt", f"line one\n{text}\n")
    [finding] = scan(tmp_path)
    assert finding == Finding("evidence/run-1/raw/TC-01.txt", 2, kind)
    message = format_finding(finding)
    assert "evidence/run-1/raw/TC-01.txt:2" in message
    assert AQ_KEY not in message and AIZA_KEY not in message


def test_short_placeholders_are_not_findings(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "GEMINI_API_KEY=your-key-here\nGEMINI_API_KEY=<key>\n")
    assert scan(tmp_path) == []


def test_known_test_placeholders_are_allowed(tmp_path: Path) -> None:
    write(
        tmp_path, "t.py", "x = 'AQ.SyntheticValue1234567890'\ny = 'AIzaSyA1234567890abcdefghij'\n"
    )
    assert scan(tmp_path) == []


@pytest.mark.parametrize(
    "rel",
    [
        ".env",
        "backend/.env",
        "backend/.env.local",
        ".venv/lib/x.txt",
        "node_modules/p/i.js",
        ".git/config",
        "frontend/dist/a.js",
        "backend/__pycache__/a.txt",
    ],
)
def test_ignored_locations_are_skipped(tmp_path: Path, rel: str) -> None:
    write(tmp_path, rel, f"GEMINI_API_KEY={AQ_KEY}\n")
    assert scan(tmp_path) == []


def test_env_example_is_scanned(tmp_path: Path) -> None:
    write(tmp_path, "backend/.env.example", f"GEMINI_API_KEY={AQ_KEY}\n")
    assert len(scan(tmp_path)) >= 1


def test_known_secret_is_found_even_if_it_matches_no_pattern(tmp_path: Path) -> None:
    write(tmp_path, "evidence/run-1/results.json", '{"x": "odd-secret-7"}\n')
    [finding] = scan(tmp_path, known_secrets=["odd-secret-7"])
    assert finding.kind == "value of the configured API key"
    assert "odd-secret-7" not in format_finding(finding)


def test_binary_files_are_ignored(tmp_path: Path) -> None:
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x00\x01\xff\xfe" + AQ_KEY.encode())
    assert scan(tmp_path) == []


def test_main_reports_findings_without_printing_the_secret(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    env_file = write(tmp_path, "backend/.env", "GEMINI_API_KEY=odd-secret-value-9\n")
    write(tmp_path, "evidence/raw.txt", "leaked odd-secret-value-9 here\n")
    code = main(["--root", str(tmp_path), "--env-file", str(env_file)])
    out = capsys.readouterr()
    assert code == 1
    assert "evidence/raw.txt:1" in out.out
    assert "odd-secret-value-9" not in out.out + out.err


def test_main_passes_on_a_clean_tree(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    env_file = write(tmp_path, "backend/.env", "GEMINI_API_KEY=odd-secret-value-9\n")
    write(tmp_path, "README.md", "nothing here\n")
    assert main(["--root", str(tmp_path), "--env-file", str(env_file)]) == 0
    assert "no secrets found" in capsys.readouterr().out


def test_main_works_without_an_env_file(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "nothing here\n")
    assert main(["--root", str(tmp_path), "--env-file", str(tmp_path / "none.env")]) == 0
