#!/usr/bin/env python3
"""The published AAN corpus names no governance engine — UIAO included.

Doctrine (2026-07-18, series owner): the Federal Organization Compliance (OrgComp) Series is a
standalone offering. An agency that needs compliance now must be able to adopt
the series without adopting — or even hearing about — any particular
automation engine. Where a book needs an engine, it speaks in evidence-contract
terms: slots, indicators, artifact shapes, "the governance engine". UIAO may
rely on and name AAN freely (it does, via the fedramp-aan-catalog adapter);
the dependency is one-way and this gate holds the AAN side of it.

What is forbidden: any word-boundary match of "uiao" (case-insensitive) in a
text file under this directory, after stripping repository-hosting URLs
(github.com/WhalerMike/uiao, whalermike.github.io/uiao) — the series is hosted
in that repository, so links to itself are hosting reality, not engine naming.

THE CLEANUP IS COMPLETE. The 79-file ratchet this gate launched with
(2026-07-18) is fully burned down: books, deck/spec YAMLs, figures, the
training subtree (scrubbed in place — it is kit content registered in the
compliance spine), and the planning docs are all engine-neutral; the
UIAO-subject analyses moved to inbox/UIAO-AAN-Integration/. What remains
below is a CLOSED PERMANENT REGISTER of functional exemptions — files whose
engine references are load-bearing, not naming debt:

  1. NO NEW NAMING — a file not listed here must contain no match.
  2. THE REGISTER IS CLOSED — additions require a documented functional
     justification of the same kind as the entries below (an operator must
     paste a real command, or a tool must state what it functionally reads).
     "It mentions the engine" is naming debt, not a justification.
  3. A REGISTERED FILE THAT GOES CLEAN MUST LEAVE — the gate fails until
     its entry is removed, so the register can still only shrink.
  4. THE HISTORICAL RECORD IS EXEMPT — AAN_Corpus_Sweep_Findings.{json,md} is
     a CLOSED audit register; rewriting its hits would falsify what was
     audited. Exempt by name, not pattern, so no new file inherits it.

Cleanup pairing note: a book's qmd, its specs/<book>.yaml deck spec, and any
figs/*.svg it references must be cleaned TOGETHER with a fresh Date Code —
cleaning the qmd alone leaves the rendered deck naming the engine (the known
control-value drift chain).

Usage:
    python check_engine_neutrality.py    # gate; exit 1 on any violation
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

FORBIDDEN = re.compile(r"\buiao\b", re.IGNORECASE)
# Full URLs into the host repository — including deep paths like
# .../tree/main/src/uiao/adapters/fedramp_aan_catalog/ — are CITATIONS
# (hosting reality / published contract wiring), not engine naming.
# Prose naming remains forbidden.
HOSTING_URLS = re.compile(
    r"(github\.com/WhalerMike/uiao\S*|whalermike\.github\.io/uiao\S*|github\.io/uiao\S*)",
    re.IGNORECASE,
)

# The closed audit register — see invariant 3.
HISTORICAL = {
    "AAN_Corpus_Sweep_Findings.json",
    "AAN_Corpus_Sweep_Findings.md",
}

SKIP_SUFFIX = {".zip", ".docx", ".pptx", ".png", ".jpg", ".jpeg", ".pdf"}
SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__"}

# This checker names the forbidden token in its own docstring and pattern.
# Exempt by filename rather than softening the pattern — a gate that cannot
# state what it forbids is a worse gate.
SELF = Path(__file__).name

# ── The permanent register (see invariant 2 — closed; shrink-only) ─────────
RATCHET = {
    # Build instructions — operators must be able to paste the REAL build
    # commands (`uiao generate aan-deck`, the batch docx path). Scrubbing
    # them would make the doc non-functional; every spec header points here
    # (§1) precisely so this is the ONE sanctioned home of those commands.
    "BUILD-DERIVATIVES.md",
    # Gate tooling — these scripts functionally READ the host repo's rule
    # files and canon catalog (real `src/…` code paths) and their docstrings
    # must state what they compare against to stay honest. Tooling is not
    # published prose.
    "check_cr26_indicators.py",
    "render_authorities_table.py",
    "render_cr26_reconciliation.py",
    "servicenow-day2/check_l3_ceiling.py",
    "validate_day2_control_maps.py",
}


def main() -> int:
    new_violations: list[str] = []
    cleaned_still_listed: list[str] = []
    stale_entries: list[str] = []
    still_dirty = 0
    scanned = 0

    seen: set[str] = set()
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or p.suffix.lower() in SKIP_SUFFIX:
            continue
        # Skip-dir test runs on the path RELATIVE to this directory — the
        # absolute path may legitimately contain e.g. ".claude" (worktrees
        # live under .claude/worktrees/), and testing absolute parts would
        # silently skip every file there.
        if any(part in SKIP_DIRS for part in p.relative_to(HERE).parts):
            continue
        if p.name in HISTORICAL or p.name == SELF:
            continue
        rel = p.relative_to(HERE).as_posix()
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        seen.add(rel)
        dirty = bool(FORBIDDEN.search(HOSTING_URLS.sub("", text)))
        if dirty and rel not in RATCHET:
            new_violations.append(rel)
        elif dirty:
            still_dirty += 1
        elif rel in RATCHET:
            cleaned_still_listed.append(rel)

    stale_entries = sorted(e for e in RATCHET if e not in seen)

    print("AAN engine neutrality (no UIAO in the published corpus)")
    print("=" * 68)
    print(f"scanned: {scanned}  ratchet remaining: {still_dirty}/{len(RATCHET)}")

    ok = True
    if new_violations:
        ok = False
        print("\nNEW engine naming (invariant 1) — rewrite in evidence-contract")
        print("terms ('the governance engine', slots, artifact shapes):")
        for rel in new_violations:
            print(f"  {rel}")
    if cleaned_still_listed:
        ok = False
        print("\nCleaned but still grandfathered (invariant 2) — remove these")
        print("entries from RATCHET so the exemption narrows permanently:")
        for rel in cleaned_still_listed:
            print(f"  {rel}")
    if stale_entries:
        ok = False
        print("\nRATCHET entries with no matching file (moved or deleted) —")
        print("remove or update these entries:")
        for rel in stale_entries:
            print(f"  {rel}")

    if ok:
        print("OK — corpus adds no engine naming; ratchet is exact.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
