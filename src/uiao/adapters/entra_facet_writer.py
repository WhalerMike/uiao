"""Entra/Graph facet writer — the AGD write-actuation target for the Entra
provider of record (ADR-109 §1 / ADR-098 microsoft-entra binding profile).

The Active Governance Directory translates an LDAP ``modify`` into governed
``FacetOperation``s and, under ``--apply``, routes them to a provider of record.
:class:`~uiao.directory.actuation.FacetWriteAdapter` is the LDAP target;
:class:`EntraFacetWriter` is the Entra target. It applies each per-facet write as
a Graph ``PATCH`` of the principal's ``onPremisesExtensionAttributes`` slot
(``extensionAttribute1..15``), matching the existing device-plane writeback
convention.

It implements the Phase-5 ``FacetApplyAdapter`` protocol (``apply`` +
``governance_review_ops``) so a :class:`~uiao.directory.actuation.FacetActuator`
can wrap it identically to any other adapter. The Graph **transport is
injected** — this class holds no credentials and does no auth.

Principal addressing: a routed operation's ``target`` is the *projected DN*,
which is not a Graph identifier. The real principal id + type are stamped onto
``operation.metadata`` by the AGD's principal resolver
(:meth:`uiao.directory.dit.Directory.principal_for`); this reads them from there.
``user`` and ``device`` principals are supported (both carry
``onPremisesExtensionAttributes``); ``servicePrincipal`` has no such container
and is refused per operation.

Caveat: for an ``onPremisesSyncEnabled`` (AD-synced) user, Graph treats
``onPremisesExtensionAttributes`` as read-only (the source of authority is
on-prem). Writes succeed only for cloud-only users and for devices; a synced
user surfaces the Graph error per operation rather than silently no-op'ing.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

# The Graph transport seam: ``(method, path, body) -> dict`` (GraphTransport).
GraphCallable = Callable[[str, str, "dict[str, Any] | None"], "dict[str, Any]"]

# Entra collection that holds each principal type's onPremisesExtensionAttributes.
_COLLECTION = {"user": "users", "device": "devices"}


class EntraFacetWriter:
    """Apply governed OrgPath facet writes to Entra principals via Graph."""

    def __init__(self, transport: GraphCallable, *, review_ops: frozenset[str] = frozenset()) -> None:
        self._transport = transport
        self._review = review_ops

    @property
    def governance_review_ops(self) -> frozenset[str]:
        return self._review

    def apply(self, operations: Iterable[FacetOperation], *, dry_run: bool = True) -> ApplyResult:
        ops = tuple(operations)
        if dry_run:
            return ApplyResult.dry(ops)
        sent: list[FacetOperation] = []
        skipped: list[FacetOperation] = []
        errors: list[tuple[FacetOperation, str]] = []
        for op in ops:
            if op.op in self._review:
                skipped.append(op)  # held for human review (ADR-092 §3/§4)
                continue
            principal_id = op.metadata.get("principal_id")
            principal_type = op.metadata.get("principal_type")
            collection = _COLLECTION.get(str(principal_type))
            if not principal_id or collection is None:
                errors.append(
                    (op, f"unresolved or unsupported Entra principal (id={principal_id!r}, type={principal_type!r})")
                )
                continue
            # A `remove` carries value=None → Graph clears the slot when set to null.
            body = {"onPremisesExtensionAttributes": {op.attribute: op.value}}
            try:
                self._transport("PATCH", f"/{collection}/{principal_id}", body)
            except Exception as exc:  # noqa: BLE001 — transport-agnostic; surfaced per op
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
