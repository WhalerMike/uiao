"""DEPRECATED: Superseded by src/uiao_impl/adapters/entra_adapter.py
and src/uiao_impl/collectors/entra/entra_collector.py (Graph API).
Retained for backward compatibility only. Do not extend."""
from __future__ import annotations

from typing import Any, List

from adapters import register
from adapters.base_adapter import (
    AdapterMetadata,
    BaseAdapter,
    CanonicalClaim,
    ClaimFilter,
    DriftReport,
    KSIBundle,
    ProvenanceRecord,
)


@register("entra-id")
class EntraIdAdapter(BaseAdapter):
    """Pulls identity claims from Microsoft Entra ID via MS Graph."""
    _tenant_id: str = ""
    _connected: bool = False

    async def connect(self, config: dict) -> bool:
        self._tenant_id = config.get("tenant_id", "")
        self._connected = bool(self._tenant_id)
        return self._connected

    async def extract_claims(self, filter: ClaimFilter) -> List[CanonicalClaim]:
        return []

    async def detect_drift(self) -> DriftReport:
        return DriftReport(adapter_id="entra-id")

    async def transform_to_canonical(self, raw: Any) -> CanonicalClaim:
        return CanonicalClaim(
            claim_id="", source_system="entra-id",
            claim_type="identity", value=raw,
        )

    async def generate_lineage(self) -> ProvenanceRecord:
        return ProvenanceRecord(
            record_id="", adapter_id="entra-id",
            source_system="Microsoft Entra ID",
        )

    async def generate_ksi_bundle(self) -> KSIBundle:
        return KSIBundle(bundle_id="", adapter_id="entra-id")

    def get_metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            adapter_id="entra-id",
            name="Microsoft Entra ID Adapter",
            version="0.1.0",
            certification_level=1,
            plane="Identity",
            capabilities=["user_sync", "group_sync", "conditional_access"],
        )

