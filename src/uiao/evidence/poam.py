from __future__ import annotations

import json
from typing import Any, Dict, List

from uiao.evidence.bundle import EvidenceBundle
from uiao.ir.models.core import Evidence

# Severity order for sorting POA&M rows
_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


def _poam_row(evidence: Evidence) -> Dict[str, Any]:
    """Build one POA&M row from a failed or warned Evidence object."""
    ksi_id = evidence.data.get("ksi_id", "")
    severity = evidence.data.get("severity", "Medium")
    status = evidence.data.get("status", "FAIL")
    return {
        "ksi_id": ksi_id,
        "control_id": evidence.control_id or "",
        "policy_id": evidence.policy_id or "",
        "status": status,
        "severity": severity,
        "details": evidence.data.get("details", ""),
        "run_id": evidence.data.get("run_id", ""),
        "tenant_id": evidence.data.get("tenant_id", ""),
        "evidence_id": evidence.id,
        "evidence_hash": evidence.hash(),
        "remediation_sla_days": _default_sla(severity),
        "recommended_action": _default_action(status, ksi_id),
    }


def _default_sla(severity: str) -> int:
    return {"Critical": 15, "High": 30, "Medium": 60, "Low": 90}.get(severity, 60)


def _default_action(status: str, ksi_id: str) -> str:
    if status == "FAIL":
        return f"Remediate control {ksi_id} — implementation gap identified."
    if status == "WARN":
        return f"Review control {ksi_id} — partial compliance, remediation recommended."
    return "No action required."


def build_poam(bundle: EvidenceBundle) -> List[Dict[str, Any]]:
    """
    Generate a deterministic POA&M from an EvidenceBundle.
    Only FAIL and WARN evidence entries are included.
    Rows are sorted by severity then KSI ID.
    """
    rows = [_poam_row(e) for e in bundle.evidence if e.evaluation.get("failed") or e.evaluation.get("warning")]
    rows.sort(key=lambda r: (_SEVERITY_ORDER.get(r["severity"], 99), r["ksi_id"]))
    return rows


def poam_to_json(rows: List[Dict[str, Any]]) -> str:
    """Serialize POA&M rows to canonical JSON string."""
    return json.dumps(rows, sort_keys=True, indent=2, ensure_ascii=False)


def poam_summary(rows: List[Dict[str, Any]]) -> str:
    total = len(rows)
    by_severity: Dict[str, int] = {}
    for r in rows:
        by_severity[r["severity"]] = by_severity.get(r["severity"], 0) + 1
    lines = [f"POA&M Summary: {total} items"]
    for sev in ["Critical", "High", "Medium", "Low"]:
        count = by_severity.get(sev, 0)
        if count:
            lines.append(f"  {sev:10s}: {count}")
    return "\n".join(lines)
