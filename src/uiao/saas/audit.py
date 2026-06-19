"""
uiao.saas.audit
--------------
Append-only audit trail for SaaS control-plane lifecycle actions.

Every tenant-lifecycle decision — onboard, suspend, resume, deprovision — is
recorded as an immutable :class:`AuditEvent` against an :class:`AuditSink`.
The trail answers "who changed which tenant, when, and what happened", which
is the evidence a governance substrate is obliged to keep about *itself*.

The default :class:`InMemoryAuditSink` is a bounded ring buffer — dependency-
free, used by tests and single-node dev. A durable Postgres-backed sink is a
drop-in behind the same protocol (future work, ADR-115); the control plane and
provisioning service only ever see :class:`AuditSink`.

Pure stdlib + ``pydantic`` — no ``[saas]`` dependency.
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


__all__ = [
    "AuditAction",
    "AuditOutcome",
    "AuditEvent",
    "AuditSink",
    "InMemoryAuditSink",
    "NullAuditSink",
]
