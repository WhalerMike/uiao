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

from inspect import isawaitable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from .auth import EntraTokenVerifier, TokenError
from .context import TenantContext, clear_current_tenant, set_current_tenant
from .errors import problem_response
from .repository import TenantRepository
from .tenant import TenantStatus


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve and bind the tenant for each data-plane request."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        verifier: EntraTokenVerifier,
        repository: TenantRepository,
        public_prefixes: tuple[str, ...] = (),
        # A sync TenantRateLimiter or an async DistributedTenantRateLimiter;
        # both expose ``check(tenant) -> RateLimitDecision`` (ADR-118).
        rate_limiter: Any = None,
    ) -> None:
        super().__init__(app)
        self._verifier = verifier
        self._repository = repository
        self._public_prefixes = public_prefixes
        self._rate_limiter = rate_limiter

    def _is_public(self, path: str) -> bool:
        return any(
            path == p or path.startswith(p.rstrip("/") + "/") or path == p.rstrip("/") for p in self._public_prefixes
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if self._is_public(path):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        scheme, _, token = auth.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            return problem_response(401, code="unauthorized", detail="Bearer token required.", instance=path)

        try:
            claims = self._verifier.verify(token.strip())
        except TokenError as exc:
            return problem_response(401, code="invalid_token", detail=str(exc), instance=path)

        tenant = await self._repository.get(claims.tenant_id)
        if tenant is None:
            return problem_response(
                403,
                code="tenant_not_onboarded",
                detail=f"Tenant {claims.tenant_id} is not onboarded.",
                instance=path,
                tenant=claims.tenant_id,
            )
        if tenant.status is not TenantStatus.ACTIVE:
            reason = tenant.suspended_reason or tenant.status.value
            return problem_response(
                403,
                code="tenant_not_active",
                detail=f"Tenant {claims.tenant_id} is {reason}.",
                instance=path,
                tenant=claims.tenant_id,
            )

        # Per-plan request-rate enforcement. The limiter may be the in-process
        # per-replica TenantRateLimiter (sync) or a DistributedTenantRateLimiter
        # over a shared store (async, ADR-118) — await the latter.
        rate_headers: dict[str, str] = {}
        if self._rate_limiter is not None:
            decision = self._rate_limiter.check(tenant)
            if isawaitable(decision):
                decision = await decision
            rate_headers = decision.headers()
            if not decision.allowed:
                return problem_response(
                    429,
                    code="rate_limited",
                    detail=f"Tenant {tenant.tenant_id} exceeded its {tenant.plan.value}-plan request rate.",
                    instance=path,
                    tenant=tenant.tenant_id,
                    headers=rate_headers,
                )

        context = TenantContext(tenant=tenant, subject=claims.subject, scopes=claims.principal_scopes)
        token_handle = set_current_tenant(context)
        request.state.tenant = context
        try:
            response = await call_next(request)
        finally:
            clear_current_tenant(token_handle)
        response.headers["x-uiao-tenant"] = tenant.tenant_id
        for header, value in rate_headers.items():
            response.headers[header] = value
        return response


__all__ = ["TenantResolutionMiddleware"]
