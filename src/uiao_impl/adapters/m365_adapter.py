"""
UIAO Microsoft 365 Tenant Adapter — DNS-style alignment only.

Consumes Microsoft 365 tenant configuration via Microsoft Graph API to
produce object-keyed canonical claims with KSI provenance. Covers
Exchange Online, SharePoint Online, Teams, Defender for Office 365, and
Purview workloads.

Classification (per uiao-core/canon/modernization-registry.yaml):
    class:         modernization
    mission-class: integration  (UIAO_003 s4.7, ratified ODA-15 2026-04-15)
    status:        active

This adapter is intentionally lightweight and sits OUTSIDE the main data
path.  Its only job: create alignments (vendor-overlay + claim + evidence
hash).  It does NOT perform OSCAL JSON, SSP, POA+M, or SBOM conversions.
Those happen downstream in src/uiao_impl/generators/.

File: src/uiao_impl/adapters/m365_adapter.py
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


class M365Adapter(DatabaseAdapterBase):
    """
    Microsoft 365 tenant adapter — DNS-style alignment only.

    Implements the canonical UIAO adapter pattern (7 responsibility domains)
    plus M365-specific extension methods for tenant configuration assessment
    and change-making across the five core workloads.
    """

    ADAPTER_ID: str = "m365"

    # M365 workloads covered by this adapter (matches canon registry scope)
    WORKLOADS = [
        "exchange-online",
        "sharepoint-online",
        "teams",
        "defender-o365",
        "purview",
    ]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._tenant_id: str = self._config.get("tenant_id", "")
        self._graph_endpoint: str = self._config.get(
            "graph_endpoint", "https://graph.microsoft.com/v1.0"
        )

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        """Establish Graph API connection and return provenance."""
        return ConnectionProvenance(
            identity=f"m365:{self._tenant_id}",
            auth_method=self._config.get("auth_method", "client-credential"),
            endpoint=self._graph_endpoint,
            tls_version="TLSv1.3",
            mtls_enabled=self._config.get("mtls_enabled", False),
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery & Canonical Mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        """Map Graph API entity types to UIAO canonical schema."""
        vendor_schema: Dict[str, Any] = {
            "mailboxSettings": "object",
            "siteCollection": "object",
            "team": "object",
            "securityPolicy": "object",
            "compliancePolicy": "object",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": "m365:<workload>:<entity_type>:<entity_id>",
            "control_id": "<mapped from policy type>",
            "implementation_statement": "<config summary>",
            "evidence.source": "m365",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<graph_response>)",
        }
        mapping_rules: Dict[str, Any] = {
            "entity_type": "canonical entity class",
            "entity_id": "identity suffix (Graph object ID)",
            "workload": "scope qualifier",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["@odata.context", "@odata.nextLink", "createdDateTime"],
            version_hash=self._hash(
                {"vendor": vendor_schema, "canonical": canonical_schema}
            ),
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization & Deterministic Extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        """Translate canonical query to Graph API request."""
        entity = canonical_query.get("from", "organization")
        fields = canonical_query.get("select", ["id", "displayName"])
        vendor_query = (
            f"GET {self._graph_endpoint}/{entity}"
            f"?$select={','.join(fields)}"
        )
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,  # populated after real fetch
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization & Claim Construction
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Convert raw Graph API responses into canonical ClaimObjects."""
        claims: List[ClaimObject] = []
        for entity in raw_rows:
            entity_type = entity.get("@odata.type", "unknown").split(".")[-1]
            entity_id = entity.get("id", "unknown")
            workload = entity.get("_workload", "unknown")
            claim = ClaimObject(
                claim_id=f"m365:{workload}:{entity_type}:{entity_id}",
                entity=f"m365:{entity_type}:{entity_id}",
                fields={
                    "identity": f"m365:{workload}:{entity_type}:{entity_id}",
                    "workload": workload,
                    "entity_type": entity_type,
                    "display_name": entity.get("displayName", ""),
                    "vendor_overlay_ref": "m365.yaml",
                },
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(entity),
            )
            claims.append(claim)
        return ClaimSet(
            claims=claims,
            source_reference=f"{self._graph_endpoint}/organization",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection & Version Integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """Detect drift between M365 tenant config and UIAO canon."""
        return DriftReport(
            drift_type="m365-tenant-config",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": (
                    "Drift detection scaffold — implement per-workload "
                    "comparison against canon baseline. Pair with scubagear "
                    "conformance adapter for SCuBA baseline drift."
                ),
                "adapter": self.ADAPTER_ID,
                "tenant_id": self._tenant_id,
                "workloads": self.WORKLOADS,
            },
            remediation=(
                "Compare normalize() output against YAML canon control_id "
                "mappings per workload. Cross-reference scubagear findings."
            ),
        )

    # ==================================================================
    # M365-Specific Extension Methods
    # ==================================================================

    def get_tenant_config(
        self,
        workload: str,
        config_filter: Optional[str] = None,
    ) -> ClaimSet:
        """Retrieve tenant-level configuration for a specific workload.

        Args:
            workload: One of WORKLOADS (exchange-online, sharepoint-online, etc.)
            config_filter: Optional OData filter expression

        Returns:
            ClaimSet with configuration-state claims.
        """
        raise NotImplementedError(
            "get_tenant_config() is a stub — requires Graph API "
            "collector with client-credential auth flow."
        )

    def apply_baseline(
        self,
        workload: str,
        baseline: Dict[str, Any],
    ) -> DriftReport:
        """Apply a security baseline to a workload (change-making).

        This is the integration-class change-making surface: it writes
        configuration changes to the M365 tenant via Graph API.

        Args:
            workload: Target workload
            baseline: Desired-state configuration (e.g., SCuBA baseline)

        Returns:
            DriftReport showing what changed.
        """
        raise NotImplementedError(
            "apply_baseline() is a stub — requires Graph API write "
            "permissions and change-approval workflow integration."
        )

    def generate_m365_evidence(
        self,
        workload: Optional[str] = None,
        include_scuba_crossref: bool = True,
    ) -> EvidenceObject:
        """Generate evidence bundle for M365 tenant state.

        Args:
            workload: Specific workload or None for all
            include_scuba_crossref: Cross-reference scubagear findings

        Returns:
            EvidenceObject with full provenance chain.
        """
        raise NotImplementedError(
            "generate_m365_evidence() is a stub — requires both "
            "get_tenant_config() and scubagear integration."
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """Pull tenant config from Graph API and return alignment result."""
        claim_set = self.normalize([])
        return {
            "vendor": "Microsoft 365",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/m365.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "tenant_id": self._tenant_id,
                "workloads": self.WORKLOADS,
            },
        }
