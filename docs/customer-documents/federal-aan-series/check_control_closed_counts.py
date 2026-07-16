#!/usr/bin/env python3
"""Assert every "Controls closed: N (enumeration)" headline matches the count of
its own enumeration.

These per-book count lines are hand-authored: the number and the list beside it
are edited by different hands at different times, so the number silently stops
matching the list (Book 01 read "16" for an 18-item list; Book 05 "12" for 13).
Nothing derived them from the spine — but they don't need the spine to be
*self-consistent*: the enumeration is right there on the same line, so N must
equal the number of comma-separated control groups (a slash-joined group such as
"AU-2/AU-12" or "CM-2/CM-6" counts as one, matching the series' convention that
Book 06's "7" already follows).

Usage:  python check_control_closed_counts.py      # exit 1 on any mismatch
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# "**Controls closed: 18** (SC-20, SC-20(1), ... , PL-8)" — capture N and the
# whole parenthesised list up to the final ')' on the line.
LINE = re.compile(r"Controls closed:\s*(\d+)\*\*\s*\((.+)\)\s*$")


def group_count(enumeration: str) -> int:
    """Count comma-separated control groups. Enhancement parens like '(1)' and
    slash-joins like 'AU-2/AU-12' carry no commas, so a top-level comma split is
    exact."""
    return len([g for g in enumeration.split(",") if g.strip()])


def main() -> int:
    problems: list[str] = []
    checked = 0
    for qmd in sorted(HERE.glob("*.qmd")):
        for i, line in enumerate(qmd.read_text(encoding="utf-8").splitlines(), 1):
            m = LINE.search(line)
            if not m:
                continue
            checked += 1
            stated = int(m.group(1))
            actual = group_count(m.group(2))
            if stated != actual:
                problems.append(
                    f"  {qmd.name}:{i}: headline says {stated}, enumeration has "
                    f"{actual} comma-groups"
                )

    print("AAN control-closed count check")
    print("=" * 44)
    print(f"'Controls closed: N' lines checked: {checked}")
    if not problems:
        print("\nOK — every 'Controls closed: N' headline matches its enumeration.")
        return 0
    print(f"\nFAIL — {len(problems)} headline/enumeration mismatch(es):")
    print("\n".join(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
