"""
uiao.saas.audit
--------------
Append-only audit trail for SaaS control-plane lifecycle actions.

Every tenant-lifecycle decision — onboard, suspend, resume, deprovision — is
recorded as an immutable :class:`AuditEvent` against an :class:`AuditSink`.
The trail answers "who changed which tenant, when, and what happened", which
is the evidence a governance substrate is obliged to keep about *itself*.

The default :class:`InMemoryAuditSink` is a bounded ring buffer — dependency-
free, used by tests and single-node dev. A durable, append-only Postgres sink
(:class:`uiao.saas.pg_audit.PostgresAuditSink`) is a drop-in behind the same
protocol, selected by :func:`build_audit_sink` when a database is configured;
the control plane and provisioning service only ever see :class:`AuditSink`.

This module is pure stdlib + ``pydantic`` — no ``[saas]`` dependency. The
Postgres sink is lazy-imported by :func:`build_audit_sink`, so importing this
module never requires SQLAlchemy.
"""

from __future__ import annotations

import uuid
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """The control-plane lifecycle actions worth auditing."""

    ONBOARD = "onboard"
    SUSPEND = "suspend"
    RESUME = "resume"
    DEPROVISION = "deprovision"


class AuditOutcome(str, Enum):
    """Whether the audited action succeeded or was rejected."""

    SUCCESS = "success"
    FAILURE = "failure"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditEvent(BaseModel):
    """One immutable entry in the SaaS control-plane audit trail."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    at: datetime = Field(default_factory=_utcnow)
    action: AuditAction
    tenant_id: str
    #: ``sub``/``oid`` of the publisher-tenant admin who performed the action.
    actor: str = Field(default="")
    outcome: AuditOutcome = Field(default=AuditOutcome.SUCCESS)
    #: Human-readable context (suspension reason, error message, etc.).
    detail: str = Field(default="")


class AuditSink(Protocol):
    """Persistence boundary for the audit trail."""

    async def record(self, event: AuditEvent) -> None: ...

    async def list(self, *, tenant_id: str | None = None, limit: int = 100) -> list[AuditEvent]: ...


class InMemoryAuditSink:
    """Bounded in-memory ring buffer. Not durable — tests and dev only."""

    def __init__(self, *, maxlen: int = 10_000) -> None:
        self._events: deque[AuditEvent] = deque(maxlen=maxlen)

    async def record(self, event: AuditEvent) -> None:
        self._events.append(event)

    async def list(self, *, tenant_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        # Most-recent-first; optionally scoped to one tenant.
        events = [e for e in reversed(self._events) if tenant_id is None or e.tenant_id == tenant_id]
        return events[: max(limit, 0)]


class NullAuditSink:
    """Discards every event — used when auditing is disabled."""

    async def record(self, event: AuditEvent) -> None:  # noqa: D401 - no-op
        return None

    async def list(self, *, tenant_id: str | None = None, limit: int = 100) -> list[AuditEvent]:
        return []


def build_audit_sink(settings) -> AuditSink:  # type: ignore[no-untyped-def]
    """Return the audit sink appropriate to ``settings``.

    * auditing disabled → :class:`NullAuditSink`
    * a database is configured → durable :class:`~uiao.saas.pg_audit.PostgresAuditSink`
      (lazy-imported; the ``[saas]`` extra)
    * otherwise → the in-memory ring buffer

    Mirrors :func:`uiao.saas.repository.build_repository`: the Postgres sink is
    only imported when a durable store is actually requested, so this stays
    importable without SQLAlchemy.
    """
    if not getattr(settings, "audit_enabled", True):
        return NullAuditSink()

    if getattr(settings, "database_url", "").strip():
        from .pg_audit import PostgresAuditSink

        return PostgresAuditSink(
            settings.database_url,
            use_entra_auth=bool(getattr(settings, "database_use_entra_auth", False)),
            entra_user=getattr(settings, "database_entra_user", ""),
            cloud=getattr(settings, "cloud", "commercial"),
            use_aws_iam_auth=bool(getattr(settings, "database_use_aws_iam_auth", False)),
            aws_region=getattr(settings, "aws_region", ""),
        )

    return InMemoryAuditSink()


__all__ = [
    "AuditAction",
    "AuditOutcome",
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "NullAuditSink",
    "build_audit_sink",
]
