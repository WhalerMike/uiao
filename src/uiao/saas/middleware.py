"""
uiao.saas.middleware
-------------------
ASGI middleware that resolves the calling tenant for every data-plane
request and binds it to the request context.

Flow per request:
  1. Public path prefixes (health, docs, control plane) bypass resolution.
  2. Extract the ``Authorization: Bearer <jwt>`` header → 401 if missing.
  3. Verify the token (:class:`~uiao.saas.auth.EntraTokenVerifier`) → 401.
  4. Look up the ``tid`` claim in the tenant registry → 403 if unknown.
  5. Reject non-ACTIVE tenants (suspended / pending / deprovisioned) → 403.
  6. Bind :class:`~uiao.saas.context.TenantContext` and stamp
     ``request.state.tenant`` for handlers/dependencies.

The middleware always clears the context var in a ``finally`` so a worker
never leaks one request's tenant into the next.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from .auth import EntraTokenVerifier, TokenError
from .context import TenantContext, clear_current_tenant, set_current_tenant
from .repository import TenantRepository
from .tenant import TenantStatus


def _json_error(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve and bind the tenant for each data-plane request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        verifier: EntraTokenVerifier,
        repository: TenantRepository,
        public_prefixes: tuple[str, ...] = (),
    ) -> None:
        super().__init__(app)
        self._verifier = verifier
        self._repository = repository
        self._public_prefixes = public_prefixes

    def _is_public(self, path: str) -> bool:
        return any(
            path == p or path.startswith(p.rstrip("/") + "/") or path == p.rstrip("/") for p in self._public_prefixes
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if self._is_public(request.url.path):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return _json_error(401, "unauthorized", "Bearer token required.")

        try:
            claims = self._verifier.verify(token.strip())
        except TokenError as exc:
            return _json_error(401, "invalid_token", str(exc))

        tenant = await self._repository.get(claims.tenant_id)
        if tenant is None:
            return _json_error(403, "tenant_not_onboarded", f"Tenant {claims.tenant_id} is not onboarded.")
        if tenant.status is not TenantStatus.ACTIVE:
            reason = tenant.suspended_reason or tenant.status.value
            return _json_error(403, "tenant_not_active", f"Tenant {claims.tenant_id} is {reason}.")

        context = TenantContext(tenant=tenant, subject=claims.subject, scopes=claims.principal_scopes)
        token_handle = set_current_tenant(context)
        request.state.tenant = context
        try:
            response = await call_next(request)
        finally:
            clear_current_tenant(token_handle)
        response.headers["x-uiao-tenant"] = tenant.tenant_id
        return response


__all__ = ["TenantResolutionMiddleware"]
