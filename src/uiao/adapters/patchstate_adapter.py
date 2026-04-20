"""
UIAO Patch State Adapter — conformance class, read-only.

Observes patch/update state across managed endpoints and produces
normalized, timestamped records for downstream policy evaluation.
Telemetry-class adapter.

Classification (per uiao/canon/adapter-registry.yaml):
    class:            conformance
    mission-class:    telemetry  (UIAO_003 s4.3)
    status:           reserved
    automation-domain: patch-management (NIST SP 800-137 App. D)

File: src/uiao/impl/adapters/patchstate_adapter.py
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


class PatchStateAdapter(DatabaseAdapterBase):
    """Patch State adapter — conformance class (read-only, telemetry)."""

    ADAPTER_ID: str = "patch-state"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._source: str = self._config.get("source", "generic")
        self._endpoint: str = self._config.get("endpoint", "")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"patch-state:{self._source}",
            auth_method=self._config.get("auth_method", "api-key"),
            endpoint=self._endpoint or f"https://{self._source}.local/api",
            tls_version=self._config.get("tls_version", "TLSv1.3"),
            mtls_enabled=False, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema: Dict[str, Any] = {
            "device_id": "string", "os": "string", "installed_patches": "list",
            "missing_patches": "list", "last_scan": "datetime",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": f"patch-state:{self._source}:<device_id>",
            "control_id": "SI-2", "evidence.source": "patch-state",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"device_id": "identity suffix", "missing_patches": "drift indicator"},
            unmapped_fields=["os_build", "reboot_pending"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        scope = canonical_query.get("from", "all-endpoints")
        vendor_query = f"GET /api/v1/patch-status?scope={scope}"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0,
            timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims: List[ClaimObject] = []
        for device in raw_rows:
            device_id = device.get("device_id", "unknown")
            missing = device.get("missing_patches", [])
            claims.append(ClaimObject(
                claim_id=f"patch-state:{self._source}:{device_id}",
                entity=f"patch-state:{device_id}",
                fields={"identity": f"patch-state:{self._source}:{device_id}",
                        "os": device.get("os", ""), "missing_count": len(missing),
                        "missing_patches": missing, "vendor_overlay_ref": f"{self._source}.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(device),
            ))
        return ClaimSet(claims=claims, source_reference=self._endpoint or self._source)

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="patch-state-posture", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift detection scaffold — compare current patch state against baseline.",
                     "adapter": self.ADAPTER_ID, "source": self._source},
            remediation="Compare missing_patches against accepted-risk register.",
        )

    def get_patch_status(self, status_data: Optional[Dict[str, Any]] = None) -> ClaimSet:
        """Parse patch status data and return claims.

        Args:
            status_data: Parsed JSON with a "devices" list.
        """
        devices = (status_data or {}).get("devices", [])
        return self.normalize(devices)

    def generate_patch_evidence(self, status_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from patch status data."""
        conn = self.connect()
        devices = (status_data or {}).get("devices", [])
        claim_set = self.normalize(devices)
        total_missing = sum(len(d.get("missing_patches", [])) for d in devices)

        return EvidenceObject(
            ksi_id=f"KSI-SI-02-{self._source}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "devices": len(devices), "total_missing_patches": total_missing},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "source": self._source, "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": self._source.title(), "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"source": self._source, "last_collected": self._now().isoformat()}}
