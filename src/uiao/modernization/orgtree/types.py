"""Shared dataclasses for the Model C orgtree consumers (ADR-084).

The five Phase 5 consumer modules (``dynamic_groups``, ``admin_units``,
``policy_targeting``, ``device_orgpath``, ``governance.drift_engine``)
all exchange per-facet operations and per-adapter apply results
through the dataclasses declared here.

Per ADR-084 §C2 (Per-facet operations as the unit of work), every
consumer's ``plan()`` returns ``FacetOperation`` instances — never a
composite-string operation. Per ADR-084 §C4 (Two-phase plan/apply),
``apply()`` consumes operations and returns an ``ApplyResult`` that
records which operations were sent (``dry_run=False``) or would have
been sent (``dry_run=True``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

# ---------------------------------------------------------------------------
# Per-facet operations (ADR-084 §C2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FacetOperation:
    """One per-facet planned operation.

    Emitted by every consumer's ``plan()``. The ``op`` field distinguishes
    the verb (``validate``, ``write``, ``remove``, ``render``); the
    ``facet`` + ``attribute`` pair identifies the Codebook facet and its
    bound ``extensionAttribute*`` slot; ``value`` is the per-facet value
    (None for ``remove``); ``target`` is the principal / device / SP /
    group / AU / policy assignment the operation acts on.
    """

    facet: str
    attribute: str
    op: str
    value: str | None
    target: str
    metadata: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Boolean composition over facet predicates (ADR-084 §C3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FacetPredicate:
    """One clause of a boolean composition: ``<facet> <op> <value>``.

    ``op`` accepts the Entra dynamic membership operators
    (``-eq``, ``-ne``, ``-in``, ``-ge``, ``-le``, ``-gt``, ``-lt``,
    ``-startsWith``, ``-contains``, ``-match``). ``value`` is a string
    for scalar operators and a list for ``-in``.
    """

    facet: str
    op: str
    value: str | list[str]


@dataclass(frozen=True)
class CompositionSpec:
    """A boolean composition of one or more ``FacetPredicate`` clauses.

    ``combinator`` is ``"and"`` (default) or ``"or"`` and is applied
    between every adjacent pair of predicates. Complex compositions
    (mixed and/or) are not supported by this shape — they must be
    expressed as multiple ``CompositionSpec`` instances combined by
    the consumer.
    """

    predicates: tuple[FacetPredicate, ...]
    combinator: str = "and"


# ---------------------------------------------------------------------------
# Snapshots — input to Compare in the drift engine (ADR-084 §C5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PrincipalSnapshot:
    """One principal's facet-slot values at snapshot time."""

    principal_id: str
    principal_type: str  # "user" | "device" | "servicePrincipal"
    attributes: Mapping[str, str]  # extensionAttribute1..10 -> value (may be "")


@dataclass(frozen=True)
class GroupSnapshot:
    """One dynamic group's observed name + rule at snapshot time."""

    object_id: str
    name: str
    membership_rule: str
    group_type: str  # "Security" | "M365"


@dataclass(frozen=True)
class AdminUnitSnapshot:
    """One Administrative Unit's observed membership rule at snapshot time."""

    object_id: str
    name: str
    membership_rule: str
    restricted_management: bool


@dataclass(frozen=True)
class PolicyTargetSnapshot:
    """One policy assignment's observed scope at snapshot time."""

    assignment_id: str
    policy_definition_id: str
    scope_rule: str


@dataclass(frozen=True)
class DevicePlaneSnapshot:
    """One device's observed per-plane facet writes at snapshot time."""

    device_id: str
    plane: str  # "entra" | "arm"
    attributes: Mapping[str, str]  # extensionAttribute1..10 OR tags.<Facet>


@dataclass(frozen=True)
class Snapshot:
    """Pre-fetched tenant state for one drift scan.

    Each consumer's ``plan()`` reads the subset of this snapshot it
    needs; the engine pre-fetches everything once and passes the whole
    object through.
    """

    generated_at: str
    principals: tuple[PrincipalSnapshot, ...] = ()
    groups: tuple[GroupSnapshot, ...] = ()
    admin_units: tuple[AdminUnitSnapshot, ...] = ()
    policy_targets: tuple[PolicyTargetSnapshot, ...] = ()
    device_planes: tuple[DevicePlaneSnapshot, ...] = ()

    @classmethod
    def now(cls, **kwargs: Any) -> Snapshot:
        """Construct a snapshot stamped with the current UTC time."""
        return cls(generated_at=datetime.now(timezone.utc).isoformat(), **kwargs)


# ---------------------------------------------------------------------------
# Apply results — output of every consumer's apply() (ADR-084 §C4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApplyResult:
    """Result of an ``Adapter.apply()`` call.

    ``operations`` is the full list passed in (preserved for audit).
    ``sent`` is the subset that were actually dispatched (empty when
    ``dry_run=True``). ``skipped`` is the subset that were *not*
    dispatched even when ``dry_run=False`` — typically because they
    fall in the adapter's ``governance_review_ops`` set. ``errors``
    captures per-operation transport failures.
    """

    operations: tuple[FacetOperation, ...]
    sent: tuple[FacetOperation, ...]
    skipped: tuple[FacetOperation, ...]
    errors: tuple[tuple[FacetOperation, str], ...] = ()
    dry_run: bool = True

    @property
    def planned_count(self) -> int:
        return len(self.operations)

    @property
    def sent_count(self) -> int:
        return len(self.sent)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @classmethod
    def dry(cls, operations: Iterable[FacetOperation]) -> ApplyResult:
        """Build a dry-run result from a planned operation list."""
        ops = tuple(operations)
        return cls(operations=ops, sent=(), skipped=ops, dry_run=True)
