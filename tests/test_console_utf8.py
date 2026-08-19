"""Tests for the shared UTF-8 stdout helper (issue #1433).

Canon prose carries characters cp1252 cannot encode. Scripts that stream that
content to stdout died with UnicodeEncodeError on Windows while passing in CI,
and — because `print` raises partway through emitting — the run read as "fewer
results" rather than as a crash.
"""

from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

_SPEC = importlib.util.spec_from_file_location("_console", SCRIPTS_DIR / "_console.py")
console = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(console)

# The exact characters that crashed each generator, plus the box-drawing that
# truncated the OrgPath slot-binding guard's findings list.
CANON_CHARS = "→ ‑ │ – —"

# Every script that streams a rendered document to stdout when --output is omitted.
STDOUT_GENERATORS = [
    "generate_customer_docs_status.py",
    "generate_document_index.py",
    "generate_sitemap.py",
    "generate_substrate_status_table.py",
]


def test_helper_is_a_noop_on_streams_without_reconfigure() -> None:
    original = sys.stdout
    try:
        sys.stdout = io.StringIO()  # no .reconfigure
        console.use_utf8_stdout()  # must not raise
    finally:
        sys.stdout = original


def test_helper_makes_stdout_utf8_and_non_fatal() -> None:
    original_out, original_err = sys.stdout, sys.stderr
    try:
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
        console.use_utf8_stdout()
        assert sys.stdout.encoding.lower().replace("-", "") == "utf8"
        assert sys.stderr.encoding.lower().replace("-", "") == "utf8"
        sys.stdout.write(CANON_CHARS)  # would raise before the call
    finally:
        sys.stdout, sys.stderr = original_out, original_err


def test_every_stdout_generator_calls_the_helper() -> None:
    """A new generator that streams to stdout must opt in, or it regresses #1433."""
    for name in STDOUT_GENERATORS:
        source = (SCRIPTS_DIR / name).read_text(encoding="utf-8")
        assert "sys.stdout.write(rendered)" in source, f"{name}: no longer streams to stdout?"
        assert "use_utf8_stdout()" in source, f"{name}: streams to stdout without use_utf8_stdout()"


def test_no_other_script_streams_to_stdout_unguarded() -> None:
    """Catch a future script picking up the pattern without the helper."""
    offenders = [
        path.name
        for path in sorted(SCRIPTS_DIR.glob("*.py"))
        if "sys.stdout.write(rendered)" in path.read_text(encoding="utf-8")
        and "use_utf8_stdout()" not in path.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"streams a rendered document to stdout without the helper: {offenders}"


def test_generators_run_bare_under_a_cp1252_console() -> None:
    """The regression itself: bare invocation, stdout forced to cp1252."""
    repo_root = SCRIPTS_DIR.parent
    for name in STDOUT_GENERATORS:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / name)],
            cwd=repo_root,
            capture_output=True,
            env={**__import__("os").environ, "PYTHONIOENCODING": "cp1252"},
            timeout=300,
        )
        assert b"UnicodeEncodeError" not in result.stderr, f"{name} still crashes under cp1252"
        assert result.returncode == 0, f"{name} exited {result.returncode}: {result.stderr[-300:]!r}"
