"""
UIAO Mainframe (z/OS Connect / MQ) Adapter — integration class.

Legacy mainframe integration — maps COBOL records and MQ messages to
canonical claims. Highest-priority FIMF adapter for federal legacy migration.

Classification: modernization / integration / reserved
Controls: CM-8, AC-2, AU-2

File: src/uiao/impl/adapters/mainframe_adapter.py
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


class MainframeAdapter(DatabaseAdapterBase):
    """Mainframe adapter — z/OS Connect / MQ integration."""

    ADAPTER_ID: str = "mainframe"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._host: str = self._config.get("host", "")
        self._transport: str = self._config.get("transport", "zos-connect")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"mainframe:{self._host}",
            auth_method=self._config.get("auth_method", "racf"),
            endpoint=self._host or "mainframe.agency.gov",
            tls_version=self._config.get("tls_version", "TLSv1.2"),
            mtls_enabled=True, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"record_type": "string", "transaction_id": "string",
                         "program_name": "string", "return_code": "integer", "timestamp": "datetime"}
        canonical_schema = {"identity": f"mainframe:{self._transport}:<transaction_id>",
                            "control_id": "CM-8", "evidence.source": "mainframe"}
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"transaction_id": "identity suffix", "program_name": "entity type"},
            unmapped_fields=["abend_code", "cpu_time", "io_count"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        program = canonical_query.get("from", "CICS")
        vendor_query = f"GET /zosConnect/apis/{program}/transactions"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0, timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for record in raw_rows:
            tid = record.get("transaction_id", "unknown")
            claims.append(ClaimObject(
                claim_id=f"mainframe:{self._transport}:{tid}",
                entity=f"mainframe:{record.get('program_name', 'unknown')}:{tid}",
                fields={"identity": f"mainframe:{self._transport}:{tid}",
                        "program_name": record.get("program_name", ""),
                        "return_code": record.get("return_code", 0),
                        "vendor_overlay_ref": "mainframe.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(record),
            ))
        return ClaimSet(claims=claims, source_reference=self._host or "mainframe")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="mainframe-inventory", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift scaffold — compare mainframe inventory against canon.",
                     "adapter": self.ADAPTER_ID, "host": self._host, "transport": self._transport},
            remediation="Compare transaction inventory against authorized program list.",
        )

    def ingest_transactions(self, data: Optional[Dict[str, Any]] = None) -> ClaimSet:
        """Ingest CICS/MQ transaction records."""
        records = (data or {}).get("transactions", [])
        return self.normalize(records)

    def generate_mainframe_evidence(self, data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from mainframe data."""
        conn = self.connect()
        records = (data or {}).get("transactions", [])
        claim_set = self.normalize(records)
        return EvidenceObject(
            ksi_id="KSI-CM-08-mainframe",
            source=self.ADAPTER_ID, timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "transactions": len(records)},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "host": self._host,
                        "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": "IBM z/OS", "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"host": self._host, "transport": self._transport, "last_collected": self._now().isoformat()}}
