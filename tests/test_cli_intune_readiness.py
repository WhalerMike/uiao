"""
tests/test_cli_intune_readiness.py
-----------------------------------
Tests for the ``uiao ir intune-readiness <survey>`` CLI subcommand.

This is the operator-UX companion to ``ir orgtree-readiness-bundle``:
the bundle command produces a signed OSCAL-bound artefact (HMAC key,
JSON Schema validation, three output files); the readiness command
just summarises the verdict counts so an operator can see whether
their fleet is enrollable without ceremony.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.ir import ir_app


def _write_survey(path: Path, computers: list[dict]) -> Path:
    payload = {"users": [], "groups": [], "computers": computers, "servers": [], "findings": []}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Help + arg validation
# ---------------------------------------------------------------------------


def test_help_exits_zero_and_documents_format() -> None:
    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", "--help"])
    assert result.exit_code == 0
    assert "intune-readiness" in result.output.lower() or "Intune" in result.output
    assert "--format" in result.output


def test_missing_file_exits_nonzero(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(tmp_path / "nope.json")])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "no such" in result.output.lower()


def test_invalid_json_exits_nonzero(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(bad)])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# Empty survey: zero counts but exit 0
# ---------------------------------------------------------------------------


def test_empty_survey_returns_zero_counts(tmp_path: Path) -> None:
    survey = _write_survey(tmp_path / "survey.json", [])

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey)])
    assert result.exit_code == 0
    assert "Total computers   : 0" in result.output


# ---------------------------------------------------------------------------
# Text output: human-readable verdict summary
# ---------------------------------------------------------------------------


def test_text_output_shows_total_ready_blocked_and_pct(tmp_path: Path) -> None:
    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": "CN=R,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=B,DC=x",
                "operating_system": "Windows 10",
                "operating_system_version": "10.0 (19044)",
            },
        ],
    )

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey)])
    assert result.exit_code == 0
    assert "Total computers   : 2" in result.output
    assert "Enroll-ready" in result.output
    assert "Enroll-blocked" in result.output
    assert "50.0%" in result.output
    assert "READY" in result.output
    assert "NEEDS_OS_UPGRADE" in result.output


def test_text_output_lists_blocked_dns(tmp_path: Path) -> None:
    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": "CN=ANCIENT,DC=x",
                "operating_system": "Windows 7",
                "operating_system_version": "6.1.7601",
            }
        ],
    )

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey)])
    assert result.exit_code == 0
    assert "CN=ANCIENT,DC=x" in result.output


def test_text_output_truncates_blocked_dns_at_ten(tmp_path: Path) -> None:
    """When more than 10 computers are blocked, output shows first 10 + a 'more' line."""
    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": f"CN=BAD-{i:02d},DC=x",
                "operating_system": "Ubuntu",
                "operating_system_version": "22.04",
            }
            for i in range(15)
        ],
    )

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey)])
    assert result.exit_code == 0
    assert "CN=BAD-00,DC=x" in result.output
    assert "CN=BAD-09,DC=x" in result.output
    assert "CN=BAD-14,DC=x" not in result.output
    assert "and 5 more" in result.output


# ---------------------------------------------------------------------------
# JSON output: machine-readable plan
# ---------------------------------------------------------------------------


def test_json_format_emits_parseable_plan(tmp_path: Path) -> None:
    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": "CN=R,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
        ],
    )

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey), "--format", "json"])
    assert result.exit_code == 0

    plan = json.loads(result.output)
    assert plan["total_computers"] == 1
    assert plan["enroll_ready_count"] == 1
    assert plan["enroll_blocked_count"] == 0
    assert plan["readiness_pct"] == 100.0
    assert plan["verdict_counts"] == {"READY": 1}


# ---------------------------------------------------------------------------
# --out writes file
# ---------------------------------------------------------------------------


def test_out_flag_writes_json_file(tmp_path: Path) -> None:
    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": "CN=R,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
        ],
    )
    out = tmp_path / "nested" / "plan.json"

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey), "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()

    plan = json.loads(out.read_text(encoding="utf-8"))
    assert plan["total_computers"] == 1
    assert plan["enroll_ready_count"] == 1
    assert "verdict_counts" in plan


def test_out_flag_works_with_json_format(tmp_path: Path) -> None:
    """--format json + --out: stdout has the plan JSON, file has the same plan JSON."""
    survey = _write_survey(tmp_path / "survey.json", [])
    out = tmp_path / "plan.json"

    runner = CliRunner()
    result = runner.invoke(ir_app, ["intune-readiness", str(survey), "--format", "json", "--out", str(out)])
    assert result.exit_code == 0
    assert out.exists()

    file_plan = json.loads(out.read_text(encoding="utf-8"))
    assert file_plan["total_computers"] == 0


# ---------------------------------------------------------------------------
# Cross-verification with the bundle command
# ---------------------------------------------------------------------------


def test_intune_readiness_matches_bundle_intune_plan(tmp_path: Path) -> None:
    """The standalone command must produce the same intune_plan as the bundle command.

    This is the contract check: ``intune-readiness`` is a quick-look
    front-end on the same ``build_intune_plan()`` the bundle command
    uses internally. Drift between them would mean operators see
    different numbers depending on which command they run.
    """
    import os

    survey = _write_survey(
        tmp_path / "survey.json",
        [
            {
                "dn": "CN=R,DC=x",
                "operating_system": "Windows 11",
                "operating_system_version": "10.0 (22631)",
                "tpm_version": "2.0",
                "hvci_enabled": True,
            },
            {
                "dn": "CN=B,DC=x",
                "operating_system": "Windows 10",
                "operating_system_version": "10.0 (19044)",
            },
        ],
    )

    runner = CliRunner()

    # Standalone command, JSON format
    standalone = runner.invoke(ir_app, ["intune-readiness", str(survey), "--format", "json"])
    assert standalone.exit_code == 0
    standalone_plan = json.loads(standalone.output)

    # Bundle command, then extract intune_plan from bundle.json
    bundle_dir = tmp_path / "bundle-out"
    bundle_result = runner.invoke(
        ir_app,
        ["orgtree-readiness-bundle", str(survey), "--out-dir", str(bundle_dir), "--insecure-dev-key"],
        env={k: v for k, v in os.environ.items() if k != "UIAO_BUNDLE_HMAC_KEY"},
        catch_exceptions=False,
    )
    assert bundle_result.exit_code == 0
    bundle_data = json.loads((bundle_dir / "bundle.json").read_text())
    bundle_plan = bundle_data["intune_plan"]

    assert standalone_plan == bundle_plan
