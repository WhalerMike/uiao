"""CLI tests for ``uiao directory`` (ADR-099)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()

SNAPSHOT = {
    "principals": [
        {"principal_id": "alice@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute1": "NCR"}},
    ]
}


def _write_snapshot(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.json"
    path.write_text(json.dumps(SNAPSHOT), encoding="utf-8")
    return path


def test_tree_emits_ldif(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "dn: cn=alice-uiao.gov,ou=people,dc=agd,dc=uiao,dc=gov" in result.output
    assert "uiaoOrgPathRegion: NCR" in result.output


def test_tree_empty_snapshot_still_projects_containers() -> None:
    result = runner.invoke(app, ["directory", "tree"])
    assert result.exit_code == 0, result.output
    assert "dn: dc=agd,dc=uiao,dc=gov" in result.output


def test_tree_missing_snapshot_fails(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


def test_tree_invalid_json_fails(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    result = runner.invoke(app, ["directory", "tree", "--snapshot", str(bad)])
    assert result.exit_code == 1
    assert "invalid json" in result.output.lower()


def test_serve_check_does_not_bind(tmp_path: Path) -> None:
    result = runner.invoke(app, ["directory", "serve", "--check", "--snapshot", str(_write_snapshot(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "would serve" in result.output.lower()
    assert "read-only" in result.output.lower()
