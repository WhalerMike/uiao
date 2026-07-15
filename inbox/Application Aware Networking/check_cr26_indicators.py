#!/usr/bin/env python3
"""Gate 6 — CR26 indicator IDs must be real, and the 29/46 conflation is banned.

The in-repo FedRAMP CR26 Moderate catalog is the SSOT: **46 indicators across 10
themes**. The series ALSO has **29 internal ADR-111 rules** (`src/uiao/ksi/rules/`),
of which **19 map 1:1** to a CR26 indicator (`AAN_CR26_Reconciliation.md`). The
corpus sweep (2026-07-14) found two recurring defects the other gates could not
see:

  1. FABRICATED INDICATOR IDs (blocking): `KSI-XXX-YYY` tokens that are not in
     the 46-indicator catalog — e.g. Vol IV Book 06 Appendix A invented
     KSI-IAM-MFA, KSI-MLA-MAU, etc. in the authorization-package book itself.
  2. THE 29-vs-46 CONFLATION (blocking): prose that calls the 29 internal rules
     "CR26 KSIs/indicators" ("all 29 CR26 KSIs", "29 CR26 Rules") or cites the
     stale "~56–63 CR26 indicators" count. The 29 are internal; CR26 has 46;
     only 19 are mapped. Claiming "all 29 CR26" asserts full catalog coverage
     the reconciliation SSOT explicitly disclaims — the highest-blast-radius
     credibility defect the sweep found.

The correct phrasing (already used in parts of Book 00) is "the 29 rules in the
series' internal KSI decomposition"; mapping to CR26 is 19 of 46.

Usage:
    python check_cr26_indicators.py            # exit 1 on any violation
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CR26_GLOB = "src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/*/catalog/json/FedRAMP_CR26_catalog.json"

SCAN_GLOBS = [
    "Vol_*_Book_*.qmd",
    "AAN-Training-Program/**/*.qmd",
    "federal-aan-conmon-gap-roadmap.md",
    "decks/*.yaml",
    "specs/*.yaml",
    "AAN_CR26_Reconciliation.md",
]

IND_RE = re.compile(r"KSI-[A-Z]{3}-[A-Z]{2,4}")
# Categorically-wrong phrasings. Tight on purpose: "29" and "CR26" legitimately
# co-occur ("the 29 rules map to 19 of the 46 CR26 indicators"), so only the
# conflating forms below fail.
# Forward-form only. A reversed "CR26 KSI schema (29 rules ...)" pattern was
# tried and dropped: it flagged the CORRECT clarifying phrasing "CR26 KSI
# schema (29 rules in the series' internal KSI decomposition)" — a cry-wolf FP.
# All real conflations in the corpus are the forward "(all) 29 CR26 X" form.
CONFLATION = [
    re.compile(r"\ball\s+29\s+CR26\b", re.I),
    re.compile(r"\b29\s+CR26\s+(KSIs?|indicators?|rules?|controls?)\b", re.I),
    re.compile(r"~?\s*5[6-9]\s*[–-]\s*6[0-3]\b[^.\n]{0,20}\b(CR26|indicators?)\b", re.I),
    re.compile(r"\b(CR26|indicators?)\b[^.\n]{0,20}~?\s*5[6-9]\s*[–-]\s*6[0-3]\b", re.I),
]


def valid_indicators() -> set[str]:
    matches = sorted(REPO.glob(CR26_GLOB))
    if not matches:
        sys.exit("CR26 catalog not found — cannot validate indicator IDs")
    return set(IND_RE.findall(matches[0].read_text(encoding="utf-8")))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    valid = valid_indicators()
    errors: list[str] = []
    ids_seen = confl_seen = 0

    for pattern in SCAN_GLOBS:
        for f in sorted(HERE.glob(pattern)):
            for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                for m in IND_RE.finditer(line):
                    ids_seen += 1
                    if m.group(0) not in valid:
                        errors.append(
                            f"{f.name}:{ln}: '{m.group(0)}' is not a CR26 Moderate indicator "
                            f"(catalog has {len(valid)}; see AAN_CR26_Reconciliation.md)"
                        )
                for rx in CONFLATION:
                    if rx.search(line):
                        confl_seen += 1
                        errors.append(
                            f"{f.name}:{ln}: 29/46 conflation — the 29 are INTERNAL rules, CR26 has 46 "
                            f"indicators (19 mapped): «{line.strip()[:80]}»"
                        )
                        break

    print("AAN CR26-indicator check")
    print("=" * 44)
    print(f"Valid CR26 indicators: {len(valid)} | indicator citations: {ids_seen}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK — every CR26 indicator id is real; no 29/46 conflation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
