#!/usr/bin/env python3
"""What a book DECLARES it renders with must be what the build actually uses.

Every book's front matter said `reference-doc: lz-reference.docx` while
render_all_docx.sh and build_distribution_kit.sh passed `--reference-doc
aan-reference.docx` on the command line. Pandoc ignores Quarto's nested
`format.docx.reference-doc` key entirely, so the CLI silently won and the
declaration was decorative — wrong, and nothing noticed.

That is harmless right up until Quarto renders these books, because Quarto reads
the front matter and the CLI is not there to save it. `lz-reference.docx` does NOT
carry the AAN callout/FouoBanner paragraph styles — `aan-reference.docx` is
lz-reference plus exactly those styles (build_aan_reference.py). So the stale
declaration was a live trap: the first Quarto render would have quietly dropped
the house style, and the text would still be there, so it would have looked fine.

Three invariants:

  1. EVERY book declares one — a book with no `format.docx.reference-doc` inherits
     whatever the project default is. Under docs/ that is the MS-Learn reference,
     i.e. the wrong house style, chosen by omission.
  2. THEY ALL AGREE — one series, one reference doc. A book that disagrees renders
     differently from its siblings for no stated reason.
  3. THE DECLARATION MATCHES THE BUILD — the file the books name must be the file
     the render scripts pass, and it must exist on disk. This is the invariant that
     was actually broken.

Usage:
    python check_reference_doc_truth.py     # gate; exit 1 on any divergence
"""
from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ["render_all_docx.sh", "build_distribution_kit.sh"]


def declared(path: Path) -> str | None:
    """The reference-doc a book declares, or None. Handles BOTH front-matter
    styles in this corpus: flow (`docx: {reference-doc: x, ...}`, 17 books) and
    expanded (`docx:` then an indented `reference-doc: x`, 41 books)."""
    text = open(path, encoding="utf-8").read()
    fm = text.split("---", 2)
    if len(fm) < 3:
        return None
    m = re.search(r"reference-doc:\s*([A-Za-z0-9._-]+)", fm[1])
    return m.group(1) if m else None


def script_ref(path: Path) -> str | None:
    m = re.search(r'^REF="([^"]+)"', open(path, encoding="utf-8").read(), re.M)
    return m.group(1) if m else None


def main() -> int:
    books = sorted(glob.glob(str(HERE / "Vol_*_Book_*.qmd")))
    problems: list[str] = []

    # 1. every book declares one
    decls: dict[str, str] = {}
    for b in books:
        d = declared(Path(b))
        name = Path(b).name
        if not d:
            problems.append(
                f"  {name}: declares no format.docx.reference-doc — it would inherit the "
                f"project default (the wrong house style, chosen by omission)"
            )
            continue
        decls[name] = d

    # 2. they all agree
    values = set(decls.values())
    if len(values) > 1:
        for v in sorted(values):
            who = [n for n, d in decls.items() if d == v]
            problems.append(f"  {len(who)} book(s) declare {v!r} — e.g. {who[0]}")
        problems.append("  the series must name ONE reference doc; these disagree")

    # 3. the declaration matches what the build passes, and exists
    refs = {s: script_ref(HERE / s) for s in SCRIPTS if (HERE / s).exists()}
    for s, r in refs.items():
        if r is None:
            problems.append(f"  {s}: no REF= found — cannot verify the build agrees")
    script_values = {r for r in refs.values() if r}
    if len(script_values) > 1:
        problems.append(f"  the render scripts disagree with each other: {sorted(script_values)}")

    if len(values) == 1 and len(script_values) == 1:
        dv, sv = values.pop(), script_values.pop()
        if dv != sv:
            problems.append(
                f"  books declare {dv!r} but the build passes {sv!r} — Pandoc ignores the "
                f"front matter and the CLI wins, so the declaration is silently false. "
                f"Quarto reads the front matter and would render with {dv!r}."
            )
        if not (HERE / dv).exists():
            problems.append(f"  {dv!r} is declared but does not exist on disk")

    print("AAN reference-doc truth")
    print("=" * 68)
    print(f"books: {len(books)} | declaring: {len(decls)} | "
          f"distinct declarations: {len(set(decls.values()))} | "
          f"scripts checked: {len(refs)}")
    if problems:
        print(f"\nFAIL — {len(problems)} divergence(s):")
        print("\n".join(problems))
        return 1
    print("\nOK — every book declares the reference doc the build actually passes, "
          "and it exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
