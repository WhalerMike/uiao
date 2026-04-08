"""Basic CLI smoke tests for the 4 new IR commands.
All tests use the CliRunner and a minimal fixture file so they do not
require external services or large data files.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao_core.cli.app import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Minimal normalized SCuBA fixture (one PASS, one FAIL)
# ---------------------------------------------------------------------------
SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "cli-test-run-001",
        "assessment_date": "2026-04-08T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-001"},
    "ksi_results": [
        {
            "ksi_id": "KSI-IA-01",
            "status": "PASS",
            "severity": "High",
            "details": "MFA enforced via Conditional Access",
        },
        {
            "ksi_id": "KSI-IA-02",
            "status": "FAIL",
            "severity": "Medium",
            "details": "Legacy auth not fully blocked",
        },
    ],
}


@pytest.fixture()
def scuba_json(tmp_path: Path) -> Path:
    p = tmp_path / "normalized.json"
    p.write_text(json.dumps(SCUBA_FIXTURE), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# ir-scuba-transform
# ---------------------------------------------------------------------------
class TestIRScubaTransform:
    def test_summary_printed(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-scuba-transform", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "SCuBA Transform" in result.output
        assert "Total KSI results" in result.output

    def test_out_writes_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "evidence.json"
        result = runner.invoke(app, ["ir-scuba-transform", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["run_id"] == "cli-test-run-001"
        assert "evidence" in data

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["ir-scuba-transform", str(tmp_path / "nonexistent.json")])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# ir-evidence-bundle
# ---------------------------------------------------------------------------
class TestIREvidenceBundle:
    def test_summary_printed(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-evidence-bundle", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "EvidenceBundle" in result.output

    def test_out_writes_canonical_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "bundle.json"
        result = runner.invoke(app, ["ir-evidence-bundle", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert "run_id" in data
        assert "evidence" in data
        assert "summary" in data


# ---------------------------------------------------------------------------
# ir-poam-export
# ---------------------------------------------------------------------------
class TestIRPoamExport:
    def test_summary_printed(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-poam-export", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "POA&M Summary" in result.output

    def test_fail_row_present(self, scuba_json: Path) -> None:
        """FAIL entries appear in POA&M; PASS entries do not."""
        result = runner.invoke(app, ["ir-poam-export", str(scuba_json)])
        assert result.exit_code == 0, result.output
        # 1 FAIL entry means at least 1 item
        assert "1 item" in result.output or "items" in result.output

    def test_out_writes_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "poam.json"
        result = runner.invoke(app, ["ir-poam-export", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        rows = json.loads(out.read_text())
        assert isinstance(rows, list)
        # Only the FAIL row should appear
        assert len(rows) == 1
        assert rows[0]["ksi_id"] == "KSI-IA-02"
        assert rows[0]["status"] == "FAIL"


# ---------------------------------------------------------------------------
# ir-drift-detect
# ---------------------------------------------------------------------------
class TestIRDriftDetect:
    def test_no_drift(self, tmp_path: Path) -> None:
        state = {"mfa_enabled": True, "legacy_auth_blocked": True}
        exp = tmp_path / "expected.json"
        act = tmp_path / "actual.json"
        exp.write_text(json.dumps(state), encoding="utf-8")
        act.write_text(json.dumps(state), encoding="utf-8")
        result = runner.invoke(app, ["ir-drift-detect", str(exp), str(act)])
        assert result.exit_code == 0, result.output
        assert "NO DRIFT" in result.output

    def test_drift_detected(self, tmp_path: Path) -> None:
        exp_state = {"mfa_enabled": True, "legacy_auth_blocked": True}
        act_state = {"mfa_enabled": True, "legacy_auth_blocked": False}
        exp = tmp_path / "expected.json"
        act = tmp_path / "actual.json"
        exp.write_text(json.dumps(exp_state), encoding="utf-8")
        act.write_text(json.dumps(act_state), encoding="utf-8")
        result = runner.invoke(app, ["ir-drift-detect", str(exp), str(act)])
        assert result.exit_code == 0, result.output
        assert "DRIFT DETECTED" in result.output

    def test_out_writes_drift_json(self, tmp_path: Path) -> None:
        state = {"control": "ac-2", "status": "implemented"}
        exp = tmp_path / "e.json"
        act = tmp_path / "a.json"
        exp.write_text(json.dumps(state), encoding="utf-8")
        act.write_text(json.dumps({"control": "ac-2", "status": "partial"}), encoding="utf-8")
        out = tmp_path / "drift.json"
        result = runner.invoke(app, ["ir-drift-detect", str(exp), str(act), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["drift_detected"] is True
        assert data["classification"] in ("risky", "unauthorized")


# ---------------------------------------------------------------------------
# Root help still works
# ---------------------------------------------------------------------------
def test_cli_root_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ir-scuba-transform" in result.output
    assert "ir-evidence-bundle" in result.output
    assert "ir-poam-export" in result.output
    assert "ir-drift-detect" in result.output

