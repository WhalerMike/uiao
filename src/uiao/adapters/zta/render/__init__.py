"""Renderers for a Zero Trust Assessment triage view.

Five output formats, dispatched by :func:`write_outputs`:

* ``exec``  — one-page executive summary (Markdown)
* ``md``    — full digest (Markdown)
* ``xlsx``  — filterable Excel workbook
* ``html``  — slim annotated HTML companion
* ``csv``   — worklist CSV
"""

from __future__ import annotations

from pathlib import Path

from uiao.adapters.zta.render._common import sanitize_basename
from uiao.adapters.zta.render.csv_out import write_csv
from uiao.adapters.zta.render.executive import render_executive
from uiao.adapters.zta.render.html import render_html
from uiao.adapters.zta.render.markdown import render_markdown
from uiao.adapters.zta.render.xlsx import write_xlsx
from uiao.adapters.zta.triage import Triage

#: Selectable formats, in display order.
FORMATS: tuple[str, ...] = ("exec", "md", "xlsx", "html", "csv")

_SUFFIX = {
    "exec": ".exec.md",
    "md": ".digest.md",
    "xlsx": ".xlsx",
    "html": ".digest.html",
    "csv": ".worklist.csv",
}


def resolve_formats(requested: list[str] | None) -> list[str]:
    """Expand ``["all"]`` / ``None`` to every format; validate names."""
    if not requested or "all" in requested:
        return list(FORMATS)
    unknown = [f for f in requested if f not in FORMATS]
    if unknown:
        raise ValueError(f"unknown format(s): {', '.join(unknown)} (choose from {', '.join(FORMATS)} or 'all')")
    return [f for f in FORMATS if f in requested]


def write_outputs(triage: Triage, out_dir: Path, formats: list[str] | None = None) -> list[Path]:
    """Render the selected formats into ``out_dir``; return the written paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    base = sanitize_basename(triage.report)
    chosen = resolve_formats(formats)
    written: list[Path] = []
    for fmt in chosen:
        path = out_dir / f"{base}{_SUFFIX[fmt]}"
        if fmt == "exec":
            path.write_text(render_executive(triage), encoding="utf-8")
        elif fmt == "md":
            path.write_text(render_markdown(triage), encoding="utf-8")
        elif fmt == "html":
            path.write_text(render_html(triage), encoding="utf-8")
        elif fmt == "csv":
            write_csv(triage, path)
        elif fmt == "xlsx":
            write_xlsx(triage, path)
        written.append(path)
    return written


__all__ = [
    "FORMATS",
    "resolve_formats",
    "write_outputs",
    "render_executive",
    "render_markdown",
    "render_html",
    "write_csv",
    "write_xlsx",
]
