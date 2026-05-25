"""Entra-side adapter for the Model C AU consumer (ADR-084 §C4)."""

from __future__ import annotations

from typing import Callable, Iterable

from uiao.modernization.orgtree.admin_units import AdminUnitPlanner, AdminUnitRegistry
from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

Transport = Callable[[str, str, dict | None], dict]

_GOVERNANCE_REVIEW_OPS: frozenset[str] = frozenset({"phantom"})


class EntraAdminUnitAdapter:
    """Plan/apply adapter for Administrative Units on Microsoft Graph."""

    def __init__(
        self,
        registry: AdminUnitRegistry,
        transport: Transport | None = None,
    ) -> None:
        self.registry = registry
        self.planner = AdminUnitPlanner(registry)
        self.transport = transport

    @property
    def governance_review_ops(self) -> frozenset[str]:
        return _GOVERNANCE_REVIEW_OPS

    def plan(self, observed: Iterable) -> list[FacetOperation]:
        return self.planner.plan(observed)

    def apply(
        self,
        operations: Iterable[FacetOperation],
        *,
        dry_run: bool = True,
    ) -> ApplyResult:
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
            except Exception as exc:  # pragma: no cover
                errors.append((op, str(exc)))

        return ApplyResult(
            operations=ops,
            sent=tuple(sent),
            skipped=tuple(skipped),
            errors=tuple(errors),
            dry_run=dry_run,
        )

    def _dispatch(self, op: FacetOperation) -> None:
        assert self.transport is not None
        if op.op == "create":
            body = op.metadata.get("graph_body")
            if body is None:
                raise ValueError("create op missing graph_body")
            self.transport("POST", "/directory/administrativeUnits", body)
        elif op.op == "update":
            object_id = op.metadata.get("object_id")
            patch_body = op.metadata.get("patch_body")
            if not object_id or not patch_body:
                raise ValueError("update op missing object_id or patch_body")
            self.transport(
                "PATCH",
                f"/directory/administrativeUnits/{object_id}",
                patch_body,
            )
        else:
            raise ValueError(f"Unsupported dispatch verb '{op.op}'")
