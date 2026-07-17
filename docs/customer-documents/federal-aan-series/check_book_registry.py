#!/usr/bin/env python3
"""The corpus on disk and the spine's book registry must agree — in both directions.

Every other AAN gate globs `HERE/Vol_*_Book_*.qmd` and reports on whatever it finds.
None of them asserts how many books there should BE. So a book that leaves the
corpus — moved, renamed, deleted — does not fail anything. Every gate simply
measures a smaller corpus and says OK.

That is not hypothetical. It is the failure this repo keeps producing:
`check_actuator_coverage.py` globbed one directory while its sibling globbed two and
reported 96% for what was really 84%; the master crosswalk omitted real spine rows
while its self-consistency gate stayed green. A percentage or a pass is only worth
something if its denominator is asserted.

It is also the specific risk of the pending move to docs/: 21 tools glob their own
directory and the spine path-qualifies all 67 sources, so relocating part of the
corpus would leave every gate globbing the remainder and passing. This gate is meant
to be watching while that happens.

Two directions, because one is not enough:

  1. REGISTRY -> DISK. Every book the spine registers must exist at its declared
     `source:`. Catches a book that moved or was deleted while the spine still
     claims it — a control-closure claim pointing at nothing.

  2. DISK -> REGISTRY. Every Vol_*_Book_*.qmd on disk must be registered in the
     spine. Catches a book authored into the corpus that no closure references —
     it renders, ships, and closes nothing.

Note the registry is NOT all .qmd: of 67 books, 58 are .qmd here and 9 are Volume
VIII chapters sourced from infoblox-ddi-book/*.md at the repo root. Direction 2 is
therefore scoped to this directory's Vol_*_Book_*.qmd; direction 1 covers all 67
wherever they live.

Usage:
    python check_book_registry.py     # gate; exit 1 on any disagreement
"""

from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import yaml


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
REPO_ROOT = _repo_root()
SPINE = HERE / "aan-compliance-spine.yml"


def registry() -> list[tuple[str, str]]:
    """(book id, declared source path) for every book the spine registers."""
    doc = yaml.safe_load(SPINE.read_text(encoding="utf-8")) or {}
    out = []
    for b in doc.get("books", []):
        src = str(b.get("source", "")).strip()
        if src:
            out.append((str(b.get("id", "?")), src))
    return out


def main() -> int:
    reg = registry()
    problems: list[str] = []

    # 1. registry -> disk
    missing = [(bid, src) for bid, src in reg if not (REPO_ROOT / src).exists()]
    for bid, src in missing:
        problems.append(
            f"  spine registers {bid!r} at {src!r} — that file does not exist. A closure claim pointing at nothing."
        )

    # 2. disk -> registry (scoped to this directory's books; Vol VIII lives at the
    #    repo root and is covered by direction 1)
    declared = {os.path.normpath(src) for _, src in reg}
    rel = os.path.relpath(HERE, REPO_ROOT)
    orphans = []
    for p in sorted(glob.glob(str(HERE / "Vol_*_Book_*.qmd"))):
        key = os.path.normpath(os.path.join(rel, os.path.basename(p)))
        if key not in declared:
            orphans.append(os.path.basename(p))
    for o in orphans:
        problems.append(f"  {o} is on disk but no spine book registers it — it renders, ships, and closes nothing.")

    qmd_registered = sum(1 for _, s in reg if s.endswith(".qmd"))
    print("AAN book registry vs disk")
    print("=" * 68)
    print(
        f"spine books: {len(reg)} (qmd: {qmd_registered}, other sources: "
        f"{len(reg) - qmd_registered}) | Vol_*_Book_*.qmd on disk: "
        f"{len(glob.glob(str(HERE / 'Vol_*_Book_*.qmd')))}"
    )
    if problems:
        print(f"\nFAIL — {len(problems)} disagreement(s):")
        print("\n".join(problems))
        return 1
    print(
        "\nOK — every registered book exists, and every book on disk is registered. "
        "The corpus cannot shrink or grow unnoticed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
