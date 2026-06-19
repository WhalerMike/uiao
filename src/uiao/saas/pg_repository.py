"""
uiao.saas.pg_repository
---------------------
Durable, Postgres-backed :class:`~uiao.saas.repository.TenantRepository`.

Gated behind the ``[saas]`` extra (SQLAlchemy async + asyncpg). It is only
imported by :func:`uiao.saas.repository.build_repository` when
``UIAO_SAAS_DATABASE_URL`` is configured, so the rest of the package — and
the blocking CI test job, which installs only ``.[api]`` — never needs these
dependencies.

The tenant registry is a single table keyed by the Entra tenant GUID. The
``data_namespace`` column is the isolation handle per-tenant evidence rows /
Blob prefixes hang off of (ADR-096 §"Data isolation").
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from .repository import TenantRepository
from .tenant import Tenant, TenantPlan, TenantStatus

_metadata = sa.MetaData()

tenants_table = sa.Table(
    "saas_tenants",
    _metadata,
    sa.Column("tenant_id", sa.String(64), primary_key=True),
    sa.Column("display_name", sa.String(256), nullable=False, server_default=""),
    sa.Column("status", sa.String(32), nullable=False),
    sa.Column("plan", sa.String(32), nullable=False),
    sa.Column("cloud", sa.String(32), nullable=False, server_default="commercial"),
    sa.Column("data_namespace", sa.String(64), nullable=False),
    sa.Column("onboarded_by", sa.String(128), nullable=False, server_default=""),
    sa.Column("suspended_reason", sa.Text(), nullable=False, server_default=""),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"),
)


def _row_to_tenant(row: Any) -> Tenant:
    return Tenant(
        tenant_id=row.tenant_id,
        display_name=row.display_name,
        status=TenantStatus(row.status),
        plan=TenantPlan(row.plan),
        cloud=row.cloud,
        data_namespace=row.data_namespace,
        onboarded_by=row.onboarded_by,
        suspended_reason=row.suspended_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
        metadata=json.loads(row.metadata_json or "{}"),
    )


def _tenant_to_values(tenant: Tenant) -> dict[str, Any]:
    def _aware(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    return {
        "tenant_id": tenant.tenant_id,
        "display_name": tenant.display_name,
        "status": tenant.status.value,
        "plan": tenant.plan.value,
        "cloud": tenant.cloud,
        "data_namespace": tenant.data_namespace,
        "onboarded_by": tenant.onboarded_by,
        "suspended_reason": tenant.suspended_reason,
        "created_at": _aware(tenant.created_at),
        "updated_at": _aware(tenant.updated_at),
        "metadata_json": json.dumps(tenant.metadata),
    }


class PostgresTenantRepository(TenantRepository):
    """SQLAlchemy-async implementation of the tenant registry."""

    def __init__(self, database_url: str, *, engine: AsyncEngine | None = None) -> None:
        self._engine: AsyncEngine = engine or create_async_engine(database_url, pool_pre_ping=True)
        self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_all(self) -> None:
        """Create the registry table if it does not exist (idempotent)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(_metadata.create_all)

    async def get(self, tenant_id: str) -> Tenant | None:
        async with self._engine.connect() as conn:
            result = await conn.execute(sa.select(tenants_table).where(tenants_table.c.tenant_id == tenant_id))
            row = result.first()
            return _row_to_tenant(row) if row is not None else None

    async def list(self) -> list[Tenant]:
        async with self._engine.connect() as conn:
            result = await conn.execute(sa.select(tenants_table).order_by(tenants_table.c.created_at))
            return [_row_to_tenant(row) for row in result.all()]

    async def upsert(self, tenant: Tenant) -> Tenant:
        values = _tenant_to_values(tenant)
        stmt = pg_insert(tenants_table).values(**values)
        update_cols = {c: stmt.excluded[c] for c in values if c != "tenant_id"}
        stmt = stmt.on_conflict_do_update(index_elements=["tenant_id"], set_=update_cols)
        async with self._engine.begin() as conn:
            await conn.execute(stmt)
        return tenant

    async def delete(self, tenant_id: str) -> None:
        async with self._engine.begin() as conn:
            await conn.execute(sa.delete(tenants_table).where(tenants_table.c.tenant_id == tenant_id))

    async def ping(self) -> bool:
        """Cheap ``SELECT 1`` connectivity check for the readiness probe."""
        try:
            async with self._engine.connect() as conn:
                await conn.execute(sa.text("SELECT 1"))
        except Exception:
            return False
        return True

    async def dispose(self) -> None:
        await self._engine.dispose()


__all__ = ["PostgresTenantRepository", "tenants_table"]
