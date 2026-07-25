#!/usr/bin/env python3
"""Link-gap scanner CLI (UIAO_145 §7 / ADR-132 Phase 2).

Thin wrapper over :mod:`uiao.evidence.link_gaps`, the package-side core
shared with the ConMon dashboard's external-interconnections panel.
Sibling of scan_publication_gaps.py and scan_lifecycle_consistency.py:
advisory by default (exit 0, report to stdout); --strict exits 1 when
any gap is found; --json emits machine-readable findings.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from dataclasses import asdict

try:
    from uiao.evidence.link_gaps import scan
except ImportError:  # direct invocation without an installed package
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "src"))
    from uiao.evidence.link_gaps import scan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--strict", action="store_true", help="exit 1 if any gap is found")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    gaps = scan()

    if args.json:
        print(json.dumps([asdict(g) for g in gaps], indent=2))
    else:
        if gaps:
            width = max(len(g.kind) for g in gaps)
            for g in gaps:
                print(f"{g.kind:<{width}}  {g.link_id}: {g.detail}")
        print(f"\nLink gaps: {len(gaps)}")
        print(f"Mode:      {'STRICT' if args.strict else 'ADVISORY (use --strict to fail on gaps)'}")

    if args.strict and gaps:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
