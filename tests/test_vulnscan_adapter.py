"""Tests for the Vulnerability Scanner Adapter (conformance / telemetry)."""

from __future__ import annotations

import pytest

from uiao_impl.adapters.vulnscan_adapter import VulnScanAdapter
from uiao_impl.adapters.database_base import (
    ClaimObject, ClaimSet, ConnectionProvenance,
    DriftReport, EvidenceObject, QueryProvenance, SchemaMappingObject,
)


@pytest.fixture
def adapter() -> VulnScanAdapter:
    return VulnScanAdapter({
        "scanner": "tenable",
        "endpoint": "https://cloud.tenable.com/api",
        "scan_policy": "fedramp-moderate",
    })


@pytest.fixture
def adapter_empty() -> VulnScanAdapter:
    return VulnScanAdapter()


class TestInstantiation:
    def test_adapter_id(self, adapter: VulnScanAdapter) -> None:
        assert adapter.ADAPTER_ID == "vuln-scan"

    def test_default_scanner(self, adapter_empty: VulnScanAdapter) -> None:
        assert adapter_empty._scanner == "generic"

    def test_custom_scanner(self, adapter: VulnScanAdapter) -> None:
        assert adapter._scanner == "tenable"

    def test_is_database_adapter_base(self, adapter: VulnScanAdapter) -> None:
        from uiao_impl.adapters.database_base import DatabaseAdapterBase
        assert isinstance(adapter, DatabaseAdapterBase)


class TestConnect:
    def test_returns_provenance(self, adapter: VulnScanAdapter) -> None:
        assert isinstance(adapter.connect(), ConnectionProvenance)

    def test_identity_includes_scanner(self, adapter: VulnScanAdapter) -> None:
        assert "tenable" in adapter.connect().identity

    def test_endpoint(self, adapter: VulnScanAdapter) -> None:
        assert adapter.connect().endpoint == "https://cloud.tenable.com/api"


class TestDiscoverSchema:
    def test_returns_mapping(self, adapter: VulnScanAdapter) -> None:
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)

    def test_has_cve_field(self, adapter: VulnScanAdapter) -> None:
        assert "cve_id" in adapter.discover_schema().vendor_schema


class TestExecuteQuery:
    def test_returns_provenance(self, adapter: VulnScanAdapter) -> None:
        assert isinstance(adapter.execute_query({"severity": "critical"}), QueryProvenance)

    def test_includes_policy(self, adapter: VulnScanAdapter) -> None:
        result = adapter.execute_query({})
        assert "fedramp-moderate" in result.vendor_query


class TestNormalize:
    def test_empty(self, adapter: VulnScanAdapter) -> None:
        result = adapter.normalize([])
        assert len(result.claims) == 0

    def test_single_finding(self, adapter: VulnScanAdapter) -> None:
        raw = [{"finding_id": "F-001", "cve_id": "CVE-2025-1234", "severity": "critical", "cvss_score": 9.8, "affected_asset": "web01"}]
        result = adapter.normalize(raw)
        assert len(result.claims) == 1
        assert "CVE-2025-1234" in str(result.claims[0].fields)
        assert result.claims[0].source == "vuln-scan"


class TestDetectDrift:
    def test_returns_report(self, adapter: VulnScanAdapter) -> None:
        assert isinstance(adapter.detect_drift(), DriftReport)

    def test_drift_type(self, adapter: VulnScanAdapter) -> None:
        assert adapter.detect_drift().drift_type == "vuln-scan-posture"


class TestEvidence:
    def test_returns_evidence(self, adapter: VulnScanAdapter) -> None:
        assert isinstance(adapter.collect_evidence("KSI-RA-05"), EvidenceObject)

    def test_source(self, adapter: VulnScanAdapter) -> None:
        assert adapter.collect_evidence("KSI-RA-05").source == "vuln-scan"


class TestExtensions:
    def test_ingest_raises(self, adapter: VulnScanAdapter) -> None:
        with pytest.raises(NotImplementedError, match="ingest_scan_results"):
            adapter.ingest_scan_results()

    def test_evidence_raises(self, adapter: VulnScanAdapter) -> None:
        with pytest.raises(NotImplementedError, match="generate_vuln_evidence"):
            adapter.generate_vuln_evidence()


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: VulnScanAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["adapter_id"] == "vuln-scan"
        assert result["metadata"]["scanner"] == "tenable"
