"""
Tests for the ServiceNow Adapter.

File: tests/test_servicenow_adapter.py

Coverage
--------
1.  Adapter instantiates with empty config (uses env defaults)
2.  connect() returns ConnectionProvenance with correct identity shape
3.  discover_schema() returns SchemaMappingObject with expected vendor + canonical keys
4.  execute_query() builds correct GET URL with sysparm_fields
5.  normalize() on empty list returns empty ClaimSet
6.  normalize() on a 2-record list returns 2 claims with correct entity and claim_id shape
7.  normalize() uses AC-2 fallback when uiao_control_id is missing
8.  detect_drift() returns info severity when collector returns empty scaffold
9.  detect_drift() returns high severity when collector returns drifted records
10. collect_and_align() returns dict with vendor, adapter_id, vendor_overlay_ref, claims, metadata keys
11. create_incident() happy-path (mock POST)  [skip if WS-A1 not merged]
12. update_incident() happy-path (mock PATCH) [skip if WS-A1 not merged]
13. create_change_request() happy-path (mock POST) [skip if WS-A1 not merged]
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from uiao.adapters.database_base import (
    ClaimSet,
    ConnectionProvenance,
    DriftReport,
    SchemaMappingObject,
)
from uiao.adapters.servicenow_adapter import ServiceNowAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter() -> ServiceNowAdapter:
    """Adapter with a recognisable instance name — no live token."""
    return ServiceNowAdapter({"instance": "test-instance", "token": ""})


@pytest.fixture
def adapter_empty() -> ServiceNowAdapter:
    """Adapter created with no config at all."""
    return ServiceNowAdapter()


# ---------------------------------------------------------------------------
# 1. Instantiation
# ---------------------------------------------------------------------------


class TestInstantiation:
    def test_instantiates_with_empty_config(self, adapter_empty: ServiceNowAdapter) -> None:
        """Adapter MUST instantiate without raising when config is omitted."""
        assert adapter_empty is not None

    def test_adapter_id(self, adapter: ServiceNowAdapter) -> None:
        assert adapter.ADAPTER_ID == "servicenow"

    def test_collector_instance_set(self, adapter: ServiceNowAdapter) -> None:
        assert adapter.collector.instance == "test-instance"


# ---------------------------------------------------------------------------
# 2. connect()
# ---------------------------------------------------------------------------


class TestConnect:
    def test_returns_connection_provenance(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert isinstance(result, ConnectionProvenance)

    def test_identity_shape(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert result.identity.startswith("servicenow:")
        assert "test-instance" in result.identity

    def test_auth_method(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert result.auth_method == "oauth-bearer"

    def test_endpoint_contains_instance(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.connect()
        assert "test-instance" in result.endpoint


# ---------------------------------------------------------------------------
# 3. discover_schema()
# ---------------------------------------------------------------------------


class TestDiscoverSchema:
    def test_returns_schema_mapping_object(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.discover_schema()
        assert isinstance(result, SchemaMappingObject)

    def test_vendor_schema_has_sys_id(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.discover_schema()
        assert "sys_id" in result.vendor_schema

    def test_canonical_schema_has_identity(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.discover_schema()
        assert "identity" in result.canonical_schema

    def test_version_hash_is_deterministic(self, adapter: ServiceNowAdapter) -> None:
        h1 = adapter.discover_schema().version_hash
        h2 = adapter.discover_schema().version_hash
        assert h1 == h2


# ---------------------------------------------------------------------------
# 4. execute_query()
# ---------------------------------------------------------------------------


class TestExecuteQuery:
    def test_builds_get_url_with_sysparm_fields(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.execute_query({"from": "incident", "select": ["sys_id", "short_description"]})
        assert "GET" in result.vendor_query
        assert "incident" in result.vendor_query
        assert "sysparm_fields" in result.vendor_query

    def test_default_table_is_incident(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.execute_query({})
        assert "incident" in result.vendor_query

    def test_custom_table_reflected(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.execute_query({"from": "change_request"})
        assert "change_request" in result.vendor_query


# ---------------------------------------------------------------------------
# 5 & 6 & 7. normalize()
# ---------------------------------------------------------------------------


class TestNormalize:
    def test_empty_list_returns_empty_claim_set(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet)
        assert len(result.claims) == 0

    def test_two_records_produce_two_claims(self, adapter: ServiceNowAdapter) -> None:
        records = [
            {"sys_id": "INC001", "short_description": "first", "uiao_control_id": "IR-4"},
            {"sys_id": "INC002", "short_description": "second", "uiao_control_id": "IR-5"},
        ]
        result = adapter.normalize(records)
        assert len(result.claims) == 2

    def test_claim_id_shape(self, adapter: ServiceNowAdapter) -> None:
        records = [{"sys_id": "INC001", "short_description": "test"}]
        claim = adapter.normalize(records).claims[0]
        assert claim.claim_id == "servicenow:INC001"

    def test_entity_shape(self, adapter: ServiceNowAdapter) -> None:
        records = [{"sys_id": "INC001", "short_description": "test"}]
        claim = adapter.normalize(records).claims[0]
        assert claim.entity == "servicenow:ticket:INC001"

    def test_ac2_fallback_when_control_id_missing(self, adapter: ServiceNowAdapter) -> None:
        """When uiao_control_id is absent the control_id field MUST default to AC-2."""
        records = [{"sys_id": "INC999", "short_description": "no control id"}]
        claim = adapter.normalize(records).claims[0]
        assert claim.fields["control_id"] == "AC-2"

    def test_source_is_adapter_id(self, adapter: ServiceNowAdapter) -> None:
        records = [{"sys_id": "INC001", "short_description": "test"}]
        claim = adapter.normalize(records).claims[0]
        assert claim.source == "servicenow"


# ---------------------------------------------------------------------------
# 8 & 9. detect_drift()
# ---------------------------------------------------------------------------


class TestDetectDrift:
    def test_returns_drift_report(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.detect_drift()
        assert isinstance(result, DriftReport)

    def test_drift_type_is_servicenow_record_divergence(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.detect_drift()
        assert result.drift_type == "servicenow-record-divergence"

    def test_info_severity_when_collector_returns_empty_scaffold(self, adapter: ServiceNowAdapter) -> None:
        """When no token is set the collector returns an empty scaffold — no drift."""
        # adapter fixture has no token, so fetch_relevant_records() returns scaffold
        result = adapter.detect_drift()
        assert result.severity == "info"

    def test_details_has_adapter_key(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.detect_drift()
        assert result.details.get("adapter") == "servicenow"

    def test_high_severity_when_collector_returns_drifted_records(self, adapter: ServiceNowAdapter) -> None:
        """When collector returns records not in canon scope, severity MUST be high."""
        drifted_records: list[dict[str, Any]] = [
            {
                "sys_id": "INC-UNKNOWN-001",
                "short_description": "undocumented ticket",
                "_drift": "new_record",
            }
        ]
        with (
            patch.object(
                adapter.collector,
                "fetch_relevant_records",
                return_value={"result": [{"sys_id": "INC-UNKNOWN-001", "short_description": "undocumented ticket"}]},
            ),
            patch.object(
                adapter.collector,
                "compare_for_drift",
                return_value=drifted_records,
            ),
        ):
            result = adapter.detect_drift()

        assert result.severity == "high"
        assert result.details["drifted_count"] == 1
        assert "INC-UNKNOWN-001" in result.details["new_records"]


# ---------------------------------------------------------------------------
# 10. collect_and_align()
# ---------------------------------------------------------------------------


class TestCollectAndAlign:
    def test_returns_dict(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_and_align()
        assert isinstance(result, dict)

    def test_required_top_level_keys(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_and_align()
        for key in ("vendor", "adapter_id", "vendor_overlay_ref", "claims", "metadata"):
            assert key in result, f"Missing key: {key}"

    def test_vendor_field(self, adapter: ServiceNowAdapter) -> None:
        assert adapter.collect_and_align()["vendor"] == "ServiceNow"

    def test_adapter_id_field(self, adapter: ServiceNowAdapter) -> None:
        assert adapter.collect_and_align()["adapter_id"] == "servicenow"

    def test_vendor_overlay_ref_field(self, adapter: ServiceNowAdapter) -> None:
        result = adapter.collect_and_align()
        assert "servicenow" in result["vendor_overlay_ref"].lower()

    def test_metadata_keys(self, adapter: ServiceNowAdapter) -> None:
        metadata = adapter.collect_and_align()["metadata"]
        for key in ("total_records", "last_collected", "instance"):
            assert key in metadata, f"Missing metadata key: {key}"


# ---------------------------------------------------------------------------
# 11-13. Write-side methods (skip if WS-A1 not yet merged)
# ---------------------------------------------------------------------------

_HAS_WRITE_METHODS = all(
    hasattr(ServiceNowAdapter, m) for m in ("create_incident", "update_incident", "create_change_request")
)

_SKIP_WRITE = pytest.mark.skipif(
    not _HAS_WRITE_METHODS,
    reason="WS-A1 write methods not yet merged — skipping write happy-path tests",
)


class TestWriteMethods:
    @_SKIP_WRITE
    def test_create_incident_happy_path(self, adapter: ServiceNowAdapter) -> None:
        """create_incident() returns ok=True and a sys_id when POST succeeds."""
        mock_response = {"result": {"sys_id": "INC-MOCK-001", "short_description": "test"}}
        with patch.object(adapter.collector, "post_record", return_value=mock_response):
            result = adapter.create_incident(
                short_description="Test incident for MFA drift",
                uiao_control_id="IA-2",
            )
        assert result["ok"] is True
        assert result["sys_id"] == "INC-MOCK-001"
        assert result["error"] is None
        assert "claim_id" in result["evidence"]

    @_SKIP_WRITE
    def test_update_incident_happy_path(self, adapter: ServiceNowAdapter) -> None:
        """update_incident() returns ok=True and preserves sys_id when PATCH succeeds."""
        mock_response = {"result": {"sys_id": "INC-MOCK-001", "state": "2"}}
        with patch.object(adapter.collector, "patch_record", return_value=mock_response):
            result = adapter.update_incident("INC-MOCK-001", state="2", work_notes="Acknowledged.")
        assert result["ok"] is True
        assert result["sys_id"] == "INC-MOCK-001"
        assert result["error"] is None

    @_SKIP_WRITE
    def test_create_change_request_happy_path(self, adapter: ServiceNowAdapter) -> None:
        """create_change_request() returns ok=True with sys_id when POST succeeds."""
        mock_response = {"result": {"sys_id": "CHG-MOCK-001", "short_description": "rotate cert"}}
        with patch.object(adapter.collector, "post_record", return_value=mock_response):
            result = adapter.create_change_request(
                short_description="Rotate CyberArk vault cert per CM-3",
                uiao_control_id="CM-3",
            )
        assert result["ok"] is True
        assert result["sys_id"] == "CHG-MOCK-001"
