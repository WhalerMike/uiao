"""
uiao.saas.control_plane
---------------------
The SaaS control-plane REST API: tenant onboarding and lifecycle management.

Mounted under ``/control/v1``. Every route requires a control-plane admin
token — an Entra access token from the *publisher* tenant carrying the
``UIAO.SaaS.Admin`` app role. The provisioning service and admin verifier are
resolved from ``app.state`` (wired by :func:`uiao.saas.app.attach_saas`), so
the router itself stays dependency-light and unit-testable.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from .auth import EntraTokenVerifier, TokenError
from .provisioning import ProvisioningService
from .repository import TenantNotFoundError
from .tenant import Tenant, TenantPlan

CONTROL_ADMIN_ROLE = "UIAO.SaaS.Admin"

router = APIRouter()


# --------------------------------------------------------------------------
# Request / response models
# --------------------------------------------------------------------------
class OnboardRequest(BaseModel):
    tenant_id: str = Field(description="Customer Entra directory (tenant) GUID")
    display_name: str = Field(default="")
    plan: TenantPlan = Field(default=TenantPlan.TRIAL)


class SuspendRequest(BaseModel):
    reason: str = Field(default="")


class OnboardResponse(BaseModel):
    tenant: Tenant
    admin_consent_url: str
    stamp_steps: list[dict[str, str]]


class StampResponse(BaseModel):
    tenant_id: str
    executed: bool
    steps: list[dict[str, str]]


# --------------------------------------------------------------------------
# Admin auth dependency
# --------------------------------------------------------------------------
def require_control_admin(request: Request) -> str:
    """Validate the control-plane admin token; return the admin subject."""
    verifier: EntraTokenVerifier | None = getattr(request.app.state, "saas_admin_verifier", None)
    if verifier is None:
        raise HTTPException(status_code=503, detail="control plane is not configured")

    auth = request.headers.get("authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required (control-plane admin)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = verifier.verify(token.strip())
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if CONTROL_ADMIN_ROLE not in claims.roles:
        raise HTTPException(status_code=403, detail=f"role {CONTROL_ADMIN_ROLE} required")
    return claims.subject


def _service(request: Request) -> ProvisioningService:
    svc: ProvisioningService | None = getattr(request.app.state, "saas_provisioning", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="provisioning service unavailable")
    return svc


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@router.post("/tenants", response_model=OnboardResponse, status_code=201)
async def onboard_tenant(
    body: OnboardRequest,
    request: Request,
    admin: str = Depends(require_control_admin),
) -> OnboardResponse:
    svc = _service(request)
    try:
        result = await svc.onboard(
            tenant_id=body.tenant_id,
            display_name=body.display_name,
            plan=body.plan,
            onboarded_by=admin,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return OnboardResponse(
        tenant=result.tenant,
        admin_consent_url=result.admin_consent_url,
        stamp_steps=[{"action": s.action, "target": s.target, "detail": s.detail} for s in result.stamp.steps],
    )


@router.get("/tenants", response_model=list[Tenant])
async def list_tenants(request: Request, admin: str = Depends(require_control_admin)) -> list[Tenant]:
    return await _service(request)._repo.list()


@router.get("/tenants/{tenant_id}", response_model=Tenant)
async def get_tenant(tenant_id: str, request: Request, admin: str = Depends(require_control_admin)) -> Tenant:
    tenant = await _service(request)._repo.get(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail=f"tenant {tenant_id} not found")
    return tenant


@router.post("/tenants/{tenant_id}/suspend", response_model=Tenant)
async def suspend_tenant(
    tenant_id: str,
    body: SuspendRequest,
    request: Request,
    admin: str = Depends(require_control_admin),
) -> Tenant:
    try:
        return await _service(request).suspend(tenant_id, reason=body.reason)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"tenant {tenant_id} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/tenants/{tenant_id}/resume", response_model=Tenant)
async def resume_tenant(tenant_id: str, request: Request, admin: str = Depends(require_control_admin)) -> Tenant:
    try:
        return await _service(request).resume(tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"tenant {tenant_id} not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete("/tenants/{tenant_id}", response_model=StampResponse)
async def deprovision_tenant(
    tenant_id: str,
    request: Request,
    admin: str = Depends(require_control_admin),
) -> StampResponse:
    try:
        result = await _service(request).deprovision(tenant_id)
    except TenantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"tenant {tenant_id} not found") from exc
    return StampResponse(
        tenant_id=result.tenant_id,
        executed=result.executed,
        steps=[{"action": s.action, "target": s.target, "detail": s.detail} for s in result.steps],
    )


__all__ = ["router", "require_control_admin", "CONTROL_ADMIN_ROLE"]
