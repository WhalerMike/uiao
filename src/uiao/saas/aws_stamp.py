"""
uiao.saas.aws_stamp
------------------
Concrete :class:`~uiao.saas.provisioning.StampExecutor` that provisions a
tenant's isolated **AWS** resources (ADR-117) — the AWS analogue of
:class:`uiao.saas.azure_stamp.AzureStampExecutor`.

The three isolation planes map cloud-for-cloud:

================  ======================  ===========================
Plane             Azure (ADR-096)         AWS (ADR-117)
================  ======================  ===========================
tenant state      Postgres schema         Postgres schema (RDS)
evidence bundles  Blob container          S3 key prefix
per-tenant secrets Key Vault scope        Secrets Manager scope
================  ======================  ===========================

The Postgres-schema plane is identical on both clouds, so the executor reuses
the generic :class:`~uiao.saas.azure_stamp.Provisioner` protocol and the
:func:`~uiao.saas.azure_stamp.require_safe_namespace` guard (both are
cloud-neutral despite their module home). The state machine is unit-tested with
fakes — no boto3, no database — exactly like the Azure executor.
"""

from __future__ import annotations

from .azure_stamp import NamespaceError, Provisioner, require_safe_namespace
from .provisioning import StampResult, StampStep
from .tenant import Tenant


class AwsStampExecutor:
    """Provision/deprovision per-tenant AWS resources across three planes.

    Any plane whose provisioner is ``None`` is skipped (its step records
    ``detail="skipped (not configured)"``), so an operator can enable planes
    incrementally — e.g. RDS-schema-only first.
    """

    def __init__(
        self,
        *,
        schema: Provisioner | None = None,
        bucket: Provisioner | None = None,
        secrets: Provisioner | None = None,
    ) -> None:
        self._schema = schema
        self._bucket = bucket
        self._secrets = secrets

    async def stamp(self, tenant: Tenant) -> StampResult:
        ns = require_safe_namespace(tenant.data_namespace)
        steps = [
            await self._run("create-db-schema", ns, self._schema, "Postgres schema for tenant-isolated state"),
            await self._run("create-s3-prefix", ns, self._bucket, "Evidence-bundle S3 key prefix"),
            await self._run("create-secrets-scope", ns, self._secrets, "Per-tenant Secrets Manager scope marker"),
        ]
        executed = any(s.detail and not s.detail.startswith("skipped") for s in steps)
        return StampResult(tenant_id=tenant.tenant_id, executed=executed, steps=steps)

    async def unstamp(self, tenant: Tenant) -> StampResult:
        ns = require_safe_namespace(tenant.data_namespace)
        steps = [
            await self._run("archive-db-schema", ns, self._schema, "Rename tenant schema to archived", archive=True),
            await self._run("archive-s3-prefix", ns, self._bucket, "Revoke + retain evidence", archive=True),
            await self._run("revoke-secrets-scope", ns, self._secrets, "Delete per-tenant secrets", archive=True),
        ]
        executed = any(s.detail and not s.detail.startswith("skipped") for s in steps)
        return StampResult(tenant_id=tenant.tenant_id, executed=executed, steps=steps)

    @staticmethod
    async def _run(
        action: str, ns: str, provisioner: Provisioner | None, detail: str, *, archive: bool = False
    ) -> StampStep:
        if provisioner is None:
            return StampStep(action=action, target=ns, detail="skipped (not configured)")
        if archive:
            await provisioner.archive(ns)
        else:
            await provisioner.create(ns)
        return StampStep(action=action, target=ns, detail=detail)


__all__ = [
    "AwsStampExecutor",
    "Provisioner",
    "NamespaceError",
    "require_safe_namespace",
]
