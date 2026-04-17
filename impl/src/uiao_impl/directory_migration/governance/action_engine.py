from datetime import datetime
import uuid
from typing import Any, Dict

from core.drift.drift_engine import DriftState
from core.governance.action_model import Action


SEVERITY_MAP: Dict[str, str] = {
      "none": "none",
      "low": "low",
      "medium": "medium",
      "high": "high",
      "critical": "critical",
}


def _base_action(
      action_type: str,
      severity: str,
      reason: str,
      details: Dict[str, Any],
      orgpath: str | None = None,
) -> Action:
      return Action(
                id=str(uuid.uuid4()),
                action_type=action_type,
                severity=SEVERITY_MAP.get(severity, "medium"),
                reason=reason,
                created_at=datetime.utcnow(),
                details=details,
                orgpath=orgpath,
      )


def determine_action(drift: DriftState) -> Action:
      """
          Map a DriftState into a concrete governance Action.
              This is intentionally simple and deterministic for early UIAO-GOS.
                  """
      if not drift.drift_detected:
                return _base_action(
                              action_type="no-op",
                              severity="none",
                              reason="No drift detected",
                              details={"drift": drift.dict()},
                              orgpath=drift.orgpath,
                )

      drift_type = drift.details.get("drift_type", "generic-drift")

    if drift_type == "missing-resource":
              return _base_action(
                            action_type="create-resource",
                            severity="high",
                            reason="Required resource is missing",
                            details={"drift": drift.dict()},
                            orgpath=drift.orgpath,
              )

    if drift_type == "misconfiguration":
              return _base_action(
                            action_type="update-configuration",
                            severity="medium",
                            reason="Configuration does not match expected state",
                            details={"drift": drift.dict()},
                            orgpath=drift.orgpath,
              )

    if drift_type == "tag-drift":
              return _base_action(
                            action_type="update-tags",
                            severity="low",
                            reason="Tags differ from expected state",
                            details={"drift": drift.dict()},
                            orgpath=drift.orgpath,
              )

    # Fallback for anything not explicitly modeled yet
    return _base_action(
              action_type="investigate",
              severity="medium",
              reason=f"Unclassified drift type: {drift_type}",
              details={"drift": drift.dict()},
              orgpath=drift.orgpath,
    )
