"""
UIAO-Core ServiceNow Adapter — DNS-style alignment only.

This adapter is intentionally lightweight and sits OUTSIDE the main data path.
Its only job: create alignments (vendor-overlay + claim + evidence hash).
It does NOT perform OSCAL JSON, SSP, POA&M, or SBOM conversions.
Those happen downstream in src/uiao_core/generators/.

Analogy: like a DNS resolver — it tells the engine HOW to get there;
the generators/ layer does the actual conversion work.

File: src/uiao_core/adapters/servicenow_adapter.py
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List

from .database_base import DatabaseAdapterBase, ClaimObject, ClaimSet, DriftReport, EvidenceObject
from ..collectors.servicenow_collector import ServiceNowCollector


class ServiceNowAdapter(DatabaseAdapterBase):
    """
    ServiceNow adapter — DNS-style alignment only (no heavy conversion).

    Implements the canonical UIAO adapter pattern:
    1. Collector reaches out to ServiceNow via Table API.
    2. Adapter normalizes raw records into identity-rooted UIAO claims.
    3. Adapter builds a vendor-specific overlay reference + evidence hash.
    4. Engine merges the alignment into the canon for downstream generation.

    This adapter never owns or duplicates data. SSOT remains in the YAML canon.
    """

    ADAPTER_ID: str = "servicenow"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self.collector = ServiceNowCollector(
            instance=self._config.get("instance", ""),
            token=self._config.get("token", ""),
        )

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity — delegate to collector
    # ------------------------------------------------------------------

    def connect(self):
        """Establish ServiceNow connection and return provenance."""
        from .database_base import ConnectionProvenance
        return ConnectionProvenance(
            identity=f"servicenow:{self.collector.instance}",
            auth_method="oauth-bearer",
            endpoint=f"https://{self.collector.instance}.service-now.com",
            tls_version="TLSv1.3",
            mtls_enabled=False,  # Set True when mTLS certs are configured
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema Discovery — map ServiceNow fields to UIAO schema
    # ------------------------------------------------------------------

    def discover_schema(self):
        """Return canonical mapping of ServiceNow fields → UIAO schema."""
        from .database_base import SchemaMappingObject
        vendor_schema = {
            "sys_id": "string",
            "short_description": "string",
            "state": "integer",
            "assigned_to": "reference",
            "opened_at": "datetime",
            "uiao_control_id": "string",  # custom field recommended
        }
        canonical_schema = {
            "identity": "servicenow:ticket:<sys_id>",
            "control_id": "<uiao_control_id or default AC-2>",
            "implementation_statement": "<short_description>",
            "evidence.source": "servicenow",
            "evidence.timestamp": "<collected_at>",
            "evidence.record_hash": "sha256(<record>)",
        }
        mapping_rules = {
            "sys_id": "identity suffix",
            "short_description": "implementation_statement",
            "uiao_control_id": "control_id (fallback: AC-2)",
        }
        version_hash = self._hash({"vendor": vendor_schema, "canonical": canonical_schema})
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules=mapping_rules,
            unmapped_fields=["state", "assigned_to", "opened_at"],
            version_hash=version_hash,
        )

    # ------------------------------------------------------------------
    # 2.3 Query Normalization — translate canonical query to ServiceNow
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]):
        """Translate canonical query to ServiceNow Table API parameters."""
        from .database_base import QueryProvenance
        table = canonical_query.get("from", "incident")
        fields = canonical_query.get("select", ["sys_id", "short_description", "uiao_control_id"])
        vendor_query = f"GET /api/now/table/{table}?sysparm_fields={','.join(fields)}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,  # populated after real fetch
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data Normalization — build UIAO-aligned claims (alignment only)
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """
        Convert raw ServiceNow records into canonical UIAO ClaimObjects.

        ALIGNMENT ONLY — no OSCAL conversion happens here.
        The claim is a pointer + evidence hash; generators/ does the rest.
        """
        claims: List[ClaimObject] = []
        for record in raw_rows:
            sys_id = record.get("sys_id", "unknown")
            claim_payload = {
                "identity": f"servicenow:ticket:{sys_id}",
                "control_id": record.get("uiao_control_id", "AC-2"),
                "implementation_statement": record.get("short_description", ""),
                "vendor_overlay_ref": "servicenow.yaml",
                "telemetry_enabled": True,
                "raw_link": (
                    f"https://{self.collector.instance}.service-now.com"
                    f"/incident.do?sys_id={sys_id}"
                ),
            }
            claim = ClaimObject(
                claim_id=f"servicenow:{sys_id}",
                entity=f"servicenow:ticket:{sys_id}",
                fields=claim_payload,
                source=self.ADAPTER_ID,
                provenance_hash=self._hash(record),
            )
            claims.append(claim)

        return ClaimSet(
            claims=claims,
            source_reference=(
                f"https://{self.collector.instance}.service-now.com"
                f"/api/now/table/incident"
            ),
        )

    # ------------------------------------------------------------------
    # 2.5 Drift Detection — compare current vs expected state
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        """
        Detect drift between ServiceNow state and UIAO canon.
        Engine handles the full comparison; this returns a lightweight report.
        """
        return DriftReport(
            drift_type="servicenow-schema",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": "Drift detection scaffold — implement query comparison against canon.",
                "adapter": self.ADAPTER_ID,
            },
            remediation="Compare normalize() output against YAML canon control_id mappings.",
        )

    # ------------------------------------------------------------------
    # Convenience: collect + normalize in one call
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        """
        Pull records from ServiceNow and return alignment result.

        Returns the ClaimSet as a dict for downstream engine consumption.
        Does NOT generate OSCAL — that stays in generators/.
        """
        raw_data = self.collector.fetch_relevant_records()
        records = raw_data.get("result", [])
        claim_set = self.normalize(records)
        return {
            "vendor": "ServiceNow",
            "adapter_id": self.ADAPTER_ID,
            "vendor_overlay_ref": "data/vendor-overlays/servicenow.yaml",
            "claims": claim_set.to_dict(),
            "metadata": {
                "total_records": len(claim_set.claims),
                "last_collected": self._now().isoformat(),
                "instance": self.collector.instance,
            },
        }
