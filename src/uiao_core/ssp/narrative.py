from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from uiao_core.coverage.coverage import CoverageLink
from uiao_core.governance.actions import GovernanceAction


@dataclass(frozen=True)
class ControlNarrative:
    nist_control: str
    summary: str
    ksis: List[str]
    scuba_policies: List[str]
    evidence_ids: List[str]
    evidence_hashes: List[str]
    drift_status: Optional[str]
    governance_action_types: List[str]


def build_control_narratives(
    links: List[CoverageLink],
    actions: List[GovernanceAction],
) -> List[ControlNarrative]:
    """Build SSP-ready narratives per NIST control from coverage + governance."""
    by_control: Dict[str, List[CoverageLink]] = {}
    for link in links:
        by_control.setdefault(link.nist_control, []).append(link)

    actions_by_evidence: Dict[str, List[GovernanceAction]] = {}
    for a in actions:
        actions_by_evidence.setdefault(a.evidence_id, []).append(a)

    narratives: List[ControlNarrative] = []

    for control, control_links in sorted(by_control.items()):
        ksis = sorted({lnk.ksi_id for lnk in control_links})
        scuba_policies = sorted({lnk.scuba_policy_id for lnk in control_links})
        evidence_ids = [lnk.evidence_id for lnk in control_links]
        evidence_hashes = [lnk.evidence_hash for lnk in control_links]

        action_types: List[str] = []
        for lnk in control_links:
            for a in actions_by_evidence.get(lnk.evidence_id, []):
                action_types.append(a.action_type)
        action_types = sorted(set(action_types))

        drift_status: Optional[str] = None
        if any(t in ("escalate", "remediate") for t in action_types):
            drift_status = "at-risk"
        elif action_types:
            drift_status = "monitored"

        summary = (
            f"Control {control} is implemented via KSIs {', '.join(ksis)} "
            f"and SCuBA policies {', '.join(scuba_policies)}. "
            f"Evidence objects {', '.join(evidence_ids)} with hashes "
            f"{', '.join(evidence_hashes)} demonstrate implementation."
        )

        narratives.append(
            ControlNarrative(
                nist_control=control,
                summary=summary,
                ksis=ksis,
                scuba_policies=scuba_policies,
                evidence_ids=evidence_ids,
                evidence_hashes=evidence_hashes,
                drift_status=drift_status,
                governance_action_types=action_types,
            )
        )

    return narratives


def format_ssp_markdown(narratives: List[ControlNarrative]) -> str:
    """Render SSP narrative sections as Markdown."""
    lines: List[str] = []
    lines.append("# System Security Plan - Narrative")
    lines.append("")

    for n in narratives:
        lines.append(f"## Control {n.nist_control}")
        lines.append("")
        lines.append(n.summary)
        lines.append("")
        if n.drift_status:
            lines.append(
                f"Drift / governance status: {n.drift_status} "
                f"({', '.join(n.governance_action_types)})"
            )
            lines.append("")

    return "\n".join(lines)
