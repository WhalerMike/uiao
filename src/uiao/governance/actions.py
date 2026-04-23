from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from uiao.ir.models.core import DriftState, Evidence

from .ownership import resolve_owner_for_ksi
from .sla import resolve_sla_days


@dataclass(frozen=True)
class GovernanceAction:
    """A single governance action derived from an Evidence + optional DriftState."""

    ksi_id: str
    control_id: Optional[str]
    policy_id: Optional[str]
    severity: str
    drift_classification: Optional[str]
    owner: str
    sla_days: int
    action_type: str
    description: str
    evidence_id: str


def classify_action_type(
    severity: str,
    drift_classification: Optional[str],
) -> str:
    """Deterministic mapping: severity + drift classification -> action type."""
    if drift_classification == "unauthorized":
        return "escalate"
    if severity in ("Critical", "High"):
        return "remediate"
    if severity in ("Medium", "Low"):
        return "monitor"
    return "review"


def build_governance_actions(
    evidence_list: List[Evidence],
    drift_states: List[DriftState],
) -> List[GovernanceAction]:
    """
    Build a deterministic list of GovernanceActions from Evidence + DriftStates.

    DriftState is matched by (resource_id, policy_ref) when available.
    One action is produced per Evidence object.
    """
    drift_index = {(d.resource_id, d.policy_ref): d for d in drift_states}

    actions: List[GovernanceAction] = []

    for e in evidence_list:
        ksi_id = str(e.data.get("ksi_id", "UNKNOWN"))
        severity = str(e.data.get("severity", "Medium"))
        resource_id = str(e.data.get("resource_id", ""))
        policy_ref = e.policy_id or ""

        drift: Optional[DriftState] = drift_index.get((resource_id, policy_ref))
        drift_classification = drift.classification if drift else None

        owner = resolve_owner_for_ksi(ksi_id)
        sla_days = resolve_sla_days(severity)
        action_type = classify_action_type(severity, drift_classification)

        description = (
            f"{action_type.upper()} for {ksi_id} (severity={severity}, drift={drift_classification or 'none'})"
        )

        actions.append(
            GovernanceAction(
                ksi_id=ksi_id,
                control_id=e.control_id,
                policy_id=e.policy_id,
                severity=severity,
                drift_classification=drift_classification,
                owner=owner,
                sla_days=sla_days,
                action_type=action_type,
                description=description,
                evidence_id=e.id,
            )
        )

    return actions
