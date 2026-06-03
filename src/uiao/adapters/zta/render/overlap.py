"""Renderer for the ZT Assessment ↔ SCuBA overlap map (Markdown)."""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.zta.model import ZtReport
from uiao.adapters.zta.overlap import OverlapMap, build_overlap
from uiao.adapters.zta.render._common import sanitize_basename


def render_overlap_md(report: ZtReport, overlap: OverlapMap) -> str:
    """Render the overlap map as Markdown."""
    demo = " — DEMO DATA" if report.is_demo else ""
    lines = [
        "# Zero Trust Assessment ↔ CISA SCuBA — Overlap Map",
        "",
        f"**{report.tenant_name or '(unknown tenant)'} · {overlap.total} checks{demo}**",
        "",
        "| Bucket | Checks | Share |",
        "| --- | ---: | ---: |",
        f"| Shared surface (a ScubaGear baseline covers this area) | {overlap.shared} | {overlap.shared_pct}% |",
        f"| ZT-only (no ScubaGear baseline exists) | {overlap.zt_only} | {overlap.zt_only_pct}% |",
        "",
        "## By pillar",
        "",
        "| ZT pillar | Shared | ZT-only |",
        "| --- | ---: | ---: |",
    ]
    for pillar, row in overlap.by_pillar.items():
        lines.append(f"| {pillar} | {row.get('shared', 0)} | {row.get('zt-only', 0)} |")
    lines += ["", "## ZT surfaces", "", "| Surface | Checks |", "| --- | ---: |"]
    for surface, n in overlap.by_surface.items():
        lines.append(f"| {surface} | {n} |")
    lines += [
        "",
        "## SCuBA-only — covered by ScubaGear, not assessed by ZT",
        "",
        "| SCuBA product | Area |",
        "| --- | --- |",
    ]
    for item in overlap.scuba_only:
        lines.append(f"| {item.get('name', item.get('product', ''))} | {item.get('note', '')} |")
    lines += [
        "",
        "> **Surface-level, not 1:1.** A *shared* surface means ScubaGear has a baseline for that area — "
        "overwhelmingly Entra identity. ScubaGear's `aad` baseline is ~20 prescriptive policies, while the "
        "Zero Trust Assessment goes much deeper, so only a subset of shared-surface checks have a true "
        "ScubaGear counterpart. The two tools reinforce each other on identity and barely overlap elsewhere.",
        "",
    ]
    return "\n".join(lines)


def write_overlap(report: ZtReport, out_path: Path) -> Path:
    """Write the overlap map Markdown to ``out_path`` (or a default name in a dir)."""
    overlap = build_overlap(report)
    if out_path.is_dir():
        out_path = out_path / f"{sanitize_basename(report)}-zt-scuba-overlap.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_overlap_md(report, overlap), encoding="utf-8")
    return out_path
