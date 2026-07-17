#!/usr/bin/env python3
"""Every vendor FedRAMP/GCC authorization assertion in a table must carry a
FedRAMP Marketplace source.

Vendor-authorization facts (does product X hold a FedRAMP Moderate ATO?) are
external and can't be derived from the spine — so they are the one drift class a
generated-from-SSOT gate can't cover. What we *can* enforce is the series' own
citation convention: the supply-chain table's Infoblox row already reads
"Yes — FR2017257053". This gate makes that mandatory — any cell asserting
"Yes — FedRAMP <level>" or "Yes — GCC <level>" must carry a marketplace source
token (an FR#### / package id, or a fedramp.gov marketplace reference), so a
level like "GCC Moderate" can be checked against the Marketplace instead of taken
on faith. Scoped to the affirmative table-cell idiom, so the series' ubiquitous
FedRAMP-Moderate *scope* prose is never touched.

Usage:  python check_vendor_authorization_sources.py     # exit 1 on any gap
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# A vendor-authorization table cell: affirmative "Yes" + a named FedRAMP/GCC level.
ASSERTION = re.compile(r"\bYes\b[^|]*\b(?:FedRAMP|GCC)\s+(?:Low|Moderate|High)\b", re.I)
# An acceptable source: a FedRAMP Marketplace package id or a marketplace reference.
SOURCE = re.compile(r"\bFR\d{4,}[A-Z]?\b|\bMSO365MT\b|fedramp\.gov", re.I)


def main() -> int:
    problems: list[str] = []
    checked = 0
    for qmd in sorted(HERE.glob("*.qmd")):
        for i, line in enumerate(qmd.read_text(encoding="utf-8").splitlines(), 1):
            if not line.lstrip().startswith("|"):
                continue
            for cell in line.split("|"):
                if not ASSERTION.search(cell):
                    continue
                checked += 1
                if not SOURCE.search(cell):
                    problems.append(
                        f"  {qmd.name}:{i}: '{cell.strip()}' asserts an authorization "
                        "level without a FedRAMP Marketplace source (FR#### / fedramp.gov)"
                    )

    print("AAN vendor-authorization source check")
    print("=" * 44)
    print(f"Vendor authorization-level cells checked: {checked}")
    if not problems:
        print("\nOK — every vendor FedRAMP/GCC authorization cell carries a Marketplace source.")
        return 0
    print(f"\nFAIL — {len(problems)} authorization assertion(s) missing a source:")
    print("\n".join(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
