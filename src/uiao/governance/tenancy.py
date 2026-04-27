"""Multi-tenant isolation (UIAO_112, §3.4) + tenancy strategy (UIAO_119, §4.4).

Production agency deployments host multiple tenants on one substrate
instance. Per UIAO_001 (SSOT) and UIAO_112, the substrate must keep
tenant data, credentials, and audit trails isolated from each other.

This module ships the v1 isolation primitives (UIAO_112) and the v1
tenancy-strategy data layer (UIAO_119):

- :class:`Tenant` — canonical declaration (id, name, credential_scope,
  parent_org, retention overrides, **tenant_class**).
- :class:`TenantClass` — Internal / Canary / Standard / Regulated.
  Drives channel and rollout decisions per UIAO_119.
- :class:`Environment` — Dev / Stage / Prod. Threaded through the
  runtime via :class:`TenantContext`.
- :class:`TenantRegistry` — loaded from
  ``src/uiao/canon/tenants.yaml``; resolves tenants by id, returns the
  default tenant for single-tenant deployments.
- :class:`TenantContext` — runtime context carried through the
  scheduler / journal / archive / API request lifecycle. Carries the
  current :class:`Environment` so downstream consumers can branch on
  Dev / Stage / Prod without re-querying canon.
- :func:`tenant_scoped_path` — helper that turns a base path + tenant
  context into a ``base/<tenant_id>/...`` namespaced path. Used by the
  EnforcementJournal, Data Lake archive, and scheduler-run output.

The module deliberately ships **scoping primitives, not enforcement**.
The journal / archive / scheduler call these helpers; per-tenant
credential delegation (real Vault / Key Vault / SecretsManager binding)
is a follow-up gated on the deployment target.

Substrate-walker hygiene gates:
    Every active tenant declaration MUST carry a non-empty
    ``credential_scope:`` list (UIAO_112). Without it the tenant cannot
    be wired to a credential backend — P2 finding.

    Every tenant declaration that carries a ``tenant_class:`` field
    MUST use one of the four canonical values (UIAO_119). An unknown
    value is a P3 schema-hygiene finding — the runtime falls back to
    ``standard`` but the canon is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml

DEFAULT_TENANT_ID = "default"
"""Sentinel tenant id used when no canon declaration exists.
Single-tenant deployments operate under this id end-to-end."""


# ---------------------------------------------------------------------------
# UIAO_119 — tenancy strategy enums
# ---------------------------------------------------------------------------


class TenantClass(str, Enum):
    """UIAO_119 tenant classes — drive channel + rollout decisions.

    - ``internal``: UIAO's own dev / test / canary tenants. All channels
      (Beta + Stable + LTS / FIPS).
    - ``canary``: early-adopter agencies willing to take Beta and Stable
      channels. First non-internal stage in the rollout pipeline.
    - ``standard``: production agencies on the Stable channel.
    - ``regulated``: regulated agencies on the LTS / FIPS channel
      (e.g., GCC-High customers, FedRAMP High footprint).
    """

    INTERNAL = "internal"
    CANARY = "canary"
    STANDARD = "standard"
    REGULATED = "regulated"

    @classmethod
    def parse(cls, value: Any) -> TenantClass:
        """Coerce a raw string (or None) into a class. Falls back to
        :attr:`STANDARD` for unrecognized / missing values — the
        substrate walker emits a hygiene finding when canon carries an
        unknown class.
        """
        if value is None:
            return cls.STANDARD
        s = str(value).strip().lower()
        for member in cls:
            if member.value == s:
                return member
        return cls.STANDARD


class Environment(str, Enum):
    """UIAO_119 deployment environments.

    - ``dev``: fast iteration, synthetic evidence, no canary tenants.
    - ``stage``: production topology, limited canaries, full HA / CI.
    - ``prod``: all real tenants, certified components only.
    """

    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"

    @classmethod
    def parse(cls, value: Any) -> Environment:
        if value is None:
            return cls.DEV
        s = str(value).strip().lower()
        for member in cls:
            if member.value == s:
                return member
        return cls.DEV


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Tenant:
    """One canonical tenant declaration."""

    id: str
    name: str = ""
    credential_scope: frozenset[str] = frozenset()
    """Names of credential bindings this tenant is allowed to use.
    Resolved at runtime against a credential backend (Key Vault / Vault
    / etc). Empty set is a registry-hygiene violation on an active
    tenant."""
    parent_org: str = ""
    retention_years: int = 0
    """Optional override of the per-adapter retention. 0 means
    "use the adapter default."""
    boundary: str = "GCC-Moderate"
    status: str = "active"
    tenant_class: TenantClass = TenantClass.STANDARD
    """UIAO_119 class — drives channel + rollout decisions. Defaults to
    ``standard`` (most agencies); Internal is the substrate developer's
    own tenants, Canary is early-adopters, Regulated is GCC-High / LTS."""

    @property
    def is_active(self) -> bool:
        return self.status.strip().lower() == "active"

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "credential_scope": sorted(self.credential_scope),
            "parent_org": self.parent_org,
            "retention_years": self.retention_years,
            "boundary": self.boundary,
            "status": self.status,
            "tenant_class": self.tenant_class.value,
        }


@dataclass(frozen=True)
class TenantContext:
    """Runtime context carried through scheduler / journal / archive.

    Populated by the API or CLI entrypoint from the request principal,
    then propagated. The scheduler / journal / archive helpers consult
    :attr:`tenant_id` to decide which subdirectory / namespace to use.

    UIAO_119 extends this with :attr:`environment` so downstream
    consumers (feature-flag evaluator, journal record builder,
    migration sandbox) can branch on Dev / Stage / Prod without
    re-querying canon. The default is :attr:`Environment.DEV` so a
    fresh substrate runs developer-mode unless explicitly promoted.
    """

    tenant_id: str = DEFAULT_TENANT_ID
    actor: str = ""
    """Free-form actor identifier — Entra OID, service principal name,
    automation pipeline, etc."""
    environment: Environment = Environment.DEV
    """UIAO_119 deployment environment carried through the request /
    dispatch lifecycle."""

    @classmethod
    def default(cls) -> TenantContext:
        return cls(tenant_id=DEFAULT_TENANT_ID, actor="system")

    def as_tag_dict(self, tenant: Optional[Tenant] = None) -> dict[str, str]:
        """Tagging payload for journal records, log lines, and OSCAL
        back-matter resources.

        Always carries ``tenant_id``, ``actor``, and ``environment``;
        adds ``tenant_class`` when the caller passes the resolved
        :class:`Tenant`. Downstream consumers (EnforcementJournal,
        ArchiveEntry.extra) merge this dict into their record-level
        metadata so a query for "all PROD records for tenant X under
        actor Y" works with a single filter.
        """
        out: dict[str, str] = {
            "tenant_id": self.tenant_id,
            "actor": self.actor,
            "environment": self.environment.value,
        }
        if tenant is not None:
            out["tenant_class"] = tenant.tenant_class.value
        return out


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


@dataclass
class TenantRegistry:
    """Holds the loaded tenant declarations."""

    tenants: dict[str, Tenant] = field(default_factory=dict)

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self.tenants.get(tenant_id)

    def require(self, tenant_id: str) -> Tenant:
        """Return the tenant or raise KeyError. Single-tenant deployments
        synthesize the default tenant when no canon file is present."""
        if tenant_id == DEFAULT_TENANT_ID and tenant_id not in self.tenants:
            return Tenant(
                id=DEFAULT_TENANT_ID,
                name="Default tenant (single-tenant deployment)",
                credential_scope=frozenset({"default"}),
                parent_org="",
                status="active",
            )
        if tenant_id not in self.tenants:
            raise KeyError(f"unknown tenant '{tenant_id}'")
        return self.tenants[tenant_id]

    def active(self) -> list[Tenant]:
        return [t for t in self.tenants.values() if t.is_active]


def _coerce_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        s = value.strip()
        return frozenset({s}) if s else frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(v).strip() for v in value if str(v).strip())
    return frozenset()


def load_tenants(paths: Iterable[str | Path]) -> TenantRegistry:
    """Read ``tenants:`` declarations from one or more YAML files.

    Later files override earlier by id. Missing files are silently
    skipped — a deployment with no tenant canon still works under the
    synthetic default tenant.
    """
    by_id: dict[str, Tenant] = {}
    for path in paths:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not doc:
            continue
        raw_tenants = doc.get("tenants") if isinstance(doc, Mapping) else None
        if not isinstance(raw_tenants, list):
            continue
        for entry in raw_tenants:
            if not isinstance(entry, Mapping):
                continue
            tid = str(entry.get("id", "")).strip()
            if not tid:
                continue
            try:
                ry = int(entry.get("retention_years", 0) or 0)
            except (TypeError, ValueError):
                ry = 0
            by_id[tid] = Tenant(
                id=tid,
                name=str(entry.get("name", "")).strip(),
                credential_scope=_coerce_set(entry.get("credential_scope")),
                parent_org=str(entry.get("parent_org", "")).strip(),
                retention_years=max(0, ry),
                boundary=str(entry.get("boundary", "GCC-Moderate")).strip(),
                status=str(entry.get("status", "active")).strip(),
                tenant_class=TenantClass.parse(entry.get("tenant_class")),
            )
    return TenantRegistry(tenants=by_id)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def tenant_scoped_path(base: str | Path, ctx: Optional[TenantContext]) -> Path:
    """Return ``base/<tenant_id>`` so journal / archive / scheduler runs
    land under a per-tenant subtree.

    A ``None`` context (or the default tenant on a single-tenant
    deployment) returns ``base/default``. The convention keeps even
    single-tenant deployments multi-tenant-ready: when a second tenant
    is later added, no path migration is required.
    """
    tenant_id = (ctx.tenant_id if ctx else DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID
    return Path(base) / tenant_id


def assert_tenant_match(
    expected: Optional[TenantContext],
    actual: Optional[TenantContext],
) -> None:
    """Raise :class:`PermissionError` when contexts disagree.

    Caller (scheduler / journal / API request) supplies the current
    request's tenant; the resource (an EnforcementAction, ArchiveEntry,
    etc.) supplies the tenant it was originally written under. Mismatch
    is a substrate-isolation violation.
    """
    expected_id = (expected.tenant_id if expected else DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID
    actual_id = (actual.tenant_id if actual else DEFAULT_TENANT_ID) or DEFAULT_TENANT_ID
    if expected_id != actual_id:
        raise PermissionError(f"tenant mismatch: caller='{expected_id}' resource='{actual_id}'")


__all__ = [
    "DEFAULT_TENANT_ID",
    "Environment",
    "Tenant",
    "TenantClass",
    "TenantContext",
    "TenantRegistry",
    "assert_tenant_match",
    "load_tenants",
    "tenant_scoped_path",
]
