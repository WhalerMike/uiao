"""Supplemental Entra authorization classifiers — SCuBA detection gaps.

This module hosts UIAO authorization rules that are *not* covered by the
cisagov/ScubaGear SCuBA baselines but are treated as material under
RFC-0026 continuous monitoring (UIAO_132) and ADR-012 DT-04 (DRIFT-AUTHZ).

Each classifier consumes normalized Entra tenant state and returns a
list of :class:`DriftState` objects with ``drift_class=DRIFT-AUTHZ`` —
one per at-risk resource. The list is empty when nothing was flagged,
which is how callers distinguish "no risk" from "classifier not run".

Rules registered here:

- :func:`detect_pim_groups_password_reset_escalation` — GAP-ENT-001,
  cisagov/ScubaGear#2072. Flags groups that are PIM-for-Groups-enrolled
  and also hold a password-reset-capable directory role assignment.

Roadmap: ``docs/docs/uiao-rfc-0026-roadmap.md`` (enhancement E4).
Registry: ``src/uiao/canon/gcc-boundary-gap-registry.yaml`` (GAP-ENT-001).
Drift taxonomy: ``src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from uiao.governance.drift import DRIFT_AUTHZ, _dict_delta
from uiao.ir.models.core import DriftState, ProvenanceRecord, canonical_hash

# Directory roles whose permission set includes the ability to reset
# passwords for privileged accounts. A principal that can pivot into any
# of these via a PIM-for-Groups elevation can bypass MFA on those target
# accounts (cisagov/ScubaGear#2072). Sourced from the Entra ID
# built-in role catalog; subset covers Password-Reset > Privileged.
_PASSWORD_RESET_ESCALATION_ROLES = frozenset(
    {
        "Password Administrator",
        "Helpdesk Administrator",
        "User Administrator",
        "Authentication Administrator",
        "Privileged Authentication Administrator",
        "Global Administrator",
    }
)

# Compensating-control identifier registered in
# src/uiao/canon/gcc-boundary-gap-registry.yaml under GAP-ENT-001.
POLICY_REF_PIM_GROUPS_ESCALATION = "UIAO-AUTHZ-001"


def _normalize_role_name(value: Any) -> Optional[str]:
    """Strip + normalize a role name for case-insensitive comparison."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def _role_names_for_group(group_id: str, group_role_assignments: Dict[str, Any]) -> List[str]:
    """Extract role names for a group, tolerating two input shapes.

    Accepts:
        {"group-a": ["Password Administrator", "Reports Reader"]}
        {"group-a": [{"role_name": "Password Administrator", ...}, ...]}
    """
    raw = group_role_assignments.get(group_id, [])
    names: List[str] = []
    for item in raw:
        if isinstance(item, str):
            name = _normalize_role_name(item)
        elif isinstance(item, dict):
            name = _normalize_role_name(item.get("role_name") or item.get("roleDefinitionDisplayName"))
        else:
            name = None
        if name:
            names.append(name)
    return names


def detect_pim_groups_password_reset_escalation(
    entra_state: Dict[str, Any],
    *,
    provenance: ProvenanceRecord,
    additional_risky_roles: Optional[Iterable[str]] = None,
) -> List[DriftState]:
    """Flag PIM-for-Groups enrollments that create a password-reset escalation path.

    Args:
        entra_state: Normalized Entra tenant snapshot. Expected keys:
            ``pim_for_groups`` — list of group IDs enrolled in PIM for Groups,
                OR a dict keyed by group ID with arbitrary metadata values
            ``group_role_assignments`` — dict mapping group ID to a list of
                role names (strings) or role dicts carrying a ``role_name``
                (or Graph-style ``roleDefinitionDisplayName``) field
            Both keys are optional; missing or empty values yield no findings.
        provenance: Provenance record for the scan, propagated to every
            emitted :class:`DriftState`.
        additional_risky_roles: Extend the default password-reset role set
            (e.g. for agency-specific custom roles). Case-sensitive match.

    Returns:
        List of :class:`DriftState` objects with ``drift_class=DRIFT-AUTHZ``
        and ``classification='unauthorized'``, one per at-risk group.
        Empty list when no escalation path is detected. Resource IDs are
        shaped ``entra:group:<group-id>`` so findings can be correlated
        with downstream entra-adapter claims.
    """
    findings: List[DriftState] = []

    pim_enrollment = entra_state.get("pim_for_groups") or []
    if isinstance(pim_enrollment, dict):
        pim_group_ids = list(pim_enrollment.keys())
    else:
        pim_group_ids = [str(gid) for gid in pim_enrollment]

    if not pim_group_ids:
        return findings

    group_role_assignments = entra_state.get("group_role_assignments") or {}
    if not isinstance(group_role_assignments, dict):
        return findings

    risky_roles = set(_PASSWORD_RESET_ESCALATION_ROLES)
    if additional_risky_roles:
        risky_roles.update(str(r).strip() for r in additional_risky_roles if r)

    for group_id in pim_group_ids:
        role_names = _role_names_for_group(group_id, group_role_assignments)
        escalating = [r for r in role_names if r in risky_roles]
        if not escalating:
            continue

        resource_id = f"entra:group:{group_id}"
        # Expected baseline: group is not simultaneously PIM-enrolled AND
        # holding a password-reset-capable role. Actual state carries the
        # observed escalating role set so downstream analysts see the
        # specific role causing the finding without re-querying the tenant.
        expected_state: Dict[str, Any] = {
            "pim_enabled": False,
            "password_reset_roles": [],
        }
        actual_state: Dict[str, Any] = {
            "pim_enabled": True,
            "password_reset_roles": sorted(escalating),
            "all_roles": sorted(role_names),
        }
        # Construct the DriftState directly (rather than through
        # build_drift_state) because escalation paths are always
        # "unauthorized" regardless of how many fields happen to differ;
        # the generic _classify_drift heuristic would downgrade a
        # 2-field delta to "risky". This mirrors how
        # drift.classify_authz_drift handles escalation_hit.
        #
        # DriftState carries expected/actual as hashes only, so the
        # forensic detail (specific escalating roles, full role set)
        # is folded into the delta under purpose-named keys — the
        # same pattern classify_identity_drift uses for
        # `identity_reasons`.
        delta: Dict[str, Any] = dict(_dict_delta(expected_state, actual_state))
        delta["escalating_roles"] = sorted(escalating)
        delta["all_roles"] = sorted(role_names)
        findings.append(
            DriftState(
                id=f"drift-authz:{resource_id}:{POLICY_REF_PIM_GROUPS_ESCALATION}",
                resource_id=resource_id,
                policy_ref=POLICY_REF_PIM_GROUPS_ESCALATION,
                expected_hash=canonical_hash(expected_state),
                actual_hash=canonical_hash(actual_state),
                drift_detected=True,
                classification="unauthorized",
                delta=delta,
                provenance=provenance,
                drift_class=DRIFT_AUTHZ,
            )
        )

    return findings
