"""Executive-summary renderer — concise Markdown for leadership."""

from __future__ import annotations

from uiao.adapters.zta.applicability import is_premium_gated
from uiao.adapters.zta.render._common import posture_sentence, title_line
from uiao.adapters.zta.triage import Triage

_TOP_N = 10


def render_executive(triage: Triage) -> str:
    """Render a one-page executive summary as Markdown."""
    r = triage.report
    lines: list[str] = [
        "# Zero Trust Assessment — Executive Summary",
        "",
        f"**{title_line(triage)}**",
        "",
        "## Posture",
        "",
        posture_sentence(triage),
        "",
        "## What matters now",
        "",
        f"- **{len(triage.worklist)} high-risk findings** require attention "
        f"(filter: risk={'/'.join(triage.risks)}, status={'/'.join(triage.statuses)}).",
        f"- **{triage.premium_gated_total} of {len(r.tests)} checks are premium/P2-SKU-gated** — "
        "verify each SKU's availability in the GCC / FedRAMP Moderate boundary before treating a "
        "skipped or failed result as a real gap.",
        "- Outcomes are **recomputed from per-test results**; the report's own summary block is not "
        "used (it does not reconcile).",
        "",
    ]

    if triage.worklist:
        lines.append(f"## Top {min(_TOP_N, len(triage.worklist))} findings")
        lines.append("")
        for t in triage.worklist[:_TOP_N]:
            badge = " _(premium SKU)_" if is_premium_gated(t) else ""
            lines.append(f"1. **[{t.pillar}]** {t.test_title}{badge}")
        lines.append("")

    lines.append("---")
    lines.append(
        "_Findings are tenant-specific and classified Controlled — do not publish raw results. "
        "Remediation is proposed, not applied (federal L3 actuation ceiling)._"
    )
    lines.append("")
    return "\n".join(lines)
