"""Health-check endpoint for the UIAO FastAPI service.

No auth required. Verifies AD LDAP reachability, Entra token acquirability,
and workspace-root presence. Useful for liveness/readiness probes.
"""

from __future__ import annotations

import os
import platform
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..auth.entra_token import EntraTokenProvider

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    server: str
    python_version: str
    ad_reachable: bool
    entra_reachable: bool
    workspace_root_exists: bool
    detail: str = ""


@router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Health check — no auth required."""
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", "")
    workspace_ok = Path(workspace).is_dir() if workspace else False

    # LDAP ping — just open a socket to port 389
    ad_server = os.environ.get("UIAO_AD_DEFAULT_SERVER", "")
    ad_ok = False
    if ad_server:
        import socket

        try:
            socket.setdefaulttimeout(3)
            with socket.create_connection((ad_server, 389)):
                ad_ok = True
        except (TimeoutError, OSError):
            ad_ok = False

    # Entra token
    entra_ok = False
    entra_detail = ""
    token_provider: EntraTokenProvider = request.app.state.token_provider
    try:
        token_provider.get_token()
        entra_ok = True
    except RuntimeError as e:
        entra_detail = str(e)

    overall = "healthy" if (ad_ok and entra_ok and workspace_ok) else "degraded"

    return HealthResponse(
        status=overall,
        server=platform.node(),
        python_version=platform.python_version(),
        ad_reachable=ad_ok,
        entra_reachable=entra_ok,
        workspace_root_exists=workspace_ok,
        detail=entra_detail,
    )
