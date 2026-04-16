"""UIAO-GOS Non-Person Identity (NPI) Adapter.

ARC 5 provider for governing non-person identities in Entra ID:
service principals, managed identities, workload identities,
application registrations, and automated service accounts.

Classification: Controlled
Boundary: GCC-Moderate
Version: 0.1.0
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.providers.base_adapter import BaseAdapter


class NPIAdapter(BaseAdapter):
    """Non-Person Identity governance adapter.

    Manages lifecycle, credential hygiene, permission scope,
    and drift detection for all non-human identities in Entra ID.
    """

    NAME = "entra-npi"
    VERSION = "0.1.0"
    PROVIDER_CATEGORY = "identity"
    BOUNDARY = "GCC-Moderate"

    # NPI sub-types governed by this adapter
    NPI_TYPES = [
        "service_principal",
        "managed_identity_system",
        "managed_identity_user",
        "workload_identity",
        "app_registration",
        "automated_service_account",
    ]

    CAPABILITIES = [
        "npi_inventory",
        "credential_expiry_detection",
        "permission_scope_audit",
        "owner_accountability",
        "stale_npi_detection",
        "secret_rotation_enforcement",
        "federated_credential_governance",
    ]

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self._npi_cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # ARC 5 contract: health_check
    # ------------------------------------------------------------------
    def health_check(self) -> Dict[str, Any]:
        """Validate connectivity to Entra ID NPI endpoints."""
        return {
            "adapter": self.NAME,
            "version": self.VERSION,
            "status": "healthy",
            "npi_types_supported": self.NPI_TYPES,
            "capabilities": self.CAPABILITIES,
        }

    # ------------------------------------------------------------------
    # ARC 5 contract: fetch_state
    # ------------------------------------------------------------------
    def fetch_state(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve current NPI state from Entra ID.

        Args:
            scope: Optional NPI type filter from NPI_TYPES.

        Returns:
            Current state dictionary for all NPIs in scope.
        """
        return {
            "adapter": self.NAME,
            "scope": scope or "all",
            "identities": [],
            "credential_status": {},
            "permission_grants": {},
            "owner_map": {},
            "_stub": True,
        }

    # ------------------------------------------------------------------
    # ARC 5 contract: expected_state
    # ------------------------------------------------------------------
    def expected_state(self, scope: Optional[str] = None) -> Dict[str, Any]:
        """Return canonical desired state for NPIs.

        Desired-state includes:
        - Maximum credential lifetime (days)
        - Required owner assignment
        - Permitted permission scopes
        - Approved federated credential issuers
        """
        return {
            "adapter": self.NAME,
            "scope": scope or "all",
            "policies": {
                "max_credential_lifetime_days": 90,
                "require_owner": True,
                "allow_password_credentials": False,
                "approved_federated_issuers": [],
                "stale_threshold_days": 180,
            },
            "_stub": True,
        }

    # ------------------------------------------------------------------
    # ARC 5 contract: remediate
    # ------------------------------------------------------------------
    def remediate(
        self,
        drift_items: List[Dict[str, Any]],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Remediate NPI drift findings.

        Args:
            drift_items: Drift records from the drift engine.
            dry_run: If True, report planned actions without executing.

        Returns:
            Remediation report with actions taken or planned.
        """
        return {
            "adapter": self.NAME,
            "dry_run": dry_run,
            "drift_count": len(drift_items),
            "actions_planned": [],
            "actions_executed": [],
            "_stub": True,
        }

    # ------------------------------------------------------------------
    # NPI-specific helpers
    # ------------------------------------------------------------------
    def classify_identity(self, identity: Dict[str, Any]) -> str:
        """Classify an Entra object into an NPI sub-type."""
        return identity.get("npi_type", "unknown")

    def audit_credential_hygiene(
        self, identity_id: str
    ) -> Dict[str, Any]:
        """Check credential age, rotation status, and secret count."""
        return {
            "identity_id": identity_id,
            "credentials": [],
            "compliant": False,
            "_stub": True,
        }
