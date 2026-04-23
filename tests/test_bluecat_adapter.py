"""
Tests for the BlueCat Address Manager (BAM) Adapter.

File: tests/test_bluecat_adapter.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.adapters.bluecat_adapter import BlueCatAdapter
from uiao.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def adapter() -> BlueCatAdapter:
    return BlueCatAdapter(
        {
            "bam_host": "bam01.agency.com",
            "configuration": "prod",
            "auth_method": "api-token",
        }
    )


@pytest.fixture
def adapter_empty() -> BlueCatAdapter:
    return BlueCatAdapter()


@pytest.fixture
def host_records() -> dict:
    return _load("bluecat-host-records.json")


@pytest.fixture
def dhcp_ranges() -> dict:
    return _load("bluecat-dhcp-ranges.json")


@pytest.fixture
def ip_addresses() -> dict:
    return _load("bluecat-ip-addresses.json")


class TestInstantiation:
    def test_adapter_id(self, adapter: BlueCatAdapter) -> None:
        assert adapter.ADAPTER_ID == "bluecat-address-manager"

    def test_default_config(self, adapter_empty: BlueCatAdapter) -> None:
        assert adapter_empty._bam_host == ""
        assert adapter_empty._configuration == "default"
        assert adapter_empty._api_version == "v1"

    def test_custom_config(self, adapter: BlueCatAdapter) -> None:
        assert adapter._bam_host == "bam01.agency.com"
        assert adapter._configuration == "prod"

    def test_scope_defined(self, adapter: BlueCatAdapter) -> None:
        assert len(adapter.SCOPE) == 4
        for required in ("dns-records", "dhcp-scopes", "ip-allocations", "side-by-side-ad"):
            assert required in adapter.SCOPE
        assert "network-views" not in adapter.SCOPE

    def test_is_database_adapter_base(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter, DatabaseAdapterBase)


class TestConnect:
    def test_connect_returns_provenance(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter.connect(), ConnectionProvenance)

    def test_connect_identity_includes_bam_host(self, adapter: BlueCatAdapter) -> None:
        assert "bam01.agency.com" in adapter.connect().identity

    def test_connect_identity_includes_configuration(self, adapter: BlueCatAdapter) -> None:
        assert "prod" in adapter.connect().identity

    def test_connect_endpoint(self, adapter: BlueCatAdapter) -> None:
        assert adapter.connect().endpoint == "https://bam01.agency.com/Services/REST/v1/"

    def test_connect_mtls_default_true(self, adapter: BlueCatAdapter) -> None:
        assert adapter.connect().mtls_enabled is True


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)

    def test_vendor_schema_covers_all_object_types(self, adapter: BlueCatAdapter) -> None:
        schema = adapter.discover_schema()
        for required in ("HostRecord", "AliasRecord", "DHCP4Range", "IP4Address"):
            assert required in schema.vendor_schema

    def test_unmapped_fields_captured(self, adapter: BlueCatAdapter) -> None:
        assert "udfs" in adapter.discover_schema().unmapped_fields

    def test_version_hash_deterministic(self, adapter: BlueCatAdapter) -> None:
        assert adapter.discover_schema().version_hash == adapter.discover_schema().version_hash


class TestExecuteQuery:
    def test_returns_query_provenance(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter.execute_query({"from": "dns-records"}), QueryProvenance)

    def test_each_scope_yields_distinct_endpoint(self, adapter: BlueCatAdapter) -> None:
        seen = {adapter.execute_query({"from": s}).vendor_query for s in adapter.SCOPE}
        assert len(seen) == len(adapter.SCOPE)

    def test_query_includes_configuration(self, adapter: BlueCatAdapter) -> None:
        assert "configuration=prod" in adapter.execute_query({"from": "dns-records"}).vendor_query

    def test_query_uses_api_version(self, adapter: BlueCatAdapter) -> None:
        assert "/Services/REST/v1/" in adapter.execute_query({"from": "dhcp-scopes"}).vendor_query

    def test_unknown_scope_falls_back(self, adapter: BlueCatAdapter) -> None:
        assert "HostRecord" in adapter.execute_query({"from": "totally-fake-scope"}).vendor_query


class TestNormalize:
    def test_empty_input(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_host_record_claim_id_shape(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "host-record", "name": "web01.contoso.gov", "ipv4addr": "10.0.1.1"}])
        assert result.claims[0].claim_id == "bluecat:prod:host-record:web01.contoso.gov"
        assert result.claims[0].source == "bluecat-address-manager"

    def test_alias_record_claim_id_shape(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "alias-record", "name": "api.contoso.gov", "canonical": "web01"}])
        assert result.claims[0].claim_id == "bluecat:prod:alias-record:api.contoso.gov"

    def test_dhcp_range_claim_id_shape(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "dhcp-range", "start": "10.0.1.10", "end": "10.0.1.99"}])
        assert "10.0.1.10-10.0.1.99" in result.claims[0].claim_id

    def test_ip_address_claim_id_shape(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "ip-address", "ipv4addr": "10.0.1.5", "mac": "00-1B-21-AA"}])
        assert result.claims[0].claim_id == "bluecat:prod:ip-address:10.0.1.5"

    def test_ip_address_state_preserved(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "ip-address", "ipv4addr": "10.0.1.5", "state": "DHCP_RESERVED"}])
        assert result.claims[0].fields["state"] == "DHCP_RESERVED"

    def test_mixed_types_in_one_set(self, adapter: BlueCatAdapter) -> None:
        rows = [
            {"type": "host-record", "name": "host1", "ipv4addr": "1.1.1.1"},
            {"type": "dhcp-range", "start": "1.1.1.10", "end": "1.1.1.20"},
            {"type": "ip-address", "ipv4addr": "1.1.1.5", "mac": "aa"},
        ]
        result = adapter.normalize(rows)
        assert len(result.claims) == 3
        types = {c.fields["object_type"] for c in result.claims}
        assert types == {"host-record", "dhcp-range", "ip-address"}

    def test_unknown_type_falls_through(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "exotic", "name": "x", "id": 99}])
        assert len(result.claims) == 1
        assert "raw" in result.claims[0].fields


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter.detect_drift(), DriftReport)

    def test_scaffold_when_inputs_missing(self, adapter: BlueCatAdapter) -> None:
        result = adapter.detect_drift()
        assert result.severity == "info"
        assert "not configured" in result.details["message"]

    def test_real_diff_emits_drift(self) -> None:
        baseline = [{"type": "host-record", "id": 1, "name": "a", "ipv4addr": "1.1.1.1"}]
        live = [{"type": "host-record", "id": 2, "name": "b", "ipv4addr": "2.2.2.2"}]
        a = BlueCatAdapter(
            {
                "bam_host": "bam",
                "configuration": "prod",
                "baseline_records": baseline,
                "live_records": live,
            }
        )
        result = a.detect_drift()
        assert result.severity == "high"
        assert result.details["summary"]["drift_count"] == 2

    def test_no_drift_when_baseline_matches(self) -> None:
        rows = [{"type": "host-record", "id": 1, "name": "a", "ipv4addr": "1.1.1.1"}]
        a = BlueCatAdapter(
            {
                "bam_host": "bam",
                "configuration": "prod",
                "baseline_records": rows,
                "live_records": rows,
            }
        )
        result = a.detect_drift()
        assert result.severity == "info"
        assert result.details["summary"]["drift_count"] == 0

    def test_drift_type_constant(self, adapter: BlueCatAdapter) -> None:
        assert adapter.detect_drift().drift_type == "bluecat-ipam-config"


class TestGetAllObjects:
    """Real BAM JSON parsing tests via injected payloads."""

    def test_parses_host_records(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        result = adapter.get_all_objects(scope="dns-records", bam_json=host_records)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) >= 3
        names = {c.fields.get("name", "") for c in result.claims}
        assert "web01.contoso.gov" in names

    def test_expands_pipe_delimited_properties(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        """Verifies _entity_properties expansion reaches claim fields."""
        result = adapter.get_all_objects(scope="dns-records", bam_json=host_records)
        web_claims = [c for c in result.claims if c.fields.get("name") == "web01.contoso.gov"]
        assert any(c.fields.get("ipv4addr") == "10.0.1.100" for c in web_claims)

    def test_parses_dhcp_ranges(self, adapter: BlueCatAdapter, dhcp_ranges: dict) -> None:
        result = adapter.get_all_objects(scope="dhcp-scopes", bam_json=dhcp_ranges)
        assert len(result.claims) == 3
        ranges = [c for c in result.claims if c.fields["object_type"] == "dhcp-range"]
        assert len(ranges) == 3

    def test_parses_ip_addresses(self, adapter: BlueCatAdapter, ip_addresses: dict) -> None:
        result = adapter.get_all_objects(scope="ip-allocations", bam_json=ip_addresses)
        states = {c.fields.get("state", "") for c in result.claims}
        assert "STATIC" in states
        assert "DHCP_RESERVED" in states

    def test_no_payload_returns_empty(self, adapter: BlueCatAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records")
        assert len(result.claims) == 0

    def test_provenance_deterministic(self, adapter: BlueCatAdapter, dhcp_ranges: dict) -> None:
        r1 = adapter.get_all_objects(scope="dhcp-scopes", bam_json=dhcp_ranges)
        r2 = adapter.get_all_objects(scope="dhcp-scopes", bam_json=dhcp_ranges)
        assert {c.provenance_hash for c in r1.claims} == {c.provenance_hash for c in r2.claims}

    def test_scope_none_iterates_all(self, dhcp_ranges: dict) -> None:
        a = BlueCatAdapter(
            {
                "bam_host": "bam",
                "configuration": "prod",
                "_dhcp-scopes_json": dhcp_ranges,
            }
        )
        result = a.get_all_objects()
        assert len(result.claims) == 3


class TestPushDnsChange:
    def test_returns_drift_report(self, adapter: BlueCatAdapter) -> None:
        result = adapter.push_dns_change("HostRecord", "host1.example.gov", {"addresses": "10.0.0.1"})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "bluecat-dns-change"

    def test_proposed_change_in_details(self, adapter: BlueCatAdapter) -> None:
        result = adapter.push_dns_change("HostRecord", "host1", {"addresses": "10.0.0.1"})
        assert result.details["name"] == "host1"
        assert result.details["proposed"]["addresses"] == "10.0.0.1"


class TestPushDhcpChange:
    def test_returns_drift_report(self, adapter: BlueCatAdapter) -> None:
        result = adapter.push_dhcp_change("dhcp-range", "10.0.1.10-10.0.1.99", {"comment": "expand"})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "bluecat-dhcp-change"

    def test_identifier_preserved(self, adapter: BlueCatAdapter) -> None:
        result = adapter.push_dhcp_change("ip-address", "10.0.1.5", {"macAddress": "00-11-22"})
        assert result.details["identifier"] == "10.0.1.5"
        assert result.details["scope_type"] == "ip-address"


class TestEmitEventStream:
    def test_writes_ndjson(self, adapter: BlueCatAdapter, tmp_path: Path) -> None:
        events = [{"k": 1, "user": "alice"}, {"k": 2, "user": "bob"}]
        out = adapter.emit_event_stream(events, tmp_path / "events.ndjson")
        lines = out.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["user"] == "alice"

    def test_empty_events_writes_empty_file(self, adapter: BlueCatAdapter, tmp_path: Path) -> None:
        out = adapter.emit_event_stream([], tmp_path / "empty.ndjson")
        assert out.read_text() == ""

    def test_default_path(self, adapter: BlueCatAdapter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        out = adapter.emit_event_stream([{"x": 1}])
        assert out.name == "event-stream.ndjson"
        assert out.exists()


class TestGenerateIpamEvidence:
    def test_returns_evidence(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", bam_json=host_records)
        assert isinstance(result, EvidenceObject)

    def test_source(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", bam_json=host_records)
        assert result.source == "bluecat-address-manager"

    def test_ksi_id_includes_configuration(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", bam_json=host_records)
        assert "prod" in result.ksi_id
        assert "BAM" in result.ksi_id

    def test_provenance_includes_bam_host(self, adapter: BlueCatAdapter, host_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", bam_json=host_records)
        assert result.provenance["bam_host"] == "bam01.agency.com"

    def test_normalized_claims_present(self, adapter: BlueCatAdapter, dhcp_ranges: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dhcp-scopes", bam_json=dhcp_ranges)
        assert result.normalized_data is not None
        assert len(result.normalized_data["claims"]) == 3


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: BlueCatAdapter) -> None:
        assert isinstance(adapter.collect_and_align(), dict)

    def test_vendor_field(self, adapter: BlueCatAdapter) -> None:
        assert adapter.collect_and_align()["vendor"] == "BlueCat"

    def test_adapter_id_field(self, adapter: BlueCatAdapter) -> None:
        assert adapter.collect_and_align()["adapter_id"] == "bluecat-address-manager"

    def test_metadata_bam_host(self, adapter: BlueCatAdapter) -> None:
        assert adapter.collect_and_align()["metadata"]["bam_host"] == "bam01.agency.com"

    def test_metadata_scope_count(self, adapter: BlueCatAdapter) -> None:
        assert len(adapter.collect_and_align()["metadata"]["scope"]) == 4


class TestFailureModes:
    def test_normalize_handles_missing_fields(self, adapter: BlueCatAdapter) -> None:
        result = adapter.normalize([{"type": "host-record"}])
        assert result.claims[0].fields["name"] == ""

    def test_get_all_objects_swallows_parse_errors(self, adapter: BlueCatAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records", bam_json={"unexpected": True})
        assert isinstance(result, ClaimSet)

    def test_get_all_objects_with_garbage_payload(self, adapter: BlueCatAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records", bam_json="not-a-dict")  # type: ignore[arg-type]
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_malformed_properties_string_does_not_raise(self, adapter: BlueCatAdapter) -> None:
        payload = {"result": [{"id": 1, "properties": "no-equals-sign|also-bad"}]}
        result = adapter.get_all_objects(scope="dns-records", bam_json=payload)
        assert isinstance(result, ClaimSet)

    def test_collect_evidence_base_method_works(self, adapter: BlueCatAdapter) -> None:
        result = adapter.collect_evidence("KSI-IPAM-test")
        assert isinstance(result, EvidenceObject)
        assert result.source == "bluecat-address-manager"
