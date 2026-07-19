#!/usr/bin/env python3
"""Drift gate for hand-written spine counts in the AAN prose.

The per-book authorities tables, the spine crosswalk, and the claim->evidence
matrix are all *generated* and drift-gated. The books' **prose** is not — and it
quotes the same numbers: "68 closures across 17 of 67 books", "each of the 68
closure claims", "only 11 of 68 claims yet carry a named test", "the spine's
generated-and-gated closures cover 17 of 67 books".

Those sentences are hand-maintained, so adding one book silently falsifies every
one of them. That happened on 2026-07-14: registering Vol VII Book 06 left four
stale claims across three Vol 0 books (65->68 closures, 16->17 books, 66->67
books, 59->68 claims, "11 of 65"->"11 of 68"). Nothing caught it; a reader would
simply have been told the wrong number.

This scans the prose for the count *patterns* and asserts each against the spine
(and the generated matrix). It is deliberately pattern-driven rather than
exhaustive: it can only catch sentences shaped like the ones below. A number
phrased a new way is invisible to it — so this reduces the class, it does not
eliminate it.

Usage:
    python check_prose_counts.py            # report
    python check_prose_counts.py --strict   # exit 1 on any drift (CI gate)
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
SPINE = HERE / "orgcomp-compliance-spine.yml"
MATRIX = HERE / "OrgComp_Claim_Evidence_Test_Matrix.md"

# Files whose prose quotes spine counts. Add to this list, not to the regexes,
# when a new book starts quoting them.
SCANNED = [
    "Vol_0_Book_00_OrgComp_Executive_Summary.qmd",
    "Vol_0_Book_00a_OrgComp_Executive_Brief.qmd",
    "Vol_0_Book_02_OrgComp_Control_Crosswalk.qmd",
]


def truth() -> dict[str, int]:
    spine = yaml.safe_load(SPINE.read_text(encoding="utf-8"))
    closures = spine["closures"]
    facts = {
        "closures": len(closures),
        "books_total": len(spine["books"]),
        "books_with_closures": len({c["book"] for c in closures}),
        "controls": len({c["control"] for c in closures}),
    }
    if MATRIX.exists():
        m = MATRIX.read_text(encoding="utf-8")
        rows = len(re.findall(r"^\| [A-Z]{2}-\d", m, re.M))
        untested = len(re.findall(r"no falsifying test bound yet", m))
        facts["claims"] = rows
        facts["claims_tested"] = rows - untested
    return facts


# (regex, description, callable(match, facts) -> error|None). Each pattern names
# the groups it checks so a mismatch reports both numbers.
def _checks(f: dict[str, int]) -> list[tuple[re.Pattern[str], str, object]]:
    def cmp(label: str, got: str, want: int) -> str | None:
        return None if int(got.replace(",", "")) == want else f"{label}: prose says {got}, spine says {want}"

    return [
        (
            re.compile(r"\*\*(\d+) closures across (\d+) of (\d+) books\*\*"),
            "N closures across N of N books",
            lambda m: [
                cmp("closures", m.group(1), f["closures"]),
                cmp("books-with-closures", m.group(2), f["books_with_closures"]),
                cmp("books-total", m.group(3), f["books_total"]),
            ],
        ),
        (
            re.compile(r"\((\d+) distinct\s*\n?\s*controls\)"),
            "(N distinct controls)",
            lambda m: [cmp("distinct controls", m.group(1), f["controls"])],
        ),
        (
            re.compile(r"~?(\d+) of (\d+) books carry closure rows"),
            "N of N books carry closure rows",
            lambda m: [
                cmp("books-with-closures", m.group(1), f["books_with_closures"]),
                cmp("books-total", m.group(2), f["books_total"]),
            ],
        ),
        (
            re.compile(r"each of the (\d+) closure claims"),
            "each of the N closure claims",
            lambda m: [cmp("claims", m.group(1), f.get("claims", -1))],
        ),
        (
            re.compile(r"closures cover \*\*(\d+) of (\d+) books\*\*"),
            "closures cover N of N books",
            lambda m: [
                cmp("books-with-closures", m.group(1), f["books_with_closures"]),
                cmp("books-total", m.group(2), f["books_total"]),
            ],
        ),
        (
            re.compile(r"only \*\*(\d+) of (\d+)\*\*\s*\n?\s*claims yet carry a named test"),
            "only N of N claims carry a named test",
            lambda m: [
                cmp("claims-tested", m.group(1), f.get("claims_tested", -1)),
                cmp("claims", m.group(2), f.get("claims", -1)),
            ],
        ),
    ]


def scan() -> tuple[list[str], int]:
    f = truth()
    problems: list[str] = []
    matched = 0
    for name in SCANNED:
        p = HERE / name
        if not p.exists():
            problems.append(f"{name}: MISSING from disk (listed in SCANNED)")
            continue
        text = p.read_text(encoding="utf-8")
        for rx, label, check in _checks(f):
            for m in rx.finditer(text):
                matched += 1
                for err in check(m):
                    if err:
                        problems.append(f"{name}: [{label}] {err}")
    return problems, matched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--strict", action="store_true", help="exit 1 on any drift")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    f = truth()
    problems, matched = scan()
    print("AAN prose-count drift check")
    print("=" * 44)
    print("Spine truth: " + ", ".join(f"{k}={v}" for k, v in sorted(f.items())))
    print(f"Count claims matched in prose: {matched}")
    if problems:
        print("\nDRIFT:")
        for p in problems:
            print(f"  - {p}")
        print("\nFix the prose (or regenerate) so it matches the spine.")
    else:
        print("\nOK — every matched prose count agrees with the spine.")
    if matched == 0:
        print("\nWARNING: no count claims matched. Either the prose stopped quoting")
        print("counts, or it rephrased them and this gate has gone blind. Check.")
    return 1 if (problems and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
