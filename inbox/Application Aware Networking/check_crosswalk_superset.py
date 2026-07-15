#!/usr/bin/env python3
"""Assert the hand-maintained crosswalk + designation tables are a true
superset of the compliance spine.

The spine-derived crosswalk gate (``render_crosswalk.py --check``) only proves
the *generated slice* is self-consistent; it never checks that the
hand-maintained master table in ``Vol_0_Book_02`` actually contains every spine
closure, nor that the master designation table in ``Vol_0_Book_00`` lists every
substantive book. This gate closes both gaps: a spine closure (control in a
volume) that is missing from the master, or a book-with-closures missing from
the designation table, fails CI — the exact drift class that let AC-2(3),
AC-2(4), SA-9(2) and four books go un-indexed.

Superset, not equality: the master intentionally indexes more than the spine can
currently prove, so we only assert spine ⊆ master.

Usage:  python check_crosswalk_superset.py        # exit 1 on any gap
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from render_crosswalk import book_labels, load_spine

HERE = Path(__file__).resolve().parent
MASTER = HERE / "Vol_0_Book_02_FedAAN_Control_Crosswalk.qmd"
DESIGN = HERE / "Vol_0_Book_00_FedAAN_Executive_Summary.qmd"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def spine_controls(spine: dict) -> set[str]:
    """Every distinct control the spine closes."""
    return {c["control"] for c in spine["closures"]}


def master_controls(text: str) -> set[str]:
    """Every control id that has a row in the master crosswalk table.

    The invariant is control-level, not (control, volume): by the crosswalk's
    own stated design (Volumes VII-IX *coordinate* controls the architecture
    volumes already close), a coordination volume is deliberately not re-listed
    in an existing control's row. What must never happen is a spine-closed
    control having *no* master row at all — the drift that hid AC-2(3)/AC-2(4)/
    SA-9(2).
    """
    return set(re.findall(r"^\|\s*\*\*([A-Z]{2}-[0-9][0-9A-Za-z()\-]*)\*\*", text, re.M))


def designation_books(text: str) -> set[str]:
    """Set of 'Vol <roman> Book <nn>' rows present in the designation table."""
    return set(re.findall(r"^\|\s*(Vol [IVX]+ Book [0-9A-Za-z]+)\s*\|", text, re.M))


def _is_canonical_series_book(book: dict) -> bool:
    """True for the canonical Vol_<roman>_Book_<nn> series files. Excludes the
    infoblox-ddi-book sub-chapters (their own book) and any non-series source,
    which the designation table does not enumerate row-per-chapter."""
    base = book.get("source", "").rsplit("/", 1)[-1]
    return bool(re.match(r"Vol_[IVX0-9]+_Book_[0-9A-Za-z]+_", base))


def main() -> int:
    spine = load_spine()
    labels = book_labels(spine)
    books_by_id = {b["id"]: b for b in spine["books"]}

    # --- 1. master crosswalk ⊇ spine, control-level ---
    want = spine_controls(spine)
    have = master_controls(_read(MASTER))
    missing = sorted(want - have, key=lambda c: (c.split("(")[0], c))

    # --- 2. designation table lists every canonical series book with closures ---
    closing = {c["book"] for c in spine["closures"]}
    design = designation_books(_read(DESIGN))
    missing_books: list[str] = []
    for book_id in sorted(closing):
        book = books_by_id[book_id]
        if not _is_canonical_series_book(book):
            continue
        roman, short = labels[book_id]              # short = "Vol X Bk NN"
        want_row = f"Vol {roman} Book {short.rsplit(' ', 1)[-1]}"
        if want_row not in design:
            missing_books.append(f"  {want_row} ({book_id}) has spine closures but no designation-table row")

    print("AAN crosswalk-superset check")
    print("=" * 44)
    print(f"Spine controls: {len(want)} | master rows: {len(have)} | "
          f"canonical closing books: {sum(_is_canonical_series_book(books_by_id[b]) for b in closing)} | "
          f"designation rows: {len(design)}")
    if not missing and not missing_books:
        print("\nOK — master crosswalk has a row for every spine control; "
              "designation table lists every canonical series book with closures.")
        return 0
    if missing:
        print(f"\nFAIL — {len(missing)} spine control(s) have no master crosswalk row:")
        print("\n".join(f"  {c}" for c in missing))
    if missing_books:
        print(f"\nFAIL — {len(missing_books)} canonical book(s) with closures missing a designation-table row:")
        print("\n".join(missing_books))
    return 1


if __name__ == "__main__":
    sys.exit(main())
