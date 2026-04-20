"""Policy-targeting adapter (Phase 5, MOD_N / ADR-039).

Closes the "policy consumer" layer of the OrgTree. Phases 2–4 produced
the governance surface:

* Phase 2 — OrgTree-* dynamic groups (MOD_B)
* Phase 3 — Restricted Management AUs + scoped roles (MOD_D)
* Phase 4 — device-plane OrgPath on Entra devices + Arc machines (MOD_C)

Phase 5 **binds existing policy objects to that surface**:

* **Intune** configuration profiles / compliance policies are assigned
  to OrgTree-* dynamic groups with ``include`` or ``exclude`` intent via
  ``POST /deviceManagement/{kind}s/{id}/assignments``.
* **Azure Policy** definitions are assigned at subscription scope and
  filtered to Arc machines whose ``OrgPath`` ARM tag matches a prefix
  pattern (e.g., ``startsWith 'ORG-IT-INF'``).

Policy **bodies** are out of scope — only the binding.

The adapter consumes the canonical :class:`PolicyTargetingCanon` from
:mod:`uiao.modernization.orgtree.policy_targets` plus pre-fetched tenant
state and emits a plan with eight op types across two transports. Never
auto-remediates phantom assignments (the policy-consumer layer has the
broadest blast radius — unauthorised policy = every targeted device
gets reconfigured).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

from uiao.modernization.orgtree import (
    ArcPolicyAssignment,
    IntuneAssignment,
    PolicyTargetingCanon,
)
from uiao.modernization.orgtree.policy_targets import (
    default_policy_targeting_canon,
)


logger = logging.getLogger(__name__)


OP_INTUNE_ASSIGN_CREATE = "intune-assign-create"
OP_INTUNE_ASSIGN_UPDATE = "intune-assign-update"
OP_INTUNE_ASSIGN_PHANTOM = "intune-assign-phantom"
OP_INTUNE_PROFILE_MISSING = "intune-profile-missing"
OP_ARC_POLICY_CREATE = "arc-policy-create"
OP_ARC_POLICY_UPDATE = "arc-policy-update"
OP_ARC_POLICY_PHANTOM = "arc-policy-phantom"
OP_ARC_POLICY_DEF_MISSING = "arc-policy-definition-missing"

OPS_AUTO_APPLIED = frozenset({
    OP_INTUNE_ASSIGN_CREATE,
    OP_INTUNE_ASSIGN_UPDATE,
    OP_ARC_POLICY_CREATE,
    OP_ARC_POLICY_UPDATE,
})
OPS_GOVERNANCE_REVIEW = frozenset({
    OP_INTUNE_ASSIGN_PHANTOM,
    OP_ARC_POLICY_PHANTOM,
    OP_INTUNE_PROFILE_MISSING,
    OP_ARC_POLICY_DEF_MISSING,
})


@dataclass
class PlannedOperation:
    op: str
    target: str
    reason: str
    canonical: Optional[object] = None  # IntuneAssignment | ArcPolicyAssignment
    current_state: Optional[Dict[str, Any]] = None
    intune_profile_id: Optional[str] = None
    intune_group_id: Optional[str] = None
    arc_definition_id: Optional[str] = None


@dataclass
class PolicyTargetingPlan:
    generated_at: str
    total_canonical_intune: int
    total_canonical_arc: int
    total_tenant_intune_profiles: int
    total_tenant_arc_assignments: int
    operations: List[PlannedOperation] = field(default_factory=list)

    def by_op(self, op: str) -> List[PlannedOperation]:
        return [o for o in self.operations if o.op == op]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_canonical_intune": self.total_canonical_intune,
            "total_canonical_arc": self.total_canonical_arc,
            "total_tenant_intune_profiles": self.total_tenant_intune_profiles,
            "total_tenant_arc_assignments": self.total_tenant_arc_assignments,
            "operations": [
                {"op": o.op, "target": o.target, "reason": o.reason}
                for o in self.operations
            ],
        }


@dataclass
class OperationResult:
    op: str
    target: str
    status: str
    detail: str = ""


@dataclass
class PolicyTargetingReport:
    generated_at: str
    dry_run: bool
    results: List[OperationResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.status == "written")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [r.__dict__ for r in self.results],
        }


class EntraPolicyTargetingAdapter:
    """Modernization adapter: bind Intune + Azure Policy to the OrgTree."""

    ADAPTER_ID = "entra-policy-targeting"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        canon: Optional[PolicyTargetingCanon] = None,
    ) -> None:
        self._config = config or {}
        self._canon = canon or default_policy_targeting_canon()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def plan(
        self,
        current_intune_profiles: Optional[List[Dict[str, Any]]] = None,
        current_intune_assignments: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        current_arc_assignments: Optional[List[Dict[str, Any]]] = None,
        group_id_resolver: Optional[Dict[str, str]] = None,
        arc_definition_id_resolver: Optional[Dict[str, str]] = None,
    ) -> PolicyTargetingPlan:
        """Diff canon vs tenant state.

        Parameters
        ----------
        current_intune_profiles:
            Graph response from
            ``GET /deviceManagement/configurationPolicies`` (and
            ``deviceCompliancePolicies``, concatenated). Each entry must
            expose at minimum ``id`` and ``displayName``.
        current_intune_assignments:
            Map of ``{profile_id: [assignment, ...]}`` where each
            assignment is the Graph
            ``deviceManagement/{kind}s/{id}/assignments`` payload with
            ``target.groupId`` and ``target.@odata.type``.
        current_arc_assignments:
            ARM response from
            ``GET /providers/Microsoft.Authorization/policyAssignments``
            filtered or scanned for OrgTree-* assignments. Each entry
            exposes ``id``, ``name``, ``properties.policyDefinitionId``,
            ``properties.scope``, and ``properties.parameters``.
        group_id_resolver:
            Map ``{group_displayName → groupId}`` for Entra groups.
        arc_definition_id_resolver:
            Map ``{definition_displayName → policyDefinitionId}`` for
            Azure Policy.
        """
        profiles_by_name = {
            p.get("displayName"): p
            for p in (current_intune_profiles or [])
        }
        profiles_by_id = {
            p.get("id"): p
            for p in (current_intune_profiles or [])
        }
        assignments_by_profile_id = current_intune_assignments or {}
        arc_by_name = {
            a.get("name"): a
            for a in (current_arc_assignments or [])
        }
        group_resolver = group_id_resolver or {}
        arc_def_resolver = arc_definition_id_resolver or {}

        plan = PolicyTargetingPlan(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_canonical_intune=len(self._canon.intune_assignments),
            total_canonical_arc=len(self._canon.arc_policy_assignments),
            total_tenant_intune_profiles=len(profiles_by_id),
            total_tenant_arc_assignments=len(arc_by_name),
        )

        # ---- Intune ----
        for assignment in self._canon.intune_assignments:
            self._plan_intune(
                assignment,
                profiles_by_name,
                profiles_by_id,
                assignments_by_profile_id,
                group_resolver,
                plan,
            )

        # ---- Arc ----
        for name, assignment in self._canon.arc_policy_assignments.items():
            self._plan_arc(
                assignment,
                arc_by_name,
                arc_def_resolver,
                plan,
            )

        return plan

    def _plan_intune(
        self,
        assignment: IntuneAssignment,
        profiles_by_name: Mapping[str, Dict[str, Any]],
        profiles_by_id: Mapping[str, Dict[str, Any]],
        assignments_by_profile_id: Mapping[str, List[Dict[str, Any]]],
        group_resolver: Mapping[str, str],
        plan: PolicyTargetingPlan,
    ) -> None:
        ref = assignment.profile_ref
        profile = (
            profiles_by_id.get(ref.value) if ref.match_by == "id"
            else profiles_by_name.get(ref.value)
        )
        if profile is None:
            plan.operations.append(PlannedOperation(
                op=OP_INTUNE_PROFILE_MISSING,
                target=f"{ref.value} -> {assignment.target_group}",
                reason=(
                    f"Canonical Intune {ref.kind} '{ref.value}' not found in "
                    "tenant — author the profile first (out of scope for "
                    "this adapter), then re-run reconcile."
                ),
                canonical=assignment,
            ))
            return

        profile_id = profile.get("id")
        group_id = group_resolver.get(assignment.target_group)
        current_targets = assignments_by_profile_id.get(profile_id, [])

        matching = [
            a for a in current_targets
            if _intune_assignment_matches(a, assignment, group_id)
        ]
        non_matching_same_group = [
            a for a in current_targets
            if _intune_assignment_same_group(a, group_id)
            and not _intune_assignment_matches(a, assignment, group_id)
        ]

        if matching:
            return  # Already aligned.

        if non_matching_same_group:
            # Same group is assigned but with wrong intent — update.
            plan.operations.append(PlannedOperation(
                op=OP_INTUNE_ASSIGN_UPDATE,
                target=f"{ref.value} -> {assignment.target_group}",
                reason=(
                    "Intent drift: tenant assigns same group with different "
                    "intent than canon requires."
                ),
                canonical=assignment,
                current_state={"current_assignments": non_matching_same_group},
                intune_profile_id=profile_id,
                intune_group_id=group_id,
            ))
            return

        plan.operations.append(PlannedOperation(
            op=OP_INTUNE_ASSIGN_CREATE,
            target=f"{ref.value} -> {assignment.target_group}",
            reason=(
                "Canonical Intune assignment missing — group is not in "
                "the profile's assignments[] yet."
            ),
            canonical=assignment,
            intune_profile_id=profile_id,
            intune_group_id=group_id,
        ))

    def _plan_arc(
        self,
        assignment: ArcPolicyAssignment,
        arc_by_name: Mapping[str, Dict[str, Any]],
        arc_def_resolver: Mapping[str, str],
        plan: PolicyTargetingPlan,
    ) -> None:
        name = assignment.assignment_name
        tenant = arc_by_name.get(name)
        canonical_def_id = (
            assignment.policy_definition.value
            if assignment.policy_definition.match_by == "policyDefinitionId"
            else arc_def_resolver.get(assignment.policy_definition.value)
        )
        if canonical_def_id is None:
            plan.operations.append(PlannedOperation(
                op=OP_ARC_POLICY_DEF_MISSING,
                target=name,
                reason=(
                    f"Azure Policy definition "
                    f"'{assignment.policy_definition.value}' not resolvable "
                    "— pass arc_definition_id_resolver or use match_by: "
                    "policyDefinitionId."
                ),
                canonical=assignment,
            ))
            return

        if tenant is None:
            plan.operations.append(PlannedOperation(
                op=OP_ARC_POLICY_CREATE,
                target=name,
                reason=(
                    "Canonical Arc policy assignment missing — no Azure "
                    "Policy assignment with this name in the subscription."
                ),
                canonical=assignment,
                arc_definition_id=canonical_def_id,
            ))
            return

        props = tenant.get("properties", {}) or {}
        tenant_def = props.get("policyDefinitionId")
        tenant_scope = props.get("scope")
        tenant_parameters = props.get("parameters", {}) or {}

        drift_reasons: List[str] = []
        if tenant_def and tenant_def != canonical_def_id:
            drift_reasons.append(
                f"policyDefinitionId drift: tenant={tenant_def!r} "
                f"canonical={canonical_def_id!r}"
            )
        # OrgPath selector shape is passed through the Azure Policy
        # `orgPathPrefix` + `matchMode` parameters (one canonical naming
        # convention — policy bodies that implement the filter must
        # accept these two params).
        tenant_prefix = (
            tenant_parameters.get("orgPathPrefix", {}).get("value")
            if isinstance(tenant_parameters.get("orgPathPrefix"), dict)
            else tenant_parameters.get("orgPathPrefix")
        )
        tenant_mode = (
            tenant_parameters.get("matchMode", {}).get("value")
            if isinstance(tenant_parameters.get("matchMode"), dict)
            else tenant_parameters.get("matchMode")
        )
        if tenant_prefix != assignment.orgpath_selector.prefix:
            drift_reasons.append(
                f"orgPathPrefix drift: tenant={tenant_prefix!r} "
                f"canonical={assignment.orgpath_selector.prefix!r}"
            )
        if tenant_mode != assignment.orgpath_selector.match_mode:
            drift_reasons.append(
                f"matchMode drift: tenant={tenant_mode!r} "
                f"canonical={assignment.orgpath_selector.match_mode!r}"
            )

        if drift_reasons:
            plan.operations.append(PlannedOperation(
                op=OP_ARC_POLICY_UPDATE,
                target=name,
                reason="; ".join(drift_reasons),
                canonical=assignment,
                current_state=tenant,
                arc_definition_id=canonical_def_id,
            ))

    # Detect assignment_name-prefixed assignments in tenant that aren't in
    # canon — "phantom" assignments. Caller passes these via
    # ``current_arc_assignments`` filtered to the OrgTree- prefix.
    def _detect_arc_phantoms(
        self,
        arc_by_name: Mapping[str, Dict[str, Any]],
    ) -> List[str]:
        canonical_names = set(self._canon.arc_policy_assignments.keys())
        return [n for n in arc_by_name if n.startswith("OrgTree-") and n not in canonical_names]

    def apply(
        self,
        plan: PolicyTargetingPlan,
        dry_run: bool = True,
    ) -> PolicyTargetingReport:
        report = PolicyTargetingReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
        )
        for op in plan.operations:
            if op.op in OPS_GOVERNANCE_REVIEW:
                report.results.append(OperationResult(
                    op=op.op,
                    target=op.target,
                    status="skipped-manual",
                    detail=(
                        "Policy-consumer drift requires governance review; "
                        "never auto-applied."
                    ),
                ))
                continue
            if dry_run:
                report.results.append(OperationResult(
                    op=op.op,
                    target=op.target,
                    status="skipped-dry-run",
                    detail="Dry run — no tenant write issued.",
                ))
                continue
            try:
                self._execute(op)
                report.results.append(OperationResult(
                    op=op.op,
                    target=op.target,
                    status="written",
                ))
            except Exception as exc:  # pragma: no cover - network path
                logger.exception("Apply failed for %s", op.target)
                report.results.append(OperationResult(
                    op=op.op,
                    target=op.target,
                    status="failed",
                    detail=str(exc),
                ))
        return report

    def reconcile(
        self,
        current_intune_profiles: Optional[List[Dict[str, Any]]] = None,
        current_intune_assignments: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        current_arc_assignments: Optional[List[Dict[str, Any]]] = None,
        group_id_resolver: Optional[Dict[str, str]] = None,
        arc_definition_id_resolver: Optional[Dict[str, str]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        plan = self.plan(
            current_intune_profiles=current_intune_profiles,
            current_intune_assignments=current_intune_assignments,
            current_arc_assignments=current_arc_assignments,
            group_id_resolver=group_id_resolver,
            arc_definition_id_resolver=arc_definition_id_resolver,
        )
        report = self.apply(plan, dry_run=dry_run)
        return {"plan": plan.to_dict(), "report": report.to_dict()}

    def _execute(self, op: PlannedOperation) -> None:
        """Issue the write for an approved operation.

        Kept minimal — callers subclass to wire Graph and ARM credentials
        per their tenant. Default raises so ``dry_run=False`` is
        intentional.
        """
        raise RuntimeError(
            f"{op.op} requires subclass override of _execute — Phase 5 "
            "ships the planning + dispatch surface; Graph (Intune) and "
            "ARM (Azure Policy) credential wiring is deliberately "
            "deferred so operators choose the credential story that "
            "fits their tenant."
        )


# ---------------------------------------------------------------------------
# Helpers for matching tenant assignments against canon
# ---------------------------------------------------------------------------

_INCLUDE_TARGET_TYPES = frozenset({
    "#microsoft.graph.groupAssignmentTarget",
    "microsoft.graph.groupAssignmentTarget",
})
_EXCLUDE_TARGET_TYPES = frozenset({
    "#microsoft.graph.exclusionGroupAssignmentTarget",
    "microsoft.graph.exclusionGroupAssignmentTarget",
})


def _intune_target_group_id(assignment: Dict[str, Any]) -> Optional[str]:
    target = assignment.get("target") or {}
    return target.get("groupId")


def _intune_target_intent(assignment: Dict[str, Any]) -> Optional[str]:
    target = assignment.get("target") or {}
    odata = target.get("@odata.type") or target.get("odataType")
    if odata in _INCLUDE_TARGET_TYPES:
        return "include"
    if odata in _EXCLUDE_TARGET_TYPES:
        return "exclude"
    return None


def _intune_assignment_same_group(
    tenant: Dict[str, Any], group_id: Optional[str],
) -> bool:
    return (
        group_id is not None
        and _intune_target_group_id(tenant) == group_id
    )


def _intune_assignment_matches(
    tenant: Dict[str, Any],
    canonical: IntuneAssignment,
    group_id: Optional[str],
) -> bool:
    return (
        _intune_assignment_same_group(tenant, group_id)
        and _intune_target_intent(tenant) == canonical.intent
    )
