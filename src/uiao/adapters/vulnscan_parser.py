"""
vulnscan_parser.py — Vulnerability scanner output parsing.

Handles JSON output from Tenable, Qualys, or generic scanner formats.
"""

from __future__ import annotations

from typing import Dict, List

_SEVERITY_PRIORITY = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def parse_scan_results(scan_data: dict) -> List[dict]:
    """Extract findings from a vulnerability scan result.

    Args:
        scan_data: Parsed JSON with a "findings" list.

    Returns:
        List of finding dicts normalized for adapter.normalize().
    """
    findings: List[dict] = []
    for item in scan_data.get("findings", []):
        findings.append(
            {
                "finding_id": item.get("finding_id", ""),
                "cve_id": item.get("cve_id", ""),
                "severity": item.get("severity", "unknown"),
                "cvss_score": item.get("cvss_score", 0.0),
                "affected_asset": item.get("affected_asset", ""),
                "state": item.get("state", "open"),
                "title": item.get("title", ""),
                "plugin_id": item.get("plugin_id", ""),
                "first_seen": item.get("first_seen", ""),
                "last_seen": item.get("last_seen", ""),
            }
        )
    return findings


def summarize_findings(findings: List[dict]) -> dict:
    """Produce a severity summary from parsed findings.

    Returns:
        Dict with counts per severity + overall risk score.
    """
    counts: Dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    open_count = 0
    for f in findings:
        sev = f.get("severity", "info").lower()
        counts[sev] = counts.get(sev, 0) + 1
        if f.get("state") == "open":
            open_count += 1

    max_severity = max(
        (sev for sev, cnt in counts.items() if cnt > 0),
        key=lambda s: _SEVERITY_PRIORITY.get(s, 0),
        default="info",
    )

    return {
        "total": len(findings),
        "open": open_count,
        "by_severity": counts,
        "max_severity": max_severity,
    }
