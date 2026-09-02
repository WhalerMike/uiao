"""Day-2 kit figure references must satisfy two consumers at once.

The kit's `.md` files are consumed two ways, and the correct path differs:

1. **The rendered site.** Each `.md` is spliced into a wrapper `.qmd` one
   directory up via Quarto's `include` shortcode, which resolves relative
   paths against the *wrapper's* directory. So the source must say
   `servicenow-day2/figs/...`. A bare `figs/...` resolves to
   `orgcomp-series/figs/`, which holds no kit figures — Quarto then never
   copies the PNGs into `_site`, the site shows broken images, and
   `collect_kit()` finds nothing to ship. That is the
   "figure PNGs from _site: 0 (SVG sources from repo: 12)" warning the build
   printed on every deploy.

2. **The main kit zip**, where the same `.md` sits *beside* `figs/`. There the
   prefix must come back off, which `strip_figure_prefix` does on the way in.

Getting either half wrong ships broken images, so both are pinned here.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

REPO = Path(__file__).parent.parent
KIT = REPO / "docs" / "customer-documents" / "orgcomp-series" / "servicenow-day2"
FIGS = KIT / "figs"

_SPEC = importlib.util.spec_from_file_location("b", REPO / "scripts" / "build_day2_kit_download.py")
builder = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(builder)

# `![alt](path)` or `<img src="path">`
BARE = re.compile(r'(?:!\[[^\]]*\]\(|<img\s+src=")(?:\./)?figs/')
PREFIXED = re.compile(r'(?:!\[[^\]]*\]\(|<img\s+src=")(?:\./)?servicenow-day2/figs/')
ANY_PNG = re.compile(r"servicenow-day2/figs/([A-Za-z0-9._-]+\.png)")


def kit_docs() -> list[Path]:
    return sorted(KIT.glob("*.md"))


def test_there_are_kit_docs_with_figures():
    """Guard the guard — a suite that matches nothing would pass forever."""
    assert any(PREFIXED.search(p.read_text(encoding="utf-8")) for p in kit_docs())


@pytest.mark.parametrize("doc", kit_docs(), ids=lambda p: p.name)
def test_no_bare_figs_reference(doc: Path):
    """A bare `figs/` ref breaks the site render and stops the PNG shipping."""
    hits = BARE.findall(doc.read_text(encoding="utf-8"))
    assert not hits, (
        f"{doc.name} references figures as 'figs/...'; after Quarto's include "
        "that resolves to orgcomp-series/figs/ which has no kit figures. "
        "Use 'servicenow-day2/figs/...' — the zip builder strips it back."
    )


def test_every_referenced_figure_has_a_committed_svg_source():
    """Per ADR-093 the SVG is the source; the PNG is rasterized in CI."""
    missing = []
    for doc in kit_docs():
        for png in ANY_PNG.findall(doc.read_text(encoding="utf-8")):
            if not (FIGS / png).with_suffix(".svg").is_file():
                missing.append(f"{doc.name} -> {png}")
    assert not missing, f"referenced figures with no committed .svg source: {missing}"


def test_zip_rewrite_puts_paths_back_beside_the_docs():
    """In the main zip the .md sits beside figs/, so the prefix must come off."""
    doc = KIT / "CURRENT-STATE-OPERATOR-USAGE.md"
    out, n = builder.strip_figure_prefix(doc.read_text(encoding="utf-8"))
    assert n > 0, "expected figure refs to rewrite"
    assert "servicenow-day2/figs/" not in out
    assert "](figs/" in out or '<img src="figs/' in out


def test_the_two_rewrites_are_inverses():
    """Round-trip: strip for the zip, and the site form is recoverable."""
    doc = KIT / "CURRENT-STATE-OPERATOR-USAGE.md"
    original = doc.read_text(encoding="utf-8")
    stripped, n = builder.strip_figure_prefix(original)
    assert n > 0
    restored = re.sub(r'(!\[[^\]]*\]\(|<img\s+src=")figs/', r"\1servicenow-day2/figs/", stripped)
    assert restored == original
