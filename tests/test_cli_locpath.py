"""Tests for the ``uiao locpath ...`` CLI (ADR-102 / UIAO_194, ADR-104).

The LocPath library modules (registry, hr_assign, mover, drift,
e911_compliance, entra_exposure) are exercised in depth by the
``test_locpath_*`` suite; this file covers the operator-reachable CLI
veneer over them — happy-path and failure-mode for every command, per the
AGENTS.md "new CLI commands ship with happy-path + failure-mode tests"
rule.
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _hr(employee_id: str, location_code: str) -> dict:
    return {
        "employeeId": employee_id,
        "locationCode": location_code,
        "extractedAt": "2026-06-18T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# help / wiring
# ---------------------------------------------------------------------------


class TestHelpWiring:
    def test_locpath_help_lists_commands(self) -> None:
        result = runner.invoke(app, ["locpath", "--help"])
        assert result.exit_code == 0
        for cmd in ("validate", "assign", "mover", "policy-drift", "e911-check", "expose"):
            assert cmd in result.stdout

    def test_validate_help_lists_subcommands(self) -> None:
        result = runner.invoke(app, ["locpath", "validate", "--help"])
        assert result.exit_code == 0
        assert "registry" in result.stdout
        assert "duty-station-map" in result.stdout

    def test_expose_help_lists_subcommands(self) -> None:
        result = runner.invoke(app, ["locpath", "expose", "--help"])
        assert result.exit_code == 0
        assert "groups" in result.stdout
        assert "admin-units" in result.stdout


# ---------------------------------------------------------------------------
# validate (phase 1)
# ---------------------------------------------------------------------------


class TestValidate:
    def test_registry_canonical_passes(self) -> None:
        result = runner.invoke(app, ["locpath", "validate", "registry"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout
        assert "reference" in result.stdout

    def test_duty_station_map_canonical_passes(self) -> None:
        result = runner.invoke(app, ["locpath", "validate", "duty-station-map"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout

    def test_registry_missing_file_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["locpath", "validate", "registry", "--registry", str(tmp_path / "nope.yaml")])
        assert result.exit_code == 1

    def test_registry_invalid_yaml_fails(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text("registry_id: x\nnodes: not-a-list\n", encoding="utf-8")
        result = runner.invoke(app, ["locpath", "validate", "registry", "--registry", str(bad)])
        assert result.exit_code == 1
        assert "invalid" in result.stdout.lower()


# ---------------------------------------------------------------------------
# assign (phase 2)
# ---------------------------------------------------------------------------


class TestAssign:
    def test_assign_resolves_and_reports_findings(self, tmp_path: Path) -> None:
        export = _write_json(
            tmp_path / "hr.json",
            [_hr("E001", "HQ"), _hr("E002", "HQ-B3-210"), _hr("E003", "REMOTE-XYZ"), _hr("E004", "")],
        )
        out = tmp_path / "plan.json"
        result = runner.invoke(app, ["locpath", "assign", str(export), "--out", str(out)])
        assert result.exit_code == 0
        assert "Assignments : 2" in result.stdout
        assert "REMOTE-XYZ" in result.stdout

        plan = json.loads(out.read_text(encoding="utf-8"))
        assert len(plan["assignments"]) == 2
        assert {a["employee_id"] for a in plan["assignments"]} == {"E001", "E002"}
        # E001 -> Site; E002 -> Space under the Site, both governed by the Site.
        assert all(a["site_path"] == "/USA/MD/ANNAPOLIS-HQ" for a in plan["assignments"])
        codes = {f["error_code"] for f in plan["findings"]}
        assert "GOV-LOCPATH-002" in codes  # unmapped REMOTE-XYZ
        assert "GOV-LOCPATH-001" in codes  # empty code

    def test_assign_strict_exits_nonzero_on_findings(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E003", "REMOTE-XYZ")])
        result = runner.invoke(app, ["locpath", "assign", str(export), "--strict"])
        assert result.exit_code == 1

    def test_assign_clean_input_strict_passes(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        result = runner.invoke(app, ["locpath", "assign", str(export), "--strict"])
        assert result.exit_code == 0

    def test_assign_empty_export_fails(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [])
        result = runner.invoke(app, ["locpath", "assign", str(export)])
        assert result.exit_code == 1

    def test_assign_missing_file_fails(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["locpath", "assign", str(tmp_path / "nope.json")])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# mover (phase 3)
# ---------------------------------------------------------------------------


class TestMover:
    def test_mover_detects_move_and_join(self, tmp_path: Path) -> None:
        prev = _write_json(tmp_path / "prev.json", [_hr("E001", "HQ")])
        cur = _write_json(tmp_path / "cur.json", [_hr("E001", "HQ-B3-210"), _hr("E002", "HQ")])
        out = tmp_path / "moves.json"
        result = runner.invoke(
            app, ["locpath", "mover", "--previous", str(prev), "--current", str(cur), "--out", str(out)]
        )
        assert result.exit_code == 0
        assert "joiners=1" in result.stdout
        assert "movers=1" in result.stdout

        plan = json.loads(out.read_text(encoding="utf-8"))
        kinds = {e["employee_id"]: e["kind"] for e in plan["events"]}
        assert kinds == {"E001": "move", "E002": "join"}
        assert len(plan["findings"]) == 2

    def test_mover_strict_exits_nonzero_on_events(self, tmp_path: Path) -> None:
        prev = _write_json(tmp_path / "prev.json", [_hr("E001", "HQ")])
        cur = _write_json(tmp_path / "cur.json", [_hr("E001", "HQ-B3-210")])
        result = runner.invoke(app, ["locpath", "mover", "--previous", str(prev), "--current", str(cur), "--strict"])
        assert result.exit_code == 1

    def test_mover_no_change_no_events(self, tmp_path: Path) -> None:
        same = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        result = runner.invoke(app, ["locpath", "mover", "--previous", str(same), "--current", str(same), "--strict"])
        assert result.exit_code == 0
        assert "0 event(s)" in result.stdout


# ---------------------------------------------------------------------------
# policy-drift (phase 3)
# ---------------------------------------------------------------------------


class TestPolicyDrift:
    def test_policy_drift_flags_breakout_mismatch(self, tmp_path: Path) -> None:
        observed = _write_json(
            tmp_path / "obs.json",
            [{"loc_path": "/USA/MD/ANNAPOLIS-HQ", "breakout_observed": "Centralized"}],
        )
        out = tmp_path / "drift.json"
        result = runner.invoke(app, ["locpath", "policy-drift", str(observed), "--out", str(out)])
        assert result.exit_code == 0
        findings = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["error_code"] == "GOV-LOCPATH-009" for f in findings)

    def test_policy_drift_strict_exits_nonzero(self, tmp_path: Path) -> None:
        observed = _write_json(
            tmp_path / "obs.json",
            [{"loc_path": "/USA/MD/ANNAPOLIS-HQ", "breakout_observed": "Centralized"}],
        )
        result = runner.invoke(app, ["locpath", "policy-drift", str(observed), "--strict"])
        assert result.exit_code == 1

    def test_policy_drift_unregistered_site_is_semantic_gap(self, tmp_path: Path) -> None:
        observed = _write_json(tmp_path / "obs.json", [{"loc_path": "/USA/MD/GHOST-SITE"}])
        out = tmp_path / "drift.json"
        result = runner.invoke(app, ["locpath", "policy-drift", str(observed), "--out", str(out)])
        assert result.exit_code == 0
        findings = json.loads(out.read_text(encoding="utf-8"))
        assert any(f["error_code"] == "GOV-LOCPATH-007" for f in findings)


# ---------------------------------------------------------------------------
# e911-check (ADR-104)
# ---------------------------------------------------------------------------


class TestE911Check:
    def test_e911_canonical_registry_is_complete(self) -> None:
        result = runner.invoke(app, ["locpath", "e911-check"])
        assert result.exit_code == 0
        assert "PASS" in result.stdout

    def test_e911_strict_passes_on_complete_canon(self) -> None:
        result = runner.invoke(app, ["locpath", "e911-check", "--strict"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# expose (phase 4)
# ---------------------------------------------------------------------------


class TestExpose:
    def test_groups_assigned_membership(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ"), _hr("E002", "HQ-B3-210")])
        out = tmp_path / "groups.json"
        result = runner.invoke(app, ["locpath", "expose", "groups", str(export), "--out", str(out)])
        assert result.exit_code == 0
        assert "assigned-membership" in result.stdout
        specs = json.loads(out.read_text(encoding="utf-8"))
        assert len(specs) == 1
        assert specs[0]["name"] == "LocPath-Site-ANNAPOLIS-HQ-Users"
        assert sorted(specs[0]["member_employee_ids"]) == ["E001", "E002"]
        # Assigned mode carries no rule, so no graph_body is rendered (needs object_ids).
        assert specs[0]["membership_rule"] is None
        assert specs[0]["graph_body"] is None

    def test_admin_units_dynamic_rule(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        out = tmp_path / "aus.json"
        result = runner.invoke(
            app,
            ["locpath", "expose", "admin-units", str(export), "--locator", "ext_locPath", "--out", str(out)],
        )
        assert result.exit_code == 0
        assert "dynamic-rule" in result.stdout
        specs = json.loads(out.read_text(encoding="utf-8"))
        assert specs[0]["name"] == "AU-Site-ANNAPOLIS-HQ"
        assert specs[0]["membership_rule"] == '(ext_locPath -startsWith "/USA/MD/ANNAPOLIS-HQ")'
        assert specs[0]["graph_body"]["membershipType"] == "Dynamic"
        assert specs[0]["graph_body"]["isMemberManagementRestricted"] is True

    def test_admin_units_unrestricted_flag(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        out = tmp_path / "aus.json"
        result = runner.invoke(
            app, ["locpath", "expose", "admin-units", str(export), "--unrestricted", "--out", str(out)]
        )
        assert result.exit_code == 0
        specs = json.loads(out.read_text(encoding="utf-8"))
        assert specs[0]["restricted_management"] is False

    def test_groups_prefix_filter(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        out = tmp_path / "groups.json"
        result = runner.invoke(
            app,
            ["locpath", "expose", "groups", str(export), "--prefix", "/USA/MD/ANNAPOLIS-HQ", "--out", str(out)],
        )
        assert result.exit_code == 0
        specs = json.loads(out.read_text(encoding="utf-8"))
        assert len(specs) == 1

    def test_groups_bad_prefix_fails(self, tmp_path: Path) -> None:
        export = _write_json(tmp_path / "hr.json", [_hr("E001", "HQ")])
        result = runner.invoke(app, ["locpath", "expose", "groups", str(export), "--prefix", "/USA/MD/GHOST"])
        assert result.exit_code == 1
