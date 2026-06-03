"""Remediation playbook renderer — Markdown how-to-fix + CSV tracker.

Surfaces, per failed finding, the check's own remediation steps + Microsoft Learn
links + the admin console to fix it in + the failing-object deep links. No
scripts are authored — the content is the report's own guidance, restructured.
"""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from uiao.adapters.zta.model import ZtReport
from uiao.adapters.zta.remediation import RemediationCard, build_cards
from uiao.adapters.zta.render._common import sanitize_basename

_AFFECTED_CAP = 1200  # chars of the failing-object listing to inline per card


@dataclass(frozen=True)
class RemediationOutputs:
    """Paths written by :func:`write_remediation`."""

    playbook: Path
    tracker: Path
    count: int


def _summary(cards: list[RemediationCard]) -> list[str]:
    by_console = Counter(c.console for c in cards)
    by_pillar = Counter(c.pillar for c in cards)
    lines = ["## Summary", "", "| Console | Findings |", "| --- | ---: |"]
    lines += [f"| {console} | {n} |" for console, n in sorted(by_console.items(), key=lambda kv: -kv[1])]
    lines += ["", "| Pillar | Findings |", "| --- | ---: |"]
    lines += [f"| {pillar} | {n} |" for pillar, n in sorted(by_pillar.items())]
    lines.append("")
    return lines


def _card_md(card: RemediationCard) -> list[str]:
    why = card.rationale.replace("\n", " ").strip()
    if len(why) > 360:
        why = why[:357].rstrip() + "…"
    lines = [
        f"### `{card.test_id}` {card.title}",
        "",
        f"**{card.pillar}** · risk {card.risk} · severity {card.severity} · {card.bucket} · fix in **{card.console}**",
        "",
    ]
    if why:
        lines += [f"*Why it matters:* {why}", ""]
    lines += ["**How to fix — Microsoft's remediation action:**", ""]
    lines.append(
        card.remediation if card.remediation else "_No remediation text in the report; see the references below._"
    )
    lines.append("")
    lines.append(f"**Where:** [{card.console}]({card.console_url})")
    lines.append("")
    if card.learn:
        lines.append("**References:** " + " · ".join(f"[{title}]({url})" for title, url in card.learn[:6]))
        lines.append("")
    if card.affected:
        affected = card.affected
        truncated = len(affected) > _AFFECTED_CAP
        if truncated:
            affected = affected[:_AFFECTED_CAP].rstrip() + "\n\n_…affected-object list truncated; see the full report._"
        lines += [
            "<details><summary>Affected objects / deep links (from the report)</summary>",
            "",
            affected,
            "",
            "</details>",
            "",
        ]
    return lines


def render_playbook(report: ZtReport, cards: list[RemediationCard]) -> str:
    """Render the remediation playbook as Markdown, grouped by pillar."""
    demo = " — DEMO DATA" if report.is_demo else ""
    lines = [
        "# Zero Trust Assessment — Remediation Playbook",
        "",
        f"**{report.tenant_name or '(unknown tenant)'} ({report.domain or 'n/a'}) · "
        f"tool v{report.current_version or '?'} · {len(cards)} findings{demo}**",
        "",
        "> Findings are tenant-specific **Controlled** data — keep this in-boundary and do not "
        "publish raw results. Steps and links below are the assessment's own remediation guidance; "
        "apply changes only through your normal change-control process.",
        "",
    ]
    lines += _summary(cards)
    by_pillar: dict[str, list[RemediationCard]] = {}
    for c in cards:
        by_pillar.setdefault(c.pillar, []).append(c)
    for pillar in sorted(by_pillar):
        lines += [f"## {pillar}", ""]
        for card in by_pillar[pillar]:
            lines += _card_md(card)
    return "\n".join(lines)


_TRACKER_COLUMNS = [
    "TestId",
    "Pillar",
    "Risk",
    "SeverityScore",
    "PriorityBucket",
    "Console",
    "ConsoleUrl",
    "Title",
    "PrimaryReference",
    "Status",  # blank — for the team to track (Open / In progress / Done / Risk-accepted)
    "Owner",
    "Notes",
]


def write_tracker_csv(cards: list[RemediationCard], path: Path) -> Path:
    """Write a one-row-per-finding remediation tracker (with blank Status/Owner/Notes)."""
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=_TRACKER_COLUMNS)
        writer.writeheader()
        for c in cards:
            writer.writerow(
                {
                    "TestId": c.test_id,
                    "Pillar": c.pillar,
                    "Risk": c.risk,
                    "SeverityScore": c.severity,
                    "PriorityBucket": c.bucket,
                    "Console": c.console,
                    "ConsoleUrl": c.console_url,
                    "Title": c.title,
                    "PrimaryReference": c.learn[0][1] if c.learn else "",
                    "Status": "",
                    "Owner": "",
                    "Notes": "",
                }
            )
    return path


def write_remediation(
    report: ZtReport,
    out_dir: Path,
    *,
    statuses: tuple[str, ...] = ("Failed",),
) -> RemediationOutputs:
    """Render the remediation playbook + tracker into ``out_dir``."""
    cards = build_cards(report, statuses=statuses)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = sanitize_basename(report)
    playbook = out_dir / f"{base}-remediation-playbook.md"
    tracker = out_dir / f"{base}-remediation-tracker.csv"
    playbook.write_text(render_playbook(report, cards), encoding="utf-8")
    write_tracker_csv(cards, tracker)
    return RemediationOutputs(playbook=playbook, tracker=tracker, count=len(cards))
