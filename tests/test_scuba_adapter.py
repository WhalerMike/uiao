"""Tests for ScubaAdapter (SCuBA / ScubaGear assessment ingestion)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from uiao_core.adapters.scuba_adapter import (
    SCUBA_TO_KSI_MAP,
    ScubaAdapter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SCUBAGEAR_REPORT = {
    "TestResults": [
        {
            "PolicyId": "MS.AAD.2.1v1",
            "Criticality": "Shall",
            "Requirement": "MFA SHALL be required for all users",
            "RequirementMet": True,
            "ActualValue": {"mfa_enabled": True, "user_count": 42},
            "NoSuchEvent": False,
        },
        {
            "PolicyId": "MS.AAD.1.1v1",
            "Criticality": "Shall",
            "Requirement": "Legacy authentication SHALL be blocked",
            "RequirementMet": False,
            "ActualValue": {"legacy_auth_blocked": False},
            "NoSuchEvent": False,
        },
        {
            "PolicyId": "MS.DEFENDER.2.1v1",
            "Criticality": "Shall",
            "Requirement": "Audit logging SHALL be enabled",
            "RequirementMet": True,
            "ActualValue": {"audit_log_enabled": True},
            "NoSuchEvent": False,
        },
        {
            "PolicyId": "MS.EXO.1.1v1",
            "Criticality": "Shall",
            "Requirement": "Transport encryption SHALL be enforced",
            "RequirementMet": True,
            "ActualValue": {"tls_version": "TLSv1.2"},
            "NoSuchEvent": False,
        },
    ]
}


@pytest.fixture
def report_file(tmp_path: Path) -> Path:
    """Write a sample ScubaGear JSON report to a temp file."""
    p = tmp_path / "scuba_report.json"
    p.write_text(json.dumps(SAMPLE_SCUBAGEAR_REPORT))
    return p


@pytest.fixture
def adapter(report_file: Path) -> ScubaAdapter:
    """Return a connected ScubaAdapter pointing at the sample report."""
    a = ScubaAdapter(config={"report_path": str(report_file)})
    a.connect()
    return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScubaAdapterInit:
    def test_adapter_id(self) -> None:
        a = ScubaAdapter()
        assert a.ADAPTER_ID == "scuba"

    def test_no_report_path(self) -> None:
        a = ScubaAdapter()
        provenance = a.connect()
        assert "no-report-loaded" in provenance.identity

    def test_report_path_set(self, report_file: Path) -> None:
        a = ScubaAdapter(config={"report_path": str(report_file)})
        assert a._report_path == report_file


class TestScubaAdapterConnect:
    def test_connect_loads_report(self, adapter: ScubaAdapter) -> None:
        assert adapter._raw_report is not None
        assert "TestResults" in adapter._raw_report

    def test_connect_provenance_identity(self, adapter: ScubaAdapter, report_file: Path) -> None:
        provenance = adapter.connect()
        assert "scuba:" in provenance.identity
        assert provenance.auth_method == "file"

    def test_extract_results(self, adapter: ScubaAdapter) -> None:
        results = adapter._extract_results()
        assert len(results) == 4
        assert results[0]["PolicyId"] == "MS.AAD.2.1v1"


class TestScubaAdapterNormalize:
    def test_normalize_returns_claim_set(self, adapter: ScubaAdapter) -> None:
        results = adapter._extract_results()
        claim_set = adapter.normalize(results)
        assert len(claim_set.claims) == 4

    def test_normalize_pass_result(self, adapter: ScubaAdapter) -> None:
        results = [r for r in adapter._extract_results() if r["RequirementMet"] is True]
        claim_set = adapter.normalize(results)
        for claim in claim_set.claims:
            assert claim.fields["scuba_result"] == "pass"

    def test_normalize_fail_result(self, adapter: ScubaAdapter) -> None:
        results = [r for r in adapter._extract_results() if r["RequirementMet"] is False]
        claim_set = adapter.normalize(results)
        assert all(c.fields["scuba_result"] == "fail" for c in claim_set.claims)

    def test_normalize_control_id_mapping(self, adapter: ScubaAdapter) -> None:
        results = adapter._extract_results()
        claim_set = adapter.normalize(results)
        # MS.AAD.2.1v1 should map to IA-2
        aad_claim = next(c for c in claim_set.claims if "MS.AAD.2.1v1" in c.claim_id)
        assert aad_claim.fields["control_id"] == "IA-2"

    def test_normalize_unmapped_policy(self, adapter: ScubaAdapter) -> None:
        # An unknown policy should get control_id "N/A"
        results = [{"PolicyId": "MS.UNKNOWN.1.1v1", "RequirementMet": True}]
        claim_set = adapter.normalize(results)
        assert claim_set.claims[0].fields["control_id"] == "N/A"


class TestScubaAdapterCollectAndAlign:
    def test_collect_and_align_structure(self, adapter: ScubaAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["vendor"] == "CISA SCuBA / ScubaGear"
        assert result["adapter_id"] == "scuba"
        assert "claims" in result
        assert "metadata" in result

    def test_collect_and_align_counts(self, adapter: ScubaAdapter) -> None:
        result = adapter.collect_and_align()
        meta = result["metadata"]
        assert meta["total_policies"] == 4
        assert meta["passing"] == 3
        assert meta["failing"] == 1

    def test_collect_and_align_overlay_ref(self, adapter: ScubaAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["vendor_overlay_ref"] == "data/vendor-overlays/scuba.yaml"


class TestScubaAdapterDriftDetection:
    def test_detect_drift_has_failing(self, adapter: ScubaAdapter) -> None:
        report = adapter.detect_drift()
        assert report.drift_type == "scuba-policy-regression"
        assert report.severity == "high"
        assert report.details["failing_policies"] == 1

    def test_detect_drift_no_failing(self) -> None:
        a = ScubaAdapter()
        a._raw_report = {
            "TestResults": [
                {"PolicyId": "MS.AAD.2.1v1", "RequirementMet": True}
            ]
        }
        report = a.detect_drift()
        assert report.severity == "none"


class TestScubaKsiMapping:
    def test_ksi_map_aad_entries(self) -> None:
        assert SCUBA_TO_KSI_MAP["MS.AAD.2.1v1"] == "IA-2"
        assert SCUBA_TO_KSI_MAP["MS.AAD.1.1v1"] == "AC-2"

    def test_ksi_map_defender_entries(self) -> None:
        assert SCUBA_TO_KSI_MAP["MS.DEFENDER.2.1v1"] == "AU-2"

    def test_get_ksi_evidence(self, adapter: ScubaAdapter) -> None:
        evidence = adapter.get_ksi_evidence("IA-2")
        assert len(evidence) == 1
        assert evidence[0]["PolicyId"] == "MS.AAD.2.1v1"

    def test_get_ksi_evidence_no_match(self, adapter: ScubaAdapter) -> None:
        evidence = adapter.get_ksi_evidence("XX-99")
        assert evidence == []
