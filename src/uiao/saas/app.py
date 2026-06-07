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

from fastapi import FastAPI

from .auth import EntraTokenVerifier, SignatureVerifier, jwks_verifier
from .control_plane import router as control_router
from .middleware import TenantResolutionMiddleware
from .provisioning import ProvisioningService, StampExecutor
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
) -> FastAPI:
    """Wire SaaS tenancy + control plane onto ``app`` and return it."""
    settings = settings or SaasSettings()
    repository = repository or build_repository(settings)

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

    if provisioning_service is None:
        provisioning_service = ProvisioningService(
            repository=repository,
            app_client_id=settings.app_client_id,
            cloud=settings.cloud,
            executor=stamp_executor,
        )

    # Stash on app.state for routers / dependencies.
    app.state.saas_settings = settings
    app.state.saas_repository = repository
    app.state.saas_data_verifier = data_verifier
    app.state.saas_admin_verifier = admin_verifier
    app.state.saas_provisioning = provisioning_service

    # Tenant-resolution middleware for the data plane.
    app.add_middleware(
        TenantResolutionMiddleware,
        verifier=data_verifier,
        repository=repository,
        public_prefixes=settings.public_prefixes(),
    )

    # Control plane.
    if settings.provisioning_enabled:
        app.include_router(control_router, prefix="/control/v1", tags=["SaaS Control Plane"])

    # Liveness probe (Container Apps health probe target).
    if not any(getattr(r, "path", None) == "/healthz" for r in app.routes):

        @app.get("/healthz", tags=["Health"])
        async def _healthz() -> dict[str, str]:  # pragma: no cover - trivial
            return {"status": "ok", "plane": "saas"}

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
