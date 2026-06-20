"""
uiao.saas.pg_audit
-----------------
Durable, Postgres-backed :class:`~uiao.saas.audit.AuditSink` — the drop-in
ADR-115 named as future work behind the audit protocol.

Where :class:`~uiao.saas.audit.InMemoryAuditSink` keeps the control-plane audit
trail in a process-local ring buffer (lost on restart / scale-in), this sink
persists every lifecycle event to an **append-only** ``saas_audit_events``
table, so the substrate's evidence about its own decisions survives the
process. It is gated behind the ``[saas]`` extra (SQLAlchemy async + asyncpg)
and shares the tenant registry's database and passwordless connection posture
via :func:`uiao.saas.pg_repository.build_pg_engine` — so on Azure it
authenticates with an Entra token and on AWS with an RDS IAM token, no DB
password (ADR-116 / ADR-117).

Append-only by construction: the sink only ever ``INSERT``s and ``SELECT``s;
there is no update or delete path.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from .audit import AuditEvent
from .pg_repository import build_pg_engine

_metadata = sa.MetaData()

audit_events_table = sa.Table(
    "saas_audit_events",
    _metadata,
    sa.Column("id", sa.String(64), primary_key=True),
    sa.Column("at", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("action", sa.String(32), nullable=False),
    sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
    sa.Column("actor", sa.String(128), nullable=False, server_default=""),
    sa.Column("outcome", sa.String(16), nullable=False),
    sa.Column("detail", sa.Text(), nullable=False, server_default=""),
)


class PostgresAuditSink:
    """SQLAlchemy-async, append-only audit trail (ADR-115 durable sink)."""

    def __init__(
        self,
        database_url: str,
        *,
        engine: AsyncEngine | None = None,
        use_entra_auth: bool = False,
        entra_user: str = "",
        cloud: str = "commercial",
        use_aws_iam_auth: bool = False,
        aws_region: str = "",
    ) -> None:
        self._engine: AsyncEngine = engine or build_pg_engine(
            database_url,
            use_entra_auth=use_entra_auth,
            entra_user=entra_user,
            cloud=cloud,
            use_aws_iam_auth=use_aws_iam_auth,
            aws_region=aws_region,
        )

    async def create_all(self) -> None:
        """Create the audit table if it does not exist (idempotent)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(_metadata.create_all)

    async def record(self, event: AuditEvent) -> None:
        stmt = sa.insert(audit_events_table).values(
            id=event.id,
            at=event.at,
            action=event.action.value,
            tenant_id=event.tenant_id,
            actor=event.actor,
            outcome=event.outcome.value,
            detail=event.detail,
        )
        async with self._engine.begin() as conn:
            await conn.execute(stmt)

    async def list(self, *, tenant_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        stmt = sa.select(audit_events_table).order_by(audit_events_table.c.at.desc()).limit(max(limit, 0))
        if tenant_id is not None:
            stmt = stmt.where(audit_events_table.c.tenant_id == tenant_id)
        async with self._engine.connect() as conn:
            rows = (await conn.execute(stmt)).all()
        return [
            AuditEvent(
                id=row.id,
                at=row.at,
                action=row.action,
                tenant_id=row.tenant_id,
                actor=row.actor,
                outcome=row.outcome,
                detail=row.detail,
            )
            for row in rows
        ]

    async def dispose(self) -> None:
        await self._engine.dispose()


__all__ = ["PostgresAuditSink", "audit_events_table"]
