"""
UIAO SIEM / Audit Event Adapter — conformance class.

Ingests audit events and security alerts from SIEM platforms
(Sentinel, Splunk, etc.). Highest-value telemetry adapter for
the Evidence Fabric.

Classification: conformance / telemetry / reserved
Controls: AU-2, AU-3, AU-6, SI-4

File: src/uiao/impl/adapters/siem_adapter.py
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


class SiemAdapter(DatabaseAdapterBase):
    """SIEM adapter — audit event and security alert telemetry."""

    ADAPTER_ID: str = "siem"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._platform: str = self._config.get("platform", "generic")
        self._endpoint: str = self._config.get("endpoint", "")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"siem:{self._platform}",
            auth_method=self._config.get("auth_method", "api-key"),
            endpoint=self._endpoint or f"https://{self._platform}.local/api",
            tls_version="TLSv1.3", mtls_enabled=False, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"event_id": "string", "timestamp": "datetime", "source": "string",
                         "severity": "string", "category": "string", "message": "string", "raw_log": "string"}
        canonical_schema = {"identity": f"siem:{self._platform}:<event_id>",
                            "control_id": "AU-2", "evidence.source": "siem"}
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"event_id": "identity suffix", "category": "event classification",
                           "severity": "maps to evidence severity model"},
            unmapped_fields=["raw_log", "host", "process_id"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        category = canonical_query.get("from", "security-alerts")
        vendor_query = f"GET /api/v1/events?category={category}&limit=1000"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0, timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for event in raw_rows:
            eid = event.get("event_id", "unknown")
            claims.append(ClaimObject(
                claim_id=f"siem:{self._platform}:{eid}",
                entity=f"siem:event:{eid}",
                fields={"identity": f"siem:{self._platform}:{eid}",
                        "category": event.get("category", ""), "severity": event.get("severity", ""),
                        "message": event.get("message", ""), "event_source": event.get("source", ""),
                        "vendor_overlay_ref": f"{self._platform}.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(event),
            ))
        return ClaimSet(claims=claims, source_reference=self._endpoint or self._platform)

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="siem-audit-coverage", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift scaffold — verify audit event coverage against AU-2 requirements.",
                     "adapter": self.ADAPTER_ID, "platform": self._platform},
            remediation="Compare event categories against required AU-2 audit event types.",
        )

    def ingest_events(self, events_data: Optional[Dict[str, Any]] = None) -> ClaimSet:
        """Ingest security events from SIEM."""
        events = (events_data or {}).get("events", [])
        return self.normalize(events)

    def generate_audit_evidence(self, events_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from SIEM events."""
        conn = self.connect()
        events = (events_data or {}).get("events", [])
        claim_set = self.normalize(events)
        severity_counts = {}
        for e in events:
            s = e.get("severity", "unknown")
            severity_counts[s] = severity_counts.get(s, 0) + 1
        return EvidenceObject(
            ksi_id=f"KSI-AU-02-{self._platform}",
            source=self.ADAPTER_ID, timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "total_events": len(events),
                      "by_severity": severity_counts},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "platform": self._platform,
                        "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": self._platform.title(), "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"platform": self._platform, "last_collected": self._now().isoformat()}}
