#!/usr/bin/env python3
"""AAN owns its callout classes; Quarto must not be able to claim them.

Quarto CLAIMS `::: {.callout-*}` and rewrites those divs inside its own pipeline
BEFORE any user filter runs. The consequence, measured: rendering an AAN book with
Quarto dropped every house style — CalloutImportant, CalloutWarning, CalloutTip,
CaptionedFigure — and replaced the quiet navy-bordered panel with Quarto's own
red-bordered widget. Pointing the front matter at orgcomp-reference.docx and attaching
the filter did NOT help: the output was byte-identical to the untouched Quarto
render, because the filter never sees a div Quarto already took.

Renaming the classes to `aan-*` takes them back. Quarto has no opinion about
`.aan-important`, so orgcomp-callouts.lua maps it to the house docx style and
lz-style.css styles the HTML box. Verified across 6 books: pandoc@HEAD ==
pandoc@renamed == quarto@renamed, all six styles, including ExecSummary.

This gate keeps that true:

  1. NO QUARTO-OWNED CLASSES — a book using `::: {.callout-x}` hands the div back
     to Quarto. Under Pandoc it still looks right (the CLI passes the filter), so
     the regression is invisible until Quarto renders it — and the batch build is
     Pandoc, so nothing routine would surface it. That is exactly how the
     reference-doc bug hid for months.
  2. THE FILTER IS DECLARED — `.aan-*` styling depends on orgcomp-callouts.lua. Pandoc
     gets it from the CLI, but Quarto only applies filters a document declares. A
     book that uses the classes without declaring the filter renders unstyled.
  3. EVERY CLASS IS MAPPED — an `.aan-*` div whose class the filter does not map is
     a plain paragraph wearing a class name.

Usage:
    python check_callout_classes.py     # gate; exit 1 on any breach
"""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILTER = HERE / "orgcomp-callouts.lua"
FILTER_DECL = "orgcomp-callouts.lua"


def mapped_classes() -> set[str]:
    text = FILTER.read_text(encoding="utf-8")
    return set(re.findall(r'\["([a-z0-9-]+)"\]\s*=', text))


def main() -> int:
    books = sorted(glob.glob(str(HERE / "Vol_*_Book_*.qmd")))
    mapped = mapped_classes()
    problems: list[str] = []
    n_divs = 0

    for b in books:
        name = Path(b).name
        text = Path(b).read_text(encoding="utf-8")
        parts = text.split("---", 2)
        fm = parts[1] if len(parts) > 2 else ""

        # 1. no Quarto-owned callout classes
        stolen = re.findall(r"::: \{\.(callout-[a-z]+)\}", text)
        for cls in sorted(set(stolen)):
            problems.append(
                f"  {name}: uses '.{cls}' — Quarto claims .callout-* and rewrites the div "
                f"before the filter runs, silently dropping the house style. Use '.aan-{cls[8:]}'."
            )

        used = set(re.findall(r"::: \{\.(aan-[a-z]+)\}", text))
        n_divs += len(re.findall(r"::: \{\.aan-[a-z]+\}", text))

        # 2. the filter must be declared for Quarto to apply it
        if used and FILTER_DECL not in fm:
            problems.append(
                f"  {name}: uses {sorted(used)[0]!r} but declares no "
                f"'filters: [{FILTER_DECL}]' — Pandoc gets the filter from the CLI, "
                f"Quarto would render these divs unstyled."
            )

        # 3. every class used must be mapped
        for cls in sorted(used - mapped):
            problems.append(f"  {name}: '.{cls}' is not mapped in {FILTER.name}")

    print("AAN callout class ownership")
    print("=" * 68)
    print(f"books: {len(books)} | aan-* divs: {n_divs} | classes mapped by the filter: {len(mapped)}")
    if problems:
        print(f"\nFAIL — {len(problems)} breach(es):")
        print("\n".join(problems))
        return 1
    print(
        "\nOK — no Quarto-owned callout classes; every book that uses the AAN classes "
        "declares the filter, and every class it uses is mapped."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
