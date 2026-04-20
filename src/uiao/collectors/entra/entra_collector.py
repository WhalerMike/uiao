from __future__ import annotations

"""
Entra ID evidence collector.

This collector is responsible for:
- Retrieving Conditional Access policies
- Evaluating MFA and authentication method registration details
- Inspecting directory roles and members
- Collecting organization and named locations information

It is designed to feed KSIs related to identity assurance, privileged access,
and session protection.
"""

import logging
from typing import Any, Dict, Optional

try:
    import httpx
    from azure.identity import ClientSecretCredential
except ImportError:
    httpx = None
    ClientSecretCredential = None

# In-package import; adjust if package layout changes
from ..base_collector import BaseCollector, EvidenceObject

logger = logging.getLogger(__name__)


class EntraCollector(BaseCollector):
    """
    Collector for Microsoft Entra ID (Azure AD) via Microsoft Graph API.

    Collects evidence on:
    - Conditional Access policies
    - MFA registration details
    - Directory roles and privileged members
    - Authentication methods policy
    - Organization info
    - Named locations

    This implementation uses azure-identity for token acquisition and httpx
    for API calls. Supports both client-credential (app-only) and delegated flows.
    """

    COLLECTOR_ID: str = "entra"

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the Entra ID collector.

        Expected configuration keys:
        - tenant_id: str
            Azure AD tenant ID
        - client_id: str
            Service principal (app) client ID
        - client_secret: str
            Service principal client secret
        - authority: Optional[str]
            Token endpoint (default: https://login.microsoftonline.com/{tenant_id})
        - api_base_url: Optional[str]
            Graph API base URL (default: https://graph.microsoft.com/v1.0)
        """
        super().__init__(config=config)
        if httpx is None or ClientSecretCredential is None:
            logger.warning(
                "azure-identity and httpx are required for EntraCollector; "
                "install with: pip install 'uiao[graph]'"
            )

        self._tenant_id: Optional[str] = self._config.get("tenant_id")
        self._client_id: Optional[str] = self._config.get("client_id")
        self._client_secret: Optional[str] = self._config.get("client_secret")
        self._authority: str = self._config.get(
            "authority", f"https://login.microsoftonline.com/{self._tenant_id}"
        )
        self._api_base_url: str = self._config.get("api_base_url", "https://graph.microsoft.com/v1.0")
        self._scope: str = "https://graph.microsoft.com/.default"
        self._credential: Optional[ClientSecretCredential] = None
        self._http_client: Optional[httpx.Client] = None

    def _get_credential(self) -> Optional[ClientSecretCredential]:
        """
        Lazy-initialize and cache the Azure credential.

        Returns None if credentials are not configured.
        """
        if self._credential is not None:
            return self._credential

        if ClientSecretCredential is None:
            logger.error("ClientSecretCredential not available; install azure-identity")
            return None

        if not all([self._tenant_id, self._client_id, self._client_secret]):
            logger.warning("Entra ID credentials not fully configured (tenant_id, client_id, client_secret)")
            return None

        try:
            self._credential = ClientSecretCredential(
                tenant_id=self._tenant_id,
                client_id=self._client_id,
                client_secret=self._client_secret,
                authority=self._authority,
            )
            return self._credential
        except Exception as e:
            logger.error(f"Failed to create ClientSecretCredential: {e}")
            return None

    def _get_http_client(self) -> Optional[httpx.Client]:
        """
        Lazy-initialize and cache the HTTP client with token acquisition.
        """
        if self._http_client is not None:
            return self._http_client

        if httpx is None:
            logger.error("httpx not available; install httpx")
            return None

        credential = self._get_credential()
        if credential is None:
            return None

        try:
            # Create a custom transport that injects the Bearer token
            class BearerTokenAuth(httpx.Auth):
                def __init__(self, credential: ClientSecretCredential, scope: str):
                    self.credential = credential
                    self.scope = scope
                    self.token: Optional[str] = None
                    self.token_expires_at: float = 0

                def auth_flow(self, request: httpx.Request) -> Any:
                    import time

                    # Refresh token if expired (with 60s buffer)
                    if time.time() > self.token_expires_at - 60:
                        try:
                            token_response = self.credential.get_token(self.scope)
                            self.token = token_response.token
                            self.token_expires_at = token_response.expires_on
                        except Exception as e:
                            logger.error(f"Failed to acquire token: {e}")
                            self.token = None

                    if self.token:
                        request.headers["Authorization"] = f"Bearer {self.token}"

                    yield request

            auth = BearerTokenAuth(credential=credential, scope=self._scope)
            self._http_client = httpx.Client(auth=auth, timeout=30.0)
            return self._http_client
        except Exception as e:
            logger.error(f"Failed to create HTTP client: {e}")
            return None

    def _call_graph_api(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """
        Call a Graph API endpoint and return the response JSON.

        Parameters
        ----------
        endpoint:
            Path after base URL (e.g., '/identity/conditionalAccess/policies')

        Returns
        -------
        Optional[Dict[str, Any]]
            The API response as a dict, or None if the call fails.
        """
        client = self._get_http_client()
        if client is None:
            logger.warning(f"No HTTP client available; skipping {endpoint}")
            return None

        url = f"{self._api_base_url}{endpoint}"
        try:
            response = client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"Graph API call to {endpoint} failed: {e}")
            return None

    def _normalize_conditional_access(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize Conditional Access policies data.

        Parameters
        ----------
        raw:
            Raw response from /identity/conditionalAccess/policies

        Returns
        -------
        Dict[str, Any]
            Normalized structure with policy counts and details.
        """
        if not raw or "value" not in raw:
            return {"policy_count": 0, "policies": []}

        policies = raw.get("value", [])
        normalized = {
            "policy_count": len(policies),
            "policies": [
                {
                    "id": p.get("id"),
                    "displayName": p.get("displayName"),
                    "state": p.get("state"),
                    "conditions": p.get("conditions", {}),
                }
                for p in policies
            ],
        }
        return normalized

    def _normalize_auth_methods(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize authentication method registration details.

        Parameters
        ----------
        raw:
            Raw response from /reports/authenticationMethods/userRegistrationDetails

        Returns
        -------
        Dict[str, Any]
            Normalized structure with registration stats.
        """
        if not raw or "value" not in raw:
            return {"registered_user_count": 0, "methods_summary": {}}

        users = raw.get("value", [])
        methods_count: Dict[str, int] = {}

        for user in users:
            methods = user.get("authenticationMethods", [])
            for method in methods:
                method_type = method.get("type", "unknown")
                methods_count[method_type] = methods_count.get(method_type, 0) + 1

        normalized = {
            "registered_user_count": len(users),
            "methods_summary": methods_count,
        }
        return normalized

    def _normalize_directory_roles(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize directory roles and member counts.

        Parameters
        ----------
        raw:
            Raw response from /directoryRoles

        Returns
        -------
        Dict[str, Any]
            Normalized structure with role counts and details.
        """
        if not raw or "value" not in raw:
            return {"role_count": 0, "roles": []}

        roles = raw.get("value", [])
        normalized = {
            "role_count": len(roles),
            "roles": [
                {
                    "id": r.get("id"),
                    "displayName": r.get("displayName"),
                    "description": r.get("description"),
                }
                for r in roles
            ],
        }
        return normalized

    def _normalize_auth_policy(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize authentication methods policy.

        Parameters
        ----------
        raw:
            Raw response from /policies/authenticationMethodsPolicy

        Returns
        -------
        Dict[str, Any]
            Normalized structure with policy details.
        """
        if not raw:
            return {"is_configured": False}

        normalized = {
            "is_configured": True,
            "id": raw.get("id"),
            "description": raw.get("description"),
            "authenticationMethodConfigurations": raw.get("authenticationMethodConfigurations", []),
        }
        return normalized

    def _normalize_organization(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize organization information.

        Parameters
        ----------
        raw:
            Raw response from /organization (typically returns an array)

        Returns
        -------
        Dict[str, Any]
            Normalized structure with org details.
        """
        if not raw or "value" not in raw or len(raw["value"]) == 0:
            return {"is_found": False}

        org = raw["value"][0]
        normalized = {
            "is_found": True,
            "id": org.get("id"),
            "displayName": org.get("displayName"),
            "countryLetterCode": org.get("countryLetterCode"),
            "createdDateTime": org.get("createdDateTime"),
        }
        return normalized

    def _normalize_named_locations(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Normalize named locations data.

        Parameters
        ----------
        raw:
            Raw response from /identity/conditionalAccess/namedLocations

        Returns
        -------
        Dict[str, Any]
            Normalized structure with location counts.
        """
        if not raw or "value" not in raw:
            return {"location_count": 0, "locations": []}

        locations = raw.get("value", [])
        normalized = {
            "location_count": len(locations),
            "locations": [
                {
                    "id": loc.get("id"),
                    "displayName": loc.get("displayName"),
                    "locationType": loc.get("locationType") or "unknown",
                }
                for loc in locations
            ],
        }
        return normalized

    def collect(self, ksi_id: str) -> EvidenceObject:
        """
        Collect Entra ID evidence for the given KSI.

        Collects:
        - Conditional Access policies
        - MFA registration details
        - Directory roles
        - Authentication methods policy
        - Organization info
        - Named locations

        If Graph API is unreachable or credentials aren't configured,
        returns empty evidence with a clear warning (does not crash).

        Parameters
        ----------
        ksi_id:
            Identifier of the KSI for which evidence is being collected.

        Returns
        -------
        EvidenceObject
            Canonical evidence object containing raw and normalized Entra data.
        """
        raw_data: Dict[str, Any] = {
            "source": "EntraID",
            "tenant_id": self._tenant_id,
            "collection_timestamp_utc": self._now().isoformat(),
            "conditional_access_policies": self._call_graph_api("/identity/conditionalAccess/policies"),
            "auth_method_registration": self._call_graph_api(
                "/reports/authenticationMethods/userRegistrationDetails"
            ),
            "directory_roles": self._call_graph_api("/directoryRoles"),
            "auth_methods_policy": self._call_graph_api("/policies/authenticationMethodsPolicy"),
            "organization": self._call_graph_api("/organization"),
            "named_locations": self._call_graph_api("/identity/conditionalAccess/namedLocations"),
        }

        normalized_data: Dict[str, Any] = {
            "conditional_access": self._normalize_conditional_access(
                raw_data.get("conditional_access_policies")
            ),
            "auth_methods": self._normalize_auth_methods(raw_data.get("auth_method_registration")),
            "directory_roles": self._normalize_directory_roles(raw_data.get("directory_roles")),
            "auth_policy": self._normalize_auth_policy(raw_data.get("auth_methods_policy")),
            "organization": self._normalize_organization(raw_data.get("organization")),
            "named_locations": self._normalize_named_locations(raw_data.get("named_locations")),
        }

        provenance = self._build_provenance(raw_data=raw_data)

        evidence = EvidenceObject(
            ksi_id=ksi_id,
            source="EntraID",
            timestamp=self._now(),
            raw_data=raw_data,
            normalized_data=normalized_data,
            provenance=provenance,
            freshness_valid=False,  # Validator will set this based on freshness_window
        )
        return evidence

    def health_check(self) -> bool:
        """
        Perform a health check for the Entra ID collector.

        Verifies that:
        - Configuration is present (tenant_id, client_id, client_secret)
        - Credentials can be created
        - A lightweight Graph endpoint (/organization) is reachable

        Returns
        -------
        bool
            True if the collector appears healthy and ready to collect evidence,
            False otherwise.
        """
        # Check configuration presence
        required_keys = ["tenant_id", "client_id", "client_secret"]
        for key in required_keys:
            if not self._config.get(key):
                logger.warning(f"Entra ID collector missing required config key: {key}")
                return False

        # Try to acquire credentials
        credential = self._get_credential()
        if credential is None:
            logger.warning("Entra ID collector failed to create credentials")
            return False

        # Try a lightweight API call to verify connectivity
        org_response = self._call_graph_api("/organization")
        if org_response is None:
            logger.warning("Entra ID collector failed to reach /organization endpoint")
            return False

        logger.info("Entra ID collector health check passed")
        return True
