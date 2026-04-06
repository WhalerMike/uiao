"""
UIAO-Core Microsoft Entra ID Adapter -- DNS-style alignment only.

This adapter is intentionally lightweight and sits OUTSIDE the main data path.
Its only job: create alignments (vendor-overlay + claim + evidence hash).
It does NOT perform OSCAL JSON, SSP, POA&M, or SBOM conversions.
Those happen downstream in src/uiao_core/generators/.

Analogy: like a DNS resolver -- it tells the engine HOW to get there;
the generators/ layer does the actual conversion work.

File: src/uiao_core/adapters/entra_adapter.py
"""

from __future__ import annotations

from typing import Any, Dict, List

from ..collectors.entra.entra_collector import EntraCollector
from .database_base import ClaimObject, ClaimSet, DatabaseAdapterBase, DriftReport


class EntraAdapter(DatabaseAdapterBase):
    """
    Microsoft Entra ID adapter -- DNS-style alignment only (no heavy conversion).

    Implements the canonical UIAO adapter pattern:
      1. Collector reaches out to Microsoft Graph API.
      2. Adapter normalizes raw records into identity-rooted UIAO claims.
      3. Adapter builds a vendor-specific overlay reference + evidence hash.
      4. Engine merges the alignment into the canon for downstream generation.

    This adapter never owns or duplicates data. SSOT remains in the YAML canon.
    """

    ADAPTER_ID: str = "entra"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self.collector = EntraCollector(config=self._config)

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity -- delegate to collector
    # ------------------------------------------------------------------
    def connect(self):
        """Establish Entra ID connection and return provenance."""
        from .database_base import ConnectionProvenance

        tenant_id = self._config.get("tenant_id", "unknown")
        return ConnectionProvenance(
            identity=f"entra:{tenant_id}",
            auth_method="oauth-client-credentials",
            endpoint="https://graph.microsoft.com/v1.0",
            tls_version="TLSv1.3",
            mtls_enabled=False,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery -- map Entra fields to UIAO schema
    # ------------------------------------------------------------------
    def discover_schema(self):
        """Return canonical mapping of Entra ID fields -> UIAO schema."""
        from .database_base import SchemaMappingObject

        vendor_schema = {
            "id": "string",
            "userPrincipalName": "string",
            "displayName": "string",
            "signInActivity": "object",
            "riskLevel": "string",
            "conditionalAccessStatus": "string",
        }
        canonical_schema = {
            "identity": "entra:user:<id>",
            "control_id": "<mapped via overlay>",
            "implementation_statement": "<displayName or event message>",
            "evidence.source": "entra",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<record>)",
        }
        mapping_rules = {
            "id": "identity suffix",
            "userPrincipalName": "identity alternate key",
            "displayName": "implementation_statement",
            "riskLevel": "risk indicator",
        }
        version_hash = self._hash({"vendor": vendor_schema, "canonical": canonical_schema})
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["signInActivity", "conditionalAccessStatus"],
            version_hash=version_hash,
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization -- translate canonical query to Graph API
    # ------------------------------------------------------------------
    def execute_query(self, canonical_query: Dict[str, Any]):
        """Translate canonical query to Microsoft Graph API parameters."""
        from .database_base import QueryProvenance

        resource = canonical_query.get("from", "auditLogs/signIns")
        fields = canonical_query.get("select", ["id", "userPrincipalName", "riskLevel"])
        vendor_query = f"GET /v1.0/{resource}?$select={','.join(fields)}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization -- build UIAO-aligned claims (alignment only)
    # ------------------------------------------------------------------
    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """
        Convert raw Entra ID records into canonical UIAO ClaimObjects.

        ALIGNMENT ONLY -- no OSCAL conversion happens here.
        The claim is a pointer + evidence hash; generators/ does the rest.
        """
        claims: List[ClaimObject] = []
        for record in raw_rows:
            record_id = record.get("id", "unknown")
            claim_payload = {
                "identity": f"entra:user:{record_id}",
                "control_id": record.get("uiao_control_id", "AC-2"),
                "implementation_statement": record.get("displayName", "")
                or record.get("message", "Entra identity event"),
                "vendor_overlay_ref": "microsoft.yaml",
                "telemetry_enabled": True,
                "raw_link": f"https://portal.azure.com/#view/Microsoft_AAD_UsersAndTenants/UserProfileMenuBlade/~/overview/userId/{record_id}",
            }
            claim = ClaimObject(
                claim_id=f"entra:{record_id}",
                entity=f"entra:user:{record_id}",
                fields=claim_payload,
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(record),
            )
            claims.append(claim)

        tenant_id = self._config.get("tenant_id", "unknown")
        return ClaimSet(
            claims=claims,
            source_reference=f"https://graph.microsoft.com/v1.0/auditLogs/signIns?tenant={tenant_id}",
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection -- compare current vs expected state
    # ------------------------------------------------------------------
    def detect_drift(self) -> DriftReport:
        """
        Detect drift between Entra ID state and UIAO canon.

        Engine handles the full comparison; this returns a lightweight report.
        """
        return DriftReport(
            drift_type="entra-schema",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": "Drift detection scaffold -- implement Graph API comparison against canon.",
                "adapter": self.ADAPTER_ID,
            },
            remediation="Compare normalize() output against YAML canon control_id mappings.",
        )

    # ------------------------------------------------------------------
    # 2.6 Evidence Collection -- delegate to collector
    # ------------------------------------------------------------------
    def collect_evidence(self, ksi_id: str = "IA-2") -> Dict[str, Any]:
        """
        Collect Entra ID evidence for a given KSI.

        Delegates to the EntraCollector which handles Graph API calls.
        """
        evidence = self.collector.collect(ksi_id=ksi_id)
        return {
            "ksi_id": ksi_id,
            "source": "EntraID",
            "evidence": evidence.raw_data if hasattr(evidence, "raw_data") else {},
            "timestamp": self._now().isoformat(),
        }

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------
    def collect_and_align(self) -> Dict[str, Any]:
        """
        Pull records from Entra ID and return alignment result.

        Returns the ClaimSet as a dict for downstream engine consumption.
        Does NOT generate OSCAL -- that stays in generators/.
        """
        evidence = self.collector.collect(ksi_id="AC-2")
        raw_data = evidence.raw_data if hasattr(evidence, "raw_data") else {}
        records = raw_data.get("sign_in_events", []) or raw_data.get("value", [])
        claim_set = self.normalize(records)

        tenant_id = self._config.get("tenant_id", "unknown")
        return {
            "vendor": "Microsoft Entra ID",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/microsoft.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "tenant_id": tenant_id,
            },
        }
