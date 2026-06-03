"""Slim annotated-HTML renderer.

A small self-contained companion to the tool's 3 MB report: the honest
roll-ups, applicability, and the worklist with per-finding flags — openable
without loading the original bundle.
"""

from __future__ import annotations

from html import escape

from uiao.adapters.zta.applicability import derive_applicability, is_premium_gated
from uiao.adapters.zta.model import STATUS_ORDER
from uiao.adapters.zta.render._common import posture_sentence, title_line
from uiao.adapters.zta.triage import Triage

_CSS = """
body{font-family:Segoe UI,Arial,sans-serif;margin:2rem;color:#1a1a1a;background:#fff}
h1{color:#1F3864} h2{color:#1F3864;border-bottom:2px solid #2E75B6;padding-bottom:.2rem;margin-top:2rem}
.meta{color:#555;margin-bottom:1rem}
.cards{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0}
.card{border:1px solid #ddd;border-radius:8px;padding:.75rem 1rem;min-width:9rem}
.card .n{font-size:1.6rem;font-weight:700;color:#1F3864} .card .l{color:#555;font-size:.85rem}
table{border-collapse:collapse;width:100%;margin:.5rem 0;font-size:.9rem}
th,td{border:1px solid #ddd;padding:.4rem .55rem;text-align:left;vertical-align:top}
th{background:#1F3864;color:#fff} tr:nth-child(even){background:#f5f8fc}
.risk-High{color:#C00000;font-weight:700} .risk-Medium{color:#BF8F00} .risk-Low{color:#548235}
.badge{display:inline-block;background:#FBE4D5;color:#843C0C;border-radius:4px;padding:0 .4rem;font-size:.75rem}
.note{color:#555;font-size:.85rem} footer{margin-top:2rem;color:#777;font-size:.8rem}
"""


def _card(n: int, label: str) -> str:
    return f'<div class="card"><div class="n">{n}</div><div class="l">{escape(label)}</div></div>'


def render_html(triage: Triage) -> str:
    """Render the slim annotated digest as a self-contained HTML string."""
    r = triage.report
    parts: list[str] = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        "<title>Zero Trust Assessment — Digest</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>Zero Trust Assessment — Digest</h1>",
        f'<p class="meta">{escape(title_line(triage))}</p>',
        f"<p>{escape(posture_sentence(triage))}</p>",
        '<div class="cards">',
        _card(triage.actionable_total, "actionable findings"),
        _card(triage.skipped_total, "skipped (non-gap)"),
        _card(triage.planned_total, "planned (non-gap)"),
        _card(triage.premium_gated_total, "premium-SKU-gated"),
        _card(len(r.tests), "checks total"),
        "</div>",
        '<p class="note">Outcomes are recomputed from per-test results; the report\'s own '
        "summary block is not used (it does not reconcile).</p>",
    ]

    # Pillar x status
    parts.append("<h2>Pillar &times; Status</h2><table><tr><th>Pillar</th>")
    parts.extend(f"<th>{escape(s)}</th>" for s in STATUS_ORDER)
    parts.append("</tr>")
    for pillar, counts in triage.pillar_crosstab.items():
        cells = "".join(f"<td>{counts.get(s, 0)}</td>" for s in STATUS_ORDER)
        parts.append(f"<tr><td>{escape(pillar)}</td>{cells}</tr>")
    parts.append("</table>")

    # Worklist
    parts.append(
        f"<h2>Worklist — risk={escape('/'.join(triage.risks))}, "
        f"status={escape('/'.join(triage.statuses))} ({len(triage.worklist)})</h2>"
    )
    parts.append(
        "<table><tr><th>TestId</th><th>Pillar</th><th>Risk</th><th>Title</th><th>SKU</th><th>Applicability</th></tr>"
    )
    for t in triage.worklist:
        badge = '<span class="badge">premium</span>' if is_premium_gated(t) else ""
        risk_cls = f"risk-{escape(t.test_risk)}"
        parts.append(
            f"<tr><td>{escape(t.test_id)}</td><td>{escape(t.pillar)}</td>"
            f'<td class="{risk_cls}">{escape(t.test_risk)}</td>'
            f"<td>{escape(t.test_title)}</td><td>{badge}</td>"
            f"<td>{escape(derive_applicability(t).value)}</td></tr>"
        )
    parts.append("</table>")

    parts.append(
        "<footer>Classification: Controlled · boundary: GCC-Moderate. "
        "Raw findings are tenant-specific vulnerability data — do not publish. "
        "Remediation is proposed, not applied (federal L3 actuation ceiling).</footer>"
    )
    parts.append("</body></html>")
    return "".join(parts)
