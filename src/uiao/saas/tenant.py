"""
uiao.saas.tenant
---------------
The :class:`Tenant` aggregate — a customer Entra tenant onboarded into the
UIAO SaaS — and its lifecycle enums.

A tenant is identified by its Entra ID directory (tenant) GUID. Onboarding
records the consent grant, allocates a data namespace (used to isolate the
tenant's evidence / Postgres rows / Blob prefixes), and tracks the lifecycle
state machine: ``PENDING → ACTIVE → SUSPENDED → ACTIVE`` /
``→ DEPROVISIONED``.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class TenantStatus(str, Enum):
    """Lifecycle state of an onboarded tenant."""

    PENDING = "pending"  # consent recorded, stamp not yet complete
    ACTIVE = "active"  # serving governance traffic
    SUSPENDED = "suspended"  # temporarily disabled (billing / abuse / request)
    DEPROVISIONED = "deprovisioned"  # offboarded; retained for audit


class TenantPlan(str, Enum):
    """Commercial plan — gates quotas and feature flags."""

    TRIAL = "trial"
    STANDARD = "standard"
    ENTERPRISE = "enterprise"
    GOV = "gov"  # GCC-Moderate / sovereign customers


#: Allowed lifecycle transitions. Keys are current states; values are the set
#: of states reachable from them.
_TRANSITIONS: dict[TenantStatus, frozenset[TenantStatus]] = {
    TenantStatus.PENDING: frozenset({TenantStatus.ACTIVE, TenantStatus.DEPROVISIONED}),
    TenantStatus.ACTIVE: frozenset({TenantStatus.SUSPENDED, TenantStatus.DEPROVISIONED}),
    TenantStatus.SUSPENDED: frozenset({TenantStatus.ACTIVE, TenantStatus.DEPROVISIONED}),
    TenantStatus.DEPROVISIONED: frozenset(),  # terminal
}

_GUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_tenant_guid(value: str) -> bool:
    """Return True if ``value`` is a well-formed Entra tenant GUID."""
    return bool(_GUID_RE.match(value or ""))


def derive_namespace(tenant_id: str) -> str:
    """Derive a stable, filesystem/DB-safe data namespace from a tenant GUID."""
    return "t-" + tenant_id.replace("-", "").lower()[:24]


class Tenant(BaseModel):
    """A customer Entra tenant onboarded into the UIAO SaaS."""

    tenant_id: str = Field(description="Entra ID directory (tenant) GUID")
    display_name: str = Field(default="")
    status: TenantStatus = Field(default=TenantStatus.PENDING)
    plan: TenantPlan = Field(default=TenantPlan.TRIAL)
    cloud: str = Field(default="commercial")
    #: Isolation namespace for this tenant's data (DB schema / Blob prefix).
    data_namespace: str = Field(default="")
    #: The admin who initiated onboarding (sub/oid claim), for audit.
    onboarded_by: str = Field(default="")
    suspended_reason: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: object) -> None:  # noqa: D401
        # Auto-allocate the data namespace once at construction if unset.
        if not self.data_namespace and is_tenant_guid(self.tenant_id):
            object.__setattr__(self, "data_namespace", derive_namespace(self.tenant_id))

    @property
    def is_serving(self) -> bool:
        """True when the tenant may receive governance traffic."""
        return self.status is TenantStatus.ACTIVE

    def can_transition_to(self, target: TenantStatus) -> bool:
        """Return True if ``target`` is a legal next state."""
        return target in _TRANSITIONS[self.status]

    def with_status(self, target: TenantStatus, *, reason: str = "") -> Tenant:
        """Return a copy advanced to ``target`` (validates the transition)."""
        if target is self.status:
            return self
        if not self.can_transition_to(target):
            raise ValueError(f"illegal tenant transition {self.status.value} → {target.value}")
        updates: dict[str, object] = {"status": target, "updated_at": _utcnow()}
        if target is TenantStatus.SUSPENDED:
            updates["suspended_reason"] = reason
        elif target is TenantStatus.ACTIVE:
            updates["suspended_reason"] = ""
        return self.model_copy(update=updates)


__all__ = [
    "Tenant",
    "TenantStatus",
    "TenantPlan",
    "is_tenant_guid",
    "derive_namespace",
]
