from __future__ import annotations

from typing import Any, Dict, List

from uiao.coverage.coverage import CoverageLink
from uiao.governance.actions import GovernanceAction


def build_lineage_index(
    links: List[CoverageLink],
    actions: List[GovernanceAction],
) -> Dict[str, Any]:
    """
    Build a machine-readable lineage index:
      NIST control -> {
        ksis: [...],
        scuba_policies: [...],
        evidence: [{id, hash}],
        governance_actions: [...]
      }
    """
    by_control: Dict[str, Dict[str, Any]] = {}

    actions_by_evidence: Dict[str, List[GovernanceAction]] = {}
    for a in actions:
        actions_by_evidence.setdefault(a.evidence_id, []).append(a)

    for link in links:
        entry = by_control.setdefault(
            link.nist_control,
            {
                "ksis": set(),
                "scuba_policies": set(),
                "evidence": [],
                "governance_actions": [],
            },
        )
        entry["ksis"].add(link.ksi_id)
        entry["scuba_policies"].add(link.scuba_policy_id)
        entry["evidence"].append({"id": link.evidence_id, "hash": link.evidence_hash})
        for a in actions_by_evidence.get(link.evidence_id, []):
            entry["governance_actions"].append(
                {
                    "evidence_id": a.evidence_id,
                    "action_type": a.action_type,
                    "owner": a.owner,
                    "sla_days": a.sla_days,
                    "severity": a.severity,
                }
            )

    normalized: Dict[str, Any] = {}
    for control, entry in by_control.items():
        normalized[control] = {
            "ksis": sorted(entry["ksis"]),
            "scuba_policies": sorted(entry["scuba_policies"]),
            "evidence": entry["evidence"],
            "governance_actions": entry["governance_actions"],
        }

    return normalized

