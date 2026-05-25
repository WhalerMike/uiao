"""Entra-side adapter for the Model C dynamic-group consumer (ADR-084 §C4).

Wraps the :py:class:`uiao.modernization.orgtree.dynamic_groups.DynamicGroupPlanner`
plan/apply cycle with the Microsoft Graph transport. Per ADR-084 §C4
``dry_run=True`` is the default; promotion to ``dry_run=False`` is an
operator decision per scan.

Per ADR-078 / ADR-036, this adapter supersedes the retired Model A
composite-string wrapper.

The adapter does not call Graph from inside ``plan()`` — planning is
pure. The transport seam is the ``transport`` callable passed to
``apply()``, which lets tests substitute a recording mock without
patching Graph SDKs.
"""

from __future__ import annotations

from typing import Callable, Iterable

from uiao.modernization.orgtree.dynamic_groups import (
    DynamicGroupLibrary,
    DynamicGroupPlanner,
)
from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

# Transport callable: takes (method, path, body) -> dict response.
# Real implementations wrap msgraph SDK; tests substitute a recorder.
Transport = Callable[[str, str, dict | None], dict]


# Per ADR-084 §C5, the engine honours each adapter's governance-review
# set: ops in this set are never auto-remediated even when dry_run=False.
_GOVERNANCE_REVIEW_OPS: frozenset[str] = frozenset({"phantom"})


class EntraDynamicGroupAdapter:
    """Plan/apply adapter for dynamic groups on Microsoft Graph.

    Construct with a :py:class:`DynamicGroupLibrary` and an optional
    transport; call :py:meth:`plan` against a snapshot list to get
    operations; call :py:meth:`apply` to dispatch (or dry-run) them.
    """

    def __init__(
        self,
        library: DynamicGroupLibrary,
        transport: Transport | None = None,
    ) -> None:
        self.library = library
        self.planner = DynamicGroupPlanner(library)
        self.transport = transport

    @property
    def governance_review_ops(self) -> frozenset[str]:
        """Op verbs that are never auto-remediated (ADR-084 §C5)."""
        return _GOVERNANCE_REVIEW_OPS

    def plan(self, observed: Iterable) -> list[FacetOperation]:
        """Delegate planning to the consumer (pure, no I/O)."""
        return self.planner.plan(observed)

    def apply(
        self,
        operations: Iterable[FacetOperation],
        *,
        dry_run: bool = True,
    ) -> ApplyResult:
        """Dispatch (or dry-run) the planned operations.

        Governance-review operations (``phantom``) are always skipped —
        humans review before deletion.
        """
        ops = tuple(operations)
        sent: list[FacetOperation] = []
        skipped: list[FacetOperation] = []
        errors: list[tuple[FacetOperation, str]] = []

        for op in ops:
            if op.op in self.governance_review_ops:
                skipped.append(op)
                continue
            if dry_run:
                skipped.append(op)
                continue
            if self.transport is None:
                errors.append((op, "no transport configured"))
                continue
            try:
                self._dispatch(op)
                sent.append(op)
            except Exception as exc:  # pragma: no cover - transport-specific
                errors.append((op, str(exc)))

        return ApplyResult(
            operations=ops,
            sent=tuple(sent),
            skipped=tuple(skipped),
            errors=tuple(errors),
            dry_run=dry_run,
        )

    # ------------------------------------------------------------------
    # Transport dispatch — translates a FacetOperation to a Graph call.
    # ------------------------------------------------------------------
    def _dispatch(self, op: FacetOperation) -> None:
        assert self.transport is not None  # narrow for type-checkers
        if op.op == "create":
            body = op.metadata.get("graph_body")
            if body is None:
                raise ValueError("create op missing graph_body in metadata")
            self.transport("POST", "/groups", body)
        elif op.op == "update":
            object_id = op.metadata.get("object_id")
            if not object_id:
                raise ValueError("update op missing object_id in metadata")
            self.transport(
                "PATCH",
                f"/groups/{object_id}",
                {"membershipRule": op.value},
            )
        else:
            raise ValueError(f"Unsupported dispatch verb '{op.op}'")
