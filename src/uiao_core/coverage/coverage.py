from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from uiao_core.ir.models.core import Evidence


@dataclass(frozen=True)
class CoverageLink:
    nist_control: str
    ksi_id: str
    scuba_policy_id: str
    evidence_id: str
    evidence_hash: str


def build_coverage_links(
    evidence_list: List[Evidence],
) -> List[CoverageLink]:
    """
    Build NIST -> KSI -> SCuBA policy -> Evidence -> hash links.

    Reads from Evidence.data keys: ksi_id, nist_control, scuba_policy_id.
    Falls back gracefully when keys are absent.
    """
    links: List[CoverageLink] = []
    for e in evidence_list:
        data = e.data or {}
        ksi_id = str(data.get("ksi_id", "UNKNOWN"))
        nist_control = str(data.get("nist_control", "UNKNOWN"))
        scuba_policy_id = str(data.get("scuba_policy_id", e.policy_id or "UNKNOWN"))
        links.append(
            CoverageLink(
                nist_control=nist_control,
                ksi_id=ksi_id,
                scuba_policy_id=scuba_policy_id,
                evidence_id=e.id,
                evidence_hash=e.hash(),
            )
        )
    return links


def format_ssp_section(links: List[CoverageLink]) -> str:
    """Render a simple SSP-style coverage section as Markdown."""
    by_control: Dict[str, List[CoverageLink]] = {}
    for link in links:
        by_control.setdefault(link.nist_control, []).append(link)

    lines: List[str] = []
    lines.append("# System Security Plan - Control Coverage")
    lines.append("")
    for control in sorted(by_control.keys()):
        lines.append(f"## Control {control}")
        for link in by_control[control]:
            lines.append(
                f"- KSI **{link.ksi_id}** via SCuBA policy {link.scuba_policy_id} "
                f"-> Evidence {link.evidence_id} (hash {link.evidence_hash})"
            )
        lines.append("")
    return "\n".join(lines)
