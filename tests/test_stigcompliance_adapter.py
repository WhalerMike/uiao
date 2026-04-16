"""Tests for the STIG Compliance Adapter (conformance / policy)."""

from __future__ import annotations
import pytest
from uiao_impl.adapters.stigcompliance_adapter import StigComplianceAdapter
from uiao_impl.adapters.database_base import (
    ClaimSet, ConnectionProvenance, DriftReport, EvidenceObject, SchemaMappingObject,
)


@pytest.fixture
def adapter() -> StigComplianceAdapter:
    return StigComplianceAdapter({"benchmark": "RHEL9-STIG", "target": "web01", "engine": "openscap"})


class TestBasics:
    def test_adapter_id(self, adapter: StigComplianceAdapter) -> None:
        assert adapter.ADAPTER_ID == "stig-compliance"

    def test_connect(self, adapter: StigComplianceAdapter) -> None:
        r = adapter.connect()
        assert isinstance(r, ConnectionProvenance)
        assert "openscap" in r.identity

    def test_schema(self, adapter: StigComplianceAdapter) -> None:
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)

    def test_query(self, adapter: StigComplianceAdapter) -> None:
        r = adapter.execute_query({"from": "RHEL9-STIG"})
        assert "RHEL9-STIG" in r.vendor_query

    def test_normalize_empty(self, adapter: StigComplianceAdapter) -> None:
        assert len(adapter.normalize([]).claims) == 0

    def test_normalize_rule(self, adapter: StigComplianceAdapter) -> None:
        raw = [{"rule_id": "SV-001", "result": "pass", "severity": "high", "title": "Test"}]
        r = adapter.normalize(raw)
        assert len(r.claims) == 1
        assert "SV-001" in r.claims[0].claim_id

    def test_drift(self, adapter: StigComplianceAdapter) -> None:
        assert adapter.detect_drift().drift_type == "stig-compliance-posture"

    def test_evidence(self, adapter: StigComplianceAdapter) -> None:
        assert isinstance(adapter.collect_evidence("KSI-CM-06"), EvidenceObject)

    def test_extension_raises(self, adapter: StigComplianceAdapter) -> None:
        with pytest.raises(NotImplementedError):
            adapter.run_stig_assessment()
        with pytest.raises(NotImplementedError):
            adapter.generate_stig_evidence()

    def test_collect_and_align(self, adapter: StigComplianceAdapter) -> None:
        r = adapter.collect_and_align()
        assert r["adapter_id"] == "stig-compliance"
