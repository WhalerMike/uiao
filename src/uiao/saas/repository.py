"""
uiao.saas.repository
-------------------
The tenant registry abstraction and its in-memory implementation.

:class:`TenantRepository` is the persistence boundary for the SaaS control
plane. The async, dependency-free :class:`InMemoryTenantRepository` is used
by tests and single-node dev runs; the durable, Postgres-backed
implementation lives in :mod:`uiao.saas.pg_repository` (behind the ``[saas]``
extra) and is only imported when ``UIAO_SAAS_DATABASE_URL`` is set.
"""

from __future__ import annotations

import abc
import asyncio

from .tenant import Tenant, TenantStatus


class TenantNotFoundError(LookupError):
    """Raised when a tenant GUID has no registered record."""


class TenantRepository(abc.ABC):
    """Async persistence boundary for :class:`~uiao.saas.tenant.Tenant`."""

    @abc.abstractmethod
    async def get(self, tenant_id: str) -> Tenant | None:
        """Return the tenant, or ``None`` if not registered."""

    @abc.abstractmethod
    async def list(self) -> list[Tenant]:
        """Return all registered tenants."""

    @abc.abstractmethod
    async def upsert(self, tenant: Tenant) -> Tenant:
        """Insert or replace ``tenant``; returns the stored record."""

    @abc.abstractmethod
    async def delete(self, tenant_id: str) -> None:
        """Remove a tenant record (hard delete; use deprovision for soft)."""

    async def ping(self) -> bool:
        """Return True if the backing store is reachable (readiness probe).

        The default implementation exercises a cheap read; durable backends
        override it with a lightweight connectivity check.
        """
        try:
            await self.list()
        except Exception:  # pragma: no cover - defensive; durable stores override
            return False
        return True

    async def require(self, tenant_id: str) -> Tenant:
        """Return the tenant or raise :class:`TenantNotFoundError`."""
        tenant = await self.get(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(tenant_id)
        return tenant

    async def set_status(self, tenant_id: str, status: TenantStatus, *, reason: str = "") -> Tenant:
        """Advance a tenant's lifecycle state, validating the transition."""
        tenant = await self.require(tenant_id)
        updated = tenant.with_status(status, reason=reason)
        return await self.upsert(updated)


class InMemoryTenantRepository(TenantRepository):
    """Dict-backed registry. Not durable — for tests and dev only."""

    def __init__(self, tenants: list[Tenant] | None = None) -> None:
        self._tenants: dict[str, Tenant] = {t.tenant_id: t for t in (tenants or [])}
        self._lock = asyncio.Lock()

    async def get(self, tenant_id: str) -> Tenant | None:
        async with self._lock:
            return self._tenants.get(tenant_id)

    async def list(self) -> list[Tenant]:
        async with self._lock:
            return list(self._tenants.values())

    async def upsert(self, tenant: Tenant) -> Tenant:
        async with self._lock:
            self._tenants[tenant.tenant_id] = tenant
            return tenant

    async def delete(self, tenant_id: str) -> None:
        async with self._lock:
            self._tenants.pop(tenant_id, None)


def build_repository(settings) -> TenantRepository:  # type: ignore[no-untyped-def]
    """Return a repository appropriate to ``settings``.

    Falls back to the in-memory registry when no database URL is configured.
    The Postgres repository is lazy-imported so the ``[saas]`` extra is only
    required when a durable store is actually requested.
    """
    if getattr(settings, "database_url", "").strip():
        from .pg_repository import PostgresTenantRepository

        return PostgresTenantRepository(settings.database_url)
    return InMemoryTenantRepository()


__all__ = [
    "TenantRepository",
    "InMemoryTenantRepository",
    "TenantNotFoundError",
    "build_repository",
]
