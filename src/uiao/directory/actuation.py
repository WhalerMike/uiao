"""Write-path actuation seam for the Active Governance Directory (ADR-109 §3).

ADR-109's :class:`~uiao.directory.writes.WriteRouter` translates an LDAP
``modify`` into governed ``FacetOperation``s and, by default, only *plans*
them. This module provides the seam that turns an approved plan into a real
change against the provider of record — by routing the operations into an
existing Phase-5 modernization adapter's ``apply`` (ADR-036–039 / ADR-084).

It does **not** itself talk to any provider: the adapter (and its transport)
is **injected**. What this layer adds is the ADR-092 §3 actuation gate:

* actuation is **off by default** — a :class:`FacetActuator` raises
  :class:`ActuationDisabled` unless explicitly ``enabled`` (the L3 opt-in);
* the adapter's own ``governance_review_ops`` are honoured — high-blast-radius
  verbs the adapter declares are *skipped* (held for human review), never
  auto-applied, even when actuation is enabled (ADR-092 §3/§4);
* every apply produces an auditable :class:`ApplyResult` recorded on the
  actuator.

The result is an ``apply_fn`` the WriteRouter can call (``WriteRouter(
dry_run=False, apply_fn=actuator.as_apply_fn())``) that drives real,
gated, audited actuation while the provider transport stays injected.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

# A per-principal directory write: ``(target_dn, attribute, value) -> None``.
# This is the seam a concrete transport (e.g. ``LdapTransport.modify``) fills.
PrincipalWriteFn = Callable[[str, str, str], None]


class ActuationDisabled(RuntimeError):
    """Raised when actuation is attempted on a not-explicitly-enabled actuator."""


class ActuationError(RuntimeError):
    """Raised when the adapter reports per-operation transport errors."""


@runtime_checkable
class FacetApplyAdapter(Protocol):
    """The minimal slice of the Phase-5 ``Adapter`` contract actuation needs.

    Matches ADR-084 / the drift engine's ``Adapter`` protocol: ``apply``
    consumes ``FacetOperation``s (dry-run by default) and returns an
    :class:`ApplyResult`; ``governance_review_ops`` names the verbs that must
    never auto-fire (held for review).
    """

    @property
    def governance_review_ops(self) -> frozenset[str]: ...

    def apply(self, operations: Iterable[FacetOperation], *, dry_run: bool = True) -> ApplyResult: ...


@dataclass
class FacetActuator:
    """Routes governed FacetOperations into an adapter's ``apply``, gated.

    ``enabled`` is the ADR-092 §3 L3 opt-in: while False, any actuation
    raises :class:`ActuationDisabled`, so a WriteRouter wired to a disabled
    actuator stays effectively plan-only. The adapter's
    ``governance_review_ops`` are always honoured (those ops are skipped,
    held for review). Each apply is appended to :attr:`audit`.
    """

    adapter: FacetApplyAdapter
    enabled: bool = False
    audit: list[ApplyResult] = field(default_factory=list)

    def apply(self, operations: tuple[FacetOperation, ...]) -> ApplyResult:
        """Apply ``operations`` through the adapter (raises if not enabled)."""
        if not self.enabled:
            raise ActuationDisabled(
                "actuation is disabled; enable it explicitly (ADR-092 §3 L3) before applying writes"
            )
        result = self.adapter.apply(operations, dry_run=False)
        self.audit.append(result)
        if result.errors:
            detail = "; ".join(f"{op.facet}@{op.target}: {msg}" for op, msg in result.errors)
            raise ActuationError(f"actuation reported {len(result.errors)} error(s): {detail}")
        return result

    def as_apply_fn(self) -> Callable[[tuple[FacetOperation, ...]], None]:
        """Adapt :meth:`apply` to the WriteRouter ``apply_fn`` signature."""

        def _apply(operations: tuple[FacetOperation, ...]) -> None:
            self.apply(operations)

        return _apply


@dataclass
class FacetWriteAdapter:
    """Adapt a per-principal directory write into the Phase-5 apply protocol.

    The AGD write path (ADR-109) translates an LDAP ``modify`` into per-facet
    ``write`` / ``remove`` :class:`FacetOperation`s against a target principal
    DN. A directory *transport* (e.g. :meth:`LdapTransport.modify
    <uiao.adapters.ldap_transport.LdapTransport.modify>`) knows how to set one
    attribute on one DN, but it is **not** a Phase-5 ``Adapter`` — it has no
    ``governance_review_ops`` and returns no :class:`ApplyResult`. This adapter
    bridges the two: it presents the :class:`FacetApplyAdapter` contract the
    :class:`FacetActuator` consumes while delegating the actual I/O to the
    injected ``write_fn``.

    ``write_fn`` receives ``(target_dn, attribute, value)``; a ``remove``
    operation passes the empty string (the ``ldap`` profile clears a facet by
    writing an empty value). Operations whose ``op`` is in ``review_ops`` are
    held (skipped) for human review, never dispatched — the per-adapter half of
    the ADR-092 §3/§4 gate that :class:`FacetActuator` enforces globally.
    """

    write_fn: PrincipalWriteFn
    review_ops: frozenset[str] = frozenset()

    @property
    def governance_review_ops(self) -> frozenset[str]:
        return self.review_ops

    def apply(self, operations: Iterable[FacetOperation], *, dry_run: bool = True) -> ApplyResult:
        ops = tuple(operations)
        if dry_run:
            return ApplyResult.dry(ops)
        sent: list[FacetOperation] = []
        skipped: list[FacetOperation] = []
        errors: list[tuple[FacetOperation, str]] = []
        for op in ops:
            if op.op in self.review_ops:
                skipped.append(op)
                continue
            try:
                self.write_fn(op.target, op.attribute, op.value or "")
            except Exception as exc:  # noqa: BLE001 — transport-agnostic; surfaced as a per-op error
                errors.append((op, str(exc)))
                continue
            sent.append(op)
        return ApplyResult(
            operations=ops,
            sent=tuple(sent),
            skipped=tuple(skipped),
            errors=tuple(errors),
            dry_run=False,
        )
