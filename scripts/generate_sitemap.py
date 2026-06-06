#!/usr/bin/env python3
"""Regenerate the whole-site sitemap tree for docs/sitemap.qmd.

Reads the navbar + sidebar definitions from ``docs/_quarto.yml`` — the
single source of truth for the site's navigation — and emits a Markdown
file with the *entire* navigation rendered as nested, clickable lists:
one ``##`` section per sidebar pane (Findings, Academy, Reference
Architecture, Canonical Specs, ADRs, Schemas, Customer Documents, About),
plus a "Quick links" section for navbar-only pages (Home, Download, the
Getting-started menu) that no sidebar pane covers.

The point: the sidebar panes are useful for reading *within* a section,
but there is no single page where a reader can scan the whole corpus at
once. This generator produces exactly that — a flat, scrollable "browse
everything" page that mirrors the sidebar tree faithfully because it is
derived from the same ``_quarto.yml`` the sidebar is.

docs/sitemap.qmd includes the output via Quarto's ``{{< include >}}``
shortcode, so the visible tree cannot drift from the navigation config.

Link/title resolution
---------------------
Every navigation entry is a path relative to ``docs/`` (the Quarto
project root). Titles are read from each target ``.qmd``'s frontmatter
``title:`` (falling back to a prettified filename stem); links rewrite
``.qmd`` → ``.html`` and are emitted relative to ``docs/`` (where
sitemap.qmd lives), so they resolve on the published site.

CI / drift
----------
Output is committed; ``.github/workflows/sitemap-drift.yml`` re-runs the
script on every PR touching ``docs/_quarto.yml``, any ``docs/**/*.qmd``
(titles come from frontmatter), the committed output, or this script,
and fails if the committed file diverges. Mirrors the anti-drift posture
of ``generate_document_index.py``.

Usage
-----
::

    python scripts/generate_sitemap.py --output docs/data/sitemap-tree.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
# Quarto's project root is docs/ (that is where _quarto.yml lives), so
# every href/section path in the config is resolved relative to it.
DOCS_DIR = REPO_ROOT / "docs"
QUARTO_CONFIG = DOCS_DIR / "_quarto.yml"
DEFAULT_OUTPUT = DOCS_DIR / "data" / "sitemap-tree.md"
# The sitemap page itself (relative to docs/) — excluded from its own
# listing so the tree does not link to the page you are already on.
SELF_PATH = "sitemap.qmd"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)

# Cache of resolved titles so we read each .qmd at most once.
_TITLE_CACHE: dict[str, str] = {}


def _prettify_stem(stem: str) -> str:
    """Fallback title from a filename stem (``foo-bar`` → ``Foo Bar``)."""
    return stem.replace("-", " ").replace("_", " ").strip().title() or stem


def _title_for(rel_path: str) -> str:
    """Resolve a navigation .qmd path to its frontmatter title.

    ``rel_path`` is relative to ``docs/``. Missing file or missing
    ``title:`` falls back to the prettified filename stem so the sitemap
    never carries a raw path as link text.
    """
    if rel_path in _TITLE_CACHE:
        return _TITLE_CACHE[rel_path]
    target = DOCS_DIR / rel_path
    title = _prettify_stem(Path(rel_path).stem)
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        print(f"  warning: sitemap entry not found on disk: {rel_path}", file=sys.stderr)
        _TITLE_CACHE[rel_path] = title
        return title
    m = _FRONTMATTER_RE.match(text)
    if m:
        try:
            fm = yaml.safe_load(m.group("body"))
        except yaml.YAMLError:
            fm = None
        if isinstance(fm, dict) and fm.get("title"):
            title = str(fm["title"]).strip()
    _TITLE_CACHE[rel_path] = title
    return title


def _escape_link_text(text: str) -> str:
    """Escape markdown link-text metacharacters (``[`` / ``]``)."""
    return text.replace("[", r"\[").replace("]", r"\]")


def _url_for(rel_path: str) -> str:
    """Rewrite a .qmd nav path to the site-relative .html URL."""
    return rel_path[:-4] + ".html" if rel_path.endswith(".qmd") else rel_path


def _link(rel_path: str, text: str | None = None) -> str:
    """Markdown link to a nav entry's rendered page."""
    label = text if text is not None else _title_for(rel_path)
    return f"[{_escape_link_text(label)}]({_url_for(rel_path)})"


def _is_path(value: str) -> bool:
    return isinstance(value, str) and value.endswith(".qmd")


def _bullet(depth: int, body: str) -> str:
    return f"{'  ' * depth}- {body}"


def _render_contents(items: list, depth: int, lines: list[str]) -> None:
    """Render a sidebar/menu ``contents`` list as nested bullets."""
    for item in items or []:
        if isinstance(item, str):
            lines.append(_bullet(depth, _link(item)))
        elif isinstance(item, dict):
            if "section" in item:
                sec = item["section"]
                head = _link(sec) if _is_path(sec) else f"**{sec}**"
                lines.append(_bullet(depth, head))
                _render_contents(item.get("contents", []), depth + 1, lines)
            elif "menu" in item:
                lines.append(_bullet(depth, f"**{item.get('text', '')}**"))
                _render_contents(item["menu"], depth + 1, lines)
            elif "href" in item:
                lines.append(_bullet(depth, _link(item["href"], item.get("text"))))
            elif "text" in item:
                lines.append(_bullet(depth, item["text"]))


def _collect_sidebar_paths(sidebar: list, acc: set[str]) -> None:
    """Gather every .qmd path referenced anywhere in the sidebar panes."""

    def walk(items: list) -> None:
        for item in items or []:
            if isinstance(item, str):
                if _is_path(item):
                    acc.add(item)
            elif isinstance(item, dict):
                for key in ("section", "href"):
                    val = item.get(key)
                    if _is_path(val):
                        acc.add(val)
                walk(item.get("contents", []))
                walk(item.get("menu", []))

    for pane in sidebar or []:
        walk(pane.get("contents", []))


def _render_quick_links(navbar: dict, sidebar_paths: set[str], lines: list[str]) -> None:
    """Render navbar entries that no sidebar pane already covers.

    Captures Home, Download, and the Getting-started menu — pages
    reachable only from the navbar — so the sitemap is genuinely
    "everything," not just the sidebar panes. Entries already present in
    a sidebar pane (e.g. the About menu) are skipped to avoid duplication.
    """
    quick: list[str] = []
    for slot in ("left", "right"):
        for item in navbar.get(slot, []) or []:
            if not isinstance(item, dict):
                continue
            if "menu" in item:
                fresh = [
                    m
                    for m in item["menu"]
                    if isinstance(m, dict)
                    and m.get("href")
                    and m["href"] not in sidebar_paths
                    and m["href"] != SELF_PATH
                ]
                if fresh:
                    quick.append(_bullet(0, f"**{item.get('text', '')}**"))
                    _render_contents(fresh, 1, quick)
            elif item.get("href"):
                if item["href"] not in sidebar_paths and item["href"] != SELF_PATH:
                    quick.append(_bullet(0, _link(item["href"], item.get("text"))))
    if quick:
        lines.append("## Quick links")
        lines.append("")
        lines.extend(quick)
        lines.append("")


def render() -> str:
    config = yaml.safe_load(QUARTO_CONFIG.read_text(encoding="utf-8"))
    website = config.get("website", {}) if isinstance(config, dict) else {}
    navbar = website.get("navbar", {}) or {}
    sidebar = website.get("sidebar", []) or []

    sidebar_paths: set[str] = set()
    _collect_sidebar_paths(sidebar, sidebar_paths)

    lines: list[str] = [
        "<!-- GENERATED by scripts/generate_sitemap.py — do not hand-edit. -->",
        "<!-- Regenerate: python scripts/generate_sitemap.py --output docs/data/sitemap-tree.md -->",
        "",
    ]

    _render_quick_links(navbar, sidebar_paths, lines)

    for pane in sidebar:
        title = pane.get("title") or pane.get("id") or "Section"
        lines.append(f"## {title}")
        lines.append("")
        for item in pane.get("contents", []) or []:
            # Promote first-level sections to H3 so the page TOC lets a
            # reader jump between groups; deeper levels stay as bullets.
            if isinstance(item, dict) and "section" in item:
                sec = item["section"]
                head = _link(sec) if _is_path(sec) else sec
                lines.append(f"### {head}")
                lines.append("")
                body: list[str] = []
                _render_contents(item.get("contents", []), 0, body)
                lines.extend(body)
                lines.append("")
            else:
                _render_contents([item], 0, lines)
        # Normalize trailing blank line between panes.
        if lines and lines[-1] != "":
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Write output to this path (default: stdout). Conventional location: "
            f"{DEFAULT_OUTPUT.relative_to(REPO_ROOT)}"
        ),
    )
    args = parser.parse_args(argv)

    rendered = render()

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        out_path = args.output.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Force LF newlines so output is byte-identical between Windows
        # authoring and Linux CI (matches generate_document_index.py).
        out_path.write_bytes(rendered.encode("utf-8"))
        try:
            shown = out_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = out_path
        print(f"wrote sitemap tree to {shown}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
