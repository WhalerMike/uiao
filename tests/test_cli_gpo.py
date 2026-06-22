"""CLI tests for `uiao orgtree gpo analyze | plan`.

Happy-path + failure-mode coverage per the repo's new-command rule.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.orgtree import orgtree_app

runner = CliRunner()

_BACKUP = Path(__file__).parent / "fixtures" / "gpo" / "backup"


def test_gpo_analyze_summary_happy_path() -> None:
    result = runner.invoke(orgtree_app, ["gpo", "analyze", str(_BACKUP)])
    assert result.exit_code == 0, result.output
    assert "GPO analysis" in result.output
    assert "csp-mappable" in result.output


def test_gpo_analyze_json_and_out(tmp_path: Path) -> None:
    out = tmp_path / "analysis.json"
    result = runner.invoke(orgtree_app, ["gpo", "analyze", str(_BACKUP), "--json", "--out", str(out)])
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["gpo_count"] == 5
    assert "rollup_by_portability" in payload


def test_gpo_plan_happy_path() -> None:
    result = runner.invoke(orgtree_app, ["gpo", "plan", str(_BACKUP)])
    assert result.exit_code == 0, result.output
    assert "migration plan" in result.output
    assert "OrgTree-Finance-Devices" in result.output


def test_gpo_plan_json(tmp_path: Path) -> None:
    out = tmp_path / "plan.json"
    result = runner.invoke(orgtree_app, ["gpo", "plan", str(_BACKUP), "--out", str(out)])
    assert result.exit_code == 0, result.output
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert "plans" in payload
    assert len(payload["plans"]) == 5


def test_gpo_analyze_missing_dir_fails_closed() -> None:
    result = runner.invoke(orgtree_app, ["gpo", "analyze", "/no/such/backup/dir"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_gpo_plan_rejects_file_path(tmp_path: Path) -> None:
    afile = tmp_path / "not-a-dir.txt"
    afile.write_text("x", encoding="utf-8")
    result = runner.invoke(orgtree_app, ["gpo", "plan", str(afile)])
    assert result.exit_code == 1
    assert "not found" in result.output
