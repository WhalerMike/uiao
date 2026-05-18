"""MS SQL Estate Inventory Adapter — Tier-A1 (read-only AD + Azure Resource Graph).

Conformance adapter that discovers and attributes the Microsoft SQL Server
estate across an agency tenant. Read-only by design; no write operations,
no SSOT mutation. Output is a normalized inventory of every MS SQL surface
the substrate can reach via:

* AD LDAP — Kerberos-registered instances via ``MSSQLSvc/*`` SPN scan
  (reuses ``uiao.adapters.modernization.active_directory.survey``).
* Azure Resource Graph — Azure SQL Database, Azure SQL Managed Instance,
  Azure Arc-enrolled SQL Server, SQL on Azure VMs.

This is the **Tier-A1** scope: the WHERE and the WHO. It does *not* connect
to individual SQL instances to enumerate inside-the-instance state
(databases, schemas, tables, row counts) — that is Tier-A2, a sibling
adapter that extends ``DatabaseAdapterBase`` per instance and requires
separate authorization (a SQL login with ``VIEW SERVER STATE`` + ``VIEW
ANY DEFINITION``).

Companion to the rationalization process spec at
``inbox/Modernization/sql-modernization-research/2026-05-17-orgpath-mssql-estate-rationalization-process.md``
(Phase 1, "Estate Enumeration with OrgPath Attribution"). Tier-A1
delivers everything that document specifies for Phase 1 except the
inside-the-instance system-catalog queries.

Read-only invariants:

* No write operations against any SQL instance.
* No write operations against AD or Azure resources.
* All outputs are normalized JSON objects; no canonical state mutation.
* The adapter consumes existing AD survey output (per ``survey.py``) and
  Azure Resource Graph queries (read-only Reader role).

OrgPath attribution cascades per UIAO_153 / ADR-063:

1. Owning principal's ``extensionAttribute1`` (preferred).
2. Hosting computer's ``extensionAttribute1`` (fallback).
3. ARM tag ``OrgPath`` for cloud instances (preferred for that subset).
4. ``ORG-BRANCH-UNPOSITIONED`` (fires ``DRIFT-IDENTITY``).

Registry status: this adapter is **NOT** registered in
``adapter-registry.yaml`` as of this commit. Registration is a separate
canon-change PR requiring ADR ratification (the registry has strict
slot counts per the registry's own header comment).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ._graph_clouds import DEFAULT_CLOUD, resolve_graph_base
from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    QueryProvenance,
    SchemaMappingObject,
)
from .mssql_parser import normalize_arg_resource, normalize_spn_record

logger = logging.getLogger(__name__)


# Canonical OrgPath regex (UIAO_151). Local copy to avoid governance.drift
# dependency cycle — same pattern as EntraAdapter._ORGPATH_REGEX.
_ORGPATH_REGEX = re.compile(r"^ORG(-[A-Z0-9]{2,6}){0,8}$")

# Quarantine OrgPath for unattributed instances (per ADR-073 §"Intent").
ORGPATH_UNPOSITIONED = "ORG-BRANCH-UNPOSITIONED"

# The Azure Resource Graph KQL query that surfaces every MS SQL surface.
# Single query covers Azure SQL DB, MI, Arc-enrolled SQL, SQL-on-VM.
ARG_QUERY_MSSQL_RESOURCES = """
Resources
| where type in~ (
    'microsoft.sql/servers',
    'microsoft.sql/servers/databases',
    'microsoft.sql/managedinstances',
    'microsoft.sql/managedinstances/databases',
    'microsoft.azurearcdata/sqlserverinstances',
    'microsoft.sqlvirtualmachine/sqlvirtualmachines'
  )
| project
    id,
    name,
    type,
    location,
    resourceGroup,
    subscriptionId,
    properties,
    tags,
    orgpath = tostring(tags['OrgPath'])
| order by type asc, id asc
"""


@dataclass
class MSSQLInstanceClaim:
    """Single normalized SQL instance claim — wire-format for downstream."""

    identifier: str  # canonical "host\\instance" or ARM resource id
    source: str  # "ad-spn" | "arg-azure-sql" | "arg-managed-instance" | etc.
    host: Optional[str]
    port: Optional[int]
    instance_name: Optional[str]
    owning_principal: Optional[str]  # SPN principal or ARM principal
    orgpath: str  # always populated; UNPOSITIONED if no source resolves
    orgpath_attribution_source: str  # "principal-extension" | "host-extension" | "arm-tag" | "unpositioned"
    azure_resource_id: Optional[str]
    azure_resource_type: Optional[str]
    azure_subscription_id: Optional[str]
    azure_location: Optional[str]
    discovered_at: str  # ISO-8601 UTC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identifier": self.identifier,
            "source": self.source,
            "host": self.host,
            "port": self.port,
            "instance_name": self.instance_name,
            "owning_principal": self.owning_principal,
            "orgpath": self.orgpath,
            "orgpath_attribution_source": self.orgpath_attribution_source,
            "azure_resource_id": self.azure_resource_id,
            "azure_resource_type": self.azure_resource_type,
            "azure_subscription_id": self.azure_subscription_id,
            "azure_location": self.azure_location,
            "discovered_at": self.discovered_at,
        }


class MSSQLInventoryAdapter(DatabaseAdapterBase):
    """MS SQL Estate Inventory Adapter (Tier-A1: AD + ARG, read-only).

    Delegates Active Directory SPN discovery to the existing AD survey
    adapter (``uiao.adapters.modernization.active_directory.survey``)
    and the Azure Resource Graph half to a tenant-scoped ARG client.

    Config keys:

    * ``tenant_id`` (str, optional) — Entra tenant for ARG queries.
    * ``cloud`` (str, default ``commercial``) — ``commercial``,
      ``gcc-high``, or ``dod``. Resolves ARG and Graph endpoints
      via ``_graph_clouds.resolve_graph_base``.
    * ``spn_inventory_input`` (list[dict], optional) — pre-fetched SPN
      records (from ``survey.extract_spn_inventory()``). When
      provided, the adapter does not re-query AD. Useful for the
      "AD survey was run separately, here's the output" flow common
      in federal engagements where AD access is via a different
      authorization gate than ARG.
    * ``arg_query_results`` (list[dict], optional) — pre-fetched ARG
      results. Same dependency-injection pattern as ``spn_inventory_input``.
    * ``arg_client_factory`` (callable, optional) — factory returning
      an Azure Resource Graph client. If absent and ``arg_query_results``
      is also absent, ARG discovery is skipped with a warning.

    Output shape: see ``src/uiao/schemas/mssql-inventory/mssql-inventory.schema.json``.
    """

    ADAPTER_ID: str = "mssql-inventory"

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config or {})
        self._tenant_id: Optional[str] = self._config.get("tenant_id")
        self._cloud: str = self._config.get("cloud", DEFAULT_CLOUD)
        self._spn_inventory_input: Optional[List[Dict[str, Any]]] = self._config.get("spn_inventory_input")
        self._arg_query_results: Optional[List[Dict[str, Any]]] = self._config.get("arg_query_results")
        self._arg_client_factory = self._config.get("arg_client_factory")
        # Graph endpoint resolved for consistency with other adapters; not
        # used directly here (ARG is a separate API surface), but the cloud
        # parameter selection must agree with the rest of the substrate.
        self._graph_endpoint: str = resolve_graph_base(
            cloud=self._cloud,
            graph_api_version="v1.0",
            explicit=self._config.get("graph_endpoint"),
            adapter_name="MSSQLInventoryAdapter",
        )
        self._claims_cache: Optional[ClaimSet] = None

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity Domain
    # ------------------------------------------------------------------
    def connect(self) -> ConnectionProvenance:
        """Record the read-only connection envelope (no actual SQL connection)."""
        return ConnectionProvenance(
            identity=self._tenant_id or "ad-bound-context",
            auth_method="entra-managed-identity-or-ad-read-only",
            endpoint=self._graph_endpoint,
            tls_version="1.3",
            mtls_enabled=False,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping Domain
    # ------------------------------------------------------------------
    def discover_schema(self) -> SchemaMappingObject:
        """Return the canonical schema for the inventory output."""
        canonical = {
            "MSSQLInstanceClaim": {
                "identifier": "string",
                "source": "enum[ad-spn,arg-azure-sql,arg-managed-instance,arg-arc-sql,arg-sql-on-vm]",
                "host": "string|null",
                "port": "integer|null",
                "instance_name": "string|null",
                "owning_principal": "string|null",
                "orgpath": "string",
                "orgpath_attribution_source": "enum[principal-extension,host-extension,arm-tag,unpositioned]",
                "azure_resource_id": "string|null",
                "azure_resource_type": "string|null",
                "azure_subscription_id": "string|null",
                "azure_location": "string|null",
                "discovered_at": "iso8601-timestamp",
            }
        }
        vendor = {
            "ad-spn": "servicePrincipalName matching MSSQLSvc/*",
            "azure-resource-graph": "Resources where type in~ ('microsoft.sql/*', 'microsoft.azurearcdata/*', 'microsoft.sqlvirtualmachine/*')",
        }
        mapping_rules = {
            "ad-spn->MSSQLInstanceClaim": "parse SPN; resolve owning principal; cascade OrgPath via UIAO_153",
            "arg-resource->MSSQLInstanceClaim": "extract tags.OrgPath ARM tag; cascade via UIAO_153",
        }
        return SchemaMappingObject(
            vendor_schema=vendor,
            canonical_schema=canonical,
            mapping_rules=mapping_rules,
            unmapped_fields=[],
            version_hash=self._hash(canonical),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction Domain
    # ------------------------------------------------------------------
    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Run the AD + ARG discovery (read-only).

        ``canonical_query`` is accepted but currently only one canonical
        shape is supported: ``{"select": ["mssql_instances"]}``. The
        adapter ignores other queries to remain explicit about scope.
        """
        if canonical_query.get("select") != ["mssql_instances"]:
            return QueryProvenance(
                canonical_query=canonical_query,
                vendor_query="UNSUPPORTED",
                execution_plan_hash=self._hash("unsupported"),
                row_count=0,
                timestamp=self._now(),
            )

        spn_records = self._fetch_spn_inventory()
        arg_records = self._fetch_arg_resources()

        claims: List[ClaimObject] = []
        for spn_record in spn_records:
            normalized = normalize_spn_record(spn_record)
            if normalized is None:
                continue
            claim = ClaimObject(
                claim_id=f"ad-spn::{normalized.identifier}",
                entity="mssql-instance",
                fields=normalized.to_dict(),
                source="ad-spn",
                provenance_hash=self._hash(normalized.to_dict()),
            )
            claims.append(claim)

        for arg_record in arg_records:
            normalized = normalize_arg_resource(arg_record)
            if normalized is None:
                continue
            claim = ClaimObject(
                claim_id=f"{normalized.source}::{normalized.identifier}",
                entity="mssql-instance",
                fields=normalized.to_dict(),
                source=normalized.source,
                provenance_hash=self._hash(normalized.to_dict()),
            )
            claims.append(claim)

        self._claims_cache = ClaimSet(
            claims=claims,
            source_reference="ad-spn+azure-resource-graph",
        )

        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query="ad-ldap(MSSQLSvc/*) + " + ARG_QUERY_MSSQL_RESOURCES.strip(),
            execution_plan_hash=self._hash({"spn_count": len(spn_records), "arg_count": len(arg_records)}),
            row_count=len(claims),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization & Claim Construction Domain
    # ------------------------------------------------------------------
    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Convert raw records to ClaimSet. Used when caller provides own data.

        For the standard happy path, ``execute_query`` already populates
        ``_claims_cache``. This method is the explicit normalization entry
        point for callers that want to pass raw records directly (e.g.
        unit tests or staged-discovery flows).
        """
        claims: List[ClaimObject] = []
        for row in raw_rows:
            if "servicePrincipalName" in row or row.get("source") == "ad-spn":
                normalized = normalize_spn_record(row)
            else:
                normalized = normalize_arg_resource(row)
            if normalized is None:
                continue
            claim = ClaimObject(
                claim_id=f"{normalized.source}::{normalized.identifier}",
                entity="mssql-instance",
                fields=normalized.to_dict(),
                source=normalized.source,
                provenance_hash=self._hash(normalized.to_dict()),
            )
            claims.append(claim)
        return ClaimSet(
            claims=claims,
            source_reference="caller-supplied",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity Domain
    # ------------------------------------------------------------------
    def detect_drift(self) -> DriftReport:
        """Identify policy violations in the discovered inventory.

        Drift conditions surfaced by this adapter (Tier-A1 scope):

        * ``DRIFT-IDENTITY``: instance with no resolvable OrgPath (cascades
          to ``ORG-BRANCH-UNPOSITIONED``).
        * ``DRIFT-PROVENANCE``: ARM tag ``OrgPath`` present but not matching
          UIAO_151 codebook regex.

        The substrate's canonical ``DriftReport`` shape carries a single
        ``drift_type`` + ``details``; per-claim findings are aggregated
        into the ``details`` payload as a list. Aggregation matches the
        existing ``EntraAdapter`` and ``IntuneAdapter`` patterns. The
        most-severe class found governs the report-level ``severity``;
        if no findings, ``drift_type`` is ``no-drift`` and ``severity`` is
        ``P4`` (informational).
        """
        if self._claims_cache is None:
            self.execute_query({"select": ["mssql_instances"]})

        per_claim_findings: List[Dict[str, Any]] = []
        assert self._claims_cache is not None
        for claim in self._claims_cache.claims:
            fields = claim.fields
            orgpath = fields.get("orgpath", ORGPATH_UNPOSITIONED)
            if orgpath == ORGPATH_UNPOSITIONED:
                per_claim_findings.append(
                    {
                        "claim_id": claim.claim_id,
                        "drift_class": "DRIFT-IDENTITY",
                        "severity": "P2",
                        "reason": "unpositioned",
                    }
                )
                continue
            if not _ORGPATH_REGEX.match(orgpath):
                per_claim_findings.append(
                    {
                        "claim_id": claim.claim_id,
                        "drift_class": "DRIFT-PROVENANCE",
                        "severity": "P2",
                        "orgpath": orgpath,
                        "reason": "regex-violation",
                    }
                )

        if not per_claim_findings:
            drift_type = "no-drift"
            severity = "P4"
        else:
            classes_present = {f["drift_class"] for f in per_claim_findings}
            # DRIFT-IDENTITY ranked above DRIFT-PROVENANCE for severity rollup.
            drift_type = "DRIFT-IDENTITY" if "DRIFT-IDENTITY" in classes_present else "DRIFT-PROVENANCE"
            severity = "P2"

        now = self._now()
        return DriftReport(
            drift_type=drift_type,
            severity=severity,
            first_observed=now,
            last_observed=now,
            details={
                "adapter_id": self.ADAPTER_ID,
                "evaluated_claims": len(self._claims_cache.claims),
                "findings_count": len(per_claim_findings),
                "findings": per_claim_findings,
            },
            remediation="Remediate per UIAO_153 / ADR-063 cascade rules for unattributed instances; correct OrgPath values per UIAO_151 codebook for regex violations.",
        )

    # ------------------------------------------------------------------
    # Private fetch helpers
    # ------------------------------------------------------------------
    def _fetch_spn_inventory(self) -> List[Dict[str, Any]]:
        """Return SPN inventory records; reuses dependency-injected data if present."""
        if self._spn_inventory_input is not None:
            return self._spn_inventory_input
        try:
            from uiao.adapters.modernization.active_directory.survey import (
                extract_spn_inventory,
            )

            return list(extract_spn_inventory(phase="pre_migration"))
        except Exception:
            logger.warning(
                "AD survey unavailable; SPN inventory will be empty. "
                "Provide spn_inventory_input config key to inject pre-fetched data."
            )
            return []

    def _fetch_arg_resources(self) -> List[Dict[str, Any]]:
        """Return ARG records; reuses dependency-injected data if present."""
        if self._arg_query_results is not None:
            return self._arg_query_results
        if self._arg_client_factory is None:
            logger.warning(
                "No ARG client factory configured; Azure-side inventory will be empty. "
                "Provide arg_client_factory config key for runtime ARG queries."
            )
            return []
        try:
            client = self._arg_client_factory()
            return list(client.resources(query=ARG_QUERY_MSSQL_RESOURCES))
        except Exception as exc:
            logger.warning("ARG query failed: %s", exc)
            return []
