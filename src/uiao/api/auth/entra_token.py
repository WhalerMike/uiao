"""
impl/src/uiao/impl/api/auth/entra_token.py
-------------------------------------------
Outbound authentication: MSAL client credentials for Microsoft Graph API

Flow: Client Credentials (OAuth2, app-only identity)
  1. App registration in Entra ID with Application permissions.
  2. Service authenticates using client secret or certificate.
  3. MSAL returns a Bearer token for graph.microsoft.com scope.
  4. Token is cached in memory; MSAL handles refresh before expiry.

Environment variables required (machine-level on IIS server):
  UIAO_ENTRA_TENANT_ID      Entra ID tenant GUID
  UIAO_ENTRA_CLIENT_ID      App registration client ID
  UIAO_ENTRA_CLIENT_SECRET  Client secret (or see cert path below)
  UIAO_ENTRA_CERT_PATH      (optional) path to PFX/PEM for cert auth
  UIAO_ENTRA_CERT_PASSWORD  (optional) PFX password if using cert
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

import msal  # type: ignore

# Graph API scope for application permissions
GRAPH_SCOPE = ["https://graph.microsoft.com/.default"]

# Entra ID authority base
AUTHORITY_BASE = "https://login.microsoftonline.com"


@dataclass
class TokenResult:
    access_token: str
    expires_in: int    # seconds
    token_type: str = "Bearer"


class EntraTokenProvider:
    """
    Wraps MSAL ConfidentialClientApplication for the UIAO service.

    Uses in-memory token cache (per MSAL default) — tokens survive
    across requests but not across process restarts. This is acceptable
    because IIS app pools restart infrequently and MSAL re-acquires
    automatically on expiry.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: Optional[str] = None,
        cert_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._authority = f"{AUTHORITY_BASE}/{tenant_id}"

        # Build credential — certificate takes precedence over secret
        if cert_path:
            credential = self._load_cert_credential(cert_path, cert_password)
        elif client_secret:
            credential = client_secret
        else:
            raise ValueError(
                "Either UIAO_ENTRA_CLIENT_SECRET or UIAO_ENTRA_CERT_PATH "
                "must be set."
            )

        self._msal_app = msal.ConfidentialClientApplication(
            client_id=client_id,
            authority=self._authority,
            client_credential=credential,
        )

    @classmethod
    def from_environment(cls) -> "EntraTokenProvider":
        """
        Construct from machine-level environment variables.
        Raises clear RuntimeError if any required variable is missing.
        """
        required = {
            "UIAO_ENTRA_TENANT_ID": os.environ.get("UIAO_ENTRA_TENANT_ID"),
            "UIAO_ENTRA_CLIENT_ID": os.environ.get("UIAO_ENTRA_CLIENT_ID"),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}. "
                "Set these as Machine-level variables on the IIS server. "
                "Never put credentials in code or git."
            )

        return cls(
            tenant_id=required["UIAO_ENTRA_TENANT_ID"],
            client_id=required["UIAO_ENTRA_CLIENT_ID"],
            client_secret=os.environ.get("UIAO_ENTRA_CLIENT_SECRET"),
            cert_path=os.environ.get("UIAO_ENTRA_CERT_PATH"),
            cert_password=os.environ.get("UIAO_ENTRA_CERT_PASSWORD"),
        )

    def get_token(self) -> TokenResult:
        """
        Acquire a Graph API token (synchronous).
        MSAL returns from cache if the cached token is still valid (>5 min remaining).
        Automatically re-acquires if expired.
        """
        result = self._msal_app.acquire_token_for_client(scopes=GRAPH_SCOPE)

        if "access_token" not in result:
            error = result.get("error", "unknown")
            desc = result.get("error_description", "no description")
            raise RuntimeError(
                f"MSAL token acquisition failed: {error} — {desc}. "
                "Check Entra app registration, client secret expiry, "
                "and network connectivity to login.microsoftonline.com."
            )

        return TokenResult(
            access_token=result["access_token"],
            expires_in=result.get("expires_in", 3600),
        )

    async def get_token_async(self) -> TokenResult:
        """Async wrapper — runs MSAL sync call in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_token)

    async def warm_cache(self) -> None:
        """
        Pre-acquire a token at startup so the first real request isn't delayed.
        Logs a warning if token acquisition fails but does NOT raise —
        startup should succeed even if Entra is temporarily unreachable.
        """
        try:
            await self.get_token_async()
        except RuntimeError as e:
            import logging
            logging.getLogger(__name__).warning(
                f"MSAL cache warm-up failed (non-fatal): {e}"
            )

    def get_auth_headers(self) -> dict[str, str]:
        """Return Authorization header dict ready for httpx/requests."""
        token = self.get_token()
        return {"Authorization": f"Bearer {token.access_token}"}

    @staticmethod
    def _load_cert_credential(cert_path: str, cert_password: Optional[str]) -> dict:
        """
        Load a certificate credential for MSAL.
        Supports PEM (no password) and PFX (with optional password).
        """
        import cryptography.hazmat.primitives.serialization as serialization
        from cryptography.hazmat.primitives.serialization import pkcs12

        path = cert_path
        with open(path, "rb") as f:
            data = f.read()

        if path.lower().endswith(".pfx") or path.lower().endswith(".p12"):
            pwd = cert_password.encode() if cert_password else None
            private_key, cert, _ = pkcs12.load_key_and_certificates(data, pwd)
            pem_key = private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
            pem_cert = cert.public_bytes(serialization.Encoding.PEM)
            return {"private_key": pem_key, "thumbprint": None, "public_certificate": pem_cert}
        else:
            # PEM format
            return {"private_key": data, "thumbprint": None}
