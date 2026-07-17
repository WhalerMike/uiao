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

  3. NUMBER->THEME MISBINDING (blocking): a KSI-0NN indicator number bound to the
     wrong theme — e.g. KSI-011..014 (which are KSI-CMT, Change Management)
     labelled KSI-SCR (Supply Chain Risk = KSI-015/016). The number->theme map
     is derived from AAN_CR26_Reconciliation.md (the SSOT), for KSI-011..029
     only (KSI-001..010 are the shared ScuBA baseline spanning several themes).

Usage:
    python check_cr26_indicators.py            # exit 1 on any violation
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Walk up to the repository root rather than counting directory levels.

    A hardcoded `parents[N]` encodes this file's depth. That silently broke when
    the corpus moved from inbox/ (depth 2) to docs/customer-documents/ (depth 3):
    the index still resolved, just to the wrong directory. Walking to the .git
    marker survives the next move too.
    """
    p = Path(__file__).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise SystemExit(f"repo root not found (no .git above {p})")


HERE = Path(__file__).resolve().parent
REPO = _repo_root()
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

# --- KSI number -> theme binding (3rd check) --------------------------------
# The corpus sweep found KSI-011..014 (which are KSI-CMT, Change Management)
# repeatedly mislabelled as KSI-SCR (Supply Chain Risk = KSI-015/016). The
# number->theme map is derived from AAN_CR26_Reconciliation.md (the SSOT), so
# this gate tracks the SSOT rather than hardcoding it. Only KSI-011..029 are
# enforced: KSI-001..010 are the shared ScuBA baseline that legitimately spans
# several themes (IAM/MLA/CNA/SVC), so they carry no single canonical theme.
_THEME_ABBR = "CED|CMT|CNA|IAM|INR|MLA|PIY|RPL|SCR|SVC"
# A KSI-0NN (optionally a range) bound within a short window to a theme
# sub-indicator "KSI-TTT-YYY" — e.g. "KSI-011 through KSI-014 (KSI-SCR-MIT ...)".
_BIND_SUBIND = re.compile(
    r"(KSI-0\d\d)(?:\s*(?:\.\.0?\d\d|[–-]\s*KSI-0\d\d|through\s+KSI-0\d\d|to\s+KSI-0\d\d))?"
    r"[^.\n]{0,35}?KSI-(" + _THEME_ABBR + r")-"
)
# Table-cell form "KSI-011..014 (4) | SCR — ..." (bare theme code after a pipe).
_BIND_BARE = re.compile(r"(KSI-0\d\d)\s*\.\.0?\d\d\s*\(\d+\)\s*\|\s*(" + _THEME_ABBR + r")\b")
# Theme-first table row "| KSI-IAM | KSI-001, KSI-017-019 | ..." — a theme cell
# followed by a cell listing the numbers it (wrongly) claims.
_BIND_THEMEFIRST = re.compile(r"\|\s*KSI-(" + _THEME_ABBR + r")\s*\|\s*([^|]*)")


def _recon_rows() -> list[tuple[str, list[str]]]:
    recon = HERE / "AAN_CR26_Reconciliation.md"
    rows: list[tuple[str, list[str]]] = []
    for line in recon.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        mt = re.match(r"(KSI-[A-Z]{2,3})\s*\(", cells[0])
        if mt:
            rows.append((mt.group(1), cells))
    return rows


def number_theme_map() -> dict[str, str]:
    """KSI-0NN -> KSI-TTT parsed from the reconciliation SSOT, 011..029 only."""
    m: dict[str, str] = {}
    for theme, cells in _recon_rows():
        for c in cells:
            for n in re.findall(r"KSI-(0\d\d)\b", c):
                if "011" <= n <= "029":
                    m["KSI-" + n] = theme
    return m


def canonical_themes() -> set[str]:
    """The 10 canonical CR26 theme codes (KSI-TTT), from the reconciliation SSOT."""
    return {theme for theme, _ in _recon_rows()}


# A bare theme code KSI-TTT (2-3 letters), not a KSI-TTT-YYY sub-indicator and
# not a KSI-0NN number. Catches invented codes like KSI-CM/KSI-DAT/KSI-IR.
THEME_RE = re.compile(r"KSI-([A-Z]{2,3})(?![-A-Z0-9])")
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
    num2theme = number_theme_map()
    canon = canonical_themes()
    errors: list[str] = []
    ids_seen = confl_seen = bind_seen = theme_seen = 0

    def _check_binding(f_name: str, ln: int, line: str) -> None:
        nonlocal bind_seen
        for rx in (_BIND_SUBIND, _BIND_BARE):
            for mm in rx.finditer(line):
                num, theme = mm.group(1), "KSI-" + mm.group(2)
                bind_seen += 1
                canon = num2theme.get(num)
                if canon and canon != theme:
                    errors.append(
                        f"{f_name}:{ln}: {num} belongs to {canon}, but is bound "
                        f"here to {theme} — see AAN_CR26_Reconciliation.md: "
                        f"«{line.strip()[:70]}»"
                    )
        # Theme-first table row: "| KSI-TTT | KSI-0NN, KSI-0MM |"
        for mm in _BIND_THEMEFIRST.finditer(line):
            theme = "KSI-" + mm.group(1)
            for num in re.findall(r"KSI-0\d\d", mm.group(2)):
                bind_seen += 1
                canon = num2theme.get(num)
                if canon and canon != theme:
                    errors.append(
                        f"{f_name}:{ln}: {num} belongs to {canon}, but the "
                        f"'{theme}' row claims it — see AAN_CR26_Reconciliation.md: "
                        f"«{line.strip()[:70]}»"
                    )

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
                _check_binding(f.name, ln, line)
                for tm in THEME_RE.finditer(line):
                    theme = tm.group(0)
                    theme_seen += 1
                    if theme not in canon:
                        errors.append(
                            f"{f.name}:{ln}: '{theme}' is not a canonical CR26 theme "
                            f"(the 10 are {', '.join(sorted(canon))}) — "
                            f"see AAN_CR26_Reconciliation.md: «{line.strip()[:60]}»"
                        )

    print("AAN CR26-indicator check")
    print("=" * 44)
    print(
        f"Valid CR26 indicators: {len(valid)} | indicator citations: {ids_seen} | "
        f"number->theme bindings: {bind_seen} | theme codes: {theme_seen}"
    )
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK — every CR26 indicator id is real; no 29/46 conflation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
