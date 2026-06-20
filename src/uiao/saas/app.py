"""
uiao.saas.app
------------
Composition root: augment a FastAPI data-plane app with the SaaS control
plane and tenant-resolution middleware.

:func:`attach_saas` is intentionally idempotent-friendly and dependency-
injectable — tests pass an in-memory repository and an
``insecure_allow_unsigned`` verifier; production passes nothing and lets it
build a Postgres repository + JWKS signature verification from
:class:`~uiao.saas.settings.SaasSettings`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from starlette.responses import JSONResponse, Response

from .audit import AuditSink, build_audit_sink
from .auth import EntraTokenVerifier, SignatureVerifier, jwks_verifier
from .control_plane import router as control_router
from .errors import install_problem_handlers
from .middleware import TenantResolutionMiddleware
from .provisioning import ProvisioningService, StampExecutor
from .ratelimit import TenantRateLimiter
from .repository import TenantRepository, build_repository
from .settings import SaasSettings


def _build_signature_verifier(settings: SaasSettings) -> SignatureVerifier | None:
    """Return a JWKS verifier unless running in insecure (dev/test) mode."""
    if settings.insecure_allow_unsigned_tokens:
        return None
    return jwks_verifier(settings.cloud)


def attach_saas(
    app: FastAPI,
    *,
    settings: SaasSettings | None = None,
    repository: TenantRepository | None = None,
    data_verifier: EntraTokenVerifier | None = None,
    admin_verifier: EntraTokenVerifier | None = None,
    provisioning_service: ProvisioningService | None = None,
    stamp_executor: StampExecutor | None = None,
    rate_limiter: Any = None,
    audit_sink: AuditSink | None = None,
) -> FastAPI:
    """Wire SaaS tenancy + control plane onto ``app`` and return it."""
    settings = settings or SaasSettings()
    repository = repository or build_repository(settings)

    if audit_sink is None:
        # Durable Postgres sink when a database is configured, else in-memory
        # (or null when auditing is disabled). ADR-115.
        audit_sink = build_audit_sink(settings)

    if rate_limiter is None and settings.rate_limiting_enabled:
        if settings.rate_limit_redis_url:
            # Globally-exact limit across replicas via a shared Redis store (ADR-118).
            from .ratelimit import DistributedTenantRateLimiter, RedisWindowStore

            rate_limiter = DistributedTenantRateLimiter(
                RedisWindowStore(settings.rate_limit_redis_url),
                window_seconds=settings.rate_limit_window_seconds,
            )
        else:
            rate_limiter = TenantRateLimiter(window_seconds=settings.rate_limit_window_seconds)

    if data_verifier is None:
        data_verifier = EntraTokenVerifier(
            audience=settings.api_audience,
            cloud=settings.cloud,
            allowed_tenants=settings.allowed_tenants(),
            signature_verifier=_build_signature_verifier(settings),
            insecure_allow_unsigned=settings.insecure_allow_unsigned_tokens,
        )

    if admin_verifier is None:
        publisher = {settings.publisher_tenant_id} if settings.publisher_tenant_id else None
        admin_verifier = EntraTokenVerifier(
            audience=settings.api_audience,
            cloud=settings.cloud,
            allowed_tenants=publisher,
            signature_verifier=_build_signature_verifier(settings),
            insecure_allow_unsigned=settings.insecure_allow_unsigned_tokens,
        )

    # When stamp execution is enabled, build the concrete Azure executor from
    # the configured backing resources (lazy-imports the [saas] Azure deps).
    # Otherwise leave it None → ProvisioningService uses the dry-run executor.
    if stamp_executor is None and settings.stamp_execution_enabled:
        from .azure_provisioners import build_stamp_executor

        stamp_executor = build_stamp_executor(settings)

    if provisioning_service is None:
        provisioning_service = ProvisioningService(
            repository=repository,
            app_client_id=settings.app_client_id,
            cloud=settings.cloud,
            executor=stamp_executor,
            audit=audit_sink,
        )

    # Stash on app.state for routers / dependencies.
    app.state.saas_settings = settings
    app.state.saas_repository = repository
    app.state.saas_data_verifier = data_verifier
    app.state.saas_admin_verifier = admin_verifier
    app.state.saas_provisioning = provisioning_service
    app.state.saas_audit = audit_sink
    app.state.saas_rate_limiter = rate_limiter

    # Uniform RFC 9457 problem+json for control-plane HTTPExceptions.
    install_problem_handlers(app)

    # Tenant-resolution middleware for the data plane.
    app.add_middleware(
        TenantResolutionMiddleware,
        verifier=data_verifier,
        repository=repository,
        public_prefixes=settings.public_prefixes(),
        rate_limiter=rate_limiter,
    )

    # Control plane.
    if settings.provisioning_enabled:
        app.include_router(control_router, prefix="/control/v1", tags=["SaaS Control Plane"])

    # Liveness probe (Container Apps / ECS health probe target).
    if not any(getattr(r, "path", None) == "/healthz" for r in app.routes):

        @app.get("/healthz", tags=["Health"])
        async def _healthz() -> dict[str, str]:  # pragma: no cover - trivial
            return {"status": "ok", "plane": "saas"}

    # Readiness probe — confirms the tenant registry is reachable. Container
    # orchestrators withhold traffic until this returns 200.
    if not any(getattr(r, "path", None) == "/readyz" for r in app.routes):

        @app.get("/readyz", tags=["Health"])
        async def _readyz() -> Response:
            ok = await repository.ping()
            body = {"status": "ready" if ok else "degraded", "registry": "ok" if ok else "unreachable"}
            return JSONResponse(status_code=200 if ok else 503, content=body)

    return app


def build_saas_app(
    *,
    settings: SaasSettings | None = None,
    include_data_plane: bool = True,
    **kwargs: object,
) -> FastAPI:
    """Build a standalone SaaS FastAPI app.

    When ``include_data_plane`` is true the existing ``uiao.api`` routers are
    composed in; otherwise a bare control-plane app is returned (useful for
    running the control plane as its own Container App).
    """
    if include_data_plane:
        from uiao.api.app import app as data_app

        return attach_saas(data_app, settings=settings, **kwargs)  # type: ignore[arg-type]

    app = FastAPI(title="UIAO SaaS Control Plane", version="0.1.0")
    return attach_saas(app, settings=settings, **kwargs)  # type: ignore[arg-type]


__all__ = ["attach_saas", "build_saas_app"]
