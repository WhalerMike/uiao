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


class TestGetRunningConfig:
    """Real PAN-OS XML parsing tests."""

    @pytest.fixture
    def sec_xml(self) -> str:
        from pathlib import Path
        return (Path(__file__).parent / "fixtures" / "panos-security-rules.xml").read_text()

    @pytest.fixture
    def nat_xml(self) -> str:
        from pathlib import Path
        return (Path(__file__).parent / "fixtures" / "panos-nat-rules.xml").read_text()

    def test_parses_security_rules(self, adapter: PaloAltoAdapter, sec_xml: str) -> None:
        result = adapter.get_running_config(scope="security-policies", xml_content=sec_xml)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 3

    def test_rule_names_in_claims(self, adapter: PaloAltoAdapter, sec_xml: str) -> None:
        result = adapter.get_running_config(scope="security-policies", xml_content=sec_xml)
        names = {c.fields.get("rule_name", "") for c in result.claims}
        assert "allow-dns-outbound" in names
        assert "deny-all-default" in names

    def test_action_preserved(self, adapter: PaloAltoAdapter, sec_xml: str) -> None:
        result = adapter.get_running_config(scope="security-policies", xml_content=sec_xml)
        deny_rules = [c for c in result.claims if c.fields.get("action") == "deny"]
        assert len(deny_rules) == 1
        assert "deny-all-default" in deny_rules[0].claim_id

    def test_parses_nat_rules(self, adapter: PaloAltoAdapter, nat_xml: str) -> None:
        result = adapter.get_running_config(scope="nat-rules", xml_content=nat_xml)
        assert len(result.claims) == 1
        assert "nat-web-servers" in result.claims[0].claim_id

    def test_provenance_deterministic(self, adapter: PaloAltoAdapter, sec_xml: str) -> None:
        r1 = adapter.get_running_config(scope="security-policies", xml_content=sec_xml)
        r2 = adapter.get_running_config(scope="security-policies", xml_content=sec_xml)
        assert {c.provenance_hash for c in r1.claims} == {c.provenance_hash for c in r2.claims}


class TestPushConfigChange:
    def test_returns_drift_report(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.push_config_change("security-rule", "test-rule", {"action": "deny"})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "palo-alto-config-change"

    def test_proposed_changes_in_details(self, adapter: PaloAltoAdapter) -> None:
        result = adapter.push_config_change("security-rule", "allow-dns", {"action": "deny"})
        assert result.details["rule_name"] == "allow-dns"
        assert result.details["proposed_changes"]["action"] == "deny"


class TestGenerateFirewallEvidence:
    @pytest.fixture
    def adapter_with_xml(self) -> PaloAltoAdapter:
        from pathlib import Path
        sec_xml = (Path(__file__).parent / "fixtures" / "panos-security-rules.xml").read_text()
        return PaloAltoAdapter({
            "host": "fw01.agency.gov",
            "vsys": "vsys1",
            "_security_rules_xml": sec_xml,
        })

    def test_returns_evidence(self, adapter_with_xml: PaloAltoAdapter) -> None:
        result = adapter_with_xml.generate_firewall_evidence()
        assert isinstance(result, EvidenceObject)

    def test_source(self, adapter_with_xml: PaloAltoAdapter) -> None:
        assert adapter_with_xml.generate_firewall_evidence().source == "palo-alto"

    def test_has_normalized_claims(self, adapter_with_xml: PaloAltoAdapter) -> None:
        result = adapter_with_xml.generate_firewall_evidence()
        assert result.normalized_data is not None
        assert len(result.normalized_data["claims"]) == 3

    def test_provenance_includes_host(self, adapter_with_xml: PaloAltoAdapter) -> None:
        result = adapter_with_xml.generate_firewall_evidence()
        assert result.provenance["host"] == "fw01.agency.gov"


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
