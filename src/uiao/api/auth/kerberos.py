"""
impl/src/uiao/impl/api/auth/kerberos.py
----------------------------------------
Inbound authentication: Windows Authentication via IIS Negotiate/Kerberos

How it works on Windows Server 2026 + IIS:
  1. IIS is configured with Windows Authentication + Kernel Mode Auth.
  2. Client sends request; IIS challenges with WWW-Authenticate: Negotiate.
  3. Client responds with Kerberos service ticket for
     HTTP/uiao-api.corp.contoso.com (the SPN registered on the service account).
  4. IIS validates the ticket and populates the AUTH_USER server variable.
  5. FastAPI sees the request with X-IIS-WindowsAuthUser header injected
     by HttpPlatformHandler (or reads from environment via REMOTE_USER).

For outbound LDAP queries (ldap3 → AD):
  The process runs AS the service account (IIS app pool identity).
  ldap3 uses SASL GSSAPI which calls into the Windows SSPI stack.
  No explicit credentials required — the OS Kerberos TGT is used.

Dependencies:
  Windows-only path: no ldap3 GSSAPI dependencies needed on developer
  Linux/Mac — use the username/password ldap3 path for local dev.
"""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request, status


@dataclass
class WindowsIdentity:
    """Represents an authenticated Windows principal."""

    username: str  # e.g. CORP\jsmith
    domain: str  # e.g. CORP
    account: str  # e.g. jsmith
    is_service: bool  # True if this is a service account or machine account


def get_windows_identity(request: Request) -> Optional[WindowsIdentity]:
    """
    Extract the Windows identity from the request.

    IIS + HttpPlatformHandler sets the authenticated user in:
      - HTTP_X_IIS_WINDOWSAUTHUSER  (custom header injected by IIS)
      - REMOTE_USER                 (standard CGI variable)
      - HTTP_AUTH_USER              (fallback)

    Returns None if no Windows identity is present (anonymous or
    non-Windows auth).
    """
    # Header name after IIS HttpPlatformHandler forwarding
    raw = (
        request.headers.get("x-iis-windowsauthuser")
        or request.headers.get("remote-user")
        or request.headers.get("x-auth-user")
        or os.environ.get("REMOTE_USER", "")
    )

    if not raw:
        return None

    # Windows format: DOMAIN\username or just username
    if "\\" in raw:
        domain, account = raw.split("\\", 1)
    else:
        domain = os.environ.get("USERDOMAIN", "")
        account = raw

    is_service = account.lower().startswith("svc-") or account.endswith("$")

    return WindowsIdentity(
        username=raw,
        domain=domain,
        account=account,
        is_service=is_service,
    )


def require_windows_auth(request: Request) -> WindowsIdentity:
    """
    FastAPI dependency: require a valid Windows identity.
    Raises HTTP 401 if not authenticated.
    Raises HTTP 403 if authenticated but is a machine account (ends with $).

    Usage in route:
        @router.post("/run")
        async def run_survey(identity: WindowsIdentity = Depends(require_windows_auth)):
            ...
    """
    identity = get_windows_identity(request)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Windows authentication required. "
            "Ensure IIS Windows Authentication is enabled "
            "and caller is domain-joined.",
            headers={"WWW-Authenticate": "Negotiate"},
        )
    # Reject pure machine accounts ($) — these shouldn't call the API directly
    if identity.account.endswith("$") and not identity.is_service:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Machine accounts are not permitted to call this API directly.",
        )
    return identity


# ------------------------------------------------------------------
# Outbound: LDAP connection using Kerberos SSPI (Windows only)
# ------------------------------------------------------------------


def get_ldap_connection(server_hostname: str):
    """
    Create an ldap3 connection using Kerberos SASL (Windows SSPI).

    On Windows: uses the process identity (IIS service account) via GSSAPI.
    No credentials in code — the OS handles the Kerberos ticket.

    On non-Windows (dev/CI): falls back to environment-variable credentials
    for basic bind (UIAO_AD_USER, UIAO_AD_PASSWORD).

    Returns an open, bound ldap3 Connection.
    """
    from ldap3 import ALL, Connection, Server  # type: ignore

    srv = Server(server_hostname, get_info=ALL, use_ssl=False)

    if platform.system() == "Windows":
        from ldap3 import GSSAPI, SASL  # type: ignore

        conn = Connection(
            srv,
            authentication=SASL,
            sasl_mechanism=GSSAPI,
            auto_bind=True,
        )
    else:
        # Dev/CI fallback — use explicit credentials
        ad_user = os.environ.get("UIAO_AD_USER")
        ad_pass = os.environ.get("UIAO_AD_PASSWORD")
        if not ad_user or not ad_pass:
            raise RuntimeError(
                "Non-Windows environment: set UIAO_AD_USER and UIAO_AD_PASSWORD "
                "for LDAP bind, or run on a domain-joined Windows host for "
                "Kerberos SSPI authentication."
            )
        conn = Connection(srv, user=ad_user, password=ad_pass, auto_bind=True)

    return conn
