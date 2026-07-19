#!/usr/bin/env python3
"""Render the B.1.3 §6.1 fix-coverage matrix from the gap-matrix YAML.

Single source of truth is ``src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml``
(the per-row ``rebuild:`` block). This script regenerates the table + summary
between the ``rebuild-coverage`` markers in B.1.3 so the doc never drifts from
the data.

Usage:
    python scripts/generate_rebuild_coverage.py          # rewrite B.1.3 in place
    python scripts/generate_rebuild_coverage.py --check   # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML

REPO = Path(__file__).resolve().parents[1]
YML = REPO / "src/uiao/canon/data/gcc-moderate-telemetry-gaps.yaml"
DOC = REPO / ("docs/customer-documents/orgcomp-series/boundary/B1-3-rebuilding-boundary-blocked-analytics.qmd")

BEGIN = (
    "<!-- BEGIN: rebuild-coverage (generated from "
    "gcc-moderate-telemetry-gaps.yaml by "
    "scripts/generate_rebuild_coverage.py - do not edit by hand) -->"
)
END = "<!-- END: rebuild-coverage -->"

VERDICT_LABEL = {
    "fixes": "**Fixes**",
    "partial-substitute": "Partial — substitute",
    "partial-bounded": "Partial — bounded",
    "not-fixed": "**Not fixed**",
}


def build_block() -> str:
    yaml = YAML()
    rows = yaml.load(YML)["gaps"]
    lines = [
        "| # | Signal (gap id) | Disposition | Verdict | Rebuild path & residual |",
        "|---|---|---|---|---|",
    ]
    buckets = {"fixes": [], "partial": [], "not-fixed": []}
    for n, row in enumerate(rows, 1):
        rb = row.get("rebuild") or {}
        verdict = rb.get("verdict", "")
        label = VERDICT_LABEL.get(verdict, verdict)
        impact = f"{rb.get('path', '')}. Residual: {rb.get('residual', '')}."
        lines.append(f"| {n} | {row['signal']} (`{row['id']}`) | {row['documented']} | {label} | {impact} |")
        if verdict == "fixes":
            buckets["fixes"].append(n)
        elif verdict == "not-fixed":
            buckets["not-fixed"].append(n)
        else:
            buckets["partial"].append(n)

    def fmt(ns: list[int]) -> str:
        return ", ".join(str(x) for x in ns)

    total = len(rows)
    summary = [
        "",
        f"**Coverage summary** — of {total} blocked signals:",
        "",
        "| Verdict | Count | Rows |",
        "|---|---|---|",
        f"| Fixes (rebuilt or retention) | {len(buckets['fixes'])} | {fmt(buckets['fixes'])} |",
        f"| Partial (substitute or bounded) | {len(buckets['partial'])} | {fmt(buckets['partial'])} |",
        f"| Not fixed (irreducible / suppressed) | {len(buckets['not-fixed'])} | {fmt(buckets['not-fixed'])} |",
    ]
    return "\n".join(lines + summary)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if out of date")
    args = ap.parse_args()

    text = DOC.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        print(f"markers not found in {DOC.name}", file=sys.stderr)
        return 2
    block = build_block()
    replacement = f"{BEGIN}\n{block}\n{END}"
    new_text = pattern.sub(lambda _: replacement, text)

    if args.check:
        if new_text != text:
            print("B.1.3 §6.1 is out of date — run generate_rebuild_coverage.py", file=sys.stderr)
            return 1
        print("B.1.3 §6.1 is up to date.")
        return 0

    if new_text != text:
        DOC.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"regenerated rebuild-coverage matrix in {DOC.name}")
    else:
        print("no change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
