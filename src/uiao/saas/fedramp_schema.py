"""FedRAMP 20x tenant schema extension for the UIAO SaaS plane.

Adds three tables to the existing ``saas_tenants`` schema (ADR-096):

``fedramp_tenant_config``
    Per-tenant FedRAMP baseline selection and MAS scope overrides.  One row
    per tenant.

``fedramp_ksi_evidence``
    Durable store for KSI evidence records (UIAO_133 §2.2).  Partitioned by
    ``tenant_id``.  ``artifact_row`` + ``emitted_at`` determines freshness.

``fedramp_drift_events``
    Persisted DRIFT-EVIDENCE-STALE / DRIFT-SCHEMA / DRIFT-PROVENANCE events.
    Partitioned by ``tenant_id``.  ``remediated_at`` NULL = open event.

All tables follow the existing SQLAlchemy Core pattern from pg_repository.py
(no ORM, no Alembic).  Schema is created via ``create_fedramp_schema(engine)``
called from the SaaS provisioner at tenant onboarding time.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from ..models.fedramp import (
    DriftSeverity,
    FedRampBaseline,
    KsiDriftEvent,
    KsiEvidenceRecord,
)

# ---------------------------------------------------------------------------
# Table definitions
# ---------------------------------------------------------------------------

_metadata = sa.MetaData()

fedramp_tenant_config = sa.Table(
    "fedramp_tenant_config",
    _metadata,
    sa.Column("tenant_id", sa.String(64), primary_key=True),
    sa.Column(
        "fedramp_baseline",
        sa.String(32),
        nullable=False,
        server_default=FedRampBaseline.GCC_MODERATE.value,
    ),
    sa.Column(
        "cr26_snapshot_sha",
        sa.String(64),
        nullable=False,
        server_default="",
    ),
    # JSON blob: {component_path: mas_scope_value}
    sa.Column("mas_scope_overrides_json", sa.Text(), nullable=False, server_default="{}"),
    # JSON blob: last DryRunResult.summary()
    sa.Column("last_dry_run_json", sa.Text(), nullable=False, server_default="{}"),
    sa.Column(
        "last_dry_run_at",
        sa.DateTime(timezone=True),
        nullable=True,
    ),
    sa.Column(
        "adr106_ratified",
        sa.Boolean(),
        nullable=False,
        server_default="false",
    ),
    sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
    ),
    sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
    ),
)

fedramp_ksi_evidence = sa.Table(
    "fedramp_ksi_evidence",
    _metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
    sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
    sa.Column("artifact_uuid", sa.String(64), nullable=False, index=True),
    sa.Column("artifact_row", sa.SmallInteger(), nullable=False),
    sa.Column("oscal_element", sa.String(64), nullable=False),
    sa.Column("responsible_component", sa.String(128), nullable=False),
    # Comma-separated KSI theme values
    sa.Column("ksi_themes", sa.Text(), nullable=False),
    sa.Column("ksi_mapping_source", sa.Text(), nullable=False),
    sa.Column("ksi_freshness_cadence", sa.String(32), nullable=False),
    sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("is_stale", sa.Boolean(), nullable=False, server_default="false"),
    sa.Column("staleness_age_seconds", sa.Float(), nullable=True),
    # Full OSCAL payload
    sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
    sa.UniqueConstraint("tenant_id", "artifact_uuid", name="uq_fedramp_evidence_uuid"),
)

fedramp_drift_events = sa.Table(
    "fedramp_drift_events",
    _metadata,
    sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
    sa.Column("tenant_id", sa.String(64), nullable=False, index=True),
    sa.Column("event_id", sa.String(64), nullable=False, unique=True),
    sa.Column("drift_class", sa.String(64), nullable=False),
    sa.Column("severity", sa.String(4), nullable=False, index=True),
    sa.Column("subject", sa.String(128), nullable=False),
    sa.Column("expected_cadence", sa.String(32), nullable=True),
    sa.Column("actual_age_seconds", sa.Float(), nullable=True),
    # Comma-separated KSI theme values
    sa.Column("ksi_themes", sa.Text(), nullable=False, server_default=""),
    sa.Column("detail", sa.Text(), nullable=False, server_default=""),
    sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("remediated_at", sa.DateTime(timezone=True), nullable=True),
)


# ---------------------------------------------------------------------------
# Schema management
# ---------------------------------------------------------------------------


async def create_fedramp_schema(engine: AsyncEngine) -> None:
    """Create all FedRAMP tables if they do not already exist.

    Safe to call multiple times (``checkfirst=True``).  Called by the SaaS
    provisioner at tenant onboarding.
    """
    async with engine.begin() as conn:
        await conn.run_sync(
            _metadata.create_all,
            checkfirst=True,
        )


# ---------------------------------------------------------------------------
# Repository helpers
# ---------------------------------------------------------------------------


class FedRampTenantRepository:
    """Async CRUD helpers for the FedRAMP tenant tables."""

    def __init__(self, session_maker: async_sessionmaker) -> None:
        self._sm = session_maker

    # ------------------------------------------------------------------
    # Tenant config
    # ------------------------------------------------------------------

    async def upsert_config(
        self,
        tenant_id: str,
        baseline: FedRampBaseline = FedRampBaseline.GCC_MODERATE,
        cr26_snapshot_sha: str = "",
        mas_scope_overrides: dict[str, str] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._sm() as session, session.begin():
            await session.execute(
                sa.dialects.postgresql.insert(fedramp_tenant_config)
                .values(
                    tenant_id=tenant_id,
                    fedramp_baseline=baseline.value,
                    cr26_snapshot_sha=cr26_snapshot_sha,
                    mas_scope_overrides_json=json.dumps(mas_scope_overrides or {}),
                    last_dry_run_json="{}",
                    adr106_ratified=False,
                    created_at=now,
                    updated_at=now,
                )
                .on_conflict_do_update(
                    index_elements=["tenant_id"],
                    set_={
                        "fedramp_baseline": baseline.value,
                        "cr26_snapshot_sha": cr26_snapshot_sha,
                        "mas_scope_overrides_json": json.dumps(mas_scope_overrides or {}),
                        "updated_at": now,
                    },
                )
            )

    async def get_config(self, tenant_id: str) -> dict[str, Any] | None:
        async with self._sm() as session:
            row = await session.execute(
                sa.select(fedramp_tenant_config).where(fedramp_tenant_config.c.tenant_id == tenant_id)
            )
            r = row.one_or_none()
            if r is None:
                return None
            return dict(r._mapping)

    async def record_dry_run(self, tenant_id: str, dry_run_summary: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        async with self._sm() as session, session.begin():
            await session.execute(
                sa.update(fedramp_tenant_config)
                .where(fedramp_tenant_config.c.tenant_id == tenant_id)
                .values(
                    last_dry_run_json=json.dumps(dry_run_summary),
                    last_dry_run_at=now,
                    adr106_ratified=dry_run_summary.get("passed", False),
                    updated_at=now,
                )
            )

    # ------------------------------------------------------------------
    # KSI evidence
    # ------------------------------------------------------------------

    async def upsert_evidence(self, tenant_id: str, record: KsiEvidenceRecord) -> None:
        async with self._sm() as session, session.begin():
            await session.execute(
                sa.dialects.postgresql.insert(fedramp_ksi_evidence)
                .values(
                    tenant_id=tenant_id,
                    artifact_uuid=record.uuid,
                    artifact_row=record.artifact_row,
                    oscal_element=record.oscal_element,
                    responsible_component=record.responsible_component,
                    ksi_themes=",".join(t.value for t in record.emission_props.ksi_themes),
                    ksi_mapping_source=record.emission_props.ksi_mapping_source,
                    ksi_freshness_cadence=record.emission_props.ksi_freshness_cadence.value,
                    emitted_at=record.emission_props.ksi_emitted_at,
                    is_stale=record.is_stale,
                    staleness_age_seconds=record.staleness_age_seconds,
                    payload_json=json.dumps(record.payload),
                )
                .on_conflict_do_update(
                    constraint="uq_fedramp_evidence_uuid",
                    set_={
                        "is_stale": record.is_stale,
                        "staleness_age_seconds": record.staleness_age_seconds,
                        "emitted_at": record.emission_props.ksi_emitted_at,
                        "payload_json": json.dumps(record.payload),
                    },
                )
            )

    async def list_evidence(
        self,
        tenant_id: str,
        stale_only: bool = False,
    ) -> list[dict[str, Any]]:
        async with self._sm() as session:
            q = sa.select(fedramp_ksi_evidence).where(fedramp_ksi_evidence.c.tenant_id == tenant_id)
            if stale_only:
                q = q.where(fedramp_ksi_evidence.c.is_stale.is_(True))
            rows = await session.execute(q)
            return [dict(r._mapping) for r in rows]

    # ------------------------------------------------------------------
    # Drift events
    # ------------------------------------------------------------------

    async def insert_drift_event(self, tenant_id: str, event: KsiDriftEvent) -> None:
        async with self._sm() as session, session.begin():
            await session.execute(
                sa.insert(fedramp_drift_events).values(
                    tenant_id=tenant_id,
                    event_id=event.event_id,
                    drift_class=event.drift_class.value,
                    severity=event.severity.value,
                    subject=event.subject,
                    expected_cadence=(event.expected_cadence.value if event.expected_cadence else None),
                    actual_age_seconds=event.actual_age_seconds,
                    ksi_themes=",".join(t.value for t in event.ksi_themes),
                    detail=event.detail,
                    detected_at=event.detected_at,
                    remediated_at=event.remediated_at,
                )
            )

    async def list_open_drift_events(
        self,
        tenant_id: str,
        min_severity: DriftSeverity | None = None,
    ) -> list[dict[str, Any]]:
        async with self._sm() as session:
            q = sa.select(fedramp_drift_events).where(
                fedramp_drift_events.c.tenant_id == tenant_id,
                fedramp_drift_events.c.remediated_at.is_(None),
            )
            if min_severity:
                severity_filter = {
                    DriftSeverity.P0: ["P0"],
                    DriftSeverity.P1: ["P0", "P1"],
                    DriftSeverity.P2: ["P0", "P1", "P2"],
                }
                q = q.where(fedramp_drift_events.c.severity.in_(severity_filter.get(min_severity, ["P0", "P1", "P2"])))
            rows = await session.execute(q.order_by(fedramp_drift_events.c.detected_at.desc()))
            return [dict(r._mapping) for r in rows]

    async def close_drift_event(self, event_id: str) -> None:
        async with self._sm() as session, session.begin():
            await session.execute(
                sa.update(fedramp_drift_events)
                .where(fedramp_drift_events.c.event_id == event_id)
                .values(remediated_at=datetime.now(timezone.utc))
            )
