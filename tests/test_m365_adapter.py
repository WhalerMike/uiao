"""
Tests for the Microsoft 365 Tenant Adapter.

Covers:
- Instantiation and configuration
- All 7 canonical responsibility domains (base class contract)
- M365-specific extension methods (stub behavior)
- collect_and_align convenience method
- ADAPTER_ID consistency with canon registry

File: tests/test_m365_adapter.py
"""

from __future__ import annotations

import pytest

from uiao_impl.adapters.m365_adapter import M365Adapter
from uiao_impl.adapters.database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


@pytest.fixture
def adapter() -> M365Adapter:
    return M365Adapter(
        {
            "tenant_id": "contoso.onmicrosoft.com",
            "auth_method": "client-credential",
            "graph_endpoint": "https://graph.microsoft.com/v1.0",
        }
    )


@pytest.fixture
def adapter_empty() -> M365Adapter:
    return M365Adapter()


class TestInstantiation:
    def test_adapter_id(self, adapter: M365Adapter) -> None:
        assert adapter.ADAPTER_ID == "m365"

    def test_default_config(self, adapter_empty: M365Adapter) -> None:
        assert adapter_empty._tenant_id == ""
        assert "graph.microsoft.com" in adapter_empty._graph_endpoint

    def test_custom_config(self, adapter: M365Adapter) -> None:
        assert adapter._tenant_id == "contoso.onmicrosoft.com"

    def test_workloads_defined(self, adapter: M365Adapter) -> None:
        assert len(adapter.WORKLOADS) == 5
        assert "exchange-online" in adapter.WORKLOADS
        assert "teams" in adapter.WORKLOADS

    def test_is_database_adapter_base(self, adapter: M365Adapter) -> None:
        from uiao_impl.adapters.database_base import DatabaseAdapterBase
        assert isinstance(adapter, DatabaseAdapterBase)


class TestConnect:
    def test_connect_returns_provenance(self, adapter: M365Adapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_connect_identity_includes_tenant(self, adapter: M365Adapter) -> None:
        result = adapter.connect()
        assert "contoso" in result.identity

    def test_connect_endpoint(self, adapter: M365Adapter) -> None:
        result = adapter.connect()
        assert result.endpoint == "https://graph.microsoft.com/v1.0"

    def test_connect_auth_method(self, adapter: M365Adapter) -> None:
        result = adapter.connect()
        assert result.auth_method == "client-credential"


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: M365Adapter) -> None:
        result = adapter.discover_schema()
        assert isinstance(result, SchemaMappingObject)

    def test_vendor_schema_has_workload_entities(self, adapter: M365Adapter) -> None:
        result = adapter.discover_schema()
        assert "mailboxSettings" in result.vendor_schema
        assert "securityPolicy" in result.vendor_schema

    def test_version_hash_deterministic(self, adapter: M365Adapter) -> None:
        h1 = adapter.discover_schema().version_hash
        h2 = adapter.discover_schema().version_hash
        assert h1 == h2


class TestExecuteQuery:
    def test_returns_query_provenance(self, adapter: M365Adapter) -> None:
        result = adapter.execute_query({"from": "users", "select": ["id", "mail"]})
        assert isinstance(result, QueryProvenance)

    def test_vendor_query_includes_graph_endpoint(self, adapter: M365Adapter) -> None:
        result = adapter.execute_query({"from": "users"})
        assert "graph.microsoft.com" in result.vendor_query

    def test_vendor_query_includes_entity(self, adapter: M365Adapter) -> None:
        result = adapter.execute_query({"from": "groups"})
        assert "groups" in result.vendor_query


class TestNormalize:
    def test_empty_input(self, adapter: M365Adapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_single_entity(self, adapter: M365Adapter) -> None:
        raw = [
            {
                "@odata.type": "#microsoft.graph.mailboxSettings",
                "id": "abc-123",
                "displayName": "Test Mailbox",
                "_workload": "exchange-online",
            }
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 1
        claim = result.claims[0]
        assert isinstance(claim, ClaimObject)
        assert "exchange-online" in claim.claim_id
        assert claim.source == "m365"

    def test_multiple_entities(self, adapter: M365Adapter) -> None:
        raw = [
            {"@odata.type": "#microsoft.graph.user", "id": "u1", "_workload": "teams"},
            {"@odata.type": "#microsoft.graph.site", "id": "s1", "_workload": "sharepoint-online"},
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 2
        ids = {c.claim_id for c in result.claims}
        assert len(ids) == 2


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: M365Adapter) -> None:
        result = adapter.detect_drift()
        assert isinstance(result, DriftReport)

    def test_drift_type(self, adapter: M365Adapter) -> None:
        result = adapter.detect_drift()
        assert result.drift_type == "m365-tenant-config"

    def test_details_include_tenant(self, adapter: M365Adapter) -> None:
        result = adapter.detect_drift()
        assert result.details["tenant_id"] == "contoso.onmicrosoft.com"

    def test_details_include_workloads(self, adapter: M365Adapter) -> None:
        result = adapter.detect_drift()
        assert len(result.details["workloads"]) == 5


class TestCollectEvidence:
    def test_returns_evidence_object(self, adapter: M365Adapter) -> None:
        result = adapter.collect_evidence("KSI-CM-02")
        assert isinstance(result, EvidenceObject)

    def test_evidence_source(self, adapter: M365Adapter) -> None:
        result = adapter.collect_evidence("KSI-CM-02")
        assert result.source == "m365"


class TestM365Extensions:
    def test_get_tenant_config_raises(self, adapter: M365Adapter) -> None:
        with pytest.raises(NotImplementedError, match="get_tenant_config"):
            adapter.get_tenant_config("exchange-online")

    def test_apply_baseline_raises(self, adapter: M365Adapter) -> None:
        with pytest.raises(NotImplementedError, match="apply_baseline"):
            adapter.apply_baseline("teams", {"setting": "value"})

    def test_generate_m365_evidence_raises(self, adapter: M365Adapter) -> None:
        with pytest.raises(NotImplementedError, match="generate_m365_evidence"):
            adapter.generate_m365_evidence()


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: M365Adapter) -> None:
        result = adapter.collect_and_align()
        assert isinstance(result, dict)

    def test_vendor_field(self, adapter: M365Adapter) -> None:
        result = adapter.collect_and_align()
        assert result["vendor"] == "Microsoft 365"

    def test_adapter_id_field(self, adapter: M365Adapter) -> None:
        result = adapter.collect_and_align()
        assert result["adapter_id"] == "m365"

    def test_metadata_tenant(self, adapter: M365Adapter) -> None:
        result = adapter.collect_and_align()
        assert result["metadata"]["tenant_id"] == "contoso.onmicrosoft.com"

    def test_metadata_workloads(self, adapter: M365Adapter) -> None:
        result = adapter.collect_and_align()
        assert len(result["metadata"]["workloads"]) == 5
