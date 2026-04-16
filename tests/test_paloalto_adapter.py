"""
Tests for the Palo Alto Networks (Firewall / NGFW) Adapter.

File: tests/test_paloalto_adapter.py
"""

from __future__ import annotations

import pytest

from uiao_impl.adapters.paloalto_adapter import PaloAltoAdapter
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
def adapter() -> PaloAltoAdapter:
    return PaloAltoAdapter(
        {
            "host": "fw01.agency.gov",
            "api_port": 443,
            "vsys": "vsys1",
            "auth_method": "api-key",
        }
    )


@pytest.fixture
def adapter_empty() -> PaloAltoAdapter:
    return PaloAltoAdapter()


class TestInstantiation:
    def test_adapter_id(self, adapter: PaloAltoAdapter) -> None:
        assert adapter.ADAPTER_ID == "palo-alto"

    def test_default_config(self, adapter_empty: PaloAltoAdapter) -> None:
        assert adapter_empty._host == ""
        assert adapter_empty._vsys == "vsys1"
        assert adapter_empty._api_port == 443

    def test_custom_config(self, adapter: PaloAltoAdapter) -> None:
        assert adapter._host == "fw01.agency.gov"

    def test_scope_defined(self, adapter: PaloAltoAdapter) -> None:
        assert len(adapter.SCOPE) == 3
        assert "security-policies" in adapter.SCOPE

    def test_is_database_adapter_base(self, adapter: PaloAltoAdapter) -> None:
        from uiao_impl.adapters.database_base import DatabaseAdapterBase
        assert isinstance(adapter, DatabaseAdapterBase)


class TestConnect:
    def test_connect_returns_provenance(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_connect_identity_includes_host(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.connect()
        assert "fw01.agency.gov" in result.identity

    def test_connect_endpoint(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.connect()
        assert result.endpoint == "https://fw01.agency.gov:443/api/"

    def test_connect_mtls_default_true(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.connect()
        assert result.mtls_enabled is True


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.discover_schema()
        assert isinstance(result, SchemaMappingObject)

    def test_vendor_schema_has_rule_types(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.discover_schema()
        assert "security-rule" in result.vendor_schema
        assert "nat-rule" in result.vendor_schema
        assert "threat-profile" in result.vendor_schema

    def test_version_hash_deterministic(self, adapter: PaloAltoAdapter) -> None:
        h1 = adapter.discover_schema().version_hash
        h2 = adapter.discover_schema().version_hash
        assert h1 == h2


class TestExecuteQuery:
    def test_returns_query_provenance(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.execute_query({"from": "security-rule"})
        assert isinstance(result, QueryProvenance)

    def test_vendor_query_includes_xpath(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.execute_query({"from": "security-rule"})
        assert "xpath" in result.vendor_query

    def test_vendor_query_includes_vsys(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.execute_query({"from": "nat-rule"})
        assert "vsys1" in result.vendor_query


class TestNormalize:
    def test_empty_input(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_single_rule(self, adapter: PaloAltoAdapter) -> None:
        raw = [
            {
                "type": "security-rule",
                "name": "allow-dns",
                "from": "trust",
                "to": "untrust",
                "action": "allow",
            }
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 1
        claim = result.claims[0]
        assert "security-rule" in claim.claim_id
        assert "allow-dns" in claim.claim_id
        assert claim.source == "palo-alto"

    def test_multiple_rules(self, adapter: PaloAltoAdapter) -> None:
        raw = [
            {"type": "security-rule", "name": "r1", "action": "allow"},
            {"type": "nat-rule", "name": "n1", "action": "translate"},
        ]
        result = adapter.normalize(raw)
        assert len(result.claims) == 2


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.detect_drift()
        assert isinstance(result, DriftReport)

    def test_drift_type(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.detect_drift()
        assert result.drift_type == "palo-alto-config"

    def test_details_include_host(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.detect_drift()
        assert result.details["host"] == "fw01.agency.gov"


class TestCollectEvidence:
    def test_returns_evidence_object(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_evidence("KSI-SC-07")
        assert isinstance(result, EvidenceObject)

    def test_evidence_source(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_evidence("KSI-SC-07")
        assert result.source == "palo-alto"


class TestPaloAltoExtensions:
    def test_get_running_config_raises(self, adapter: PaloAltoAdapter) -> None:
        with pytest.raises(NotImplementedError, match="get_running_config"):
            adapter.get_running_config()

    def test_push_config_change_raises(self, adapter: PaloAltoAdapter) -> None:
        with pytest.raises(NotImplementedError, match="push_config_change"):
            adapter.push_config_change("security-rule", "test", {"action": "deny"})

    def test_generate_firewall_evidence_raises(self, adapter: PaloAltoAdapter) -> None:
        with pytest.raises(NotImplementedError, match="generate_firewall_evidence"):
            adapter.generate_firewall_evidence()


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_and_align()
        assert isinstance(result, dict)

    def test_vendor_field(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["vendor"] == "Palo Alto Networks"

    def test_adapter_id_field(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["adapter_id"] == "palo-alto"

    def test_metadata_host(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_and_align()
        assert result["metadata"]["host"] == "fw01.agency.gov"

    def test_metadata_scope(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.collect_and_align()
        assert len(result["metadata"]["scope"]) == 3
