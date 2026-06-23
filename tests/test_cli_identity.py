from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


def test_identity_gate_invalid_json_exits_nonzero(tmp_path: Path) -> None:
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "gate-report.json").write_text("{invalid", encoding="utf-8")

    result = runner.invoke(app, ["identity", "gate", "--evidence", str(evidence_dir)])
    assert result.exit_code == 2


def test_identity_scan_invalid_leavers_json_exits_nonzero(tmp_path: Path) -> None:
    services = tmp_path / "services.json"
    services.write_text("[]", encoding="utf-8")
    leavers = tmp_path / "leavers.json"
    leavers.write_text("{invalid", encoding="utf-8")

    result = runner.invoke(
        app,
        ["identity", "scan", "--services", str(services), "--leavers", str(leavers)],
    )
    assert result.exit_code == 2
