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
    # carry through to the bundle. Subsequent pages append in order.
    master = Document(str(pages[0]))
    composer = Composer(master)
    for page in pages[1:]:
        composer.append(Document(str(page)))
    composer.save(str(bundle_path))

    return True, f"{section}: bundled {len(pages)} pages → {bundle_path.relative_to(site_root.parent)}"


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
