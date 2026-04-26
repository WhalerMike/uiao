import json
import pathlib
import pytest
from typer.testing import CliRunner
from uiao.cli.app import app

runner = CliRunner()

FAKE_SCUBA = {
    "assessment_metadata": {
        "run_id": "test-run-001",
        "assessment_date": "2025-01-01T00:00:00Z",
        "tool_version": "1.0.0",
        "collector_user": "ci",
    },
    "tenant": {"tenant_id": "test-tenant"},
    "ksi_results": [
        {"ksi_id": "KSI-IAM-01", "status": "PASS", "severity": "Low", "details": "AAD policy passed"},
        {"ksi_id": "KSI-IAM-02", "status": "FAIL", "severity": "High", "details": "MFA not enforced"},
    ],
}
FAKE_JSON = json.dumps(FAKE_SCUBA)


@pytest.fixture()
def scuba_file(tmp_path):
    f = tmp_path / "scuba.json"
    f.write_text(FAKE_JSON)
    return str(f)


def test_ir_ssp_report_markdown_default(scuba_file):
    result = runner.invoke(app, ["ir", "ssp-report", scuba_file])
    assert result.exit_code == 0, result.output
    assert len(result.output) > 10


def test_ir_ssp_report_json_format(scuba_file):
    result = runner.invoke(app, ["ir", "ssp-report", scuba_file, "--format", "json"])
    assert result.exit_code == 0, result.output
    raw = result.output[result.output.index(chr(123)) :]
    data = json.loads(raw)
    assert isinstance(data, dict)


def test_ir_ssp_report_writes_md_file(tmp_path, scuba_file):
    out = str(tmp_path / "ssp_report.md")
    result = runner.invoke(app, ["ir", "ssp-report", scuba_file, "--out", out])
    assert result.exit_code == 0, result.output
    assert pathlib.Path(out).exists()


def test_ir_ssp_report_writes_json_file(tmp_path, scuba_file):
    out = str(tmp_path / "ssp_report.json")
    result = runner.invoke(app, ["ir", "ssp-report", scuba_file, "--format", "json", "--out", out])
    assert result.exit_code == 0, result.output
    data = json.loads(pathlib.Path(out).read_text())
    assert isinstance(data, dict)


def test_ir_ssp_report_help():
    result = runner.invoke(app, ["ir", "ssp-report", "--help"])
    assert result.exit_code == 0
    assert "narrative" in result.output.lower() or "ssp" in result.output.lower()
