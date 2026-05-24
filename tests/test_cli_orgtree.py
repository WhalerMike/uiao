"""Tests for `uiao orgtree validate codebook`.

Per ADR-078, the OrgTree corpus was reset to Model C and the speculative
Model A consumer modules (dynamic-groups, admin-units, device-planes,
policy-targets, drift-engine-config) and their CLI commands were
retired. This test file covers only the surviving command:

- ``validate codebook`` (UIAO_151, Model C)
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


class TestOrgtreeHelp:
    def test_orgtree_help_lists_validate(self) -> None:
        result = runner.invoke(app, ["orgtree", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout

    def test_validate_help_lists_codebook(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "--help"])
        assert result.exit_code == 0
        assert "codebook" in result.stdout


class TestValidateCanonicalDefaults:
    def test_codebook_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "codebook"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout
        assert "UIAO_151" in result.stdout


class TestValidateBadData:
    def test_codebook_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("schema_version: '2.0.0'\nfacets: not-an-object\n")
        result = runner.invoke(app, ["orgtree", "validate", "codebook", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL" in result.stdout
