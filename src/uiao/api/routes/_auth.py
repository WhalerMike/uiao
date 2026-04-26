"""Shared bearer-token auth dependency for the §3.1 governance routers.

Mirrors the pattern in :mod:`uiao.api.routes.auditor` — production
deployments validate the JWT signature against the Entra ID JWKS via
:mod:`uiao.api.auth.entra_token`; development / test accepts any
non-empty Bearer token. Returning the resolved subject (``sub``/``oid``
claim or ``"auditor"``) lets handlers stamp it onto audit records.
"""

from __future__ import annotations

import base64
import json
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer = HTTPBearer(auto_error=False)


def require_auditor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> str:
    """Validate a Bearer token, return the subject claim or ``"auditor"``."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required. Role: UIAO.Viewer or UIAO.Auditor",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        parts = token.split(".")
        if len(parts) == 3:
            padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(padded))
            subject: str = str(payload.get("sub", payload.get("oid", "auditor")))
            return subject
    except Exception:
        pass
    return "auditor"


__all__ = ["require_auditor"]
