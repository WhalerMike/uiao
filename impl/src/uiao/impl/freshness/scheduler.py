from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Dict, List, Optional

from uiao.impl.freshness.engine import FreshnessRecord
from uiao.impl.governance.actions import GovernanceAction


@dataclasses.dataclass(frozen=True)
class RefreshJob:
    """A scheduled refresh job payload for a single stale evidence item."""

    evidence_id: str
    control_id: str
    owner: str
    severity: str
    sla_days: int
    age_days: float
    urgency: str
    dispatch_ref: str
    scheduled_at: str


def _urgency(age_days: float, sla_days: int) -> str:
    """Classify urgency based on how far past SLA the evidence is."""
    if age_days <= sla_days:
        return "normal"
    if age_days <= sla_days * 2:
        return "high"
    return "critical"


def build_refresh_schedule(
    freshness_records: List[FreshnessRecord],
    refresh_actions: List[GovernanceAction],
    now: Optional[datetime] = None,
) -> List[RefreshJob]:
    """
    Convert freshness records and refresh actions into scheduled job payloads.

    Only stale evidence with a matching refresh action is scheduled.
    Jobs are sorted by urgency (critical first) then by owner.

    Args:
        freshness_records: Output of build_freshness_records().
        refresh_actions:   Output of generate_refresh_actions().
        now:               Override wall-clock time (for testing).

    Returns:
        List of RefreshJob, sorted by urgency descending then owner ascending.
    """
    now = now or datetime.now(timezone.utc)
    scheduled_at = now.isoformat()

    action_index: Dict[str, GovernanceAction] = {
        a.evidence_id: a for a in refresh_actions if a.action_type == "refresh"
    }

    jobs: List[RefreshJob] = []
    for record in freshness_records:
        if record.status != "stale":
            continue
        action = action_index.get(record.evidence_id)
        if action is None:
            continue
        urgency = _urgency(record.age_days, record.threshold_days)
        dispatch_ref = (
            "workflow:ir-freshness-refresh"
            + "?evidence_id="
            + record.evidence_id
            + "&control_id="
            + record.control_id
            + "&owner="
            + action.owner
        )
        jobs.append(
            RefreshJob(
                evidence_id=record.evidence_id,
                control_id=record.control_id,
                owner=action.owner,
                severity=action.severity,
                sla_days=action.sla_days,
                age_days=record.age_days,
                urgency=urgency,
                dispatch_ref=dispatch_ref,
                scheduled_at=scheduled_at,
            )
        )

    urgency_order = {"critical": 0, "high": 1, "normal": 2}
    jobs.sort(key=lambda j: (urgency_order.get(j.urgency, 9), j.owner))
    return jobs


def group_jobs_by_owner(jobs: List[RefreshJob]) -> Dict[str, List[RefreshJob]]:
    """Group RefreshJob list by owner for batched dispatch."""
    groups: Dict[str, List[RefreshJob]] = {}
    for job in jobs:
        groups.setdefault(job.owner, []).append(job)
    return groups


def schedule_summary(jobs: List[RefreshJob]) -> str:
    """Return a human-readable summary of the refresh schedule."""
    if not jobs:
        return "No refresh jobs scheduled."
    by_urgency: Dict[str, int] = {}
    for job in jobs:
        by_urgency[job.urgency] = by_urgency.get(job.urgency, 0) + 1
    lines = [
        "Refresh schedule: " + str(len(jobs)) + " job(s)",
        "  Critical : " + str(by_urgency.get("critical", 0)),
        "  High     : " + str(by_urgency.get("high", 0)),
        "  Normal   : " + str(by_urgency.get("normal", 0)),
    ]
    owners = group_jobs_by_owner(jobs)
    lines.append("  Owners   : " + ", ".join(sorted(owners.keys())))
    return "\n".join(lines)

