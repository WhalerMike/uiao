"""
Tests for the Infoblox NIOS DNS / IPAM Adapter.

File: tests/test_infoblox_adapter.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.impl.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)
from uiao.impl.adapters.infoblox_adapter import InfobloxAdapter

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def adapter() -> InfobloxAdapter:
    return InfobloxAdapter(
        {
            "grid_master": "gm.agency.gov",
            "network_view": "prod",
            "auth_method": "api-key",
        }
    )


@pytest.fixture
def adapter_empty() -> InfobloxAdapter:
    return InfobloxAdapter()


@pytest.fixture
def a_records() -> dict:
    return _load("infoblox-records.json")


@pytest.fixture
def networks() -> dict:
    return _load("infoblox-networks.json")


@pytest.fixture
def dhcp_ranges() -> dict:
    return _load("infoblox-dhcp-ranges.json")


@pytest.fixture
def fixed_addresses() -> dict:
    return _load("infoblox-fixed-addresses.json")


class TestInstantiation:
    def test_adapter_id(self, adapter: InfobloxAdapter) -> None:
        assert adapter.ADAPTER_ID == "infoblox"

    def test_default_config(self, adapter_empty: InfobloxAdapter) -> None:
        assert adapter_empty._grid_master == ""
        assert adapter_empty._network_view == "default"
        assert adapter_empty._wapi_version == "v2.12"

    def test_custom_config(self, adapter: InfobloxAdapter) -> None:
        assert adapter._grid_master == "gm.agency.gov"
        assert adapter._network_view == "prod"

    def test_scope_defined(self, adapter: InfobloxAdapter) -> None:
        assert len(adapter.SCOPE) == 5
        for required in (
            "dns-records",
            "dhcp-scopes",
            "ip-allocations",
            "network-views",
            "side-by-side-ad",
        ):
            assert required in adapter.SCOPE

    def test_is_database_adapter_base(self, adapter: InfobloxAdapter) -> None:
        assert isinstance(adapter, DatabaseAdapterBase)


class TestConnect:
    def test_connect_returns_provenance(self, adapter: InfobloxAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_connect_identity_includes_grid_master(self, adapter: InfobloxAdapter) -> None:
        assert "gm.agency.gov" in adapter.connect().identity

    def test_connect_identity_includes_view(self, adapter: InfobloxAdapter) -> None:
        assert "prod" in adapter.connect().identity

    def test_connect_endpoint(self, adapter: InfobloxAdapter) -> None:
        assert adapter.connect().endpoint == "https://gm.agency.gov/wapi/v2.12/"

    def test_connect_mtls_default_true(self, adapter: InfobloxAdapter) -> None:
        assert adapter.connect().mtls_enabled is True


class TestDiscoverSchema:
    def test_returns_schema_mapping(self, adapter: InfobloxAdapter) -> None:
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)

    def test_vendor_schema_covers_all_object_types(self, adapter: InfobloxAdapter) -> None:
        schema = adapter.discover_schema()
        for required in ("record:a", "record:cname", "networkview", "range", "fixedaddress"):
            assert required in schema.vendor_schema

    def test_unmapped_fields_captured(self, adapter: InfobloxAdapter) -> None:
        assert "extattrs" in adapter.discover_schema().unmapped_fields

    def test_version_hash_deterministic(self, adapter: InfobloxAdapter) -> None:
        assert adapter.discover_schema().version_hash == adapter.discover_schema().version_hash


class TestExecuteQuery:
    def test_returns_query_provenance(self, adapter: InfobloxAdapter) -> None:
        assert isinstance(adapter.execute_query({"from": "dns-records"}), QueryProvenance)

    def test_each_scope_yields_distinct_endpoint(self, adapter: InfobloxAdapter) -> None:
        seen = set()
        for scope in adapter.SCOPE:
            seen.add(adapter.execute_query({"from": scope}).vendor_query)
        assert len(seen) == len(adapter.SCOPE)

    def test_query_includes_network_view(self, adapter: InfobloxAdapter) -> None:
        assert "network_view=prod" in adapter.execute_query({"from": "dns-records"}).vendor_query

    def test_query_uses_wapi_version(self, adapter: InfobloxAdapter) -> None:
        assert "/wapi/v2.12/" in adapter.execute_query({"from": "dns-records"}).vendor_query

    def test_unknown_scope_falls_back(self, adapter: InfobloxAdapter) -> None:
        result = adapter.execute_query({"from": "totally-fake-scope"})
        assert "record:a" in result.vendor_query


class TestNormalize:
    def test_empty_input(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_a_record_claim_id_shape(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "record-a", "name": "web01.contoso.gov", "ipv4addr": "10.0.1.1"}])
        assert result.claims[0].claim_id == "infoblox:prod:record-a:web01.contoso.gov"
        assert result.claims[0].source == "infoblox"

    def test_cname_claim_id_shape(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "record-cname", "name": "api.contoso.gov", "canonical": "web01"}])
        assert result.claims[0].claim_id == "infoblox:prod:record-cname:api.contoso.gov"

    def test_network_claim_id_shape(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "network", "cidr": "10.0.1.0/24"}])
        assert result.claims[0].claim_id == "infoblox:prod:network:10.0.1.0/24"

    def test_dhcp_range_claim_id_shape(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "dhcp-range", "start": "10.0.1.10", "end": "10.0.1.99"}])
        assert "10.0.1.10-10.0.1.99" in result.claims[0].claim_id

    def test_fixed_address_claim_id_shape(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "fixed-address", "ipv4addr": "10.0.1.5", "mac": "00:1b:21:aa:bb:01"}])
        assert result.claims[0].claim_id == "infoblox:prod:fixed-address:10.0.1.5"

    def test_mixed_types_in_one_set(self, adapter: InfobloxAdapter) -> None:
        rows = [
            {"type": "record-a", "name": "host1", "ipv4addr": "1.1.1.1"},
            {"type": "network", "cidr": "10.0.0.0/24"},
            {"type": "fixed-address", "ipv4addr": "10.0.0.5", "mac": "aa"},
        ]
        result = adapter.normalize(rows)
        assert len(result.claims) == 3
        types = {c.fields["object_type"] for c in result.claims}
        assert types == {"record-a", "network", "fixed-address"}

    def test_unknown_type_falls_through(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "exotic", "name": "x"}])
        assert len(result.claims) == 1
        assert "raw" in result.claims[0].fields


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: InfobloxAdapter) -> None:
        assert isinstance(adapter.detect_drift(), DriftReport)

    def test_scaffold_when_inputs_missing(self, adapter: InfobloxAdapter) -> None:
        result = adapter.detect_drift()
        assert result.severity == "info"
        assert "not configured" in result.details["message"]

    def test_real_diff_emits_drift(self) -> None:
        baseline = [{"type": "record-a", "name": "a", "ipv4addr": "1.1.1.1", "view": "prod", "ref": "r1"}]
        live = [{"type": "record-a", "name": "b", "ipv4addr": "2.2.2.2", "view": "prod", "ref": "r2"}]
        a = InfobloxAdapter({
            "grid_master": "gm",
            "network_view": "prod",
            "baseline_records": baseline,
            "live_records": live,
        })
        result = a.detect_drift()
        assert result.severity == "high"
        assert result.details["summary"]["drift_count"] == 2
        assert "r1" in result.details["removed"]
        assert "r2" in result.details["added"]

    def test_no_drift_when_baseline_matches(self) -> None:
        rows = [{"type": "record-a", "name": "a", "ipv4addr": "1.1.1.1", "view": "prod", "ref": "r1"}]
        a = InfobloxAdapter({
            "grid_master": "gm",
            "network_view": "prod",
            "baseline_records": rows,
            "live_records": rows,
        })
        result = a.detect_drift()
        assert result.severity == "info"
        assert result.details["summary"]["drift_count"] == 0

    def test_drift_type_constant(self, adapter: InfobloxAdapter) -> None:
        assert adapter.detect_drift().drift_type == "infoblox-ipam-config"


class TestGetAllObjects:
    """Real WAPI JSON parsing tests via injected payloads."""

    def test_parses_dns_records(self, adapter: InfobloxAdapter, a_records: dict) -> None:
        result = adapter.get_all_objects(scope="dns-records", wapi_json=a_records)
        assert isinstance(result, ClaimSet)
        assert len(result.claims) >= 3

    def test_parses_dhcp_ranges(self, adapter: InfobloxAdapter, dhcp_ranges: dict) -> None:
        result = adapter.get_all_objects(scope="dhcp-scopes", wapi_json=dhcp_ranges)
        assert len(result.claims) == 3
        ranges = [c for c in result.claims if c.fields["object_type"] == "dhcp-range"]
        assert len(ranges) == 3

    def test_parses_fixed_addresses(self, adapter: InfobloxAdapter, fixed_addresses: dict) -> None:
        result = adapter.get_all_objects(scope="ip-allocations", wapi_json=fixed_addresses)
        macs = {c.fields.get("mac", "") for c in result.claims}
        assert "00:1b:21:aa:bb:01" in macs

    def test_parses_networks(self, adapter: InfobloxAdapter, networks: dict) -> None:
        result = adapter.get_all_objects(scope="network-views", wapi_json=networks)
        cidrs = {c.fields.get("cidr", "") for c in result.claims}
        assert "10.0.1.0/24" in cidrs

    def test_no_payload_returns_empty(self, adapter: InfobloxAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records")
        assert len(result.claims) == 0

    def test_provenance_deterministic(self, adapter: InfobloxAdapter, dhcp_ranges: dict) -> None:
        r1 = adapter.get_all_objects(scope="dhcp-scopes", wapi_json=dhcp_ranges)
        r2 = adapter.get_all_objects(scope="dhcp-scopes", wapi_json=dhcp_ranges)
        assert {c.provenance_hash for c in r1.claims} == {c.provenance_hash for c in r2.claims}

    def test_scope_none_iterates_all(self, dhcp_ranges: dict) -> None:
        a = InfobloxAdapter({
            "grid_master": "gm",
            "network_view": "prod",
            "_dhcp-scopes_json": dhcp_ranges,
        })
        result = a.get_all_objects()
        assert len(result.claims) == 3


class TestPushDnsChange:
    def test_returns_drift_report(self, adapter: InfobloxAdapter) -> None:
        result = adapter.push_dns_change("record:a", "host1.example.gov", {"ipv4addr": "10.0.0.1"})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "infoblox-dns-change"

    def test_proposed_change_in_details(self, adapter: InfobloxAdapter) -> None:
        result = adapter.push_dns_change("record:a", "host1", {"ipv4addr": "10.0.0.1"})
        assert result.details["name"] == "host1"
        assert result.details["proposed"]["ipv4addr"] == "10.0.0.1"


class TestPushDhcpChange:
    def test_returns_drift_report(self, adapter: InfobloxAdapter) -> None:
        result = adapter.push_dhcp_change("dhcp-range", "10.0.1.10-10.0.1.99", {"comment": "expand"})
        assert isinstance(result, DriftReport)
        assert result.drift_type == "infoblox-dhcp-change"

    def test_identifier_preserved(self, adapter: InfobloxAdapter) -> None:
        result = adapter.push_dhcp_change("fixed-address", "10.0.1.5", {"mac": "00:11:22:33:44:55"})
        assert result.details["identifier"] == "10.0.1.5"
        assert result.details["scope_type"] == "fixed-address"


class TestEmitEventStream:
    def test_writes_ndjson(self, adapter: InfobloxAdapter, tmp_path: Path) -> None:
        events = [{"k": 1, "user": "alice"}, {"k": 2, "user": "bob"}]
        out = adapter.emit_event_stream(events, tmp_path / "events.ndjson")
        lines = out.read_text().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["user"] == "alice"

    def test_empty_events_writes_empty_file(self, adapter: InfobloxAdapter, tmp_path: Path) -> None:
        out = adapter.emit_event_stream([], tmp_path / "empty.ndjson")
        assert out.read_text() == ""

    def test_default_path(self, adapter: InfobloxAdapter, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        out = adapter.emit_event_stream([{"x": 1}])
        assert out.name == "event-stream.ndjson"
        assert out.exists()


class TestGenerateIpamEvidence:
    def test_returns_evidence(self, adapter: InfobloxAdapter, a_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", wapi_json=a_records)
        assert isinstance(result, EvidenceObject)

    def test_source(self, adapter: InfobloxAdapter, a_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", wapi_json=a_records)
        assert result.source == "infoblox"

    def test_ksi_id_includes_view(self, adapter: InfobloxAdapter, a_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", wapi_json=a_records)
        assert "prod" in result.ksi_id

    def test_provenance_includes_grid_master(self, adapter: InfobloxAdapter, a_records: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dns-records", wapi_json=a_records)
        assert result.provenance["grid_master"] == "gm.agency.gov"

    def test_normalized_claims_present(self, adapter: InfobloxAdapter, dhcp_ranges: dict) -> None:
        result = adapter.generate_ipam_evidence(scope="dhcp-scopes", wapi_json=dhcp_ranges)
        assert result.normalized_data is not None
        assert len(result.normalized_data["claims"]) == 3


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: InfobloxAdapter) -> None:
        assert isinstance(adapter.collect_and_align(), dict)

    def test_vendor_field(self, adapter: InfobloxAdapter) -> None:
        assert adapter.collect_and_align()["vendor"] == "Infoblox"

    def test_adapter_id_field(self, adapter: InfobloxAdapter) -> None:
        assert adapter.collect_and_align()["adapter_id"] == "infoblox"

    def test_metadata_grid_master(self, adapter: InfobloxAdapter) -> None:
        assert adapter.collect_and_align()["metadata"]["grid_master"] == "gm.agency.gov"

    def test_metadata_scope_count(self, adapter: InfobloxAdapter) -> None:
        assert len(adapter.collect_and_align()["metadata"]["scope"]) == 5


class TestFailureModes:
    def test_normalize_handles_missing_fields(self, adapter: InfobloxAdapter) -> None:
        result = adapter.normalize([{"type": "record-a"}])
        assert result.claims[0].fields["name"] == ""

    def test_get_all_objects_swallows_parse_errors(self, adapter: InfobloxAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records", wapi_json={"unexpected": True})
        assert isinstance(result, ClaimSet)

    def test_get_all_objects_with_garbage_payload(self, adapter: InfobloxAdapter) -> None:
        result = adapter.get_all_objects(scope="dns-records", wapi_json="not-a-dict")  # type: ignore[arg-type]
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_collect_evidence_base_method_works(self, adapter: InfobloxAdapter) -> None:
        result = adapter.collect_evidence("KSI-IPAM-test")
        assert isinstance(result, EvidenceObject)
        assert result.source == "infoblox"
