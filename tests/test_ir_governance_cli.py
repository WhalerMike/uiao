"""CLI smoke tests for ir-governance-report command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao_core.cli.app import app

runner = CliRunner()

SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "gov-cli-test-001",
        "assessment_date": "2026-04-08T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-001"},
    "ksi_results": [
        {
            "ksi_id": "KSI-IA-01",
            "status": "FAIL",
            "severity": "High",
            "details": "MFA not enforced",
        },
        {
            "ksi_id": "KSI-IA-02",
            "status": "PASS",
            "severity": "Medium",
            "details": "Legacy auth blocked",
        },
        {
            "ksi_id": "KSI-AC-01",
            "status": "FAIL",
            "severity": "Critical",
            "details": "Admin roles unreviewed",
        },
    ],
}


@pytest.fixture()
def scuba_json(tmp_path: Path) -> Path:
    p = tmp_path / "normalized.json"
    p.write_text(json.dumps(SCUBA_FIXTURE), encoding="utf-8")
    return p


class TestIRGovernanceReport:
    def test_report_printed(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-governance-report", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "UIAO Governance Report" in result.output

    def test_report_contains_action_types(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-governance-report", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "remediate" in result.output or "escalate" in result.output

    def test_report_contains_total_actions(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-governance-report", str(scuba_json)])
        assert result.exit_code == 0, result.output
        assert "Total actions" in result.output

    def test_out_writes_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "governance.json"
        result = runner.invoke(app, ["ir-governance-report", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        rows = json.loads(out.read_text())
        assert isinstance(rows, list)
        assert len(rows) == 3
        action_types = {r["action_type"] for r in rows}
        assert action_types <= {"escalate", "remediate", "monitor", "review"}

    def test_out_json_has_required_fields(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "governance.json"
        runner.invoke(app, ["ir-governance-report", str(scuba_json), "--out", str(out)])
        rows = json.loads(out.read_text())
        required = {"ksi_id", "severity", "owner", "sla_days", "action_type", "description", "evidence_id"}
        for row in rows:
            assert required <= set(row.keys()), f"Missing fields in: {row}"

    def test_cli_help_lists_command(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ir-governance-report" in result.output
