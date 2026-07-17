#!/usr/bin/env python3
"""No book may be bylined to a specific agency or an internal team.

The series is being made generic to the federal government so it can publish
without the "INTERNAL" framing. Authorship is the most visible piece of agency
identity in a book: it is in the front matter, it renders into the .docx title
block and the deck, and it is the first thing a reader outside the agency sees.
50 of 58 books were bylined "SSA Cloud Services Team".

This gate holds the line as the de-brand proceeds:

  1. EVERY BOOK DECLARES AN AUTHOR — silence is not neutrality. A book with no
     `author:` renders with whatever the project supplies, or nothing, and the
     omission is invisible in review. (Vol_0_Book_00a had none; it also shipped
     with no `format:` block, found separately.)
  2. NO AGENCY OR INTERNAL-TEAM BYLINE — an author naming a specific agency, its
     CIO office, or an internal team name is the thing being removed.

A personal byline is NOT agency identity and is deliberately allowed: two books
are attributed to their author by name, which says nothing about which agency runs
the estate.

This gate covers authorship ONLY. It is not a general de-brand check — agency
identity in prose, figures, and domains is a larger surface handled separately.
Passing this does not mean a book is generic.

Usage:
    python check_generic_authorship.py     # gate; exit 1 on any breach
"""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Substrings that make a byline agency-specific or internal. Matched
# case-insensitively against the author value only.
FORBIDDEN = [
    "ssa",
    "social security",
    "csi team",
    "cloud services infrastructure",
    "cio office",
    "office of information security",
    "ois",
]


def author_of(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    m = re.search(r'^author:\s*"?([^"\n]+)"?', parts[1], re.M)
    return m.group(1).strip() if m else None


def offending(value: str) -> list[str]:
    # word-boundary match so "OIS" does not fire inside e.g. "Poison"
    return [w for w in FORBIDDEN if re.search(r"\b" + re.escape(w) + r"\b", value, re.I)]


def main() -> int:
    books = sorted(glob.glob(str(HERE / "Vol_*_Book_*.qmd")))
    problems: list[str] = []
    authors: dict[str, int] = {}

    for b in books:
        name = Path(b).name
        a = author_of(Path(b))
        if not a:
            problems.append(
                f"  {name}: declares no author — silence is not neutrality; the omission is invisible in review"
            )
            continue
        authors[a] = authors.get(a, 0) + 1
        hits = offending(a)
        if hits:
            problems.append(
                f"  {name}: author {a!r} names {hits} — an agency/internal byline is the thing the de-brand removes"
            )

    print("AAN generic authorship")
    print("=" * 68)
    print(f"books: {len(books)} | distinct authors: {len(authors)}")
    for a, n in sorted(authors.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3}  {a}")
    if problems:
        print(f"\nFAIL — {len(problems)} breach(es):")
        print("\n".join(problems))
        return 1
    print("\nOK — every book declares an author, and none is bylined to a specific agency or internal team.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
