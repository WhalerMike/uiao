"""
UIAO Microsoft Intune Endpoint Compliance Adapter — conformance class.

Observes device compliance, endpoint protection, and update state via
Microsoft Graph API (Intune/Defender for Endpoint). Read-only telemetry.

Classification: conformance / telemetry / reserved
Controls: CM-8, SI-2, CA-7, SC-7

File: src/uiao_impl/adapters/intune_adapter.py
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from .database_base import (
    ClaimObject, ClaimSet, ConnectionProvenance, DatabaseAdapterBase,
    DriftReport, EvidenceObject, QueryProvenance, SchemaMappingObject,
)


class IntuneAdapter(DatabaseAdapterBase):
    """Intune adapter — endpoint compliance telemetry (conformance, read-only)."""

    ADAPTER_ID: str = "intune"

    SCOPE = ["device-compliance", "endpoint-protection", "configuration-profiles", "update-compliance"]

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._tenant_id: str = self._config.get("tenant_id", "")
        self._graph_endpoint: str = self._config.get("graph_endpoint", "https://graph.microsoft.com/beta")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"intune:{self._tenant_id}",
            auth_method=self._config.get("auth_method", "client-credential"),
            endpoint=f"{self._graph_endpoint}/deviceManagement",
            tls_version="TLSv1.3", mtls_enabled=False, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"deviceId": "string", "deviceName": "string", "complianceState": "string",
                         "osVersion": "string", "lastSyncDateTime": "datetime", "managementAgent": "string"}
        canonical_schema = {"identity": "intune:<tenant>:<device_id>",
                            "control_id": "CM-8", "evidence.source": "intune"}
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"deviceId": "identity suffix", "complianceState": "compliance status"},
            unmapped_fields=["enrolledDateTime", "model", "manufacturer"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        entity = canonical_query.get("from", "managedDevices")
        vendor_query = f"GET {self._graph_endpoint}/deviceManagement/{entity}?$top=100"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0, timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for device in raw_rows:
            did = device.get("deviceId", device.get("id", "unknown"))
            claims.append(ClaimObject(
                claim_id=f"intune:{self._tenant_id}:{did}",
                entity=f"intune:device:{did}",
                fields={"identity": f"intune:{self._tenant_id}:{did}",
                        "device_name": device.get("deviceName", ""),
                        "compliance_state": device.get("complianceState", "unknown"),
                        "os_version": device.get("osVersion", ""),
                        "vendor_overlay_ref": "intune.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(device),
            ))
        return ClaimSet(claims=claims, source_reference=f"{self._graph_endpoint}/deviceManagement")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="intune-endpoint-compliance", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift scaffold — compare endpoint compliance against baseline.",
                     "adapter": self.ADAPTER_ID, "tenant_id": self._tenant_id, "scope": self.SCOPE},
            remediation="Compare normalize() output against accepted compliance baseline.",
        )

    def get_compliance_status(self, scope: Optional[str] = None) -> ClaimSet:
        raise NotImplementedError("get_compliance_status() stub — requires Graph API collector with Intune permissions.")

    def generate_endpoint_evidence(self, scope: Optional[str] = None) -> EvidenceObject:
        raise NotImplementedError("generate_endpoint_evidence() stub.")

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": "Microsoft Intune", "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"tenant_id": self._tenant_id, "scope": self.SCOPE, "last_collected": self._now().isoformat()}}
