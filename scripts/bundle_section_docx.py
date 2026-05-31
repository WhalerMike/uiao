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
import re
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
    "modernization-specs",
    "operational-guides",
    "orgpath-narrative",
    "reference-architecture",
    "platform",
    "substrate",
    "validation-suites",
    "whitepapers",
]

# Filename stems (without .docx) skipped from every bundle.
SKIP_STEMS = {"index", "ROADMAP", "document-index", "TREE"}

# Sections that are organized as multi-chapter "books" (Book_NN.qmd +
# Book_NN_CPT_MM.qmd). For these, in addition to the whole-section
# bundle, emit one Book_NN-bundle.docx per book so a reader can download
# a single book as one Word file. Keyed by section directory name.
BOOK_BUNDLE_SECTIONS = {"orgpath-narrative"}

# Leading book identifier in a page filename, e.g. "Book_07a_CPT_03" ->
# "Book_07a" and "Book_07a" (the landing page) -> "Book_07a". Used to
# group a section's page .docx into per-book buckets.
BOOK_ID_RE = re.compile(r"^(Book_\d+[a-z]?)")

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
        # Skip the section bundle and any per-book bundle so a re-run (or
        # the per-book pass below) never folds a prior bundle into itself.
        if docx.name.endswith("-bundle.docx"):
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


def _book_sort_key(book_id: str) -> tuple[int, int]:
    """Order book ids so e.g. Book_07 precedes Book_07a precedes Book_08."""
    m = re.match(r"Book_(\d+)([a-z]?)$", book_id)
    if not m:
        return (0, 0)
    return (int(m.group(1)), 1 if m.group(2) else 0)


def _bundle_books(site_root: Path, section: str) -> list[tuple[bool, str]]:
    """Emit one ``Book_NN-bundle.docx`` per book within a chaptered section.

    Groups the section's page .docx by the leading ``Book_NN[a]`` filename
    token, concatenates each book's pages in filename order (landing page
    first, then chapters), and writes ``Book_NN-bundle.docx`` beside the
    book's landing page. Mirrors :func:`_bundle_one`'s TOC-strip and
    page-break behavior. Returns one ``(ok, message)`` tuple per book.
    """
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docxcompose.composer import Composer

    section_dir = site_root / section
    if not section_dir.is_dir():
        return [(False, f"{section}: directory not found at {section_dir}")]

    # Bucket page docx by book id. Files directly named Book_NN*.docx
    # qualify; section/per-book bundles and skip-stems are excluded.
    books: dict[str, list[Path]] = {}
    for docx in sorted(section_dir.rglob("*.docx")):
        if docx.name.endswith("-bundle.docx"):
            continue
        if docx.stem in SKIP_STEMS:
            continue
        m = BOOK_ID_RE.match(docx.stem)
        if not m:
            continue
        books.setdefault(m.group(1), []).append(docx)

    results: list[tuple[bool, str]] = []
    for book_id in sorted(books, key=_book_sort_key):
        pages = books[book_id]
        bundle_path = section_dir / f"{book_id}-bundle.docx"

        master = Document(str(pages[0]))
        tocs_stripped = _strip_toc_blocks(master)
        composer = Composer(master)
        for page in pages[1:]:
            master.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            chapter = Document(str(page))
            tocs_stripped += _strip_toc_blocks(chapter)
            composer.append(chapter)
        composer.save(str(bundle_path))

        results.append(
            (
                True,
                f"{section}/{book_id}: bundled {len(pages)} page(s) "
                f"(stripped {tocs_stripped} per-chapter TOC block(s)) -> "
                f"{bundle_path.relative_to(site_root.parent)}",
            )
        )

    if not results:
        results.append((False, f"{section}: no Book_NN page .docx found for per-book bundles"))
    return results


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
    parser.add_argument(
        "--canon-modernization",
        action="store_true",
        help="DEPRECATED no-op (kept for caller-flag compatibility). Per ADR-083, "
        "canon modernization pages moved into customer-documents at "
        "reference-architecture/, so they are now bundled by --all as a regular "
        "section. The flag will be removed in a follow-up PR once the Quarto "
        "workflow drops it from its invocation.",
    )
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

        # Chaptered sections also get one Book_NN-bundle.docx per book.
        # Per-book failures are logged but never fatal — a missing book
        # bundle must not block the site deploy.
        if section in BOOK_BUNDLE_SECTIONS:
            for ok_b, msg_b in _bundle_books(site_root, section):
                print(f"{'OK   ' if ok_b else 'WARN '} {msg_b}")

    # --canon-modernization is a deprecated no-op per ADR-083 (canon
    # modernization pages now live at customer-documents/reference-architecture/
    # and are bundled by --all as a regular section). Log if the flag was passed
    # so the workflow author notices.
    if args.canon_modernization:
        print(
            "INFO  --canon-modernization is a no-op per ADR-083; "
            "reference-architecture is bundled by --all as a regular section."
        )

    if args.section and failures:
        # Single-section mode: caller asked for a specific bundle, so
        # any failure is fatal.
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
