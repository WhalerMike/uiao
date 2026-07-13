#!/usr/bin/env python3
"""Generate the spine-derived control crosswalk from the compliance spine.

The hand-maintained master crosswalk in
`Vol_0_Book_02_FedAAN_Control_Crosswalk.qmd` indexes 146 controls across all
66 books — but most of those rows are hand-authored, because the spine only
carries closure rows for the books that have been back-filled. This renders
the slice the spine *can* prove: for every control that appears in a spine
closure, the volume/book(s) where it is closed, its family, whether it is a
Closure-Necessity anchor, and the FedRAMP 20x KSI theme(s) it maps to.

It is the machine-derived companion to the hand-maintained master table, and
it is CI-gated the same way the per-book authorities tables are — so as the
spine is back-filled book by book, this crosswalk grows toward the full master
automatically and can never silently drift from the spine.

Coverage is stated honestly up top: this is NOT series-wide control coverage,
it is the coverage the spine can currently prove.

Usage:
    python render_crosswalk.py            # write AAN_Spine_Crosswalk.md
    python render_crosswalk.py --check     # drift gate (exit 1 if stale)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
SPINE = HERE / "aan-compliance-spine.yml"
OUT = HERE / "AAN_Spine_Crosswalk.md"

# Volume id -> roman label used in the "Where addressed" cells. The series
# numbers Volume 0 as the Executive Summary & Program volume.
ROMAN = {
    "vol-0": "0",
    "vol-1": "I",
    "vol-2": "II",
    "vol-3": "III",
    "vol-4": "IV",
    "vol-5": "V",
    "vol-6": "VI",
    "vol-7": "VII",
    "vol-8": "VIII",
    "vol-9": "IX",
}
# Roman -> sort rank so "Where addressed" and the coverage table order by volume.
ROMAN_RANK = {r: i for i, r in enumerate(ROMAN.values())}


def load_spine(path: Path = SPINE) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _book_volume(spine: dict) -> dict[str, str]:
    """Map each book id to its owning volume id (authoritative membership)."""
    out: dict[str, str] = {}
    for vol in spine["volumes"]:
        for book_id in vol["books"]:
            out[book_id] = vol["id"]
    return out


def _book_number(book: dict) -> str:
    """Derive a book's within-volume number from its source filename.

    The series' canonical volume/book numbering lives in the source path
    (``Vol_<roman>_Book_<nn>_...`` for in-folder books, ``NN-*.md`` for the
    repo-root DDI chapters), so parse it there and fall back to target_slot.
    """
    base = book.get("source", "").rsplit("/", 1)[-1]
    m = re.match(r"Vol_[IVX0-9]+_Book_([0-9A-Za-z]+)_", base)
    if m:
        return m.group(1)
    m = re.match(r"(\d+)-", base)
    if m:
        return m.group(1)
    if "appendix" in base.lower():
        m = re.search(r"appendix-([A-Za-z0-9]+)", base.lower())
        return m.group(1).upper() if m else "A"
    ts = book.get("target_slot", "")
    return ts.split("-")[-1] if "-" in ts else ts


def book_labels(spine: dict) -> dict[str, tuple[str, str]]:
    """Map book id -> (roman, "Vol <roman> Bk <nn>") for every registered book."""
    vol_of = _book_volume(spine)
    out: dict[str, tuple[str, str]] = {}
    for book in spine["books"]:
        roman = ROMAN.get(vol_of.get(book["id"], ""), "?")
        out[book["id"]] = (roman, f"Vol {roman} Bk {_book_number(book)}")
    return out


def _control_sort_key(control: str) -> tuple[str, int, int]:
    """Natural sort: family, base number, enhancement number."""
    m = re.match(r"([A-Z]+)-(\d+)(?:\((\d+)\))?", control)
    if not m:
        return (control, 0, 0)
    return (m.group(1), int(m.group(2)), int(m.group(3) or 0))


def _family(control: str) -> str:
    m = re.match(r"([A-Z]+)-", control)
    return m.group(1) if m else control


def aggregate(spine: dict) -> list[dict]:
    """Collapse closures into one crosswalk row per control."""
    labels = book_labels(spine)
    by_control: dict[str, dict] = {}
    for c in spine["closures"]:
        ctrl = c["control"]
        row = by_control.setdefault(
            ctrl,
            {"control": ctrl, "title": c["title"], "family": _family(ctrl),
             "books": set(), "ksi": set(), "necessity": False},
        )
        row["books"].add(labels[c["book"]][1])
        row["ksi"].update(c.get("ksi") or [])
        if c.get("necessity"):
            row["necessity"] = True
    rows = list(by_control.values())
    rows.sort(key=lambda r: _control_sort_key(r["control"]))
    return rows


def _where(books: set[str]) -> str:
    def key(label: str) -> tuple[int, int]:
        m = re.match(r"Vol (\S+) Bk (\w+)", label)
        roman = m.group(1) if m else "?"
        num = m.group(2) if m else "0"
        digits = re.sub(r"\D", "", num) or "0"
        return (ROMAN_RANK.get(roman, 99), int(digits))

    return ", ".join(sorted(books, key=key))


def render() -> str:
    spine = load_spine()
    closures = spine["closures"]
    rows = aggregate(spine)
    total_books = len(spine["books"])
    books_with_closures = sorted({c["book"] for c in closures})
    labels = book_labels(spine)

    L: list[str] = []
    L.append("# AAN Spine-Derived Control Crosswalk")
    L.append("")
    L.append(
        "> **Generated file — do not hand-edit.** Produced by "
        "`render_crosswalk.py` from `aan-compliance-spine.yml`. Regenerate when "
        "closures change; CI-gated by `aan-authorities-drift.yml`."
    )
    L.append("")
    L.append("## Coverage (stated honestly)")
    L.append("")
    L.append(
        f"- This crosswalk is rendered from the **{len(closures)} closure rows** "
        f"the spine carries across **{len(books_with_closures)} of {total_books} "
        "books**. It is the machine-derived slice of the series control "
        "crosswalk — **not** series-wide coverage. The hand-maintained master "
        "table in `Vol_0_Book_02_FedAAN_Control_Crosswalk.qmd` indexes the full "
        "146 controls across all books; that superset is author-maintained until "
        "the spine back-fill reaches every book."
    )
    L.append(
        f"- It aggregates those closures into **{len(rows)} distinct controls**. "
        "A control closed in several books lists each volume/book. As the spine "
        "is back-filled book by book, this table grows toward the full master "
        "automatically and cannot silently drift from the spine."
    )
    L.append("")
    L.append("## Crosswalk")
    L.append("")
    L.append("| Control | Title | Family | Where addressed (spine) | FedRAMP 20x KSI |")
    L.append("|---|---|---|---|---|")
    for r in rows:
        ctrl = r["control"] + (" †" if r["necessity"] else "")
        ksi = ", ".join(sorted(r["ksi"])) if r["ksi"] else "—"
        L.append(f"| {ctrl} | {r['title']} | {r['family']} | {_where(r['books'])} | {ksi} |")
    L.append("")
    L.append(
        "*† = Closure-Necessity anchor (no alternate closure path; see the "
        "per-book alternate-path rebuttals in the authorities tables).*"
    )
    L.append("")

    # Coverage by volume — distinct controls closed within each volume.
    vol_of = _book_volume(spine)
    by_vol: dict[str, set[str]] = {}
    for c in closures:
        by_vol.setdefault(vol_of.get(c["book"], "?"), set()).add(c["control"])
    L.append("## Control coverage by volume (spine)")
    L.append("")
    L.append(
        "Distinct controls the spine closes within each volume (a control closed "
        "in several volumes is counted in each)."
    )
    L.append("")
    L.append("| Volume | Distinct controls closed |")
    L.append("|---|---|")
    for vol in spine["volumes"]:
        n = len(by_vol.get(vol["id"], set()))
        if n:
            L.append(f"| Vol {ROMAN.get(vol['id'], '?')} | {n} |")
    L.append(f"| **Series total (distinct)** | **{len(rows)}** |")
    L.append("")
    L.append(": Spine control coverage by volume {.striped}")
    L.append("")

    # FedRAMP 20x KSI view — KSI theme -> contributing controls.
    by_ksi: dict[str, set[str]] = {}
    for c in closures:
        for k in c.get("ksi") or []:
            by_ksi.setdefault(k, set()).add(c["control"])
    L.append("## FedRAMP 20x KSI view (spine)")
    L.append("")
    L.append("| FedRAMP 20x KSI | Controls mapped |")
    L.append("|---|---|")
    for ksi in sorted(by_ksi):
        ctrls = ", ".join(sorted(by_ksi[ksi], key=_control_sort_key))
        L.append(f"| **{ksi}** | {ctrls} |")
    L.append("")
    L.append(": FedRAMP 20x Key Security Indicator → contributing controls (spine) {.striped}")
    L.append("")

    # Closure-bearing book roster — makes the 15-of-66 slice explicit.
    L.append("## Closure-bearing books in this slice")
    L.append("")
    title_of = {b["id"]: b["title"] for b in spine["books"]}
    L.append("| Book | Volume/Book | Title |")
    L.append("|---|---|---|")
    for book_id in sorted(books_with_closures, key=lambda b: (
            ROMAN_RANK.get(labels[b][0], 99), labels[b][1])):
        L.append(f"| {book_id} | {labels[book_id][1]} | {title_of[book_id]} |")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="drift gate (exit 1 if stale)")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    content = render()
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != content:
            print(f"DRIFT — regenerate: python {Path(__file__).name}")
            return 1
        print(f"OK — {OUT.name} matches the spine.")
        return 0
    OUT.write_text(content, encoding="utf-8")
    print(f"Wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
