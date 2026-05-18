"""
UIAO CyberArk Credential Rotation Adapter — integration class.

Credential rotation and privileged access management — change-making
actions against vault/PAM systems.

Classification: modernization / integration / reserved
Controls: IA-5, IA-5(1), AC-2, AC-6

File: src/uiao/impl/adapters/cyberark_adapter.py
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests  # type: ignore[import-untyped]

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
        self._vault_url: str = self._config.get("vault_url", "") or self._config.get("base_url", "")
        self._safe: str = self._config.get("safe", "default")
        self._auth_token: str = self._config.get("auth_token", "") or self._config.get("token", "")
        self._api_base: str = self._normalize_api_base(self._vault_url)
        self._request_timeout_seconds: int = int(self._config.get("timeout_seconds", 30))
        self._verify_tls: bool = bool(self._config.get("verify_tls", True))

    @staticmethod
    def _normalize_api_base(vault_url: str) -> str:
        base = (vault_url or "").strip().rstrip("/")
        if not base:
            return "https://vault.local/PasswordVault/API"
        lower = base.lower()
        if lower.endswith("/passwordvault/api"):
            return base
        if lower.endswith("/passwordvault"):
            return f"{base}/API"
        return f"{base}/PasswordVault/API"

    def _auth_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-CyberArk-Safe": self._safe,
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self._auth_token:
            raise RuntimeError("CYBERARK_TOKEN (or config auth_token/token) is required for CyberArk API calls")

        endpoint_path = path if path.startswith("/") else f"/{path}"
        url = f"{self._api_base}{endpoint_path}"

        try:
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=self._auth_headers(),
                json=json_body,
                params=params,
                timeout=self._request_timeout_seconds,
                verify=self._verify_tls,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"CyberArk API {method.upper()} {endpoint_path} failed: {exc}") from exc

        if not response.text:
            return {}
        try:
            return response.json()  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            return {"raw_text": response.text}

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"cyberark:{self._safe}",
            auth_method=self._config.get("auth_method", "cyberark-credential"),
            endpoint=self._api_base,
            tls_version="TLSv1.3",
            mtls_enabled=True,
            timestamp=self._now(),
        )

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema = {
            "AccountID": "string",
            "SafeName": "string",
            "PlatformID": "string",
            "Address": "string",
            "UserName": "string",
            "LastModifiedTime": "datetime",
        }
        canonical_schema = {
            "identity": "cyberark:<safe>:<account_id>",
            "control_id": "IA-5",
            "evidence.source": "cyberark",
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules={"AccountID": "identity suffix", "PlatformID": "platform classifier"},
            unmapped_fields=["SecretType", "SecretManagement"],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        safe = canonical_query.get("from", self._safe)
        search = str(canonical_query.get("search", "")).strip()
        limit = int(canonical_query.get("limit", 100))
        vendor_query = f"GET /PasswordVault/API/Accounts?search={search}&limit={limit}&safe={safe}"
        row_count = 0
        try:
            payload = self._request(
                "GET",
                "/Accounts",
                params={"search": search, "limit": limit, "safeName": safe},
            )
            accounts = payload.get("value") or payload.get("Accounts") or []
            if isinstance(accounts, list):
                row_count = len(accounts)
        except RuntimeError:
            row_count = 0
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=row_count,
            timestamp=self._now(),
        )

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        claims = []
        for account in raw_rows:
            aid = account.get("id") or account.get("AccountID") or account.get("accountId") or "unknown"
            safe_name = account.get("safeName") or account.get("SafeName") or self._safe
            claims.append(
                ClaimObject(
                    claim_id=f"cyberark:{safe_name}:{aid}",
                    entity=f"cyberark:account:{aid}",
                    fields={
                        "identity": f"cyberark:{safe_name}:{aid}",
                        "platform": account.get("platformId") or account.get("PlatformID", ""),
                        "username": account.get("userName") or account.get("UserName", ""),
                        "owner": account.get("owner", ""),
                        "rotation_window_days": account.get("rotationWindowDays"),
                        "last_rotated_at": account.get("lastRotatedAt") or account.get("LastModifiedTime"),
                        "vendor_overlay_ref": "cyberark.yaml",
                    },
                    source=self.ADAPTER_ID,
                    provenance_hash=self._hash(account),
                )
            )
        return ClaimSet(claims=claims, source_reference=f"{self._api_base}/Accounts")

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="cyberark-credential-posture",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": "Drift scaffold — compare rotation schedule vs actual.",
                "adapter": self.ADAPTER_ID,
                "safe": self._safe,
            },
            remediation="Compare last-rotation timestamps against policy-mandated intervals.",
        )

    def create_account(self, account_payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(account_payload)
        payload.setdefault("safeName", self._safe)
        return self._request("POST", "/Accounts", json_body=payload)

    def verify_credential(self, account_id: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/Accounts/{account_id}/Verify",
            json_body={"safeName": self._safe},
        )

    def get_account_activities(self, account_id: str) -> List[Dict[str, Any]]:
        activities_payload = self._request(
            "GET",
            f"/Accounts/{account_id}/Activities",
            params={"safeName": self._safe},
        )
        values = activities_payload.get("value") or activities_payload.get("Activities") or []
        return values if isinstance(values, list) else []

    def rotate_credential(self, account_id: str, rotation_cause: str = "policy-scheduled-rotation") -> DriftReport:
        """Rotate + verify a privileged credential and emit drift report evidence."""
        observed = self._now()
        try:
            change_response = self._request(
                "POST",
                f"/Accounts/{account_id}/Change",
                json_body={
                    "safeName": self._safe,
                    "ChangeImmediately": True,
                    "reason": rotation_cause,
                },
            )
            verify_response = self.verify_credential(account_id)
            activities = self.get_account_activities(account_id)
            verification_passed = bool(
                verify_response.get("success", True)
                and not verify_response.get("verificationFailed", False)
                and not verify_response.get("error")
            )
            return DriftReport(
                drift_type="cyberark-credential-rotation",
                severity="info" if verification_passed else "high",
                first_observed=observed,
                last_observed=self._now(),
                details={
                    "adapter": self.ADAPTER_ID,
                    "account_id": account_id,
                    "safe": self._safe,
                    "rotation_cause": rotation_cause,
                    "verification_passed": verification_passed,
                    "change_response": change_response,
                    "verify_response": verify_response,
                    "activity_count": len(activities),
                    "activities": activities,
                },
                remediation=(
                    None
                    if verification_passed
                    else f"Verification failed after rotating account {account_id}; review CyberArk activity trail."
                ),
            )
        except RuntimeError as exc:
            return DriftReport(
                drift_type="cyberark-credential-rotation",
                severity="high",
                first_observed=observed,
                last_observed=self._now(),
                details={
                    "adapter": self.ADAPTER_ID,
                    "account_id": account_id,
                    "safe": self._safe,
                    "rotation_cause": rotation_cause,
                    "verification_passed": False,
                    "error": str(exc),
                },
                remediation=f"Resolve CyberArk API error and retry credential rotation for account {account_id}.",
            )

    def generate_rotation_evidence(self, accounts_data: Optional[Dict[str, Any]] = None) -> EvidenceObject:
        """Generate evidence bundle from vault account data."""
        conn = self.connect()
        accounts = (accounts_data or {}).get("value", [])
        rotation_event = (accounts_data or {}).get("rotation_event", {})
        claim_set = self.normalize(accounts)

        return EvidenceObject(
            ksi_id=f"KSI-CARK-005-{self._safe}",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={
                "connection": conn.to_dict(),
                "accounts": len(accounts),
                "rotation_cause": rotation_event.get("rotation_cause", "unspecified"),
                "verification_passed": rotation_event.get("verification_passed", False),
                "account_id": rotation_event.get("account_id"),
            },
            normalized_data=claim_set.to_dict(),
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "safe": self._safe,
                "hash": self._hash(claim_set.to_dict()),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=True,
        )

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {
            "vendor": "CyberArk",
            "adapter_id": self.ADAPTER_ID,
            "claims": claim_set.to_dict(),
            "metadata": {"vault_url": self._vault_url, "safe": self._safe, "last_collected": self._now().isoformat()},
        }
