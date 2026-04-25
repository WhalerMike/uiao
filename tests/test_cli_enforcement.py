"""Behavioral tests for the `uiao enforcement` sub-app.

Closes the F1 gap from the M5 public-surface audit: confirms that
the Enforcement Runtime (UIAO_111) is reachable from the CLI and
behaves correctly against the shipped fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

FIXTURE = Path("examples/quickstart/scuba-normalized.json")


def test_list_policies_shows_demo_set() -> None:
    """uiao enforcement list-policies must enumerate the built-in demo policies."""
    result = runner.invoke(app, ["enforcement", "list-policies"])
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert "mfa-demo" in result.stdout
    assert "violation-demo" in result.stdout


def test_run_mfa_demo_against_quickstart_fixture() -> None:
    """uiao enforcement run --policy mfa-demo evaluates IR objects from the quickstart fixture.

    The fixture has 5 KSI results, none carrying `mfa_enabled`, so the
    condition `not ir.get('mfa_enabled', True)` returns False for all
    of them — every record is COMPLIANT.
    """
    result = runner.invoke(
        app,
        ["enforcement", "run", str(FIXTURE), "--policy", "mfa-demo"],
    )
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert "policy=mfa-demo" in result.stdout
    assert "IR objects evaluated : 5" in result.stdout
    assert "COMPLIANT" in result.stdout


def test_run_with_violations_writes_results_to_disk(tmp_path: Path) -> None:
    """--out writes the per-object EnforcementResult list as JSON."""
    # Construct an IR object set that triggers the mfa-demo policy
    # (mfa_enabled missing or False on at least one record).
    ir_objects = [
        {"id": "user-001", "mfa_enabled": True},
        {"id": "user-002", "mfa_enabled": False},
        {"id": "user-003"},  # missing key — defaults to True per policy condition
    ]
    ir_path = tmp_path / "ir-objects.json"
    ir_path.write_text(json.dumps(ir_objects), encoding="utf-8")
    out_path = tmp_path / "enforcement-out.json"

    result = runner.invoke(
        app,
        [
            "enforcement",
            "run",
            str(ir_path),
            "--policy",
            "mfa-demo",
            "--out",
            str(out_path),
        ],
    )
    assert result.exit_code == 0, f"stdout={result.stdout}"
    assert out_path.exists()

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(payload) == 3
    states = {r["state"] for r in payload}
    assert "COMPLIANT" in states
    assert "VIOLATED" in states  # user-002 violates


def test_run_unknown_policy_exits_nonzero(tmp_path: Path) -> None:
    """A policy id outside the demo set must error out cleanly."""
    ir_path = tmp_path / "ir.json"
    ir_path.write_text("[]", encoding="utf-8")
    result = runner.invoke(
        app,
        ["enforcement", "run", str(ir_path), "--policy", "nonexistent"],
    )
    assert result.exit_code == 1
    assert "Unknown policy" in result.stdout


def test_run_missing_ir_path_exits_nonzero(tmp_path: Path) -> None:
    """A non-existent IR objects path must error out cleanly."""
    result = runner.invoke(
        app,
        ["enforcement", "run", str(tmp_path / "nope.json")],
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout
