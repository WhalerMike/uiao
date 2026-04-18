#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_numbering.py — Enforce canon numbering/renaming/relocation policy.

Purpose
-------
Canon documents under ``docs/`` and ``generation-inputs/`` follow a strict
numbering convention (e.g. ``NN-short-slug.md`` for ordered canon, and stable
filenames for referenced inputs). This script is the CI gate that blocks
pull requests which silently renumber, rename, or relocate canonical files.

Current state
-------------
This is the initial post-split scaffold. It walks the canon trees, collects
the set of canonical filenames, and emits a deterministic summary. It treats
missing canon directories as a soft-skip (some branches legitimately touch
only one side of canon) and exits 0.

Full numbering enforcement (diff against ``main``, forbidden-rename
detection, stable-name registry) is tracked separately; this file exists so
the ``canon-validation`` workflow has a stable entrypoint and can surface
the canon inventory as a CI log artifact until full checks land.

Usage
-----
    python scripts/validate_numbering.py

Exit codes
----------
0 — canon inventory collected (or canon dirs absent).
1 — unrecoverable error (I/O, encoding).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CANON_ROOTS = ("docs", "generation-inputs")


def collect_canon_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        p.relative_to(REPO_ROOT)
        for p in root.rglob("*")
        if p.is_file() and not any(part.startswith(".") for part in p.parts)
    )


def main() -> int:
    any_found = False
    for name in CANON_ROOTS:
        root = REPO_ROOT / name
        files = collect_canon_files(root)
        if not root.exists():
            print(f"[validate_numbering] {name}/ — absent, skipping.")
            continue
        any_found = True
        print(f"[validate_numbering] {name}/ — {len(files)} canon files:")
        for f in files:
            print(f"  {f.as_posix()}")

    if not any_found:
        print("[validate_numbering] no canon roots present on this branch; nothing to check.")
    print("[validate_numbering] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
