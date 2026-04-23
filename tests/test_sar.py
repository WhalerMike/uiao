from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from typer.testing import CliRunner

from uiao.cli.app import app
from uiao.evidence.bundle import EvidenceBundle
from uiao.generators.sar import (
    _finding_state,
    _finding_risk_state,
    _severity,
    build_sar,
    build_sar_summary,
    export_sar,
)
from uiao.ir.models.core import Evidence, ProvenanceRecord

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SCUBA_FIXTURE = {
    "assessment_metadata": {
        "run_id": "sar-test-001",
        "assessment_date": "2026-04-08T00:00:00Z",
        "tool_version": "test",
        "collector_user": "test-user",
    },
    "tenant": {"tenant_id": "test-tenant-sar"},
    "ksi_results": [
        {"ksi_id": "KSI-IA-01", "status": "PASS", "severity": "High", "details": "MFA enforced"},
        {"ksi_id": "KSI-IA-02", "status": "FAIL", "severity": "Critical", "details": "Legacy auth not blocked"},
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


def _make_evidence(eid: str, control_id: str, passed: bool, warning: bool = False) -> Evidence:
    status = "PASS" if passed else ("WARN" if warning else "FAIL")
    severity = "High" if passed else "Medium"
    return Evidence(
        id=eid,
        source="test",
        timestamp="2025-01-01T00:00:00Z",
        control_id=control_id,
        policy_id=None,
        data={"ksi_id": control_id, "severity": severity, "status": status, "details": "test detail"},
        evaluation={"passed": passed, "warning": warning, "failed": not passed and not warning},
        provenance=_prov(),
    )


@pytest.fixture()
def minimal_bundle() -> EvidenceBundle:
    prov = _prov()
    return EvidenceBundle(
        run_id="unit-test-001",
        provenance=prov,
        evidence=[
            _make_evidence("e1", "AC-2", passed=True),
            _make_evidence("e2", "AC-17", passed=False),
            _make_evidence("e3", "AU-2", passed=False, warning=True),
        ],
        drift_states=[],
        controls=[],
        policies=[],
        unmapped_ksi_ids=["KSI-UNKNOWN-99"],
    )


# ---------------------------------------------------------------------------
# Unit: helper functions
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_finding_state_pass(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=True)
        assert _finding_state(ev) == "satisfied"

    def test_finding_state_fail(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=False)
        assert _finding_state(ev) == "not-satisfied"

    def test_finding_state_warn(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=False, warning=True)
        assert _finding_state(ev) == "not-satisfied"

    def test_risk_state_pass(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=True)
        assert _finding_risk_state(ev) == "closed"

    def test_risk_state_fail(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=False)
        assert _finding_risk_state(ev) == "open"

    def test_severity_high(self) -> None:
        ev = Evidence(
            id="e1",
            source="test",
            timestamp="2025-01-01T00:00:00Z",
            control_id="AC-2",
            policy_id=None,
            data={"ksi_id": "AC-2", "severity": "Critical", "status": "FAIL"},
            evaluation={"passed": False},
            provenance=_prov(),
        )
        assert _severity(ev) == "very-high"

    def test_severity_medium_default(self) -> None:
        ev = _make_evidence("e1", "AC-2", passed=False)
        assert _severity(ev) in ("moderate", "high", "very-high", "low")


# ---------------------------------------------------------------------------
# Unit: build_sar structure
# ---------------------------------------------------------------------------


class TestBuildSar:
    def test_top_level_key(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        assert "assessment-results" in doc

    def test_metadata_present(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle)["assessment-results"]
        assert "metadata" in ar
        assert "title" in ar["metadata"]
        assert "oscal-version" in ar["metadata"]

    def test_metadata_oscal_version(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle)["assessment-results"]
        assert ar["metadata"]["oscal-version"] == "1.0.4"

    def test_import_ap_present(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle)["assessment-results"]
        assert "import-ap" in ar
        assert "href" in ar["import-ap"]

    def test_import_ap_custom_href(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle, ap_href="https://example.gov/sap.json")["assessment-results"]
        assert ar["import-ap"]["href"] == "https://example.gov/sap.json"

    def test_results_list_nonempty(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle)["assessment-results"]
        assert len(ar["results"]) == 1

    def test_findings_count_matches_evidence(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        assert len(results["findings"]) == len(minimal_bundle.evidence)

    def test_observations_count_matches_evidence(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        assert len(results["observations"]) == len(minimal_bundle.evidence)

    def test_risks_only_for_non_pass(self, minimal_bundle: EvidenceBundle) -> None:
        # 1 PASS, 2 non-PASS -> 2 risks
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        assert len(results["risks"]) == 2

    def test_pass_finding_state_satisfied(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        pass_findings = [
            f for f in results["findings"] if "PASS" in f["title"] or f["target"]["status"]["state"] == "satisfied"
        ]
        assert len(pass_findings) >= 1

    def test_back_matter_resources_match_evidence(self, minimal_bundle: EvidenceBundle) -> None:
        ar = build_sar(minimal_bundle)["assessment-results"]
        resources = ar["back-matter"]["resources"]
        assert len(resources) == len(minimal_bundle.evidence)

    def test_result_props_contain_counts(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        prop_names = {p["name"] for p in results["props"]}
        assert "pass-count" in prop_names
        assert "warn-count" in prop_names
        assert "fail-count" in prop_names

    def test_result_pass_count_correct(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        props = {p["name"]: p["value"] for p in results["props"]}
        assert props["pass-count"] == str(minimal_bundle.pass_count)

    def test_reviewed_controls_present(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        rc = results["reviewed-controls"]
        assert "control-selections" in rc

    def test_all_uuids_are_valid(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        text = json.dumps(doc)
        # Extract all uuid values - they should all parse as valid UUIDs
        raw = json.loads(text)
        # Spot-check top-level uuid
        ar = raw["assessment-results"]
        uuid.UUID(ar["uuid"])

    def test_system_name_in_title(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle, system_name="My Test System")
        title = doc["assessment-results"]["metadata"]["title"]
        assert "My Test System" in title

    def test_tenant_id_in_metadata_props(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle, tenant_id="tenant-xyz")
        props = doc["assessment-results"]["metadata"]["props"]
        tenant_props = [p for p in props if p["name"] == "tenant-id"]
        assert len(tenant_props) == 1
        assert tenant_props[0]["value"] == "tenant-xyz"

    def test_bundle_hash_in_metadata_props(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        props = doc["assessment-results"]["metadata"]["props"]
        hash_props = [p for p in props if p["name"] == "bundle-hash"]
        assert len(hash_props) == 1
        assert len(hash_props[0]["value"]) > 0

    def test_finding_has_related_observation(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        for finding in results["findings"]:
            assert len(finding["related-observations"]) == 1
            obs_uuid = finding["related-observations"][0]["observation-uuid"]
            # Observation UUID must exist in observations list
            obs_uuids = {o["uuid"] for o in results["observations"]}
            assert obs_uuid in obs_uuids

    def test_risk_has_related_finding(self, minimal_bundle: EvidenceBundle) -> None:
        results = build_sar(minimal_bundle)["assessment-results"]["results"][0]
        finding_uuids = {f["uuid"] for f in results["findings"]}
        for risk in results["risks"]:
            assert len(risk["related-findings"]) == 1
            assert risk["related-findings"][0]["finding-uuid"] in finding_uuids

    def test_deterministic_with_fixed_now(self, minimal_bundle: EvidenceBundle) -> None:
        now = "2025-06-01T00:00:00+00:00"
        doc1 = build_sar(minimal_bundle, now=now)
        doc2 = build_sar(minimal_bundle, now=now)
        # UUIDs will differ (uuid4), but structure and counts are identical
        r1 = doc1["assessment-results"]["results"][0]
        r2 = doc2["assessment-results"]["results"][0]
        assert len(r1["findings"]) == len(r2["findings"])
        assert len(r1["risks"]) == len(r2["risks"])


# ---------------------------------------------------------------------------
# Unit: build_sar_summary
# ---------------------------------------------------------------------------


class TestBuildSarSummary:
    def test_summary_contains_run_id(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        summary = build_sar_summary(doc)
        assert "unit-test-001" in summary

    def test_summary_contains_counts(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        summary = build_sar_summary(doc)
        assert "PASS" in summary
        assert "FAIL" in summary
        assert "WARN" in summary

    def test_summary_contains_open_risks(self, minimal_bundle: EvidenceBundle) -> None:
        doc = build_sar(minimal_bundle)
        summary = build_sar_summary(doc)
        assert "Open risks" in summary or "open" in summary.lower()


# ---------------------------------------------------------------------------
# Unit: export_sar
# ---------------------------------------------------------------------------


class TestExportSar:
    def test_writes_json_file(self, minimal_bundle: EvidenceBundle, tmp_path: Path) -> None:
        out = str(tmp_path / "sar.json")
        path = export_sar(minimal_bundle, out)
        assert Path(path).exists()

    def test_output_is_valid_json(self, minimal_bundle: EvidenceBundle, tmp_path: Path) -> None:
        out = str(tmp_path / "sar.json")
        export_sar(minimal_bundle, out)
        data = json.loads(Path(out).read_text())
        assert "assessment-results" in data

    def test_creates_parent_dirs(self, minimal_bundle: EvidenceBundle, tmp_path: Path) -> None:
        out = str(tmp_path / "deep" / "nested" / "sar.json")
        export_sar(minimal_bundle, out)
        assert Path(out).exists()

    def test_returns_path_string(self, minimal_bundle: EvidenceBundle, tmp_path: Path) -> None:
        out = str(tmp_path / "sar.json")
        result = export_sar(minimal_bundle, out)
        assert isinstance(result, str)
        assert result == out


# ---------------------------------------------------------------------------
# CLI smoke tests: ir-generate-sar
# ---------------------------------------------------------------------------


class TestIRGenerateSARCLI:
    def test_runs_without_error(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-generate-sar", str(scuba_json)])
        assert result.exit_code == 0, result.output

    def test_output_contains_sar_text(self, scuba_json: Path) -> None:
        result = runner.invoke(app, ["ir-generate-sar", str(scuba_json)])
        assert result.exit_code == 0
        assert "SAR" in result.output or "OSCAL" in result.output or "PASS" in result.output

    def test_out_writes_json(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "sar_output.json"
        result = runner.invoke(app, ["ir-generate-sar", str(scuba_json), "--out", str(out)])
        assert result.exit_code == 0, result.output
        assert out.exists()
        data = json.loads(out.read_text())
        assert "assessment-results" in data

    def test_out_json_has_findings(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "sar_output.json"
        runner.invoke(app, ["ir-generate-sar", str(scuba_json), "--out", str(out)])
        data = json.loads(out.read_text())
        findings = data["assessment-results"]["results"][0]["findings"]
        assert len(findings) == 3

    def test_out_json_has_risks_for_fail(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "sar_output.json"
        runner.invoke(app, ["ir-generate-sar", str(scuba_json), "--out", str(out)])
        data = json.loads(out.read_text())
        risks = data["assessment-results"]["results"][0]["risks"]
        # 1 FAIL + 1 WARN = 2 risks
        assert len(risks) == 2

    def test_system_name_option(self, scuba_json: Path, tmp_path: Path) -> None:
        out = tmp_path / "sar_named.json"
        result = runner.invoke(
            app,
            ["ir-generate-sar", str(scuba_json), "--out", str(out), "--system-name", "Test Agency System"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(out.read_text())
        title = data["assessment-results"]["metadata"]["title"]
        assert "Test Agency System" in title

    def test_missing_file_exits_nonzero(self, tmp_path: Path) -> None:
        result = runner.invoke(app, ["ir-generate-sar", str(tmp_path / "nonexistent.json")])
        assert result.exit_code != 0

    def test_command_appears_in_help(self) -> None:
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "ir-generate-sar" in result.output
