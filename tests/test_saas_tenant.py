"""Unit tests for the SaaS tenant aggregate and lifecycle state machine."""

from __future__ import annotations

import pytest

from uiao.saas.tenant import (
    Tenant,
    TenantPlan,
    TenantStatus,
    derive_namespace,
    is_tenant_guid,
)

GUID = "12345678-1234-1234-1234-1234567890ab"


def test_guid_validation():
    assert is_tenant_guid(GUID)
    assert not is_tenant_guid("not-a-guid")
    assert not is_tenant_guid("")


def test_namespace_is_stable_and_safe():
    ns = derive_namespace(GUID)
    assert ns.startswith("t-")
    assert "-" not in ns[2:]
    assert ns == derive_namespace(GUID)  # deterministic


def test_namespace_auto_allocated_on_construction():
    t = Tenant(tenant_id=GUID)
    assert t.data_namespace == derive_namespace(GUID)
    assert t.status is TenantStatus.PENDING
    assert t.plan is TenantPlan.TRIAL


def test_legal_transitions():
    t = Tenant(tenant_id=GUID)
    active = t.with_status(TenantStatus.ACTIVE)
    assert active.is_serving
    suspended = active.with_status(TenantStatus.SUSPENDED, reason="billing")
    assert suspended.suspended_reason == "billing"
    resumed = suspended.with_status(TenantStatus.ACTIVE)
    assert resumed.suspended_reason == ""


def test_illegal_transition_rejected():
    t = Tenant(tenant_id=GUID)  # PENDING
    with pytest.raises(ValueError):
        t.with_status(TenantStatus.SUSPENDED)


def test_deprovisioned_is_terminal():
    t = Tenant(tenant_id=GUID).with_status(TenantStatus.ACTIVE).with_status(TenantStatus.DEPROVISIONED)
    assert not t.can_transition_to(TenantStatus.ACTIVE)
    with pytest.raises(ValueError):
        t.with_status(TenantStatus.ACTIVE)


def test_with_status_noop_returns_self():
    t = Tenant(tenant_id=GUID)
    assert t.with_status(TenantStatus.PENDING) is t
