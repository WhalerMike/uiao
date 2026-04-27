"""Feature flags (UIAO_119 v2, §4.4).

The feature-flag system is the v2 layer on top of the UIAO_119 v1 data
layer (``src/uiao/governance/tenancy.py``). It lets the substrate roll
features out gradually — Dev → Stage canary → Prod canary → Prod
standard → Prod regulated — without committing every callsite to
"this feature is on for everyone".

Conceptually:

- Each feature is named by a dotted identifier (``epl.action.block``,
  ``data-lake.immutable.strict``, etc.).
- Each flag declares the environments / tenant classes / explicit
  tenant ids / explicit actors it is enabled for. Empty sets mean
  "deny by default in this dimension."
- Evaluation takes a :class:`TenantContext` (current request's tenant
  + actor + environment) and an optional resolved :class:`Tenant`
  (gives access to ``tenant_class``).
- Explicit overrides win — the system supports targeted enablement
  for a single tenant id or actor regardless of class / env.

Canon location:
    Reference flags live in ``src/uiao/canon/feature-flags.yaml``.
    Each flag has a ``spec_ref:`` linking to the spec or roadmap
    section that describes it, an ``expires_at:`` date so dead flags
    don't accumulate, and the four enablement dimensions.

Walker hygiene:
    The substrate walker enforces that every active flag has a
    non-empty ``spec_ref:`` (P3 — flags without a documented owner
    rot) and that ``expires_at:`` is a parseable ISO date (P3 —
    expiration matters for cleanup).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml

from uiao.governance.tenancy import (
    Environment,
    Tenant,
    TenantClass,
    TenantContext,
)

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeatureFlag:
    """One canonical feature-flag declaration.

    Evaluation rule (see :meth:`is_enabled`):

    1. Explicit actor or tenant-id overrides — if ``ctx.actor`` is in
       ``enabled_actors`` or ``ctx.tenant_id`` is in
       ``enabled_tenant_ids``, the flag is enabled regardless of
       environment / class checks. Use sparingly — explicit overrides
       are debugging tools, not policy.
    2. Environment gate — ``ctx.environment`` must be in
       ``enabled_environments``. Empty set means "no environments
       enabled by default" (the explicit overrides above are still
       honored).
    3. Tenant-class gate — when a resolved :class:`Tenant` is supplied,
       its ``tenant_class`` must be in ``enabled_tenant_classes``.
       Without a resolved tenant the gate is skipped (the caller
       trusts the environment gate alone).
    """

    name: str
    spec_ref: str = ""
    """Pointer to the spec or roadmap section that defines this flag.
    Walker hygiene rejects flags without one."""
    expires_at: str = ""
    """ISO-8601 date the flag is scheduled to be removed by. Empty
    means "no expiration declared" (walker hygiene flags this)."""
    enabled_environments: frozenset[Environment] = frozenset()
    enabled_tenant_classes: frozenset[TenantClass] = frozenset()
    enabled_tenant_ids: frozenset[str] = frozenset()
    enabled_actors: frozenset[str] = frozenset()

    def is_enabled(
        self,
        ctx: TenantContext,
        tenant: Optional[Tenant] = None,
    ) -> bool:
        # Explicit overrides — actor or tenant id.
        if ctx.actor and ctx.actor in self.enabled_actors:
            return True
        if ctx.tenant_id and ctx.tenant_id in self.enabled_tenant_ids:
            return True
        # Environment gate.
        if ctx.environment not in self.enabled_environments:
            return False
        # Tenant-class gate (only when tenant resolved).
        if tenant is not None:
            return tenant.tenant_class in self.enabled_tenant_classes
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "spec_ref": self.spec_ref,
            "expires_at": self.expires_at,
            "enabled_environments": sorted(e.value for e in self.enabled_environments),
            "enabled_tenant_classes": sorted(c.value for c in self.enabled_tenant_classes),
            "enabled_tenant_ids": sorted(self.enabled_tenant_ids),
            "enabled_actors": sorted(self.enabled_actors),
        }


# ---------------------------------------------------------------------------
# Registry + loader
# ---------------------------------------------------------------------------


@dataclass
class FeatureFlagRegistry:
    """Holds the loaded flags and offers a typed evaluator."""

    flags: dict[str, FeatureFlag] = field(default_factory=dict)

    def get(self, name: str) -> Optional[FeatureFlag]:
        return self.flags.get(name)

    def is_enabled(
        self,
        name: str,
        ctx: TenantContext,
        tenant: Optional[Tenant] = None,
    ) -> bool:
        """Lookup ``name`` and evaluate.

        Missing flags evaluate to ``False`` — a flag check on an
        undeclared flag is a typo or a missed canon update; failing
        closed is the safer default.
        """
        flag = self.flags.get(name)
        if flag is None:
            return False
        return flag.is_enabled(ctx, tenant)


def _coerce_str_set(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()
    if isinstance(value, str):
        s = value.strip()
        return frozenset({s}) if s else frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(v).strip() for v in value if str(v).strip())
    return frozenset()


def _coerce_environment_set(value: Any) -> frozenset[Environment]:
    return frozenset(Environment.parse(v) for v in _coerce_str_set(value))


def _coerce_tenant_class_set(value: Any) -> frozenset[TenantClass]:
    return frozenset(TenantClass.parse(v) for v in _coerce_str_set(value))


def load_flags(paths: Iterable[str | Path]) -> FeatureFlagRegistry:
    """Read ``flags:`` declarations from one or more YAML files.

    Later files override earlier by name. Missing files are silently
    skipped — a deployment with no flag canon evaluates every flag to
    ``False`` (deny by default).
    """
    by_name: dict[str, FeatureFlag] = {}
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
        raw = doc.get("flags") if isinstance(doc, Mapping) else None
        if not isinstance(raw, list):
            continue
        for entry in raw:
            if not isinstance(entry, Mapping):
                continue
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            by_name[name] = FeatureFlag(
                name=name,
                spec_ref=str(entry.get("spec_ref", "")).strip(),
                expires_at=str(entry.get("expires_at", "")).strip(),
                enabled_environments=_coerce_environment_set(entry.get("environments")),
                enabled_tenant_classes=_coerce_tenant_class_set(entry.get("tenant_classes")),
                enabled_tenant_ids=_coerce_str_set(entry.get("tenant_ids")),
                enabled_actors=_coerce_str_set(entry.get("actors")),
            )
    return FeatureFlagRegistry(flags=by_name)


_CANONICAL_FLAG_PATH = "src/uiao/canon/feature-flags.yaml"


def load_canonical_flags(workspace_root: Optional[str | Path] = None) -> FeatureFlagRegistry:
    """Convenience loader pointed at the canonical path.

    ``workspace_root`` defaults to the current working directory when
    omitted (matches the convention used by the EPL + CQL canonical
    loaders).
    """
    base = Path(workspace_root) if workspace_root is not None else Path.cwd()
    return load_flags([base / _CANONICAL_FLAG_PATH])


# ---------------------------------------------------------------------------
# Date / hygiene helpers
# ---------------------------------------------------------------------------


def parse_expiry(value: str) -> Optional[date]:
    """Parse the ``expires_at:`` ISO-8601 date string. Returns
    ``None`` for empty / malformed values."""
    s = (value or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


__all__ = [
    "FeatureFlag",
    "FeatureFlagRegistry",
    "load_canonical_flags",
    "load_flags",
    "parse_expiry",
]
