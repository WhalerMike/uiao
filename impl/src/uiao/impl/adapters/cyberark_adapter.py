"""
UIAO CyberArk Credential Rotation Adapter — integration class.

Credential rotation and privileged access management — change-making
actions against vault/PAM systems.

Classification: modernization / integration / reserved
Controls: IA-5, IA-5(1), AC-2, AC-6

File: src/uiao/impl/adapters/cyberark_adapter.py
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


class CyberArkAdapter(DatabaseAdapterBase):
    """CyberArk adapter — credential rotation and privileged access management."""

    ADAPTER_ID: str = "cyberark"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._vault_url: str = self._config.get("vault_url", "")
        self._safe: str = self._config.get("safe", "default")

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"cyberark:{self._safe}",
            auth_method=self._config.get("auth_method", "cyberark-credential"),
            endpoint=self._vault_url or "https://vault.local/PasswordVault/api",
            tls_version="TLSv1.3", mtls_enabled=True, timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {"AccountID": "string", "SafeName": "string", "PlatformID": "string",
                         "Address": "string", "UserName": "string", "LastModifiedTime": "datetime"}
        canonical_schema = {"identity": "cyberark:<safe>:<account_id>",
                            "control_id": "IA-5", "evidence.source": "cyberark"}
        return SchemaMappingObject(
            vendor_schema=vendor_schema, canonical_schema=canonical_schema,
            mapping_rules={"AccountID": "identity suffix", "PlatformID": "platform classifier"},
            unmapped_fields=["SecretType", "SecretManagement"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        safe = canonical_query.get("from", self._safe)
        vendor_query = f"GET /PasswordVault/api/Accounts?filter=safeName eq {safe}"
        return QueryProvenance(
            canonical_query=canonical_query, vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query), row_count=0, timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for account in raw_rows:
            aid = account.get("AccountID", "unknown")
            claims.append(ClaimObject(
                claim_id=f"cyberark:{self._safe}:{aid}",
                entity=f"cyberark:account:{aid}",
                fields={"identity": f"cyberark:{self._safe}:{aid}",
                        "platform": account.get("PlatformID", ""),
                        "username": account.get("UserName", ""),
                        "vendor_overlay_ref": "cyberark.yaml"},
                source=self.ADAPTER_ID, provenance_hash=self._hash(account),
            ))
        return ClaimSet(claims=claims, source_reference=self._vault_url or "cyberark-vault")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="cyberark-credential-posture", severity="info",
            first_observed=self._now(), last_observed=self._now(),
            details={"message": "Drift scaffold — compare rotation schedule vs actual.", "adapter": self.ADAPTER_ID, "safe": self._safe},
            remediation="Compare last-rotation timestamps against policy-mandated intervals.",
        )

    def rotate_credential(self, account_id: str) -> DriftReport:
        """Report a credential rotation action (read-only comparison for now)."""
        return DriftReport(
            drift_type="cyberark-credential-rotation",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={"adapter": self.ADAPTER_ID, "account_id": account_id, "safe": self._safe,
                     "message": f"Rotation requested for {account_id}. Commit via vault API."},
            remediation=f"Execute rotation for account {account_id} in safe {self._safe}.",
        )

    def generate_rotation_evidence(self, accounts_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from vault account data."""
        conn = self.connect()
        accounts = (accounts_data or {}).get("value", [])
        claim_set = self.normalize(accounts)

        return EvidenceObject(
            ksi_id=f"KSI-IA-05-{self._safe}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={"connection": conn.to_dict(), "accounts": len(accounts)},
            normalized_data=claim_set.to_dict(),
            provenance={"adapter_id": self.ADAPTER_ID, "safe": self._safe, "hash": self._hash(claim_set.to_dict()), "timestamp": self._now().isoformat()},
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {"vendor": "CyberArk", "adapter_id": self.ADAPTER_ID,
                "claims": claim_set.to_dict(),
                "metadata": {"vault_url": self._vault_url, "safe": self._safe, "last_collected": self._now().isoformat()}}
