"""Tests for `uiao orgtree {validate,show,resolve,export} ...`.

Validate-verb coverage: six per-artifact verbs + the aggregate
`validate all`, against the canonical orgpath data shipped under
``uiao.canon.data.orgpath``. Bad-input paths are covered by writing a
short malformed YAML to a temp file and pointing ``--data`` at it.

Show / resolve / export coverage: happy-path and not-found paths over
the same canonical data; export-codebook round-trips through JSON.
"""

from __future__ import annotations

import json
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


# ---------------------------------------------------------------------------
# Show — print one entry from a canonical artifact
# ---------------------------------------------------------------------------


class TestShow:
    def test_show_codebook_entry(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "codebook", "ORG"])
        assert result.exit_code == 0, result.stdout
        # The Rich table breaks across lines for narrow terminals; check
        # for components that survive any wrapping.
        assert "ORG" in result.stdout
        assert "Enterprise Root" in result.stdout
        assert "UIAO_151" in result.stdout

    def test_show_codebook_entry_not_found(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "codebook", "ORG-NOTREAL"])
        assert result.exit_code == 1
        assert "NOT FOUND" in result.stdout
        assert "codebook entry" in result.stdout
        # Pluralization sanity (no "entrys"):
        assert "Known codebook entries" in result.stdout

    def test_show_dynamic_group(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "dynamic-group", "OrgTree-FIN-Users"])
        assert result.exit_code == 0, result.stdout
        assert "OrgTree-FIN-Users" in result.stdout
        assert "UIAO_152" in result.stdout

    def test_show_dynamic_group_not_found(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "dynamic-group", "OrgTree-NOTREAL"])
        assert result.exit_code == 1
        assert "NOT FOUND" in result.stdout

    def test_show_admin_unit(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "admin-unit", "AU-ORG-FIN"])
        assert result.exit_code == 0, result.stdout
        assert "AU-ORG-FIN" in result.stdout
        assert "UIAO_154" in result.stdout

    def test_show_admin_unit_not_found(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "admin-unit", "AU-NOTREAL"])
        assert result.exit_code == 1

    def test_show_device_plane(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "device-plane", "extensionAttribute1"])
        assert result.exit_code == 0, result.stdout
        assert "extensionAttribute1" in result.stdout
        assert "UIAO_153" in result.stdout

    def test_show_device_plane_not_found(self) -> None:
        result = runner.invoke(app, ["orgtree", "show", "device-plane", "no-such-plane"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Resolve — cross-reference dynamic group rules against the codebook
# ---------------------------------------------------------------------------


class TestResolve:
    def test_resolve_dynamic_group_happy(self) -> None:
        result = runner.invoke(app, ["orgtree", "resolve", "dynamic-group", "OrgTree-FIN-Users"])
        assert result.exit_code == 0, result.stdout
        assert "OrgTree-FIN-Users" in result.stdout
        assert "ORG-FIN" in result.stdout
        # All references should resolve OK against the canonical codebook.
        assert "OK" in result.stdout
        assert "MISSING" not in result.stdout
        assert "FAIL" not in result.stdout

    def test_resolve_dynamic_group_not_found(self) -> None:
        result = runner.invoke(app, ["orgtree", "resolve", "dynamic-group", "OrgTree-NOTREAL"])
        assert result.exit_code == 1
        assert "NOT FOUND" in result.stdout


# ---------------------------------------------------------------------------
# Export — emit canon as JSON for downstream consumers
# ---------------------------------------------------------------------------


class TestExport:
    def test_export_codebook_to_stdout(self) -> None:
        result = runner.invoke(app, ["orgtree", "export", "codebook"])
        assert result.exit_code == 0, result.stdout
        # Must be valid JSON with the shape UIAO_159 §F3 expects.
        payload = json.loads(result.stdout)
        assert payload["document_id"] == "UIAO_151"
        assert isinstance(payload["entries"], list)
        assert len(payload["entries"]) > 0
        first = payload["entries"][0]
        # Each entry must expose the keys the pwsh Get-OrgTreeValidationReport
        # cmdlet keys off ($entry.code).
        assert "code" in first
        assert "level" in first
        assert "description" in first

    def test_export_codebook_to_file(self, tmp_path: Path) -> None:
        out = tmp_path / "codebook.json"
        result = runner.invoke(app, ["orgtree", "export", "codebook", "--out", str(out)])
        assert result.exit_code == 0, result.stdout
        assert out.exists()
        payload = json.loads(out.read_text(encoding="utf-8"))
        assert payload["document_id"] == "UIAO_151"
        assert any(e["code"] == "ORG" for e in payload["entries"])

    def test_export_codebook_round_trip_with_validate(self, tmp_path: Path) -> None:
        """Export and re-validate isn't a round-trip in the YAML sense
        (export emits JSON, validate reads YAML), but both must agree on
        which codes count as valid. Spot-check that every exported code
        round-trips through Test-OrgPathFormat's regex (UIAO_151)."""
        import re

        result = runner.invoke(app, ["orgtree", "export", "codebook"])
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        regex = re.compile(payload["regex"])
        for entry in payload["entries"]:
            assert regex.match(entry["code"]), f"exported code violates its own regex: {entry['code']}"
