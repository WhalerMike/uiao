"""Unit tests for the in-memory tenant repository."""

from __future__ import annotations

import asyncio

import pytest

from uiao.saas.repository import InMemoryTenantRepository, TenantNotFoundError
from uiao.saas.tenant import Tenant, TenantStatus

GUID = "12345678-1234-1234-1234-1234567890ab"


def _run(coro):
    return asyncio.run(coro)


def test_upsert_and_get():
    repo = InMemoryTenantRepository()
    t = Tenant(tenant_id=GUID, display_name="Acme")
    _run(repo.upsert(t))
    fetched = _run(repo.get(GUID))
    assert fetched is not None
    assert fetched.display_name == "Acme"


def test_get_missing_returns_none():
    repo = InMemoryTenantRepository()
    assert _run(repo.get(GUID)) is None


def test_require_missing_raises():
    repo = InMemoryTenantRepository()
    with pytest.raises(TenantNotFoundError):
        _run(repo.require(GUID))


def test_list_and_delete():
    repo = InMemoryTenantRepository([Tenant(tenant_id=GUID)])
    assert len(_run(repo.list())) == 1
    _run(repo.delete(GUID))
    assert _run(repo.list()) == []


def test_set_status_validates_transition():
    repo = InMemoryTenantRepository([Tenant(tenant_id=GUID)])  # PENDING
    updated = _run(repo.set_status(GUID, TenantStatus.ACTIVE))
    assert updated.status is TenantStatus.ACTIVE
    with pytest.raises(ValueError):
        # ACTIVE -> PENDING is illegal
        _run(repo.set_status(GUID, TenantStatus.PENDING))
