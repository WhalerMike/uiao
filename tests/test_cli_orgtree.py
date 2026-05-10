"""Tests for `uiao orgtree validate ...`.

Exercises the six per-artifact validate verbs and the aggregate
`validate all` against the canonical orgpath data shipped under
``uiao.canon.data.orgpath``. Bad-input paths are covered by writing a
short malformed YAML to a temp file and pointing ``--data`` at it.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Help surface
# ---------------------------------------------------------------------------


class TestOrgtreeHelp:
    def test_orgtree_help_lists_validate(self) -> None:
        result = runner.invoke(app, ["orgtree", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.stdout

    def test_validate_help_lists_all_six_artifacts(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "--help"])
        assert result.exit_code == 0
        for verb in (
            "codebook",
            "dynamic-groups",
            "admin-units",
            "device-planes",
            "policy-targets",
            "drift-engine-config",
            "all",
        ):
            assert verb in result.stdout, f"missing verb in help: {verb}"


# ---------------------------------------------------------------------------
# Happy path — canonical data ships with the package
# ---------------------------------------------------------------------------


class TestValidateCanonicalDefaults:
    """Each verb, with no --data flag, must validate the canonical artifact."""

    def test_codebook_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "codebook"])
        assert result.exit_code == 0, result.stdout
        assert "PASS codebook" in result.stdout
        assert "UIAO_151" in result.stdout

    def test_dynamic_groups_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "dynamic-groups"])
        assert result.exit_code == 0, result.stdout
        assert "PASS dynamic-groups" in result.stdout
        assert "UIAO_152" in result.stdout

    def test_admin_units_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "admin-units"])
        assert result.exit_code == 0, result.stdout
        assert "PASS admin-units" in result.stdout
        assert "UIAO_154" in result.stdout

    def test_device_planes_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "device-planes"])
        assert result.exit_code == 0, result.stdout
        assert "PASS device-planes" in result.stdout
        assert "UIAO_153" in result.stdout

    def test_policy_targets_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "policy-targets"])
        assert result.exit_code == 0, result.stdout
        assert "PASS policy-targets" in result.stdout
        assert "UIAO_164" in result.stdout

    def test_drift_engine_config_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "drift-engine-config"])
        assert result.exit_code == 0, result.stdout
        assert "PASS drift-engine-config" in result.stdout
        assert "UIAO_163" in result.stdout

    def test_validate_all_aggregate_pass(self) -> None:
        result = runner.invoke(app, ["orgtree", "validate", "all"])
        assert result.exit_code == 0, result.stdout
        # All six per-artifact passes must appear.
        for label in (
            "PASS codebook",
            "PASS dynamic-groups",
            "PASS admin-units",
            "PASS device-planes",
            "PASS policy-targets",
            "PASS drift-engine-config",
        ):
            assert label in result.stdout, f"missing PASS line: {label}"
        assert "all 6 OrgTree corpus artifacts validated" in result.stdout


# ---------------------------------------------------------------------------
# Failure path — malformed --data file fails loudly
# ---------------------------------------------------------------------------


class TestValidateBadData:
    def test_codebook_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "codebook.yaml"
        # Top-level list, not a mapping — codebook loader rejects this.
        bad.write_text("- not_a_mapping: true\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "codebook", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL codebook" in result.stdout
        assert "UIAO_151" in result.stdout

    def test_dynamic_groups_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "dynamic-groups.yaml"
        bad.write_text("- 1\n- 2\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "dynamic-groups", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL dynamic-groups" in result.stdout

    def test_admin_units_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "admin-units.yaml"
        bad.write_text("- 1\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "admin-units", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL admin-units" in result.stdout

    def test_device_planes_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "device-planes.yaml"
        bad.write_text("- 1\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "device-planes", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL device-planes" in result.stdout

    def test_policy_targets_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "policy-targets.yaml"
        bad.write_text("- 1\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "policy-targets", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL policy-targets" in result.stdout

    def test_drift_engine_config_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "drift-engine-config.yaml"
        bad.write_text("- 1\n", encoding="utf-8")
        result = runner.invoke(app, ["orgtree", "validate", "drift-engine-config", "--data", str(bad)])
        assert result.exit_code == 1
        assert "FAIL drift-engine-config" in result.stdout
