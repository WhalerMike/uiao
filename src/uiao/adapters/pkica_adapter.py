"""
UIAO PKI / Certificate Authority Adapter — conformance class.

Observes certificate state via OCSP, CRL, and PKI APIs. Critical for
the certificate-anchored provenance model.

Classification: conformance / telemetry / reserved
Controls: IA-5, SC-12, SC-13

File: src/uiao/impl/adapters/pkica_adapter.py
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


class PkiCaAdapter(DatabaseAdapterBase):
    """PKI / Certificate Authority adapter — certificate state telemetry."""

    ADAPTER_ID: str = "pki-ca"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._ca_endpoint: str = self._config.get("ca_endpoint", "")
        self._cert_store: str = self._config.get("cert_store", "local")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"pki-ca:{self._cert_store}",
            auth_method=self._config.get("auth_method", "mutual-tls"),
            endpoint=self._ca_endpoint or "https://pki.agency.gov/ocsp",
            tls_version="TLSv1.3", mtls_enabled=True, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"serial_number": "string", "subject": "string", "issuer": "string",
                         "not_before": "datetime", "not_after": "datetime", "status": "string"}
        canonical_schema = {"identity": f"pki-ca:{self._cert_store}:<serial_number>",
                            "control_id": "SC-12", "evidence.source": "pki-ca"}
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"serial_number": "identity suffix", "status": "validity indicator"},
            unmapped_fields=["signature_algorithm", "key_usage", "san_entries"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        scope = canonical_query.get("from", "all-certificates")
        vendor_query = f"GET /api/v1/certificates?store={self._cert_store}&scope={scope}"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0, timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for cert in raw_rows:
            serial = cert.get("serial_number", "unknown")
            claims.append(ClaimObject(
                claim_id=f"pki-ca:{self._cert_store}:{serial}",
                entity=f"pki-ca:cert:{serial}",
                fields={"identity": f"pki-ca:{self._cert_store}:{serial}",
                        "subject": cert.get("subject", ""), "issuer": cert.get("issuer", ""),
                        "not_after": cert.get("not_after", ""), "status": cert.get("status", ""),
                        "vendor_overlay_ref": "pki.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(cert),
            ))
        return ClaimSet(claims=claims, source_reference=self._ca_endpoint or "pki-local")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="pki-certificate-state", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift scaffold — check certificate expiry and revocation.",
                     "adapter": self.ADAPTER_ID, "cert_store": self._cert_store},
            remediation="Check OCSP/CRL for revocation; flag certificates expiring within 30 days.",
        )

    def check_certificate_status(self, certs_data: Optional[Dict[str, Any]] = None) -> ClaimSet:
        """Parse certificate inventory and return claims."""
        certs = (certs_data or {}).get("certificates", [])
        return self.normalize(certs)

    def generate_pki_evidence(self, certs_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from certificate inventory."""
        conn = self.connect()
        certs = (certs_data or {}).get("certificates", [])
        claim_set = self.normalize(certs)
        expiring = sum(1 for c in certs if c.get("status") == "expiring")
        return EvidenceObject(
            ksi_id=f"KSI-SC-12-{self._cert_store}",
            source=self.ADAPTER_ID, timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "total_certs": len(certs), "expiring": expiring},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "cert_store": self._cert_store,
                        "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": "PKI/CA", "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"cert_store": self._cert_store, "last_collected": self._now().isoformat()}}
