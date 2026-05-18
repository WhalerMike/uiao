"""
src/uiao/identity/canonical_functions.py
----------------------------------------
Canonical Function Library per UIAO_180.

Fifteen primitives that the deterministic provisioner (UIAO_178) and
operator tooling call to mutate Entra and Azure state. Each function:

  - accepts a typed `*Spec` (or canonical ID),
  - is idempotent on the supplied desired-state payload,
  - returns a structured `*Result` carrying `outcome`, `delta`, and any
    `DriftRecord`s observed while reconciling,
  - delegates all I/O to a `DatabaseAdapterBase` instance (the
    `get_state / set_state / list_changes / apply_change` thin-adapter
    surface added in UIAO_180 §Adapter delegation).

Bodies here are deliberately thin: they own the canonical contract,
not the vendor SDK calls. Real Entra/ARM I/O lives in the adapter
modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Mapping, Optional, Protocol

from uiao.governance.drift_output import DriftRecord
from uiao.governance.tag_governance import (
    CANONICAL_KEYS,
    compute_tag_drift,
    split_tags,
)

Outcome = Literal["created", "updated", "noop", "failed"]


# ---------------------------------------------------------------------------
# Result dataclasses (UIAO_180 §Structured output)
# ---------------------------------------------------------------------------


@dataclass
class _BaseResult:
    object_id: str
    outcome: Outcome
    delta: Dict[str, Any] = field(default_factory=dict)
    drift_records: List[DriftRecord] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "outcome": self.outcome,
            "delta": self.delta,
            "drift_records": [r.to_dict() for r in self.drift_records],
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }


@dataclass
class IdentityResult(_BaseResult):
    pass


@dataclass
class GroupResult(_BaseResult):
    pass


@dataclass
class GroupMembershipResult(_BaseResult):
    pass


@dataclass
class RoleAssignmentResult(_BaseResult):
    role: str = ""


@dataclass
class ResourceIdentityResult(_BaseResult):
    pass


@dataclass
class ResourceResult(_BaseResult):
    pass


@dataclass
class RbacAssignmentResult(_BaseResult):
    role: str = ""
    scope: str = ""


@dataclass
class TagWriteResult(_BaseResult):
    written: Dict[str, str] = field(default_factory=dict)


@dataclass
class TagReadResult(_BaseResult):
    canonical: Dict[str, str] = field(default_factory=dict)
    non_canonical: Dict[str, str] = field(default_factory=dict)
    forbidden: Dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Spec inputs (UIAO_180 §Structured input)
# ---------------------------------------------------------------------------


@dataclass
class UserSpec:
    object_id: str
    user_principal_name: str
    display_name: str
    org_path: str
    owner: str
    boundary: str = "GCC-Moderate"
    lifecycle: Literal["active", "leave", "disabled"] = "active"


@dataclass
class GroupSpec:
    object_id: str
    display_name: str
    membership_type: Literal["assigned", "dynamic"]
    org_path: Optional[str] = None


@dataclass
class ManagedIdentitySpec:
    object_id: str
    resource_group: str
    subscription_id: str


@dataclass
class ResourceGroupSpec:
    object_id: str
    name: str
    subscription_id: str
    location: str


# ---------------------------------------------------------------------------
# Adapter protocol
# ---------------------------------------------------------------------------


class _ThinAdapter(Protocol):
    """The thin-adapter surface this library depends on (UIAO_180)."""

    ADAPTER_ID: str

    def get_state(self, object_id: str) -> Dict[str, Any]: ...
    def set_state(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
    def apply_change(self, object_id: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reconcile(
    adapter: _ThinAdapter,
    object_id: str,
    desired: Mapping[str, Any],
    *,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Read observed state, return the delta dict that `set_state` would write.

    Idempotency primitive: a key whose observed value equals the desired
    value is excluded from the delta, so re-running converges with no
    side effects.
    """
    observed: Dict[str, Any] = {}
    try:
        observed = adapter.get_state(object_id) or {}
    except NotImplementedError:
        observed = {}
    return {k: v for k, v in desired.items() if observed.get(k) != v}


# ---------------------------------------------------------------------------
# Identity primitives
# ---------------------------------------------------------------------------


def create_user(
    adapter: _ThinAdapter,
    spec: UserSpec,
    *,
    correlation_id: Optional[str] = None,
) -> IdentityResult:
    """Create or reconcile an Entra user principal (idempotent)."""
    desired = {
        "userPrincipalName": spec.user_principal_name,
        "displayName": spec.display_name,
        "extensionAttribute1": spec.org_path,
    }
    delta = _reconcile(adapter, spec.object_id, desired, correlation_id=correlation_id)
    if delta:
        adapter.set_state(spec.object_id, desired)
        outcome: Outcome = "updated" if "userPrincipalName" not in delta else "created"
    else:
        outcome = "noop"
    return IdentityResult(object_id=spec.object_id, outcome=outcome, delta=delta, correlation_id=correlation_id)


def disable_user(
    adapter: _ThinAdapter,
    object_id: str,
    *,
    correlation_id: Optional[str] = None,
) -> IdentityResult:
    """Set `uiao.identity.lifecycle = disabled` and disable the principal."""
    delta = adapter.apply_change(
        object_id,
        {"accountEnabled": False, "uiao.identity.lifecycle": "disabled"},
    )
    return IdentityResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


def delete_user(
    adapter: _ThinAdapter,
    object_id: str,
    *,
    correlation_id: Optional[str] = None,
) -> IdentityResult:
    """Soft-delete an Entra user (30-day recoverable window)."""
    delta = adapter.apply_change(object_id, {"__deleted__": True})
    return IdentityResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


def assign_role(
    adapter: _ThinAdapter,
    object_id: str,
    role: str,
    *,
    correlation_id: Optional[str] = None,
) -> RoleAssignmentResult:
    delta = adapter.apply_change(object_id, {"add_role": role})
    return RoleAssignmentResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        role=role,
        correlation_id=correlation_id,
    )


def remove_role(
    adapter: _ThinAdapter,
    object_id: str,
    role: str,
    *,
    correlation_id: Optional[str] = None,
) -> RoleAssignmentResult:
    delta = adapter.apply_change(object_id, {"remove_role": role})
    return RoleAssignmentResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        role=role,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Group primitives
# ---------------------------------------------------------------------------


def create_group(
    adapter: _ThinAdapter,
    spec: GroupSpec,
    *,
    correlation_id: Optional[str] = None,
) -> GroupResult:
    desired = {
        "displayName": spec.display_name,
        "membershipType": spec.membership_type,
    }
    delta = _reconcile(adapter, spec.object_id, desired, correlation_id=correlation_id)
    if delta:
        adapter.set_state(spec.object_id, desired)
    return GroupResult(
        object_id=spec.object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


def add_to_group(
    adapter: _ThinAdapter,
    object_id: str,
    group_id: str,
    *,
    correlation_id: Optional[str] = None,
) -> GroupMembershipResult:
    delta = adapter.apply_change(group_id, {"add_member": object_id})
    return GroupMembershipResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


def remove_from_group(
    adapter: _ThinAdapter,
    object_id: str,
    group_id: str,
    *,
    correlation_id: Optional[str] = None,
) -> GroupMembershipResult:
    delta = adapter.apply_change(group_id, {"remove_member": object_id})
    return GroupMembershipResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Resource / RBAC primitives
# ---------------------------------------------------------------------------


def create_managed_identity(
    adapter: _ThinAdapter,
    spec: ManagedIdentitySpec,
    *,
    correlation_id: Optional[str] = None,
) -> ResourceIdentityResult:
    desired = {
        "resourceGroup": spec.resource_group,
        "subscriptionId": spec.subscription_id,
    }
    delta = _reconcile(adapter, spec.object_id, desired, correlation_id=correlation_id)
    if delta:
        adapter.set_state(spec.object_id, desired)
    return ResourceIdentityResult(
        object_id=spec.object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


def assign_rbac(
    adapter: _ThinAdapter,
    object_id: str,
    scope: str,
    role: str,
    *,
    correlation_id: Optional[str] = None,
) -> RbacAssignmentResult:
    delta = adapter.apply_change(object_id, {"rbac_scope": scope, "rbac_role": role})
    return RbacAssignmentResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        role=role,
        scope=scope,
        correlation_id=correlation_id,
    )


def create_resource_group(
    adapter: _ThinAdapter,
    spec: ResourceGroupSpec,
    *,
    correlation_id: Optional[str] = None,
) -> ResourceResult:
    desired = {
        "name": spec.name,
        "subscriptionId": spec.subscription_id,
        "location": spec.location,
    }
    delta = _reconcile(adapter, spec.object_id, desired, correlation_id=correlation_id)
    if delta:
        adapter.set_state(spec.object_id, desired)
    return ResourceResult(
        object_id=spec.object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Tag primitives (UIAO_177)
# ---------------------------------------------------------------------------


def apply_tags(
    adapter: _ThinAdapter,
    object_id: str,
    tags: Mapping[str, str],
    *,
    correlation_id: Optional[str] = None,
) -> TagWriteResult:
    """Apply canonical (`uiao.*`) tags. Non-canonical keys are rejected.

    Use `correct_tag_drift()` if the caller wants UIAO to recompute the
    canonical state and overwrite mismatches.
    """
    rejected = {k: v for k, v in tags.items() if k not in CANONICAL_KEYS}
    if rejected:
        return TagWriteResult(
            object_id=object_id,
            outcome="failed",
            delta={"rejected_non_canonical_keys": list(rejected)},
            correlation_id=correlation_id,
        )
    delta = adapter.apply_change(object_id, {"tags": dict(tags)})
    return TagWriteResult(
        object_id=object_id,
        outcome="updated" if delta else "noop",
        delta=delta,
        written=dict(tags),
        correlation_id=correlation_id,
    )


def read_tags(
    adapter: _ThinAdapter,
    object_id: str,
    *,
    correlation_id: Optional[str] = None,
) -> TagReadResult:
    state = adapter.get_state(object_id) or {}
    observed = state.get("tags", {}) or {}
    buckets = split_tags(observed)
    return TagReadResult(
        object_id=object_id,
        outcome="noop",
        canonical=buckets["canonical"],
        non_canonical=buckets["non_canonical"],
        forbidden=buckets["forbidden"],
        correlation_id=correlation_id,
    )


def detect_tag_drift(
    adapter: _ThinAdapter,
    object_id: str,
    *,
    desired: Mapping[str, str],
    correlation_id: Optional[str] = None,
) -> List[DriftRecord]:
    """Compute tag drift records per UIAO_177."""
    state = adapter.get_state(object_id) or {}
    actual = state.get("tags", {}) or {}
    return compute_tag_drift(
        object_id,
        desired=desired,
        actual=actual,
        source_adapter=getattr(adapter, "ADAPTER_ID", "unknown"),
        correlation_id=correlation_id,
    )


def correct_tag_drift(
    adapter: _ThinAdapter,
    object_id: str,
    *,
    desired: Mapping[str, str],
    correlation_id: Optional[str] = None,
) -> TagWriteResult:
    """Detect tag drift and apply corrections in a single pass."""
    records = detect_tag_drift(adapter, object_id, desired=desired, correlation_id=correlation_id)
    if not records:
        return TagWriteResult(
            object_id=object_id,
            outcome="noop",
            delta={},
            written={},
            correlation_id=correlation_id,
        )
    result = apply_tags(adapter, object_id, desired, correlation_id=correlation_id)
    result.drift_records = records
    return result
