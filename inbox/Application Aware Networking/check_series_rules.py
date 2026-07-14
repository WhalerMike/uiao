#!/usr/bin/env python3
"""Gates 3 + 5 — series scope rule and cross-reference integrity.

GATE 3 (scope): authoring-spec §2 — the series NEVER cites, maps to, or claims
FedRAMP High. Enforced as CI, not convention. "GCC High" (a Microsoft product
name, usually appearing as "GCC High / DoD are out of scope") is NOT a High
claim and is not flagged. Known pre-existing treatments are carried in
EXCEPTIONS with the reason on record; anything new is a hard error.

GATE 5 (crossref): every "Vol X Book NN" / "Vol X Bk NN" reference must resolve
to a book registered in aan-compliance-spine.yml. Catches references to books
that were renumbered, renamed, or never existed.

Usage:
    python check_series_rules.py            # exit 1 on any violation
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from render_crosswalk import book_labels, load_spine  # noqa: E402

GLOBS = [
    "Vol_*_Book_*.qmd",
    "AAN-Training-Program/**/*.qmd",
    "decks/*.yaml",
    "specs/*.yaml",
    "federal-aan-conmon-gap-roadmap.md",
    "servicenow-day2/**/*.js",
    "servicenow-day2/*.json",
    "x_ssa_fed_compliance/**/*.js",
    "x_ssa_fed_compliance/**/*.json",
    "x_ssa_fed_compliance/**/*.md",
]

# --- Gate 3: High-claim patterns. "GCC High" excluded via lookbehind. ---
HIGH_RE = re.compile(r"(?<!GCC )(?<!GCC-)\bFedRAMP High\b|\bHigh baseline\b|\bHigh impact level\b|\bHigh-on-Moderate\b")

# Pre-existing High mentions are BASELINED per file (aan-high-claim-baseline.yml,
# captured 2026-07-14: 44 occurrences / 16 files awaiting the owner's ruling —
# spec §2 as written forbids them all). The gate is a RATCHET: a file exceeding
# its baseline fails; a file dropping below it warns to lower the baseline.
BASELINE_FILE = HERE / "aan-high-claim-baseline.yml"

# --- Gate 5: cross-reference pattern ---
XREF_RE = re.compile(r"\bVol(?:ume)?[ _]([0IVX]+)[ _](?:Book|Bk)[ _](\d{1,2}[a-zA-Z]?|[A-Z])\b")


def _norm_num(n: str) -> str:
    m = re.match(r"0*(\d+)([a-zA-Z]?)$", n)
    if m:
        return m.group(1) + m.group(2).lower()
    return n.lower()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    spine = load_spine()
    valid: set[tuple[str, str]] = set()
    for _bid, (roman, label) in book_labels(spine).items():
        num = label.rsplit(" ", 1)[-1]
        valid.add((roman, _norm_num(num)))

    import yaml

    baseline = yaml.safe_load(BASELINE_FILE.read_text(encoding="utf-8"))["baseline"] if BASELINE_FILE.exists() else {}
    errors: list[str] = []
    warnings: list[str] = []
    xrefs = 0
    high_counts: dict[str, int] = {}

    for pattern in GLOBS:
        for f in sorted(HERE.glob(pattern)):
            text = f.read_text(encoding="utf-8", errors="replace")
            for ln, line in enumerate(text.splitlines(), 1):
                if HIGH_RE.search(line):
                    high_counts[f.name] = high_counts.get(f.name, 0) + 1
                for m in XREF_RE.finditer(line):
                    xrefs += 1
                    ref = (m.group(1), _norm_num(m.group(2)))
                    if ref not in valid:
                        errors.append(
                            f"{f.name}:{ln}: cross-reference 'Vol {m.group(1)} Book {m.group(2)}' resolves to no registered book"
                        )

    # High-claim ratchet
    for name, n in sorted(high_counts.items()):
        base = baseline.get(name, 0)
        if n > base:
            errors.append(
                f"{name}: {n} High mention(s), baseline {base} — new High claims are forbidden (authoring-spec §2)"
            )
        elif n < base:
            warnings.append(f"{name}: {n} High mention(s), baseline {base} — lower the baseline (ratchet down)")
    for name, base in baseline.items():
        if name not in high_counts and base > 0:
            warnings.append(f"{name}: 0 High mentions, baseline {base} — remove the baseline entry")

    print("AAN series-rules check (scope + crossref)")
    print("=" * 44)
    print(
        f"Registered books: {len(valid)} | cross-references checked: {xrefs} | High mentions: {sum(high_counts.values())} (baseline {sum(baseline.values())})"
    )
    if warnings:
        print("\nRATCHET-DOWN warnings:")
        for w in warnings:
            print(f"  ~ {w}")
    if errors:
        print("\nERRORS:")
        for e in errors[:25]:
            print(f"  - {e}")
        if len(errors) > 25:
            print(f"  ... and {len(errors) - 25} more")
        return 1
    print("\nOK — no unrecorded High claims; every cross-reference resolves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
