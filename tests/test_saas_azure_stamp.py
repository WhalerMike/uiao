"""Unit tests for the AzureStampExecutor state machine.

Uses fake provisioners so no Azure SDK / database is required — the executor's
orchestration + namespace-safety logic is fully covered here; the real
Azure-backed provisioners (uiao.saas.azure_provisioners) are integration-tested
separately.
"""

from __future__ import annotations

import asyncio

import pytest

from uiao.saas.azure_stamp import AzureStampExecutor, NamespaceError, require_safe_namespace
from uiao.saas.tenant import Tenant

GUID = "12345678-1234-1234-1234-1234567890ab"


def _run(coro):
    return asyncio.run(coro)


class FakeProvisioner:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.archived: list[str] = []

    async def create(self, namespace: str) -> None:
        self.created.append(namespace)

    async def archive(self, namespace: str) -> None:
        self.archived.append(namespace)


def _tenant(namespace: str | None = None) -> Tenant:
    if namespace is None:
        return Tenant(tenant_id=GUID)
    return Tenant(tenant_id=GUID, data_namespace=namespace)


# --------------------------------------------------------------------------
# Namespace safety
# --------------------------------------------------------------------------
def test_require_safe_namespace_accepts_derived():
    t = _tenant()
    assert require_safe_namespace(t.data_namespace) == t.data_namespace


@pytest.mark.parametrize("bad", ["", "drop table", "t-UPPER", "x-123", "t-" + "a" * 30, 't-"; --'])
def test_require_safe_namespace_rejects(bad):
    with pytest.raises(NamespaceError):
        require_safe_namespace(bad)


def test_stamp_rejects_unsafe_namespace():
    ex = AzureStampExecutor(schema=FakeProvisioner())
    with pytest.raises(NamespaceError):
        _run(ex.stamp(_tenant("not a namespace")))


# --------------------------------------------------------------------------
# stamp / unstamp orchestration
# --------------------------------------------------------------------------
def test_stamp_all_planes():
    schema, container, secrets = FakeProvisioner(), FakeProvisioner(), FakeProvisioner()
    ex = AzureStampExecutor(schema=schema, container=container, secrets=secrets)
    t = _tenant()
    result = _run(ex.stamp(t))

    assert result.executed is True
    assert [s.action for s in result.steps] == ["create-db-schema", "create-blob-container", "create-keyvault-scope"]
    assert schema.created == [t.data_namespace]
    assert container.created == [t.data_namespace]
    assert secrets.created == [t.data_namespace]
    assert all(not s.detail.startswith("skipped") for s in result.steps)


def test_stamp_partial_planes_marks_skipped():
    schema = FakeProvisioner()
    ex = AzureStampExecutor(schema=schema)  # container + secrets are None
    t = _tenant()
    result = _run(ex.stamp(t))

    assert result.executed is True  # at least the schema ran
    by_action = {s.action: s for s in result.steps}
    assert not by_action["create-db-schema"].detail.startswith("skipped")
    assert by_action["create-blob-container"].detail.startswith("skipped")
    assert by_action["create-keyvault-scope"].detail.startswith("skipped")
    assert schema.created == [t.data_namespace]


def test_stamp_no_planes_is_all_skipped():
    ex = AzureStampExecutor()
    result = _run(ex.stamp(_tenant()))
    assert result.executed is False
    assert all(s.detail.startswith("skipped") for s in result.steps)


def test_unstamp_archives():
    schema, container, secrets = FakeProvisioner(), FakeProvisioner(), FakeProvisioner()
    ex = AzureStampExecutor(schema=schema, container=container, secrets=secrets)
    t = _tenant()
    result = _run(ex.unstamp(t))

    assert result.executed is True
    assert [s.action for s in result.steps] == ["archive-db-schema", "archive-blob-container", "revoke-keyvault-scope"]
    assert schema.archived == [t.data_namespace]
    assert container.archived == [t.data_namespace]
    assert secrets.archived == [t.data_namespace]


def test_executor_is_a_stamp_executor_for_provisioning():
    # Duck-types the StampExecutor protocol used by ProvisioningService.
    from uiao.saas.provisioning import ProvisioningService
    from uiao.saas.repository import InMemoryTenantRepository

    ex = AzureStampExecutor(schema=FakeProvisioner())
    svc = ProvisioningService(repository=InMemoryTenantRepository(), app_client_id="x", executor=ex)
    result = _run(svc.onboard(tenant_id=GUID, display_name="Acme"))
    assert result.tenant.status.value == "active"
    assert any(s.action == "create-db-schema" for s in result.stamp.steps)
