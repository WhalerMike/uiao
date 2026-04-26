from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.evidence.bundle import EvidenceBundle
from uiao.generators.ssp_inject import (
    _find_component_uuid,
    _oscal_status,
    inject_scuba_evidence,
    live_ssp_summary,
)
from uiao.ir.models.core import Evidence, ProvenanceRecord

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "ssp-inject-test-001",
        "assessment_date": "2026-04-08T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-ssp"},
    "ksi_results": [
        {"ksi_id": "KSI-IA-01", "status": "PASS", "severity": "High", "details": "MFA enforced"},
        {"ksi_id": "KSI-IA-02", "status": "FAIL", "severity": "Critical", "details": "Legacy auth"},
        {"ksi_id": "KSI-AC-01", "status": "WARN", "severity": "Medium", "details": "Review overdue"},
    ],
}


@pytest.fixture()
def scuba_json(tmp_path: Path) -> Path:
    p = tmp_path / "normalized.json"
    p.write_text(json.dumps(SCUBA_FIXTURE), encoding="utf-8")
    return p


def _prov() -> ProvenanceRecord:
    return ProvenanceRecord(source="test", timestamp="2025-01-01T00:00:00Z", version="1")


def _ev(eid: str, ctrl: str, passed: bool, warning: bool = False) -> Evidence:
    status = "PASS" if passed else ("WARN" if warning else "FAIL")
    return Evidence(
        id=eid,
        source="test",
        timestamp="2025-01-01T00:00:00Z",
        control_id=ctrl,
        policy_id=None,
        data={"ksi_id": ctrl, "severity": "High", "status": status, "details": "test"},
        evaluation={
            "passed": passed,
            "warning": warning,
            "failed": not passed and not warning,
            "canonical_hash": "abc123def456",
        },
        provenance=_prov(),
    )


@pytest.fixture()
def minimal_bundle() -> EvidenceBundle:
    prov = _prov()
    return EvidenceBundle(
        run_id="ssp-unit-001",
        provenance=prov,
        evidence=[
            _ev("e1", "AC-2", passed=True),
            _ev("e2", "AC-17", passed=False),
            _ev("e3", "AU-2", passed=False, warning=True),
        ],
        drift_states=[],
        controls=[],
        policies=[],
        unmapped_ksi_ids=[],
    )


def _minimal_ssp() -> dict:
    """Build a minimal OSCAL SSP skeleton for testing."""
    comp_uuid = "aaaa-bbbb-cccc-dddd-eeee"
    return {
        "system-implementation": {"components": [{"uuid": comp_uuid, "type": "service", "title": "TestComp"}]},
        "control-implementation": {
            "implemented-requirements": [
                {"uuid": "req-1", "control-id": "AC-2", "remarks": "pillar: identity"},
                {"uuid": "req-2", "control-id": "AC-17", "remarks": "pillar: overlay"},
                {"uuid": "req-3", "control-id": "AU-2", "remarks": "pillar: telemetry"},
                {"uuid": "req-4", "control-id": "SI-4", "remarks": "no evidence"},
            ]
        },
    }


# ---------------------------------------------------------------------------
# Unit: helper functions
# ---------------------------------------------------------------------------


class TestOscalStatus:
    def test_pass_returns_implemented(self) -> None:
        assert _oscal_status({"passed": True}) == "implemented"

    def test_warn_returns_partial(self) -> None:
        assert _oscal_status({"passed": False, "warning": True}) == "partially-implemented"

    def test_fail_returns_not_implemented(self) -> None:
        assert _oscal_status({"passed": False, "warning": False}) == "not-implemented"

    def test_empty_eval_returns_not_implemented(self) -> None:
        assert _oscal_status({}) == "not-implemented"


class TestFindComponentUuid:
    def test_returns_first_component_uuid(self) -> None:
        ssp = {"system-implementation": {"components": [{"uuid": "comp-111"}, {"uuid": "comp-222"}]}}
        assert _find_component_uuid(ssp, "KSI-IA-01") == "comp-111"

    def test_returns_none_if_no_components(self) -> None:
        ssp = {"system-implementation": {"components": []}}
        assert _find_component_uuid(ssp, "KSI-IA-01") is None

    def test_returns_none_if_no_system_implementation(self) -> None:
        ssp = {}
        assert _find_component_uuid(ssp, "KSI-IA-01") is None


# ---------------------------------------------------------------------------
# Unit: inject_scuba_evidence
# ---------------------------------------------------------------------------


class TestInjectScubaEvidence:
    def test_injects_implementation_status(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        pass_props = {p["name"]: p["value"] for p in reqs["AC-2"].get("props", [])}
        assert pass_props.get("implementation-status") == "implemented"

    def test_fail_evidence_sets_not_implemented(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        fail_props = {p["name"]: p["value"] for p in reqs["AC-17"].get("props", [])}
        assert fail_props.get("implementation-status") == "not-implemented"

    def test_warn_evidence_sets_partial(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        warn_props = {p["name"]: p["value"] for p in reqs["AU-2"].get("props", [])}
        assert warn_props.get("implementation-status") == "partially-implemented"

    def test_injects_statement(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        assert "statements" in reqs["AC-2"]
        assert len(reqs["AC-2"]["statements"]) == 1

    def test_statement_has_by_components_when_component_exists(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        stmt = reqs["AC-2"]["statements"][0]
        assert "by-components" in stmt
        assert len(stmt["by-components"]) == 1

    def test_by_component_has_evidence_hash_prop(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        bc = reqs["AC-2"]["statements"][0]["by-components"][0]
        prop_names = {p["name"] for p in bc["props"]}
        assert "evidence-hash" in prop_names
        assert "assessment-date" in prop_names

    def test_no_injection_for_unmatched_control(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        # SI-4 has no evidence in the bundle
        assert "statements" not in reqs["SI-4"]

    def test_remarks_updated_with_run_tag(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        assert "ssp-unit-001" in reqs["AC-2"]["remarks"]

    def test_idempotent_injection(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        inject_scuba_evidence(ssp, minimal_bundle)
        reqs = {r["control-id"]: r for r in ssp["control-implementation"]["implemented-requirements"]}
        # Should still have exactly 1 statement per control (idempotent)
        assert len(reqs["AC-2"]["statements"]) == 1

    def test_skips_evidence_with_no_control_id(self) -> None:
        ssp = _minimal_ssp()
        ev_no_ctrl = Evidence(
            id="e-no-ctrl",
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            control_id=None,
            policy_id=None,
            data={"ksi_id": "UNKNOWN", "status": "FAIL"},
            evaluation={"passed": False},
            provenance=_prov(),
        )
        bundle = EvidenceBundle(
            run_id="test",
            provenance=_prov(),
            evidence=[ev_no_ctrl],
            drift_states=[],
            controls=[],
            policies=[],
            unmapped_ksi_ids=["UNKNOWN"],
        )
        # Should not raise
        inject_scuba_evidence(ssp, bundle)
        reqs = ssp["control-implementation"]["implemented-requirements"]
        for r in reqs:
            assert "statements" not in r

    def test_returns_ssp_dict(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        result = inject_scuba_evidence(ssp, minimal_bundle)
        assert result is ssp


# ---------------------------------------------------------------------------
# Unit: live_ssp_summary
# ---------------------------------------------------------------------------


class TestLiveSspSummary:
    def test_contains_run_id(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        summary = live_ssp_summary({"system-security-plan": ssp}, minimal_bundle)
        assert "ssp-unit-001" in summary

    def test_contains_total_requirements(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        summary = live_ssp_summary({"system-security-plan": ssp}, minimal_bundle)
        assert "4" in summary  # 4 total reqs in minimal ssp

    def test_contains_evidence_injected_count(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        summary = live_ssp_summary({"system-security-plan": ssp}, minimal_bundle)
        assert "3" in summary  # 3 evidence items injected

    def test_contains_pass_warn_fail(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        summary = live_ssp_summary({"system-security-plan": ssp}, minimal_bundle)
        assert "1 / 1 / 1" in summary or "PASS" in summary or "Implemented" in summary

    def test_handles_ssp_without_wrapper_key(self, minimal_bundle: EvidenceBundle) -> None:
        ssp = _minimal_ssp()
        inject_scuba_evidence(ssp, minimal_bundle)
        # Pass the ssp dict directly (without "system-security-plan" wrapper)
        summary = live_ssp_summary(ssp, minimal_bundle)
        assert "ssp-unit-001" in summary


# ---------------------------------------------------------------------------
# Integration: build_live_ssp (uses real canon/data files)
# ---------------------------------------------------------------------------


class TestBuildLiveSsp:
    def test_writes_ssp_json_file(self, scuba_json: Path, tmp_path: Path) -> None:
        from uiao.generators.ssp_inject import build_live_ssp

        out = tmp_path / "live-ssp.json"
        path = build_live_ssp(normalized_json_path=scuba_json, output_path=str(out))
        assert Path(path).exists()

    def test_output_is_valid_oscal_ssp(self, scuba_json: Path, tmp_path: Path) -> None:
        from uiao.generators.ssp_inject import build_live_ssp

        out = tmp_path / "live-ssp.json"
        build_live_ssp(normalized_json_path=scuba_json, output_path=str(out))
        data = json.loads(Path(out).read_text())
        assert "system-security-plan" in data

    def test_output_has_implemented_requirements(self, scuba_json: Path, tmp_path: Path) -> None:
        from uiao.generators.ssp_inject import build_live_ssp

        out = tmp_path / "live-ssp.json"
        build_live_ssp(normalized_json_path=scuba_json, output_path=str(out))
        data = json.loads(Path(out).read_text())
        ssp = data["system-security-plan"]
        reqs = ssp["control-implementation"]["implemented-requirements"]
        assert len(reqs) > 0

    def test_some_requirements_have_implementation_status(self, scuba_json: Path, tmp_path: Path) -> None:
        from uiao.generators.ssp_inject import build_live_ssp

        out = tmp_path / "live-ssp.json"
        build_live_ssp(normalized_json_path=scuba_json, output_path=str(out))
        data = json.loads(Path(out).read_text())
        ssp = data["system-security-plan"]
        reqs = ssp["control-implementation"]["implemented-requirements"]
        injected = [r for r in reqs if any(p.get("name") == "implementation-status" for p in r.get("props", []))]
        assert len(injected) > 0

    def test_creates_parent_dirs(self, scuba_json: Path, tmp_path: Path) -> None:
        from uiao.generators.ssp_inject import build_live_ssp

        out = tmp_path / "deep" / "nested" / "live-ssp.json"
        build_live_ssp(normalized_json_path=scuba_json, output_path=str(out))
        assert out.exists()


# ---------------------------------------------------------------------------
# CLI smoke tests: ir-ssp-inject
# ---------------------------------------------------------------------------


class TestIRSspInjectCLI:
    def test_runs_without_error(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "live-ssp.json"
        result = runner.invoke(app, ["ir", "ssp-inject", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output

    def test_writes_ssp_file(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "live-ssp.json"
        runner.invoke(app, ["ir", "ssp-inject", str(scuba_json), "--out", str(out)])
        assert out.exists()

    def test_output_contains_live_ssp_text(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "live-ssp.json"
        result = runner.invoke(app, ["ir", "ssp-inject", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0
        assert "Live SSP" in result.output or "SSP" in result.output

    def test_written_file_is_oscal_ssp(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "live-ssp.json"
        runner.invoke(app, ["ir", "ssp-inject", str(scuba_json), "--out", str(out)])
        data = json.loads(out.read_text())
        assert "system-security-plan" in data

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        out = tmp_path / "live-ssp.json"
        result = runner.invoke(app, ["ir", "ssp-inject", str(tmp_path / "nonexistent.json"), "--out", str(out)])
        assert result.exit_code != 0

    def test_command_appears_in_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ir" in result.output
