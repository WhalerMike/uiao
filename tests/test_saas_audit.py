"""Unit tests for the audit trail and its wiring into the provisioning service."""

from __future__ import annotations

import asyncio
import contextlib

from types import SimpleNamespace

from uiao.saas.audit import (
    AuditAction,
    AuditEvent,
    AuditOutcome,
    InMemoryAuditSink,
    NullAuditSink,
    build_audit_sink,
)
from uiao.saas.provisioning import ProvisioningService
from uiao.saas.repository import InMemoryTenantRepository
from uiao.saas.tenant import TenantPlan

GUID = "12345678-1234-1234-1234-1234567890ab"


def _run(coro):
    return asyncio.run(coro)


# --------------------------------------------------------------------------
# InMemoryAuditSink
# --------------------------------------------------------------------------
def test_sink_records_and_lists_most_recent_first():
    sink = InMemoryAuditSink()
    _run(sink.record(AuditEvent(action=AuditAction.ONBOARD, tenant_id="a")))
    _run(sink.record(AuditEvent(action=AuditAction.SUSPEND, tenant_id="b")))
    events = _run(sink.list())
    assert [e.tenant_id for e in events] == ["b", "a"]  # newest first


def test_sink_filters_by_tenant_and_limit():
    sink = InMemoryAuditSink()
    for _ in range(5):
        _run(sink.record(AuditEvent(action=AuditAction.ONBOARD, tenant_id="a")))
        _run(sink.record(AuditEvent(action=AuditAction.ONBOARD, tenant_id="b")))
    assert len(_run(sink.list(tenant_id="a"))) == 5
    assert len(_run(sink.list(limit=3))) == 3


def test_sink_is_bounded():
    sink = InMemoryAuditSink(maxlen=2)
    for i in range(5):
        _run(sink.record(AuditEvent(action=AuditAction.ONBOARD, tenant_id=str(i))))
    assert len(_run(sink.list(limit=100))) == 2


def test_null_sink_discards():
    sink = NullAuditSink()
    _run(sink.record(AuditEvent(action=AuditAction.ONBOARD, tenant_id="a")))
    assert _run(sink.list()) == []


# --------------------------------------------------------------------------
# ProvisioningService → audit wiring
# --------------------------------------------------------------------------
def _service() -> tuple[ProvisioningService, InMemoryAuditSink]:
    sink = InMemoryAuditSink()
    svc = ProvisioningService(repository=InMemoryTenantRepository(), app_client_id="c", audit=sink)
    return svc, sink


def test_onboard_records_success_event():
    svc, sink = _service()
    _run(svc.onboard(tenant_id=GUID, display_name="Acme", plan=TenantPlan.STANDARD, onboarded_by="admin-1"))
    events = _run(sink.list())
    assert len(events) == 1
    ev = events[0]
    assert ev.action is AuditAction.ONBOARD
    assert ev.tenant_id == GUID
    assert ev.actor == "admin-1"
    assert ev.outcome is AuditOutcome.SUCCESS


def test_duplicate_onboard_records_failure_event():
    svc, sink = _service()
    _run(svc.onboard(tenant_id=GUID, onboarded_by="admin-1"))
    with contextlib.suppress(ValueError):
        _run(svc.onboard(tenant_id=GUID, onboarded_by="admin-2"))
    failures = [e for e in _run(sink.list()) if e.outcome is AuditOutcome.FAILURE]
    assert len(failures) == 1
    assert failures[0].actor == "admin-2"


def test_full_lifecycle_records_each_action():
    svc, sink = _service()
    _run(svc.onboard(tenant_id=GUID, onboarded_by="admin"))
    _run(svc.suspend(GUID, reason="billing", actor="admin"))
    _run(svc.resume(GUID, actor="admin"))
    _run(svc.deprovision(GUID, actor="admin"))
    actions = [e.action for e in reversed(_run(sink.list()))]
    assert actions == [
        AuditAction.ONBOARD,
        AuditAction.SUSPEND,
        AuditAction.RESUME,
        AuditAction.DEPROVISION,
    ]
    suspend = next(e for e in _run(sink.list()) if e.action is AuditAction.SUSPEND)
    assert suspend.detail == "billing"


def test_default_executor_has_null_audit_and_does_not_crash():
    svc = ProvisioningService(repository=InMemoryTenantRepository(), app_client_id="c")
    # No audit sink injected → NullAuditSink; lifecycle still works.
    _run(svc.onboard(tenant_id=GUID, onboarded_by="admin"))
    _run(svc.suspend(GUID, reason="x"))


# --------------------------------------------------------------------------
# build_audit_sink selection (the durable Postgres branch lazy-imports the
# [saas] extra, so only the dependency-free branches are exercised here)
# --------------------------------------------------------------------------
def _settings(**kw) -> SimpleNamespace:
    base = dict(audit_enabled=True, database_url="")
    base.update(kw)
    return SimpleNamespace(**base)


def test_build_audit_sink_disabled_is_null():
    assert isinstance(build_audit_sink(_settings(audit_enabled=False)), NullAuditSink)


def test_build_audit_sink_no_database_is_in_memory():
    assert isinstance(build_audit_sink(_settings()), InMemoryAuditSink)


def test_build_audit_sink_disabled_overrides_database():
    # Disabled wins even when a database URL is present — no durable import.
    sink = build_audit_sink(_settings(audit_enabled=False, database_url="postgresql+asyncpg://x@h/db"))
    assert isinstance(sink, NullAuditSink)
