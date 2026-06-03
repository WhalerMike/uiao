"""Full Markdown digest renderer."""

from __future__ import annotations

from uiao.adapters.zta.applicability import derive_applicability
from uiao.adapters.zta.model import STATUS_ORDER
from uiao.adapters.zta.render._common import (
    md_escape,
    ordered_status_items,
    posture_sentence,
    premium_flag,
    title_line,
)
from uiao.adapters.zta.triage import Triage


def render_markdown(triage: Triage) -> str:
    """Render the full triage digest as Markdown."""
    r = triage.report
    lines: list[str] = [
        "# Zero Trust Assessment — Digest",
        "",
        f"**{title_line(triage)}**",
        "",
        posture_sentence(triage),
        "",
        "## Outcome",
        "",
        "_Recomputed from per-test results. The report's `TestResultSummary` block is not used "
        "(it does not reconcile with the per-test statuses)._",
        "",
        "| Status | Count | Note |",
        "| --- | ---: | --- |",
    ]
    notes = {
        "Failed": "finding",
        "Investigate": "finding — manual review",
        "Passed": "",
        "Skipped": "not applicable / unlicensed — **not a gap**",
        "Planned": "tool roadmap — **not a gap**",
        "Error": "check could not run",
    }
    for status, count in ordered_status_items(triage):
        lines.append(f"| {status} | {count} | {notes.get(status, '')} |")
    lines.append("")

    # Pillar x Status
    lines.append("## Pillar × Status")
    lines.append("")
    lines.append("| Pillar | " + " | ".join(STATUS_ORDER) + " |")
    lines.append("| --- | " + " | ".join(["---:"] * len(STATUS_ORDER)) + " |")
    for pillar, row in triage.pillar_crosstab.items():
        cells = " | ".join(str(row.get(s, 0)) for s in STATUS_ORDER)
        lines.append(f"| {md_escape(pillar)} | {cells} |")
    lines.append("")

    # Applicability
    lines.append("## Applicability (GCC / FedRAMP Moderate)")
    lines.append("")
    lines.append(
        f"{triage.premium_gated_total} of {len(r.tests)} checks cite a premium/P2-class SKU. "
        "Derived from `SkippedReason` + `TestMinimumLicense` — verify each SKU's boundary "
        "availability before scoring a skip/fail as a real gap."
    )
    lines.append("")
    lines.append("| Applicability | Count |")
    lines.append("| --- | ---: |")
    for tag, count in sorted(triage.applicability_counts.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {tag} | {count} |")
    lines.append("")
    lines.append(
        f"TestId namespaces: {triage.namespace_counts.get('numeric', 0)} numeric (Graph checks), "
        f"{triage.namespace_counts.get('guid', 0)} GUID (Azure checks)."
    )
    lines.append("")

    # Worklist
    lines.append(
        f"## Worklist — risk={'/'.join(triage.risks)}, status={'/'.join(triage.statuses)} ({len(triage.worklist)})"
    )
    lines.append("")
    lines.append("| TestId | Pillar | Risk | Title | SKU | Impact | Effort | Applicability |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for t in triage.worklist:
        lines.append(
            "| "
            + " | ".join(
                [
                    md_escape(t.test_id),
                    md_escape(t.pillar),
                    md_escape(t.test_risk),
                    md_escape(t.test_title),
                    premium_flag(t),
                    md_escape(t.test_impact),
                    md_escape(t.test_implementation_cost),
                    md_escape(derive_applicability(t).value),
                ]
            )
            + " |"
        )
    lines.append("")
    lines.append("---")
    lines.append(
        "_Classification: Controlled · boundary: GCC-Moderate. Raw findings are tenant-specific "
        "vulnerability data — do not publish. Remediation is proposed, not applied (L3 ceiling)._"
    )
    lines.append("")
    return "\n".join(lines)
