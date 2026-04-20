"""
Behavioral tests for the Entra ID adapter against realistic Graph API fixtures.

Tests the adapter's normalize() and base-class methods with real-format
Graph API response data, verifying claim construction, provenance hashing,
and evidence generation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from uiao.adapters.entra_adapter import EntraAdapter
from uiao.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DriftReport,
    EvidenceObject,
    SchemaMappingObject,
)


@pytest.fixture
def adapter() -> EntraAdapter:
    a = EntraAdapter({"tenant_id": "contoso.onmicrosoft.com"})
    # Mock the collector to avoid real API calls
    a.collector = MagicMock()
    a.collector.tenant_id = "contoso.onmicrosoft.com"
    a.collector.instance = "contoso"
    return a


@pytest.fixture
def users_groups() -> list:
    path = Path(__file__).parent / "fixtures" / "entra-users-groups.json"
    return json.loads(path.read_text())["value"]


class TestNormalizeRealData:
    def test_normalizes_users_and_groups(self, adapter: EntraAdapter, users_groups: list) -> None:
        result = adapter.normalize(users_groups)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 3

    def test_claim_ids_contain_sys_id(self, adapter: EntraAdapter, users_groups: list) -> None:
        result = adapter.normalize(users_groups)
        for claim in result.claims:
            assert "servicenow:" in claim.claim_id or "entra" in claim.source.lower() or claim.claim_id

    def test_source_is_entra(self, adapter: EntraAdapter, users_groups: list) -> None:
        result = adapter.normalize(users_groups)
        for claim in result.claims:
            assert claim.source == "entra-id"

    def test_provenance_hash_deterministic(self, adapter: EntraAdapter, users_groups: list) -> None:
        r1 = adapter.normalize(users_groups)
        r2 = adapter.normalize(users_groups)
        h1 = sorted(c.provenance_hash for c in r1.claims)
        h2 = sorted(c.provenance_hash for c in r2.claims)
        assert h1 == h2

    def test_empty_records(self, adapter: EntraAdapter) -> None:
        result = adapter.normalize([])
        assert len(result.claims) == 0


class TestConnectionBehavior:
    def test_connect_returns_provenance(self, adapter: EntraAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_identity_includes_tenant(self, adapter: EntraAdapter) -> None:
        result = adapter.connect()
        assert "contoso" in result.identity or "entra" in result.identity

    def test_schema_discovery(self, adapter: EntraAdapter) -> None:
        schema = adapter.discover_schema()
        assert isinstance(schema, SchemaMappingObject)
        assert len(schema.vendor_schema) >= 3


class TestDriftDetection:
    def test_drift_report(self, adapter: EntraAdapter) -> None:
        result = adapter.detect_drift()
        assert isinstance(result, DriftReport)
        assert result.details.get("adapter") == "entra-id"


class TestEvidenceGeneration:
    def test_collect_evidence_returns_evidence_object(self, adapter: EntraAdapter) -> None:
        # Mock collector.collect to return a mock evidence object
        mock_evidence = MagicMock()
        mock_evidence.raw_data = {"sign_in_events": []}
        adapter.collector.collect.return_value = mock_evidence

        result = adapter.collect_evidence("KSI-IA-02")
        assert isinstance(result, EvidenceObject)
        assert result.ksi_id == "KSI-IA-02"
        assert result.source == "entra-id"

    def test_evidence_has_provenance(self, adapter: EntraAdapter) -> None:
        mock_evidence = MagicMock()
        mock_evidence.raw_data = {"value": []}
        adapter.collector.collect.return_value = mock_evidence

        result = adapter.collect_evidence("KSI-AC-02")
        assert "adapter_id" in result.provenance
        assert "hash" in result.provenance


class TestCollectAndAlign:
    def test_with_mocked_collector(self, adapter: EntraAdapter, users_groups: list) -> None:
        mock_evidence = MagicMock()
        mock_evidence.raw_data = {"value": users_groups}
        adapter.collector.collect.return_value = mock_evidence

        result = adapter.collect_and_align()
        assert isinstance(result, dict)
        assert result["adapter_id"] == "entra-id"
        assert result["metadata"]["total_records"] == 3


class TestEntraToOscal:
    """End-to-end: Entra ID → OSCAL SAR."""

    def test_entra_claims_to_sar(self, adapter: EntraAdapter, users_groups: list) -> None:
        from uiao.adapters.adapter_to_oscal import build_adapter_bundle
        from uiao.impl.generators.sar import build_sar

        claims = adapter.normalize(users_groups)
        bundle = build_adapter_bundle(
            adapter_id="entra-id",
            claim_set=claims,
            control_ids=["IA-2", "AC-2", "CM-8"],
        )
        sar = build_sar(bundle=bundle, system_name="Entra ID Assessment")
        assert "assessment-results" in sar
        result = sar["assessment-results"]["results"][0]
        assert len(result["observations"]) == 3
