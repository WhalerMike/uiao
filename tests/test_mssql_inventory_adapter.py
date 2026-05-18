"""Tests for the MS SQL Estate Inventory Adapter (Tier-A1).

Happy path + failure modes for the read-only AD + Azure Resource Graph
inventory adapter. No live network calls; all inputs are injected via
the adapter's config-driven dependency-injection (``spn_inventory_input``
and ``arg_query_results`` config keys).
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from uiao.adapters.database_base import ClaimSet, DriftReport
from uiao.adapters.mssql_inventory_adapter import (
    ORGPATH_UNPOSITIONED,
    MSSQLInstanceClaim,
    MSSQLInventoryAdapter,
)
from uiao.adapters.mssql_parser import (
    normalize_arg_resource,
    normalize_spn_record,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic SPN + ARG inputs
# ---------------------------------------------------------------------------


def _spn_record(
    spn: str,
    principal: str = "CORP\\svc-sql01",
    principal_orgpath: str = "ORG-CORP-US-EAST-FIN",
    host_orgpath: str = "ORG-CORP-US-EAST",
) -> Dict[str, Any]:
    return {
        "servicePrincipalName": spn,
        "principal_name": principal,
        "principal_extension_attribute_1": principal_orgpath,
        "host_extension_attribute_1": host_orgpath,
    }


def _arg_resource(
    arm_id: str,
    name: str,
    rtype: str,
    orgpath: str | None = "ORG-CORP-US-EAST-FIN",
    location: str = "eastus2",
    subscription_id: str = "00000000-0000-0000-0000-000000000001",
) -> Dict[str, Any]:
    tags: Dict[str, str] = {}
    if orgpath is not None:
        tags["OrgPath"] = orgpath
    return {
        "id": arm_id,
        "name": name,
        "type": rtype,
        "location": location,
        "resourceGroup": "rg-fin",
        "subscriptionId": subscription_id,
        "properties": {},
        "tags": tags,
        "orgpath": orgpath,
    }


# ---------------------------------------------------------------------------
# Parser unit tests
# ---------------------------------------------------------------------------


class TestSpnNormalization:
    def test_port_form_parses(self) -> None:
        claim = normalize_spn_record(_spn_record("MSSQLSvc/sql01.corp.example:1433"))
        assert claim is not None
        assert claim.source == "ad-spn"
        assert claim.host == "sql01.corp.example"
        assert claim.port == 1433
        assert claim.instance_name is None
        assert claim.identifier == "sql01.corp.example:1433"

    def test_named_instance_form_parses(self) -> None:
        claim = normalize_spn_record(_spn_record("MSSQLSvc/sql01.corp.example:MSSQLSERVER"))
        assert claim is not None
        assert claim.host == "sql01.corp.example"
        assert claim.port is None
        assert claim.instance_name == "MSSQLSERVER"
        assert claim.identifier == "sql01.corp.example\\MSSQLSERVER"

    def test_orgpath_cascade_uses_principal_first(self) -> None:
        claim = normalize_spn_record(
            _spn_record(
                "MSSQLSvc/sql01.corp.example:1433",
                principal_orgpath="ORG-CORP-US-EAST-FIN",
                host_orgpath="ORG-CORP-US-EAST",
            )
        )
        assert claim is not None
        assert claim.orgpath == "ORG-CORP-US-EAST-FIN"
        assert claim.orgpath_attribution_source == "principal-extension"

    def test_orgpath_cascade_falls_back_to_host(self) -> None:
        record = _spn_record("MSSQLSvc/sql01.corp.example:1433")
        record["principal_extension_attribute_1"] = None
        claim = normalize_spn_record(record)
        assert claim is not None
        assert claim.orgpath == "ORG-CORP-US-EAST"
        assert claim.orgpath_attribution_source == "host-extension"

    def test_orgpath_cascade_unpositioned(self) -> None:
        record = _spn_record("MSSQLSvc/sql01.corp.example:1433")
        record["principal_extension_attribute_1"] = None
        record["host_extension_attribute_1"] = None
        claim = normalize_spn_record(record)
        assert claim is not None
        assert claim.orgpath == ORGPATH_UNPOSITIONED
        assert claim.orgpath_attribution_source == "unpositioned"

    def test_non_mssql_spn_returns_none(self) -> None:
        record = _spn_record("HTTP/webapp.corp.example")
        assert normalize_spn_record(record) is None

    def test_missing_spn_returns_none(self) -> None:
        assert normalize_spn_record({}) is None


class TestArgNormalization:
    def test_azure_sql_server_parses(self) -> None:
        claim = normalize_arg_resource(
            _arg_resource(
                arm_id="/subscriptions/sub1/providers/Microsoft.Sql/servers/srv1",
                name="srv1",
                rtype="microsoft.sql/servers",
            )
        )
        assert claim is not None
        assert claim.source == "arg-azure-sql"
        assert claim.azure_resource_type == "microsoft.sql/servers"
        assert claim.orgpath == "ORG-CORP-US-EAST-FIN"
        assert claim.orgpath_attribution_source == "arm-tag"

    def test_managed_instance_parses(self) -> None:
        claim = normalize_arg_resource(
            _arg_resource(
                arm_id="/subscriptions/sub1/providers/Microsoft.Sql/managedinstances/mi1",
                name="mi1",
                rtype="microsoft.sql/managedinstances",
            )
        )
        assert claim is not None
        assert claim.source == "arg-managed-instance"

    def test_arc_sql_parses(self) -> None:
        claim = normalize_arg_resource(
            _arg_resource(
                arm_id="/subscriptions/sub1/providers/Microsoft.AzureArcData/sqlServerInstances/arc1",
                name="arc1",
                rtype="microsoft.azurearcdata/sqlserverinstances",
            )
        )
        assert claim is not None
        assert claim.source == "arg-arc-sql"

    def test_sql_on_vm_parses(self) -> None:
        claim = normalize_arg_resource(
            _arg_resource(
                arm_id="/subscriptions/sub1/providers/Microsoft.SqlVirtualMachine/sqlVirtualMachines/vm1",
                name="vm1",
                rtype="microsoft.sqlvirtualmachine/sqlvirtualmachines",
            )
        )
        assert claim is not None
        assert claim.source == "arg-sql-on-vm"

    def test_missing_orgpath_tag_yields_unpositioned(self) -> None:
        claim = normalize_arg_resource(
            _arg_resource(
                arm_id="/subscriptions/sub1/providers/Microsoft.Sql/servers/srv2",
                name="srv2",
                rtype="microsoft.sql/servers",
                orgpath=None,
            )
        )
        assert claim is not None
        assert claim.orgpath == ORGPATH_UNPOSITIONED
        assert claim.orgpath_attribution_source == "unpositioned"

    def test_unknown_resource_type_returns_none(self) -> None:
        record = _arg_resource(
            arm_id="/subscriptions/sub1/providers/Microsoft.Storage/storageAccounts/sa1",
            name="sa1",
            rtype="microsoft.storage/storageaccounts",
        )
        assert normalize_arg_resource(record) is None


# ---------------------------------------------------------------------------
# Adapter integration tests
# ---------------------------------------------------------------------------


class TestAdapterHappyPath:
    """End-to-end happy path with mixed AD + ARG inputs."""

    def _build_adapter(self) -> MSSQLInventoryAdapter:
        spn_inputs: List[Dict[str, Any]] = [
            _spn_record("MSSQLSvc/sql-east.corp.example:1433"),
            _spn_record(
                "MSSQLSvc/sql-west.corp.example:NAMED1",
                principal="CORP\\svc-sqlwest",
                principal_orgpath="ORG-CORP-US-WEST-FIN",
            ),
        ]
        arg_inputs: List[Dict[str, Any]] = [
            _arg_resource(
                arm_id="/subscriptions/s/providers/Microsoft.Sql/servers/azsql-fin",
                name="azsql-fin",
                rtype="microsoft.sql/servers",
            ),
            _arg_resource(
                arm_id="/subscriptions/s/providers/Microsoft.AzureArcData/sqlServerInstances/arc-fin",
                name="arc-fin",
                rtype="microsoft.azurearcdata/sqlserverinstances",
                orgpath=None,  # unpositioned cloud instance
            ),
        ]
        return MSSQLInventoryAdapter(
            config={
                "tenant_id": "tenant-0001",
                "cloud": "commercial",
                "spn_inventory_input": spn_inputs,
                "arg_query_results": arg_inputs,
            }
        )

    def test_connect_emits_provenance(self) -> None:
        adapter = self._build_adapter()
        prov = adapter.connect()
        assert prov.identity == "tenant-0001"
        assert prov.auth_method.startswith("entra-managed-identity")
        assert prov.tls_version == "1.3"

    def test_discover_schema_returns_canonical_shape(self) -> None:
        adapter = self._build_adapter()
        schema = adapter.discover_schema()
        assert "MSSQLInstanceClaim" in schema.canonical_schema
        assert schema.unmapped_fields == []
        assert schema.version_hash  # hash present

    def test_execute_query_returns_all_claims(self) -> None:
        adapter = self._build_adapter()
        prov = adapter.execute_query({"select": ["mssql_instances"]})
        assert prov.row_count == 4  # 2 SPN + 2 ARG

    def test_unsupported_query_returns_zero_rows(self) -> None:
        adapter = self._build_adapter()
        prov = adapter.execute_query({"select": ["something_else"]})
        assert prov.row_count == 0
        assert prov.vendor_query == "UNSUPPORTED"

    def test_detect_drift_finds_unpositioned_arc_instance(self) -> None:
        adapter = self._build_adapter()
        report = adapter.detect_drift()
        assert isinstance(report, DriftReport)
        assert report.drift_type == "DRIFT-IDENTITY"
        assert report.severity == "P2"
        assert report.details["findings_count"] == 1
        # The Arc instance with no OrgPath tag is the one flagged.
        finding = report.details["findings"][0]
        assert finding["drift_class"] == "DRIFT-IDENTITY"
        assert finding["reason"] == "unpositioned"

    def test_normalize_handles_caller_supplied_rows(self) -> None:
        adapter = self._build_adapter()
        raw = [
            _spn_record("MSSQLSvc/sql-extra.corp.example:1433"),
            _arg_resource(
                arm_id="/subscriptions/s/providers/Microsoft.Sql/servers/azsql-extra",
                name="azsql-extra",
                rtype="microsoft.sql/servers",
            ),
        ]
        cs = adapter.normalize(raw)
        assert isinstance(cs, ClaimSet)
        assert len(cs.claims) == 2
        assert cs.source_reference == "caller-supplied"


class TestAdapterNoInputs:
    """When no inputs are configured and no client factory is set, the
    adapter logs warnings and produces an empty claim set rather than
    raising — federal estates routinely run AD-only or ARG-only.
    """

    def test_empty_when_no_inputs(self) -> None:
        adapter = MSSQLInventoryAdapter(
            config={
                "spn_inventory_input": [],
                "arg_query_results": [],
            }
        )
        prov = adapter.execute_query({"select": ["mssql_instances"]})
        assert prov.row_count == 0


@pytest.mark.parametrize(
    "claim_dict_field,expected_type",
    [
        ("identifier", str),
        ("source", str),
        ("orgpath", str),
        ("orgpath_attribution_source", str),
        ("discovered_at", str),
    ],
)
def test_mssql_instance_claim_serializes_required_fields(
    claim_dict_field: str, expected_type: type
) -> None:
    """The Tier-A1 schema requires these fields non-null on every claim."""
    claim = MSSQLInstanceClaim(
        identifier="sql01.corp.example:1433",
        source="ad-spn",
        host="sql01.corp.example",
        port=1433,
        instance_name=None,
        owning_principal="CORP\\svc-sql01",
        orgpath="ORG-CORP-US-EAST-FIN",
        orgpath_attribution_source="principal-extension",
        azure_resource_id=None,
        azure_resource_type=None,
        azure_subscription_id=None,
        azure_location=None,
        discovered_at="2026-05-17T16:00:00+00:00",
    )
    payload = claim.to_dict()
    assert claim_dict_field in payload
    assert isinstance(payload[claim_dict_field], expected_type)
