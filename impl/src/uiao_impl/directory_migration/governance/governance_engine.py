from pydantic import BaseModel
from typing import Optional
from core.drift.drift_engine import DriftState, DriftClassification


class GovernanceActionType(str):
    NONE = "none"
    REVIEW = "review"
    REMEDIATE = "remediate"
    ESCALATE = "escalate"


class GovernanceAction(BaseModel):
    """
    A commercial governance action triggered by drift.
    """
    action: GovernanceActionType
    reason: str
    severity: Optional[str] = None
    details: Optional[dict] = None


def determine_governance_action(drift: DriftState) -> GovernanceAction:
    """
    Map drift classification to a commercial governance action.
    """
    if not drift.drift_detected:
        return GovernanceAction(
            action=GovernanceActionType.NONE,
            reason="No drift detected."
        )

    if drift.classification == DriftClassification.MINOR:
        return GovernanceAction(
            action=GovernanceActionType.REVIEW,
            reason="Minor drift detected.",
            severity="low",
            details=drift.details
        )

    if drift.classification == DriftClassification.MAJOR:
        return GovernanceAction(
            action=GovernanceActionType.REMEDIATE,
            reason="Major drift detected.",
            severity="high",
            details=drift.details
        )

    # Fallback (should never happen)
    return GovernanceAction(
        action=GovernanceActionType.ESCALATE,
        reason="Unexpected drift classification.",
        severity="unknown",
        details=drift.details
    )
