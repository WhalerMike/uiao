"""
uiao.saas.azure_stamp
--------------------
Concrete :class:`~uiao.saas.provisioning.StampExecutor` that provisions a
tenant's isolated Azure resources (ADR-096):

* **Postgres schema** named after the tenant's ``data_namespace`` — the
  row/schema scope its evidence + state live in.
* **Blob container** named after the namespace — the tenant-scoped
  evidence-bundle prefix.
* **Key Vault secret scope** — a marker secret establishing the per-tenant
  secret namespace (per-tenant client secrets / certs are stored under it).

Design
------
The executor composes three small **provisioner** objects, one per plane.
Each is a narrow async protocol so the executor can be unit-tested with fakes
(no Azure SDK, no database) — the blocking CI test job (``.[api]`` only) runs
the full state machine against in-memory fakes. The real Azure-backed
implementations lazy-import ``sqlalchemy`` / the Azure SDKs (the ``[saas]``
extra) and are only constructed when a provisioner is not injected.

Safety
------
The namespace is validated against a strict pattern before it is ever
interpolated into SQL or a resource name, so a malformed tenant id cannot
become an injection vector. Construction is dry-run-friendly: a provisioner
left as ``None`` records a *skipped* step rather than failing.
"""

from __future__ import annotations

import re
from typing import Protocol

from .provisioning import StampResult, StampStep
from .tenant import Tenant

# A data namespace is ``t-`` + up to 24 lowercase hex chars (see
# uiao.saas.tenant.derive_namespace). Anything else is rejected before use.
_NAMESPACE_RE = re.compile(r"^t-[a-z0-9]{1,24}$")


class NamespaceError(ValueError):
    """Raised when a tenant's data namespace is not safe to provision."""


def require_safe_namespace(namespace: str) -> str:
    """Return ``namespace`` if it is provisioning-safe, else raise."""
    if not _NAMESPACE_RE.match(namespace or ""):
        raise NamespaceError(f"unsafe data namespace {namespace!r} — expected pattern {_NAMESPACE_RE.pattern}")
    return namespace


class Provisioner(Protocol):
    """One plane's create/archive operations for a tenant namespace."""

    async def create(self, namespace: str) -> None: ...

    async def archive(self, namespace: str) -> None: ...


class AzureStampExecutor:
    """Provision/deprovision per-tenant Azure resources across three planes.

    Any plane whose provisioner is ``None`` is skipped (its step is recorded
    with ``detail="skipped (not configured)"``). This lets an operator enable
    planes incrementally — e.g. Postgres-only first.
    """

    def __init__(
        self,
        *,
        schema: Provisioner | None = None,
        container: Provisioner | None = None,
        secrets: Provisioner | None = None,
    ) -> None:
        self._schema = schema
        self._container = container
        self._secrets = secrets

    async def stamp(self, tenant: Tenant) -> StampResult:
        ns = require_safe_namespace(tenant.data_namespace)
        steps = [
            await self._run("create-db-schema", ns, self._schema, "Postgres schema for tenant-isolated state"),
            await self._run("create-blob-container", ns, self._container, "Evidence-bundle storage container"),
            await self._run("create-keyvault-scope", ns, self._secrets, "Per-tenant secret scope marker"),
        ]
        executed = any(s.detail and not s.detail.startswith("skipped") for s in steps)
        return StampResult(tenant_id=tenant.tenant_id, executed=executed, steps=steps)

    async def unstamp(self, tenant: Tenant) -> StampResult:
        ns = require_safe_namespace(tenant.data_namespace)
        steps = [
            await self._run("archive-db-schema", ns, self._schema, "Rename tenant schema to archived", archive=True),
            await self._run("archive-blob-container", ns, self._container, "Revoke + retain evidence", archive=True),
            await self._run("revoke-keyvault-scope", ns, self._secrets, "Delete per-tenant secrets", archive=True),
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
    "AzureStampExecutor",
    "Provisioner",
    "NamespaceError",
    "require_safe_namespace",
]
