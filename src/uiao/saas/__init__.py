"""
uiao.saas — Azure SaaS control plane + multi-tenant data-plane runtime
=====================================================================

This subpackage turns the single-tenant ``uiao.api`` FastAPI service into a
multi-tenant SaaS that runs on **Azure Container Apps** (ADR-096). It is the
"behind-the-scenes" governance plane: each customer Entra tenant grants
admin consent to the UIAO multi-tenant app registration, and UIAO acquires
per-tenant Microsoft Graph / ARM tokens to run governance passes on their
behalf.

Design constraints
------------------
* **Dependency isolation.** The blocking CI test job installs only
  ``.[api]``. Everything importable from this package's top level depends
  *only* on the standard library, ``pydantic`` (core dep), and
  ``fastapi``/``starlette`` (the ``[api]`` extra). The Postgres-backed
  repository and the Azure SDK integrations are isolated in
  :mod:`uiao.saas.pg_repository` and lazy-imported, so importing this
  package never requires the ``[saas]`` extra. This mirrors how
  ``uiao.api`` is gated behind ``[api]``.
* **Dry-run by default.** Provisioning plans Azure resource stamps but does
  not execute them until a concrete ``StampExecutor`` is injected — the same
  transport-free doctrine the OrgPath runtime follows.
* **Read-through tenancy.** Inbound requests carry an Entra ID bearer token;
  :class:`~uiao.saas.middleware.TenantResolutionMiddleware` resolves the
  ``tid`` claim to a registered :class:`~uiao.saas.tenant.Tenant` and binds
  it to the request context for the duration of the request.

Public surface
--------------
``attach_saas(app, …)`` augments any FastAPI app (typically the existing
``uiao.api.app:app`` data plane) with the tenant-resolution middleware and
the control-plane router. The container entrypoint is
``uiao.saas.asgi:app``.
"""

from __future__ import annotations

from .audit import AuditAction, AuditEvent, AuditSink, InMemoryAuditSink
from .context import (
    TenantContext,
    clear_current_tenant,
    get_current_tenant,
    require_current_tenant,
    set_current_tenant,
)
from .quotas import DEFAULT_QUOTAS, PlanQuota, quota_for
from .ratelimit import (
    DistributedTenantRateLimiter,
    InMemoryWindowStore,
    RateLimitDecision,
    RedisWindowStore,
    TenantRateLimiter,
    WindowStore,
)
from .repository import InMemoryTenantRepository, TenantRepository
from .settings import SaasSettings
from .tenant import Tenant, TenantPlan, TenantStatus

__all__ = [
    "SaasSettings",
    "Tenant",
    "TenantPlan",
    "TenantStatus",
    "TenantContext",
    "TenantRepository",
    "InMemoryTenantRepository",
    "PlanQuota",
    "DEFAULT_QUOTAS",
    "quota_for",
    "RateLimitDecision",
    "TenantRateLimiter",
    "DistributedTenantRateLimiter",
    "WindowStore",
    "InMemoryWindowStore",
    "RedisWindowStore",
    "AuditAction",
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "get_current_tenant",
    "require_current_tenant",
    "set_current_tenant",
    "clear_current_tenant",
    "attach_saas",
]


def attach_saas(app, **kwargs):  # type: ignore[no-untyped-def]
    """Attach the SaaS control plane + tenant middleware to a FastAPI app.

    Thin re-export of :func:`uiao.saas.app.attach_saas`. Imported lazily so
    that ``import uiao.saas`` does not pull in FastAPI unless the caller
    actually wires up an app.
    """
    from .app import attach_saas as _attach

    return _attach(app, **kwargs)
