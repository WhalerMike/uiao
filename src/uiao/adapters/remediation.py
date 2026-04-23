"""
remediation.py — Drift → Remediation workflow integration.

Converts POA&M findings from adapter drift into ServiceNow change requests
(or other ITSM systems). This closes the governance loop:

  vendor data → adapter → drift → POA&M → remediation ticket → resolution

The remediation module is adapter-agnostic: it consumes the standard
POA&M finding format produced by adapter_to_oscal.drift_to_poam_findings().
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def poam_findings_to_change_requests(
    findings: List[Dict[str, Any]],
    assignee: str = "sec-ops-team",
    priority_map: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """Convert POA&M findings into ServiceNow-format change request records.

    Each finding becomes a change request with:
    - short_description: finding title
    - description: finding description + related controls
    - priority: mapped from risk_level (high=1, moderate=2, low=3)
    - assigned_to: configurable assignee
    - category: "Security"
    - subcategory: "Remediation"
    - uiao_control_id: first related control (for UIAO adapter mapping)

    Args:
        findings: List of POA&M finding dicts (from drift_to_poam_findings).
        assignee: Default assignee for change requests.
        priority_map: Optional risk_level → priority mapping.

    Returns:
        List of ServiceNow-format change request dicts.
    """
    pmap = priority_map or {"high": "1", "moderate": "2", "low": "3"}

    change_requests: List[Dict[str, Any]] = []
    for i, finding in enumerate(findings, start=1):
        risk = finding.get("risk_level", "moderate")
        controls = finding.get("related_controls", [])

        cr = {
            "sys_id": f"CHG-AUTO-{i:04d}",
            "number": f"CHG-AUTO-{i:04d}",
            "short_description": finding.get("title", f"Remediation Item {i}"),
            "description": (
                finding.get("description", "") + (f"\n\nRelated controls: {', '.join(controls)}" if controls else "")
            ),
            "priority": pmap.get(risk, "2"),
            "state": "1",  # New
            "assigned_to": assignee,
            "category": "Security",
            "subcategory": "Remediation",
            "uiao_control_id": controls[0] if controls else "CM-3",
            "risk_level": risk,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "source": "uiao-poam-auto",
        }
        change_requests.append(cr)

    return change_requests


def generate_remediation_report(
    findings: List[Dict[str, Any]],
    change_requests: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Generate a remediation summary report.

    Args:
        findings: Original POA&M findings.
        change_requests: Generated change request records.

    Returns:
        Summary dict with counts, risk breakdown, and ticket references.
    """
    risk_counts: Dict[str, int] = {}
    for f in findings:
        r = f.get("risk_level", "unknown")
        risk_counts[r] = risk_counts.get(r, 0) + 1

    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total_findings": len(findings),
        "total_change_requests": len(change_requests),
        "by_risk_level": risk_counts,
        "change_request_ids": [cr["sys_id"] for cr in change_requests],
        "assignee": change_requests[0]["assigned_to"] if change_requests else "unassigned",
        "status": "pending_review",
    }
