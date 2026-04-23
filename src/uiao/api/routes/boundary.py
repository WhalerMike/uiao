"""
impl/src/uiao/impl/api/routes/boundary.py
------------------------------------------
API routes for GCC Boundary Probe
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from ...adapters.modernization.gcc_boundary_probe.probe import (
    BoundaryProbeReport,
    run_boundary_probe,
)
from ..auth.entra_token import EntraTokenProvider
from ..auth.kerberos import WindowsIdentity, require_windows_auth

router = APIRouter()

REGISTRY_PATH = (
    Path(__import__("os").environ.get("UIAO_WORKSPACE_ROOT", "C:/srv/uiao"))
    / "src/uiao/canon/gcc-boundary-gap-registry.yaml"
)


class BoundaryProbeRequest(BaseModel):
    include_arc: bool = False
    subscription_id: Optional[str] = None


@router.post("/run", summary="Run GCC boundary feature probe")
async def run_probe(
    body: BoundaryProbeRequest,
    request: Request,
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """
    Run the GCC boundary probe against the configured tenant.
    Detects DRIFT-BOUNDARY conditions — features silently blocked
    or explicitly unavailable in GCC-Moderate.

    Always read-only. Requires Windows Authentication.
    """
    provider: EntraTokenProvider = request.app.state.token_provider
    try:
        token = provider.get_token()
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Cannot acquire Graph token: {e}",
        ) from e

    tenant_id = __import__("os").environ.get("UIAO_ENTRA_TENANT_ID", "")

    try:
        report: BoundaryProbeReport = await run_boundary_probe(
            graph_token=token.access_token,
            tenant_id=tenant_id,
            gap_registry_path=REGISTRY_PATH if REGISTRY_PATH.exists() else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Probe failed: {exc}",
        ) from exc

    return {
        "requested_by": identity.username,
        "report": report.as_dict(),
        "unmitigated_p1_count": len(report.unmitigated_p1),
        "action_required": len(report.unmitigated_p1) > 0,
    }


@router.get("/gaps", summary="Return current gap registry")
async def get_gaps(
    identity: WindowsIdentity = Depends(require_windows_auth),
) -> dict:
    """Return the current canonical gap registry."""
    import yaml

    if not REGISTRY_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gap registry not found. Run /boundary/run first.",
        )
    registry = yaml.safe_load(REGISTRY_PATH.read_text())
    return {"registry": registry, "requested_by": identity.username}
