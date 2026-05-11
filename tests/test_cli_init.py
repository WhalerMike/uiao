"""Tests for the ``uiao init`` CLI command.

Coverage:
  1. Default invocation prints the welcome banner + walkthrough
  2. All five walkthrough steps appear in the output
  3. Every canon-ref path declared in init.py resolves on the filesystem
  4. --help exits cleanly without invoking the callback
  5. The exit code is 0 in default mode

The ``--demo`` mode subprocesses to ``uiao ir auditor-bundle`` which exercises
the OSCAL evidence pipeline; that path is covered by the existing auditor-bundle
tests, so this file focuses on the welcome / walkthrough surface.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.cli.init import _CANON_REFS, _WALKTHROUGH_STEPS

REPO_ROOT = Path(__file__).resolve().parent.parent
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_init_default_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0


def test_init_default_prints_welcome_banner(runner: CliRunner) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "UIAO" in result.output
    assert "Universal Identity-Addressing-Overlay" in result.output
    assert "10-minute new-user walkthrough" in result.output


def test_init_default_includes_all_walkthrough_steps(runner: CliRunner) -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    # Step titles come from _WALKTHROUGH_STEPS and must all appear.
    for title, _command, _description in _WALKTHROUGH_STEPS:
        # Strip rich markup since CliRunner output drops the ANSI codes,
        # but keep the title text intact.
        # Title format: "1. Verify the substrate is healthy"
        # The leading number + period must survive into output.
        assert title.split(". ", 1)[1] in result.output, f"walkthrough step missing from output: {title!r}"


def test_init_default_documents_read_only_posture(runner: CliRunner) -> None:
    """The command must explicitly tell the user it is read-only."""
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "read-only" in result.output
    assert "$HOME" in result.output


def test_init_canon_ref_paths_resolve_on_filesystem() -> None:
    """Every canon-ref path declared in init.py must exist in the repo."""
    missing: list[str] = []
    for label, path in _CANON_REFS:
        full = REPO_ROOT / path
        if not full.exists():
            missing.append(f"{label!r} -> {path}")
    assert not missing, "canon-ref targets do not exist:\n  " + "\n  ".join(missing)


def test_init_help_exits_zero(runner: CliRunner) -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    plain_output = _ANSI_ESCAPE_RE.sub("", result.output)
    assert "--demo" in plain_output
    assert "--out-dir" in plain_output


def test_init_demo_flag_fails_gracefully_when_subprocess_fails(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--demo invokes a subprocess; verify the failure path is non-zero exit
    rather than a Python traceback."""
    import subprocess as _real_subprocess

    class _FakeCompleted:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

    def _fake_run(cmd, check=False):  # type: ignore[no-untyped-def]
        return _FakeCompleted(returncode=42)

    monkeypatch.setattr("uiao.cli.init.subprocess.run", _fake_run)
    result = runner.invoke(app, ["init", "--demo", "--out-dir", str(tmp_path)])
    assert result.exit_code == 42
    # Ensure we still re-export the real subprocess module for other callers.
    _ = _real_subprocess
