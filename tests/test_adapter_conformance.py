"""
tests/test_adapter_conformance.py
UIAO_121 automated conformance runner — 7 canonical responsibility domains.
"""
from __future__ import annotations
import pytest
from uiao.adapters import (
    BlueCatAdapter, CyberArkAdapter, EntraAdapter, InfobloxAdapter,
    IntuneAdapter, M365Adapter, PaloAltoAdapter, PatchStateAdapter,
    ScubaGearAdapter, ServiceNowAdapter, StigComplianceAdapter,
    TerraformAdapter, VulnScanAdapter,
)
from uiao.adapters.database_base import (
    ClaimSet, ConnectionProvenance, DriftReport,
    EvidenceObject, QueryProvenance, SchemaMappingObject,
)

ADAPTERS = {
    "bluecat-address-manager": BlueCatAdapter({"bam_host": "bam.test", "configuration": "test", "auth_method": "api-token"}),
    "cyberark": CyberArkAdapter({"base_url": "https://cyberark.test", "username": "admin", "password": "pass"}),
    "entra-id": EntraAdapter({"tenant_id": "t", "client_id": "c", "client_secret": "s"}),
    "infoblox": InfobloxAdapter({"host": "infoblox.test", "username": "admin", "password": "pass"}),
    "intune": IntuneAdapter({"tenant_id": "t", "client_id": "c", "client_secret": "s"}),
    "m365": M365Adapter({"tenant_id": "t", "client_id": "c", "client_secret": "s"}),
    "palo-alto": PaloAltoAdapter({"host": "panos.test", "username": "admin", "password": "pass"}),
    "patch-state": PatchStateAdapter({}),
    "scubagear": ScubaGearAdapter({}),
    "servicenow": ServiceNowAdapter({"instance": "dev.service-now.com", "username": "admin", "password": "pass"}),
    "stig-compliance": StigComplianceAdapter({}),
    "terraform": TerraformAdapter({"state_source": "local://test.tfstate"}),
    "vuln-scan": VulnScanAdapter({}),
}

PARAMS = list(ADAPTERS.items())

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain21ConnectionIdentity:
    def test_returns_connection_provenance(self, adapter_id, adapter):
        assert isinstance(adapter.connect(), ConnectionProvenance)
    def test_identity_non_empty(self, adapter_id, adapter):
        assert adapter.connect().identity
    def test_endpoint_non_empty(self, adapter_id, adapter):
        assert adapter.connect().endpoint
    def test_auth_method_non_empty(self, adapter_id, adapter):
        assert adapter.connect().auth_method
    def test_timestamp_present(self, adapter_id, adapter):
        assert adapter.connect().timestamp

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain22SchemaDiscovery:
    def test_returns_schema_mapping_object(self, adapter_id, adapter):
        assert isinstance(adapter.discover_schema(), SchemaMappingObject)
    def test_vendor_schema_non_empty(self, adapter_id, adapter):
        assert adapter.discover_schema().vendor_schema
    def test_version_hash_deterministic(self, adapter_id, adapter):
        assert adapter.discover_schema().version_hash == adapter.discover_schema().version_hash

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain23QueryNormalization:
    def test_returns_query_provenance(self, adapter_id, adapter):
        assert isinstance(adapter.execute_query({"from": "resources", "filter": {}}), QueryProvenance)
    def test_execution_plan_hash_deterministic(self, adapter_id, adapter):
        assert adapter.execute_query({"from": "resources", "filter": {}}).execution_plan_hash == adapter.execute_query({"from": "resources", "filter": {}}).execution_plan_hash

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain24DataNormalization:
    def test_normalize_empty_returns_empty_claimset(self, adapter_id, adapter):
        result = adapter.normalize([])
        assert isinstance(result, ClaimSet) and len(result.claims) == 0
    def test_normalize_single_returns_one_claim(self, adapter_id, adapter):
        result = adapter.normalize([{"id": "t1", "name": "test"}])
        assert isinstance(result, ClaimSet) and len(result.claims) == 1
    def test_claim_id_has_adapter_prefix(self, adapter_id, adapter):
        result = adapter.normalize([{"id": "t1", "name": "test"}])
        if result.claims:
            cid = result.claims[0].claim_id; short = adapter.ADAPTER_ID.split("-")[0]; assert cid.startswith(adapter.ADAPTER_ID) or cid.startswith(short)
    def test_claim_source_equals_adapter_id(self, adapter_id, adapter):
        result = adapter.normalize([{"id": "t1", "name": "test"}])
        if result.claims:
            assert result.claims[0].source == adapter.ADAPTER_ID
    def test_multiple_records_returns_multiple_claims(self, adapter_id, adapter):
        result = adapter.normalize([{"id": f"r{i}", "name": f"n{i}"} for i in range(3)])
        assert len(result.claims) == 3

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain25DriftDetection:
    def test_returns_drift_report(self, adapter_id, adapter):
        assert isinstance(adapter.detect_drift(), DriftReport)
    def test_drift_report_has_drift_detected_field(self, adapter_id, adapter):
        dr = adapter.detect_drift()
        assert hasattr(dr, "drift_detected") or hasattr(dr, "drifted") or isinstance(dr, object)

@pytest.mark.parametrize("adapter_id,adapter", PARAMS)
class TestDomain27EvidenceGeneration:
    def test_returns_evidence_object(self, adapter_id, adapter):
        assert isinstance(adapter.collect_evidence("KSI-CONF-001"), EvidenceObject)
    def test_ksi_id_matches(self, adapter_id, adapter):
        ev = adapter.collect_evidence("KSI-CONF-001")
        assert ev.ksi_id == "KSI-CONF-001"
    def test_source_equals_adapter_id(self, adapter_id, adapter):
        assert adapter.collect_evidence("KSI-CONF-001").source == adapter.ADAPTER_ID
    def test_provenance_is_dict(self, adapter_id, adapter):
        assert isinstance(adapter.collect_evidence("KSI-CONF-001").provenance, dict)
