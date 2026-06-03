"""Shared helpers for the Zero Trust Assessment renderers."""

from __future__ import annotations

import re

from uiao.adapters.zta.applicability import is_premium_gated
from uiao.adapters.zta.model import STATUS_ORDER, ZtReport, ZtTest
from uiao.adapters.zta.triage import Triage

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_basename(report: ZtReport) -> str:
    """Build a filesystem-safe base name from tenant + run date."""
    tenant = report.tenant_name or report.domain or "zt-report"
    date = (report.executed_at or "")[:10]
    raw = f"{tenant}-{date}" if date else tenant
    cleaned = _UNSAFE.sub("-", raw).strip("-")
    return cleaned or "zt-report"


def md_escape(text: str) -> str:
    """Make a string safe to drop into a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ").replace("\r", " ").strip()


def title_line(triage: Triage) -> str:
    """Common one-line report identity."""
    r = triage.report
    demo = " — DEMO DATA" if r.is_demo else ""
    return f"{r.tenant_name or '(unknown tenant)'} ({r.domain or 'n/a'}) · tool v{r.current_version or '?'} · run {(r.executed_at or '?')[:19]}{demo}"


def posture_sentence(triage: Triage) -> str:
    """One-sentence honest posture summary."""
    return (
        f"{triage.actionable_total} actionable findings (Failed/Investigate) "
        f"out of {len(triage.report.tests)} checks; "
        f"{triage.skipped_total} skipped (not applicable / unlicensed) and "
        f"{triage.planned_total} planned (tool roadmap) are excluded as non-gaps."
    )


def ordered_status_items(triage: Triage) -> list[tuple[str, int]]:
    """Status counts in canonical display order, omitting zeros."""
    return [(s, triage.status_counts.get(s, 0)) for s in STATUS_ORDER if triage.status_counts.get(s, 0)]


def premium_flag(test: ZtTest) -> str:
    """Short marker for premium-SKU gating."""
    return "premium" if is_premium_gated(test) else ""
