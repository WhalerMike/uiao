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

from uiao.adapters.m365_adapter import M365Adapter
from uiao.adapters.database_base import (
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
        from uiao.adapters.database_base import DatabaseAdapterBase

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


class TestGetTenantConfig:
    """Real tenant config parsing tests."""

    @pytest.fixture
    def adapter_with_config(self) -> M365Adapter:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent / "fixtures" / "m365-tenant-config.json"
        tenant_config = json.loads(config_path.read_text())
        return M365Adapter(
            {
                "tenant_id": "contoso.onmicrosoft.com",
                "_tenant_config": tenant_config,
            }
        )

    def test_exchange_claims(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.get_tenant_config("exchange-online")
        assert isinstance(result, ClaimSet)
        assert len(result.claims) >= 2  # mailbox + transport rule

    def test_teams_claims(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.get_tenant_config("teams")
        assert len(result.claims) >= 1

    def test_purview_claims(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.get_tenant_config("purview")
        assert len(result.claims) >= 1
        assert any("purview" in c.claim_id for c in result.claims)

    def test_unknown_workload_empty(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.get_tenant_config("nonexistent")
        assert len(result.claims) == 0


class TestApplyBaseline:
    """Baseline comparison tests."""

    @pytest.fixture
    def adapter_with_config(self) -> M365Adapter:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent / "fixtures" / "m365-tenant-config.json"
        tenant_config = json.loads(config_path.read_text())
        return M365Adapter(
            {
                "tenant_id": "contoso.onmicrosoft.com",
                "_tenant_config": tenant_config,
            }
        )

    def test_returns_drift_report(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.apply_baseline("exchange-online", {})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "m365-baseline-comparison"

    def test_compliant_baseline(self, adapter_with_config: M365Adapter) -> None:
        # Empty baseline = everything compliant
        result = adapter_with_config.apply_baseline("exchange-online", {})
        assert result.severity == "info"

    def test_non_compliant_detected(self, adapter_with_config: M365Adapter) -> None:
        # Baseline expects a value that doesn't match
        baseline = {"Default Mailbox Policy.automaticRepliesSetting": "enabled"}
        result = adapter_with_config.apply_baseline("exchange-online", baseline)
        assert result.details["comparison"]["summary"]["non_compliant_count"] >= 1

    def test_missing_setting_detected(self, adapter_with_config: M365Adapter) -> None:
        baseline = {"nonexistent.setting": "value"}
        result = adapter_with_config.apply_baseline("exchange-online", baseline)
        assert result.details["comparison"]["summary"]["missing_count"] >= 1


class TestGenerateM365Evidence:
    """Evidence bundle generation tests."""

    @pytest.fixture
    def adapter_with_config(self) -> M365Adapter:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent / "fixtures" / "m365-tenant-config.json"
        tenant_config = json.loads(config_path.read_text())
        return M365Adapter(
            {
                "tenant_id": "contoso.onmicrosoft.com",
                "_tenant_config": tenant_config,
            }
        )

    def test_returns_evidence_object(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.generate_m365_evidence()
        assert isinstance(result, EvidenceObject)

    def test_evidence_source(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.generate_m365_evidence()
        assert result.source == "m365"

    def test_evidence_has_normalized_claims(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.generate_m365_evidence()
        assert result.normalized_data is not None
        assert len(result.normalized_data["claims"]) >= 5  # across all workloads

    def test_workload_filter(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.generate_m365_evidence(workload="teams")
        assert result.normalized_data is not None
        assert len(result.normalized_data["claims"]) >= 1

    def test_provenance_includes_tenant(self, adapter_with_config: M365Adapter) -> None:
        result = adapter_with_config.generate_m365_evidence()
        assert result.provenance["tenant_id"] == "contoso.onmicrosoft.com"


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
