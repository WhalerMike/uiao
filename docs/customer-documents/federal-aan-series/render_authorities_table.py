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
    python render_authorities_table.py --check-inline         # gate inline .qmd tables vs spine
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _repo_root() -> Path:
    """Walk up to the repository root rather than counting directory levels.

    A hardcoded `parents[N]` encodes this file's depth, which silently resolves to
    the WRONG directory after a move instead of failing. Walking to .git survives.
    """
    p = Path(__file__).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise SystemExit(f"repo root not found (no .git above {p})")


try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

SPINE = Path(__file__).with_name("aan-compliance-spine.yml")

# The authoritative FedRAMP CR26 OSCAL catalog vendored in the repo — the same
# source render_cr26_reconciliation.py reconciles against. KSI theme ids are
# read from it rather than hard-coded, so the vocabulary cannot drift from
# FedRAMP's own. (Reference data, not UIAO engine code — the series' stand-alone
# posture is unaffected.)
_CR26_CATALOG_GLOB = (
    "src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/*/catalog/json/FedRAMP_CR26_catalog.json"
)


def _valid_ksi_themes() -> set[str]:
    """KSI theme ids from the CR26 catalog; empty set if it cannot be read.

    Returning empty (rather than raising) keeps the spine renderable in a
    checkout without the catalog — validate() then skips the KSI check rather
    than failing closed on a missing reference file.
    """
    import re

    repo = _repo_root()
    matches = sorted(repo.glob(_CR26_CATALOG_GLOB))
    if not matches:
        return set()
    try:
        raw = matches[0].read_text(encoding="utf-8")
    except OSError:
        return set()
    return set(re.findall(r"\bKSI-[A-Z]{3}\b", raw))


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
    # KSI was previously unvalidated — an invented theme (e.g. KSI-TPR, the
    # FedRAMP 20x name that is NOT in the CR26 catalog) rendered straight into
    # the authorities table and the generated docx with nothing to catch it.
    ksi_ids = _valid_ksi_themes()

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
        if ksi_ids:
            for k in c.get("ksi") or []:
                if k not in ksi_ids:
                    errors.append(
                        f"{where}: unknown KSI theme '{k}' — not in the CR26 catalog ({', '.join(sorted(ksi_ids))})"
                    )
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
        # Escape any '|' inside a cell (enhancement titles are "Parent | Enhancement")
        # so it does not split the markdown row into an extra column.
        lines.append("| " + " | ".join(str(cells[key]).replace("|", "\\|") for key, _ in COLUMNS) + " |")
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
        # newline="\n" is load-bearing: Path.write_text uses the platform default,
        # so on Windows this emitted CRLF while the repo commits LF. The
        # line-ending hooks then normalised the file and --check reported drift
        # against its own output — regenerate, hook rewrites, check fails, repeat.
        # The text itself comes from _partial_text, shared with check(): they each
        # built it independently and drifted apart by one trailing newline the
        # moment one side changed — which reads as content drift and cannot be
        # fixed by regenerating, because the generator disagrees with itself.
        with open(target, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(_partial_text(spine, book_id))
        written.append(target)
    return written


def _partial_text(spine: dict, book_id: str) -> str:
    """The exact text of a book's partial — the ONE definition.

    emit and check each built this string themselves and disagreed by a single
    trailing newline the moment one side changed, which reads as content drift and
    is unfixable by regenerating (the generator disagrees with itself).
    """
    return render_book(spine, book_id).rstrip("\n") + "\n"


def check(spine: dict, out_dir: Path) -> int:
    """Drift gate: compare committed partials to freshly rendered output."""
    drift = []
    books_with_closures = {c["book"] for c in spine["closures"]}
    for book_id in sorted(books_with_closures):
        target = out_dir / f"authorities-{book_id}.md"
        fresh = _partial_text(spine, book_id)
        if not target.exists():
            drift.append(f"  missing: {target.name}")
        elif target.read_text(encoding="utf-8") != fresh:
            drift.append(f"  drifted: {target.name}")
    if drift:
        print("DRIFT — regenerate with --emit-dir:", *drift, sep="\n")
        return 1
    print(f"OK — {len(books_with_closures)} book partials match the spine.")
    return 0


def _spine_expected(spine: dict) -> dict[str, dict[str, tuple[frozenset[str], str]]]:
    """{book_id: {control(with †): (frozenset(ksi themes), title)}} from the spine."""
    out: dict[str, dict[str, tuple[frozenset[str], str]]] = {}
    for c in spine["closures"]:
        cells = _row_cells(spine, c)
        themes = frozenset(c["ksi"] or [])
        out.setdefault(c["book"], {})[cells["control"]] = (themes, c["title"])
    return out


def check_inline(spine: dict, roots: list[Path]) -> int:
    """Gate the INLINE authorities tables embedded in the .qmd files against the
    spine. The generated authorities-<book>.md partials are covered by --check;
    the hand-copied inline tables (same `<!-- authorities:book-… -->` marker)
    were not, which let a control->KSI mapping drift (CM-8 mislabelled KSI-CMT
    instead of KSI-PIY). This compares each inline row's Control -> {KSI, Title}
    to the spine — structurally, so caption/mechanism customisation is fine."""
    import re

    expected = _spine_expected(spine)
    marker = re.compile(r"<!--\s*authorities:(book-[\w-]+)")
    errors: list[str] = []
    tables = 0

    qmds: list[Path] = []
    for root in roots:
        qmds += sorted(root.rglob("*.qmd"))
    for qmd in qmds:
        lines = qmd.read_text(encoding="utf-8", errors="replace").splitlines()
        for i, line in enumerate(lines):
            m = marker.search(line)
            if not m:
                continue
            book_id = m.group(1)
            exp = expected.get(book_id)
            if not exp:
                continue
            tables += 1
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("|"):
                j += 1
            if j >= len(lines):
                continue
            cols = [c.strip() for c in re.split(r"(?<!\\)\|", lines[j].strip().strip("|"))]
            ncols = len(cols)
            try:
                ksi_idx = next(k for k, c in enumerate(cols) if "KSI" in c and "20x" in c)
            except StopIteration:
                errors.append(
                    f"{qmd.name}:{j + 1}: authorities:{book_id} table header missing the 'FedRAMP 20x KSI' column"
                )
                continue
            k = j + 2  # skip the |---| separator
            while k < len(lines) and lines[k].lstrip().startswith("|"):
                raw = lines[k].strip().strip("|")
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", raw)]
                k += 1
                ctrl = cells[0]
                if ctrl not in exp:
                    continue  # not a spine-tracked control row (nested header / continuation)
                want_ksi, _ = exp[ctrl]
                # A control row whose cell count != the header's almost always means
                # an unescaped '|' inside a cell (e.g. an enhancement title
                # "Parent | Enhancement"), which corrupts the row and shifts every
                # column. Report that rather than mis-reading a shifted column.
                if len(cells) != ncols:
                    errors.append(
                        f"{qmd.name}:{k}: {ctrl} row has {len(cells)} cells, header has "
                        f"{ncols} — an unescaped '|' inside a cell (escape it as '\\|')"
                    )
                    continue
                got_ksi = frozenset(t.strip() for t in cells[ksi_idx].split(",") if t.strip() and t.strip() != "—")
                if got_ksi != want_ksi:
                    errors.append(
                        f"{qmd.name}:{k}: {ctrl} KSI is {sorted(got_ksi) or ['—']}, "
                        f"spine says {sorted(want_ksi) or ['—']} — inline authorities table drifted"
                    )

    print("AAN inline-authorities drift check")
    print("=" * 44)
    print(f"Inline authorities tables checked: {tables}")
    if errors:
        print("\nERRORS:", *(f"  - {e}" for e in errors), sep="\n")
        return 1
    print("\nOK — every inline authorities row's control->KSI matches the spine.")
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
    ap.add_argument(
        "--check-inline",
        action="store_true",
        help="drift gate: inline .qmd authorities tables (control->KSI/title) vs the spine",
    )
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
    if args.check_inline:
        return check_inline(spine, [Path(__file__).parent])

    summary(spine)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
