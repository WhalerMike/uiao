#!/usr/bin/env python3
"""The published AAN corpus names no governance engine — UIAO included.

Doctrine (2026-07-18, series owner): the Federal Compliance AAN Series is a
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

RATCHET, not sweep: 79 files predate this gate and still name the engine —
heavy books whose figures render "UIAO" inside the diagram, deck/spec YAMLs
that drive PPTX slides, the training subtree pending relocation, internal
planning docs, and gate tooling whose docstrings compare against UIAO canon.
They are enumerated below and may ONLY leave this list, never join it:

  1. NO NEW NAMING — a file not listed here must contain no match.
  2. THE LIST ONLY SHRINKS — when a listed file is cleaned, this gate FAILS
     until its entry is removed. A clean file cannot quietly remain
     grandfathered; every cleanup permanently narrows the exemption.
  3. THE HISTORICAL RECORD IS EXEMPT — AAN_Corpus_Sweep_Findings.{json,md} is
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
HOSTING_URLS = re.compile(
    r"(github\.com/WhalerMike/uiao|whalermike\.github\.io/uiao|github\.io/uiao)",
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

# ── The ratchet ─────────────────────────────────────────────────────────────
# Every entry is a file that named the engine when this gate landed
# (2026-07-18). Grouped by what cleaning it takes. Shrink-only (invariant 2).
RATCHET = {
    # Training subtree — engine-side training content; disposition is
    # RELOCATION out of the series (it is already lychee-excluded), not a
    # scrub. Entries fall off as the move lands.
    "AAN-Training-Program/assessment-rubrics.qmd",
    "AAN-Training-Program/compliance-track.qmd",
    "AAN-Training-Program/implementation-track.qmd",
    "AAN-Training-Program/index.qmd",
    "AAN-Training-Program/labs/index.qmd",
    "AAN-Training-Program/labs/lab-b1-ddi.qmd",
    "AAN-Training-Program/labs/lab-b5-pim.qmd",
    "AAN-Training-Program/labs/lab-b6-purview.qmd",
    "AAN-Training-Program/labs/lab-b6-sentinel.qmd",
    "AAN-Training-Program/vendor-training-catalog.qmd",
    # Internal planning / meta docs — not book corpus; each needs a
    # keep-here-and-scrub vs move-to-engine-side decision.
    "AAN_CR26_Reconciliation.md",
    "AAN_DECK_STYLE_NOTES.md",
    "AAN_Series_Requirements.md",
    "AAN_ServiceNow_Kit_Expansion_Roadmap.md",
    "AAN_Vol_V_Training_Academy_Plan.md",
    "AAN_Vol_VII_ServiceNow_Accelerator_Build_vs_Buy.md",
    "Book06_Track4_Constructive_Critique.md",
    "BUILD-DERIVATIVES.md",
    "federal-aan-conmon-gap-roadmap.md",
    # Gate tooling — docstrings compare series claims against engine canon;
    # rewording must not weaken what the gates explain.
    "check_cr26_indicators.py",
    "render_authorities_table.py",
    "render_cr26_reconciliation.py",
    "servicenow-day2/check_l3_ceiling.py",
    "validate_day2_control_maps.py",
    # Figures that render the engine name INSIDE the diagram — need SVG
    # redraw + PNG/sidecar regen alongside their host book.
    "figs/ced-fig-01-training-dimensions.svg",
    "figs/ced-fig-02-evidence-pipeline.svg",
    "figs/mf-fig-13-fedramp-20x-mainframe.svg",
    "figs/mf-fig-14-ssot-restoration.svg",
    # Heavy books — 20+ mentions each and/or paired dirty deck specs;
    # clean qmd + spec + figs together (see pairing note).
    "Vol_IV_Book_05_FedAAN_Cybersecurity_Training_Awareness.qmd",
    "Vol_IV_Book_06_FedAAN_Authorization_Package_ConMon.qmd",
    "Vol_V_Book_01_FedAAN_Compliance_Track.qmd",
    "Vol_V_Book_02_FedAAN_Implementation_Track.qmd",
    "Vol_V_Book_03_FedAAN_Assessment_Certification.qmd",
    "Vol_V_Book_04_FedAAN_Vendor_Training_Lab_Environments.qmd",
    # Deck specs (drive PPTX slide content) — pair with their book's scrub.
    "decks/Vol_IX_Book_00.yaml",
    "decks/Vol_IX_Book_01.yaml",
    "decks/Vol_IX_Book_02.yaml",
    "decks/Vol_IX_Book_03.yaml",
    "decks/Vol_IX_Book_04.yaml",
    "decks/Vol_IX_Book_05.yaml",
    "decks/Vol_VII_Book_00.yaml",
    "decks/Vol_VII_Book_01.yaml",
    "decks/Vol_VII_Book_02.yaml",
    "decks/Vol_VII_Book_03.yaml",
    "decks/Vol_VII_Book_04.yaml",
    "decks/Vol_VII_Book_05.yaml",
    "specs/Vol_0_Book_01.yaml",
    "specs/Vol_0_Book_02.yaml",
    "specs/Vol_I_Book_00.yaml",
    "specs/Vol_I_Book_07.yaml",
    "specs/Vol_II_Book_00.yaml",
    "specs/Vol_II_Book_02.yaml",
    "specs/Vol_III_Book_00.yaml",
    "specs/Vol_III_Book_03.yaml",
    "specs/Vol_III_Book_04.yaml",
    "specs/Vol_III_Book_05.yaml",
    "specs/Vol_III_Book_06.yaml",
    "specs/Vol_III_Book_07.yaml",
    "specs/Vol_IV_Book_00.yaml",
    "specs/Vol_IV_Book_01.yaml",
    "specs/Vol_IV_Book_02.yaml",
    "specs/Vol_IV_Book_03.yaml",
    "specs/Vol_IV_Book_04.yaml",
    "specs/Vol_IV_Book_05.yaml",
    "specs/Vol_IV_Book_06.yaml",
    "specs/Vol_V_Book_00.yaml",
    "specs/Vol_V_Book_01.yaml",
    "specs/Vol_V_Book_02.yaml",
    "specs/Vol_V_Book_03.yaml",
    "specs/Vol_V_Book_04.yaml",
    "specs/Vol_VI_Book_00.yaml",
    "specs/Vol_VI_Book_01.yaml",
    "specs/Vol_VI_Book_02.yaml",
    "specs/Vol_VI_Book_03.yaml",
    "specs/Vol_VI_Book_04.yaml",
    "specs/Vol_VI_Book_05.yaml",
    "specs/Vol_VI_Book_06.yaml",
    "specs/Vol_VI_Book_07.yaml",
    "specs/Vol_VI_Book_08.yaml",
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
