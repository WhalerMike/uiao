"""Unit tests for the AwsStampExecutor state machine.

Uses fake provisioners so no boto3 / database is required — the executor's
orchestration + namespace-safety logic is fully covered here; the real
AWS-backed provisioners (uiao.saas.aws_provisioners) are integration-tested
separately. Mirrors test_saas_azure_stamp.
"""

from __future__ import annotations

import asyncio

import pytest

from uiao.saas.aws_stamp import AwsStampExecutor, NamespaceError, require_safe_namespace
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
# Namespace safety (shared guard)
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad", ["", "drop table", "t-UPPER", "x-123", "t-" + "a" * 30, 't-"; --'])
def test_guard_rejects_unsafe(bad):
    with pytest.raises(NamespaceError):
        require_safe_namespace(bad)


@pytest.mark.parametrize("bad", ["drop table", "t-UPPER", 't-"; --'])
def test_stamp_rejects_unsafe_namespace(bad):
    # A non-empty unsafe namespace reaches the guard via stamp() (an empty one
    # would be re-derived to a safe value by Tenant, so it is covered above).
    ex = AwsStampExecutor(schema=FakeProvisioner())
    with pytest.raises(NamespaceError):
        _run(ex.stamp(_tenant(bad)))


# --------------------------------------------------------------------------
# stamp / unstamp orchestration
# --------------------------------------------------------------------------
def test_stamp_runs_all_configured_planes():
    schema, bucket, secrets = FakeProvisioner(), FakeProvisioner(), FakeProvisioner()
    ex = AwsStampExecutor(schema=schema, bucket=bucket, secrets=secrets)
    t = _tenant()
    result = _run(ex.stamp(t))

    assert result.executed is True
    assert [s.action for s in result.steps] == ["create-db-schema", "create-s3-prefix", "create-secrets-scope"]
    assert schema.created == bucket.created == secrets.created == [t.data_namespace]
    assert all(not s.detail.startswith("skipped") for s in result.steps)


def test_unstamp_archives_all_planes():
    schema, bucket, secrets = FakeProvisioner(), FakeProvisioner(), FakeProvisioner()
    ex = AwsStampExecutor(schema=schema, bucket=bucket, secrets=secrets)
    t = _tenant()
    result = _run(ex.unstamp(t))

    assert [s.action for s in result.steps] == ["archive-db-schema", "archive-s3-prefix", "revoke-secrets-scope"]
    assert schema.archived == bucket.archived == secrets.archived == [t.data_namespace]


def test_unconfigured_planes_are_skipped_not_failed():
    schema = FakeProvisioner()
    ex = AwsStampExecutor(schema=schema)  # bucket + secrets are None
    result = _run(ex.stamp(_tenant()))

    by_action = {s.action: s for s in result.steps}
    assert by_action["create-db-schema"].detail.startswith("Postgres schema")
    assert by_action["create-s3-prefix"].detail == "skipped (not configured)"
    assert by_action["create-secrets-scope"].detail == "skipped (not configured)"
    assert result.executed is True  # at least one plane ran


def test_fully_unconfigured_executor_reports_not_executed():
    ex = AwsStampExecutor()
    result = _run(ex.stamp(_tenant()))
    assert result.executed is False
    assert all(s.detail == "skipped (not configured)" for s in result.steps)


def test_namespace_guard_accepts_derived():
    t = _tenant()
    assert require_safe_namespace(t.data_namespace) == t.data_namespace
