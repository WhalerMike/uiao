"""
Behavioral tests for the ServiceNow adapter against realistic fixtures.

Unlike the adapter smoke tests (test_adapters.py), these test actual
data normalization with realistic ServiceNow Table API responses.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.impl.adapters.servicenow_adapter import ServiceNowAdapter
from uiao.impl.adapters.database_base import (
    ClaimSet,
    EvidenceObject,
)


@pytest.fixture
def adapter() -> ServiceNowAdapter:
    return ServiceNowAdapter({
        "instance": "contoso-gov",
        "token": "test-token-placeholder",
    })


@pytest.fixture
def incidents() -> list:
    path = Path(__file__).parent / "fixtures" / "servicenow-incidents.json"
    return json.loads(path.read_text())["result"]


# ---------------------------------------------------------------------------
# Real data normalization
# ---------------------------------------------------------------------------


class TestNormalizeRealData:
    def test_incident_count(self, adapter: ServiceNowAdapter, incidents: list) -> None:
        result = adapter.normalize(incidents)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 4

    def test_claim_ids_contain_sys_id(self, adapter: ServiceNowAdapter, incidents: list) -> None:
        result = adapter.normalize(incidents)
        for claim in result.claims:
            assert "servicenow:" in claim.claim_id
            # sys_id should be in the claim_id
            assert any(inc["sys_id"] in claim.claim_id for inc in incidents)

    def test_control_id_mapped(self, adapter: ServiceNowAdapter, incidents: list) -> None:
        result = adapter.normalize(incidents)
        controls = {c.fields.get("control_id") for c in result.claims}
        assert "IA-2" in controls
        assert "SC-7" in controls

    def test_implementation_statement_from_description(
        self, adapter: ServiceNowAdapter, incidents: list
    ) -> None:
        result = adapter.normalize(incidents)
        descriptions = {c.fields.get("implementation_statement", "") for c in result.claims}
        assert any("MFA enrollment" in d for d in descriptions)
        assert any("firewall rule" in d for d in descriptions)

    def test_source_is_servicenow(self, adapter: ServiceNowAdapter, incidents: list) -> None:
        result = adapter.normalize(incidents)
        for claim in result.claims:
            assert claim.source == "servicenow"

    def test_provenance_hash_deterministic(
        self, adapter: ServiceNowAdapter, incidents: list
    ) -> None:
        r1 = adapter.normalize(incidents)
        r2 = adapter.normalize(incidents)
        hashes1 = sorted(c.provenance_hash for c in r1.claims)
        hashes2 = sorted(c.provenance_hash for c in r2.claims)
        assert hashes1 == hashes2

    def test_empty_records(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.normalize([])
        assert len(result.claims) == 0

    def test_missing_control_id_defaults(self, adapter: ServiceNowAdapter) -> None:
        """Records without uiao_control_id should default to AC-2."""
        result = adapter.normalize([{
            "sys_id": "INC-NO-CONTROL",
            "short_description": "No control mapped",
        }])
        assert len(result.claims) == 1
        assert result.claims[0].fields.get("control_id") == "AC-2"


# ---------------------------------------------------------------------------
# Connection & Schema
# ---------------------------------------------------------------------------


class TestConnectionBehavior:
    def test_identity_includes_instance(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert "contoso-gov" in result.identity

    def test_endpoint_is_servicenow_url(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert "contoso-gov.service-now.com" in result.endpoint

    def test_schema_maps_key_fields(self, adapter: ServiceNowAdapter) -> None:
        schema = adapter.discover_schema()
        assert "sys_id" in schema.vendor_schema
        assert "uiao_control_id" in schema.vendor_schema

    def test_query_translates_to_table_api(self, adapter: ServiceNowAdapter) -> None:
        qp = adapter.execute_query({"from": "incident"})
        assert "incident" in qp.vendor_query
        assert "api/now/table" in qp.vendor_query


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


class TestDriftBehavior:
    def test_drift_report_references_adapter(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.detect_drift()
        assert result.details["adapter"] == "servicenow"

    def test_drift_type_is_schema(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.detect_drift()
        assert "servicenow" in result.drift_type


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------


class TestEvidenceCollection:
    def test_returns_evidence_object(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_evidence("KSI-IR-04")
        assert isinstance(result, EvidenceObject)

    def test_evidence_ksi_id(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_evidence("KSI-IR-04")
        assert result.ksi_id == "KSI-IR-04"

    def test_evidence_source(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_evidence("KSI-IR-04")
        assert result.source == "servicenow"


# ---------------------------------------------------------------------------
# collect_and_align with real data pattern
# ---------------------------------------------------------------------------


class TestCollectAndAlignBehavior:
    def test_returns_alignment_dict(self, adapter: ServiceNowAdapter, incidents: list) -> None:
        """Mock the collector to avoid real API call."""
        from unittest.mock import MagicMock
        adapter.collector = MagicMock()
        adapter.collector.fetch_relevant_records.return_value = {"result": incidents}
        adapter.collector.instance = "contoso-gov"
        result = adapter.collect_and_align()
        assert isinstance(result, dict)
        assert result["adapter_id"] == "servicenow"
        assert result["vendor"] == "ServiceNow"
        assert result["metadata"]["total_records"] == 4
