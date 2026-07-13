#!/usr/bin/env python3
"""Render each Federal AAN book's "Authorities Closed Here" table from the
single compliance spine (aan-compliance-spine.yml).

The spine is the SSOT: book control-closure tables are generated, never
hand-edited in the .qmd. The drift gate (`--check`) fails when a committed book
partial diverges from what the spine now produces — the same regen-and-diff
pattern used elsewhere in the repo for derived tables.

Usage:
    python render_authorities_table.py                 # validate + summary
    python render_authorities_table.py --book book-net-enforce
    python render_authorities_table.py --emit-dir authorities
    python render_authorities_table.py --check authorities   # drift gate (exit 1 on drift)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

SPINE = Path(__file__).with_name("aan-compliance-spine.yml")

# Column order for the generated "Authorities Closed Here" table.
COLUMNS = [
    ("control", "Control"),
    ("title", "Title"),
    ("mechanism", "Closing mechanism (function, not product)"),
    ("gate_label", "Accreditation gate"),
    ("drivers_label", "Authority drivers"),
    ("slot_label", "Evidence slot"),
    ("ksi_label", "FedRAMP 20x KSI"),
    ("tool_label", "Tool-attestable?"),
]


def load_spine(path: Path = SPINE) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate(spine: dict) -> list[str]:
    """Return a list of reference errors; empty means the spine is consistent."""
    errors: list[str] = []
    book_ids = {b["id"] for b in spine["books"]}
    auth_ids = {a["id"] for a in spine["authorities"]}
    slot_ids = set(spine["slots"])
    gate_ids = set(spine["gates"])

    for i, c in enumerate(spine["closures"]):
        where = f"closure[{i}] {c.get('control', '?')}/{c.get('book', '?')}"
        if c["book"] not in book_ids:
            errors.append(f"{where}: unknown book '{c['book']}'")
        if c["gate"] not in gate_ids:
            errors.append(f"{where}: unknown gate '{c['gate']}'")
        if c["slot"] not in slot_ids:
            errors.append(f"{where}: unknown slot '{c['slot']}'")
        for d in c["drivers"]:
            if d not in auth_ids:
                errors.append(f"{where}: unknown authority driver '{d}'")
        if not isinstance(c.get("plane"), int) or not 1 <= c["plane"] <= 7:
            errors.append(f"{where}: plane must be an int 1-7")
    return errors


def _row_cells(spine: dict, c: dict) -> dict:
    auth_names = {a["id"]: a["name"] for a in spine["authorities"]}
    cells = dict(c)
    cells["gate_label"] = spine["gates"][c["gate"]].split(" (")[0]
    cells["drivers_label"] = "; ".join(auth_names[d] for d in c["drivers"])
    cells["slot_label"] = spine["slots"][c["slot"]]
    cells["ksi_label"] = ", ".join(c["ksi"]) if c["ksi"] else "—"
    cells["tool_label"] = "Yes" if c["tool"] else "No"
    control = c["control"]
    if c.get("necessity"):
        control += " †"
    cells["control"] = control
    return cells


def render_book(spine: dict, book_id: str) -> str:
    book = next((b for b in spine["books"] if b["id"] == book_id), None)
    if book is None:
        raise KeyError(f"unknown book '{book_id}'")
    rows = [c for c in spine["closures"] if c["book"] == book_id]
    if not rows:
        return (
            f"<!-- authorities:{book_id} -->\n_No closures recorded in the compliance spine for {book['title']} yet._\n"
        )

    header = "| " + " | ".join(label for _, label in COLUMNS) + " |"
    sep = "|" + "|".join("---" for _ in COLUMNS) + "|"
    lines = [f"<!-- authorities:{book_id} — generated from aan-compliance-spine.yml; do not hand-edit -->"]
    lines.append(header)
    lines.append(sep)
    for c in sorted(rows, key=lambda r: (r["plane"], r["control"])):
        cells = _row_cells(spine, c)
        lines.append("| " + " | ".join(str(cells[key]) for key, _ in COLUMNS) + " |")
    lines.append("")
    lines.append(
        f": Authorities Closed Here — {book['title']} "
        "(† = Closure-Necessity anchor: no alternate closure path) {.striped .hover}"
    )
    lines.append("")
    rebuttals = [
        (c["control"], c["alternative_rebuttal"])
        for c in sorted(rows, key=lambda r: (r["plane"], r["control"]))
        if c.get("necessity") and c.get("alternative_rebuttal")
    ]
    if rebuttals:
        lines.append(
            "**Closure-Necessity — alternate-path rebuttals (†).** For each "
            "necessity anchor, the strongest alternative a reviewer might propose "
            "and the specific reason it fails to close the control:"
        )
        lines.append("")
        for ctrl, reb in rebuttals:
            lines.append(f"- **{ctrl}** — {reb}")
        lines.append("")
    return "\n".join(lines)


def emit(spine: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    books_with_closures = {c["book"] for c in spine["closures"]}
    for book_id in sorted(books_with_closures):
        target = out_dir / f"authorities-{book_id}.md"
        target.write_text(render_book(spine, book_id) + "\n", encoding="utf-8")
        written.append(target)
    return written


def check(spine: dict, out_dir: Path) -> int:
    """Drift gate: compare committed partials to freshly rendered output."""
    drift = []
    books_with_closures = {c["book"] for c in spine["closures"]}
    for book_id in sorted(books_with_closures):
        target = out_dir / f"authorities-{book_id}.md"
        fresh = render_book(spine, book_id) + "\n"
        if not target.exists():
            drift.append(f"  missing: {target.name}")
        elif target.read_text(encoding="utf-8") != fresh:
            drift.append(f"  drifted: {target.name}")
    if drift:
        print("DRIFT — regenerate with --emit-dir:", *drift, sep="\n")
        return 1
    print(f"OK — {len(books_with_closures)} book partials match the spine.")
    return 0


def summary(spine: dict) -> None:
    n_books = len(spine["books"])
    n_auth = len(spine["authorities"])
    n_clo = len(spine["closures"])
    by_book: dict[str, int] = {}
    for c in spine["closures"]:
        by_book[c["book"]] = by_book.get(c["book"], 0) + 1
    print(f"AAN compliance spine: {n_auth} authorities, {n_books} books, {n_clo} closures.")
    print("Closures by book:")
    for b in spine["books"]:
        n = by_book.get(b["id"], 0)
        if n:
            print(f"  {b['temp_slot']:>2} → {b['target_slot']:>2}  {b['id']:<20} {n:>2}  {b['title']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--book", help="print one book's table to stdout")
    ap.add_argument("--emit-dir", help="write authorities-<book>.md partials into DIR")
    ap.add_argument("--check", metavar="DIR", help="drift gate against committed partials")
    args = ap.parse_args()

    # Windows consoles default to cp1252; the tables carry '†' and '—'.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    spine = load_spine()
    errors = validate(spine)
    if errors:
        print("SPINE VALIDATION FAILED:", *(f"  {e}" for e in errors), sep="\n")
        return 2

    if args.book:
        print(render_book(spine, args.book))
        return 0
    if args.emit_dir:
        written = emit(spine, Path(args.emit_dir))
        print(f"Wrote {len(written)} partials to {args.emit_dir}/")
        return 0
    if args.check:
        return check(spine, Path(args.check))

    summary(spine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
