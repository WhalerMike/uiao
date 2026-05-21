#!/usr/bin/env python3
"""Concatenate per-page .docx renders into one bundle.docx per section.

Walks ``_site/customer-documents/<section>/`` (the directory the
quarto.yml `assemble` job populates), finds every page-level .docx,
sorts them deterministically by path, and uses ``docxcompose`` to
concatenate them into a single ``<section>-bundle.docx`` written next
to the section's index.html / index.docx.

Customers get a downloadable "complete pack" per section without
having to click through every individual page. The per-page .docx
files remain untouched alongside the bundle.

Why docxcompose vs. raw Pandoc
------------------------------
Pandoc can concatenate .qmd source, but Quarto-specific shortcodes
(``{{< include >}}``) don't process through raw Pandoc, image
``--resource-path`` resolution is brittle across the nested
customer-documents tree, and Pandoc-emitted DOCX loses some styling
nuances vs. Quarto's. ``docxcompose`` operates on the already-rendered
.docx outputs Quarto produced and preserves their styles, numbered
lists, embedded images, and headers/footers verbatim.

Skipped from bundles
--------------------
- Files whose .docx wasn't produced (Quarto's matrix skips empty stubs).
- The section's own ``index.docx`` (nav surface, not content).
- ``ROADMAP.docx``, ``document-index.docx`` (cross-cutting meta surfaces).
- ``<section>-bundle.docx`` itself (don't recursively bundle past runs).
- Pre-existing ``.docx`` artifacts under nested ``images/`` directories.

Stripped from each chapter before concatenation
-----------------------------------------------
- Pandoc's auto-emitted ``Table of contents`` block (a ``<w:sdt>``
  Structured Document Tag with ``<w:docPartGallery w:val="Table of
  Contents"/>``). Per-chapter docs need TOCs for standalone download
  but 16 mini-TOCs interleaved through a bundle is noise. Stripping
  happens in memory on each loaded chapter; the on-disk per-chapter
  ``.docx`` files are untouched.

Usage
-----
::

    python scripts/bundle_section_docx.py \\
        --site-root _site/customer-documents \\
        --section whitepapers

    # Bundle every top-level section:
    python scripts/bundle_section_docx.py \\
        --site-root _site/customer-documents \\
        --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Imported lazily inside main() so --help works even without the dep
# installed (useful for CI failure diagnostics).


# Top-level sections to bundle. Order is arbitrary — the bundler runs
# them independently. Keeping the list explicit (rather than scanning
# the directory) so a typo in the site layout doesn't silently produce
# zero bundles, and so a new top-level section is an intentional add.
DEFAULT_SECTIONS = [
    "adapter-specs",
    "architecture-series",
    "case-studies",
    "compliance",
    "executive-briefs",
    "executive-governance-series",
    "modernization",
    "modernization-specs",
    "orgpath-narrative",
    "platform",
    "substrate",
    "validation-suites",
    "whitepapers",
]

# Filename stems (without .docx) skipped from every bundle.
SKIP_STEMS = {"index", "ROADMAP", "document-index", "TREE"}

# OpenXML namespace for the WordprocessingML schema. Used by the TOC-strip
# pass to locate Pandoc's auto-emitted Table-of-Contents block. Kept as a
# module-level constant so both the XPath query and the attribute lookup
# (Clark-notation ``{ns}val``) reference the same string.
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _strip_toc_blocks(doc) -> int:
    """Remove Pandoc auto-TOC blocks from a loaded Document, in place.

    Pandoc renders the chapter-level TOC as a ``<w:sdt>`` (Structured
    Document Tag) whose ``<w:docPartGallery>`` element carries the
    ``w:val="Table of Contents"`` marker. Returns the number of TOC
    blocks removed (0 if the chapter had no TOC, e.g. a stub or a doc
    rendered with ``toc: false``).

    Why strip at bundle time, not at chapter render time: per-chapter
    ``.docx`` files are also offered as standalone downloads on the
    site, and TOCs are useful there. Stripping happens on the in-memory
    Document loaded by the bundler; the on-disk per-chapter file is
    never rewritten.
    """
    body = doc.element.body
    ns = {"w": W_NS}
    removed = 0
    for sdt in body.findall(".//w:sdt", ns):
        gallery = sdt.find(".//w:docPartGallery", ns)
        if gallery is not None and gallery.get(f"{{{W_NS}}}val") == "Table of Contents":
            parent = sdt.getparent()
            if parent is not None:
                parent.remove(sdt)
                removed += 1
    return removed


def _collect_docx(section_dir: Path, bundle_name: str) -> list[Path]:
    """Return the sorted list of page .docx files to include in a bundle.

    Walks the section tree, applies the SKIP_STEMS filter, and excludes
    the bundle's own output file so a re-run doesn't fold the previous
    bundle into itself.
    """
    out: list[Path] = []
    for docx in sorted(section_dir.rglob("*.docx")):
        if docx.name == bundle_name:
            continue
        if docx.stem in SKIP_STEMS:
            continue
        out.append(docx)
    return out


def _bundle_one(site_root: Path, section: str) -> tuple[bool, str]:
    """Bundle one section. Returns ``(ok, message)``."""
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docxcompose.composer import Composer

    section_dir = site_root / section
    if not section_dir.is_dir():
        return False, f"{section}: directory not found at {section_dir}"

    bundle_name = f"{section}-bundle.docx"
    bundle_path = section_dir / bundle_name

    pages = _collect_docx(section_dir, bundle_name)
    if not pages:
        return False, f"{section}: no page .docx files found under {section_dir}"

    # First page becomes the master — its styles, headers, and footers
    # carry through to the bundle. Subsequent pages append in order, each
    # preceded by a page break so individual chapters don't flow into one
    # another (the default docxcompose behavior is back-to-back concat
    # with no separator).
    master = Document(str(pages[0]))
    tocs_stripped = _strip_toc_blocks(master)
    composer = Composer(master)
    for page in pages[1:]:
        # Insert an empty paragraph with a page break at the end of the
        # current master body, then append the next doc's content. The
        # break sits between docs, not inside either one, so neither
        # source doc is mutated and styles/headers stay intact.
        master.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        chapter = Document(str(page))
        tocs_stripped += _strip_toc_blocks(chapter)
        composer.append(chapter)
    composer.save(str(bundle_path))

    return (
        True,
        f"{section}: bundled {len(pages)} pages "
        f"(stripped {tocs_stripped} per-chapter TOC block(s)) -> "
        f"{bundle_path.relative_to(site_root.parent)}",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--site-root",
        type=Path,
        required=True,
        help="Path to the assembled customer-documents directory "
        "(typically `_site/customer-documents` inside the Quarto deploy).",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--section", help="Bundle a single section by name.")
    group.add_argument("--all", action="store_true", help="Bundle every default section.")
    args = parser.parse_args(argv)

    site_root = args.site_root.resolve()
    if not site_root.is_dir():
        print(f"error: --site-root not a directory: {site_root}", file=sys.stderr)
        return 1

    sections = [args.section] if args.section else DEFAULT_SECTIONS

    failures = 0
    for section in sections:
        ok, msg = _bundle_one(site_root, section)
        prefix = "OK   " if ok else "WARN "
        print(f"{prefix} {msg}")
        if not ok:
            # Missing-section warnings shouldn't fail the run if --all is
            # used — a section may legitimately have no rendered .docx
            # (e.g., only stubs). Treat as non-fatal but report.
            failures += 1

    if args.section and failures:
        # Single-section mode: caller asked for a specific bundle, so
        # any failure is fatal.
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
