"""Entra-side adapter for the Model C policy-targeting consumer (ADR-084 §C4)."""

from __future__ import annotations

from typing import Callable, Iterable

from uiao.modernization.orgtree.policy_targeting import (
    PolicyTargetLibrary,
    PolicyTargetPlanner,
)
from uiao.modernization.orgtree.types import ApplyResult, FacetOperation

Transport = Callable[[str, str, dict | None], dict]

_GOVERNANCE_REVIEW_OPS: frozenset[str] = frozenset({"rebind"})


# Maps the transport flavour to the Graph / ARM path prefix
# the adapter writes to.
_TRANSPORT_ROUTES = {
    "ca": "/identity/conditionalAccess/policies",
    "azure_policy": "/providers/Microsoft.Authorization/policyAssignments",
    "intune": "/deviceManagement/configurationPolicies",
    "defender": "/security/policies",
}


class EntraPolicyTargetAdapter:
    """Plan/apply adapter for policy assignments across CA / Azure Policy / Intune / Defender."""

    def __init__(
        self,
        library: PolicyTargetLibrary,
        transport: Transport | None = None,
    ) -> None:
        self.library = library
        self.planner = PolicyTargetPlanner(library)
        self.transport = transport

    @property
    def governance_review_ops(self) -> frozenset[str]:
        """Rebinding a policy_definition_id is a governance change."""
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
        transport_kind = op.metadata.get("transport")
        if transport_kind not in _TRANSPORT_ROUTES:
            raise ValueError(f"Unknown transport '{transport_kind}'")
        route = _TRANSPORT_ROUTES[transport_kind]

        if op.op == "create":
            body = {
                "displayName": op.metadata["assignment_name"],
                "policyDefinitionId": op.metadata["policy_definition_id"],
                "scope": op.value,
                "description": op.metadata.get("description", ""),
            }
            self.transport("POST", route, body)
        elif op.op == "update":
            self.transport(
                "PATCH",
                f"{route}/{op.target}",
                {"scope": op.value},
            )
        else:
            raise ValueError(f"Unsupported dispatch verb '{op.op}'")
