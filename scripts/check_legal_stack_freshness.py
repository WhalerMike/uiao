#!/usr/bin/env python3
"""Freshness gate for the federal cybersecurity legal-stack chart's sources.

docs/customer-documents/whitepapers/data/federal-legal-stack-sources.yml is
the SSOT for every external legal source the legal-stack chart (and the
whitepaper prose around it) cites, each entry carrying the source it was
checked against and the date of that check.

Live-fetching government sources in CI is not reliable (bot-walls, redirects,
geo/UA gating — see .lycheeignore for the fedramp.gov / learn.microsoft.com
precedent this follows), so this gate does not fetch pages. What it automates
is making SKIPPED verification visible: a `last_verified` older than
--max-age days fails in --strict-fresh mode. The scheduled workflow
(.github/workflows/legal-stack-authority-freshness.yml) runs that mode
weekly, so "nobody has re-checked these sources lately" is a red build, not a
silent decay.

To clear a failing run: open each flagged entry's `source`, confirm the
`claim` still holds (or correct the chart/whitepaper if it doesn't), and bump
`last_verified` in the registry.

Usage:
    python check_legal_stack_freshness.py                # report only
    python check_legal_stack_freshness.py --strict-fresh  # stale entries fail
    python check_legal_stack_freshness.py --max-age 90
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REGISTRY = HERE.parent / "docs" / "customer-documents" / "whitepapers" / "data" / "federal-legal-stack-sources.yml"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict-fresh",
        action="store_true",
        help="fail (exit 1) if any entry's last_verified exceeds --max-age",
    )
    parser.add_argument(
        "--max-age",
        type=int,
        default=90,
        help="days before a last_verified date is considered stale (default: 90)",
    )
    args = parser.parse_args()

    registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    sources = registry.get("sources", [])
    if not sources:
        sys.exit(f"ERROR: no `sources` entries found in {REGISTRY}")

    today = dt.date.today()
    stale: list[tuple[str, dt.date, int]] = []

    for entry in sources:
        entry_id = entry["id"]
        last_verified = entry["last_verified"]
        if isinstance(last_verified, str):
            last_verified = dt.date.fromisoformat(last_verified)
        age_days = (today - last_verified).days
        status = "STALE" if age_days > args.max_age else "fresh"
        print(f"[{status:5}] {entry_id}: last_verified={last_verified} (age={age_days}d)")
        if age_days > args.max_age:
            stale.append((entry_id, last_verified, age_days))

    if stale:
        print(
            f"\n{len(stale)} of {len(sources)} source(s) exceed --max-age "
            f"{args.max_age}d. Re-verify against `source` and bump `last_verified` "
            f"in {REGISTRY.relative_to(HERE.parent)}."
        )
        if args.strict_fresh:
            return 1
        print("(warning only — pass --strict-fresh to make this a failure)")
    else:
        print(f"\nOK: all {len(sources)} source(s) verified within {args.max_age}d.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
