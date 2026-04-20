from __future__ import annotations

from typing import Dict, List

from .actions import GovernanceAction


def summarize_actions(actions: List[GovernanceAction]) -> Dict[str, int]:
    """Aggregate governance actions by action type."""
    summary: Dict[str, int] = {}
    for a in actions:
        summary[a.action_type] = summary.get(a.action_type, 0) + 1
    return summary


def format_governance_report(actions: List[GovernanceAction]) -> str:
    """Human-readable governance report: summary + top 10 actions."""
    summary = summarize_actions(actions)
    lines = [
        "UIAO Governance Report",
        "----------------------",
        "By action type:",
    ]
    for action_type, count in sorted(summary.items()):
        lines.append(f"  {action_type:10s}: {count}")

    lines.append("")
    lines.append("Top actions:")
    for a in actions[:10]:
        lines.append(
            f"- {a.action_type.upper():10s} | {a.ksi_id:12s} | "
            f"sev={a.severity:8s} | owner={a.owner} | SLA={a.sla_days}d"
        )

    return "\n".join(lines)
