#!/usr/bin/env python3
"""Gate 2 — every cited NIST control id must exist in the Rev 5 catalog.

reference/nist-800-53r5-controls.json is distilled from the official NIST OSCAL
catalog (provenance in the file). This checker enforces:

  1. ID VALIDITY (blocking): every `XX-N` / `XX-N(n)` cited anywhere in the AAN
     corpus is a real Rev 5 control id. Kills the invented-enhancement class —
     an external assessment reviewed on 2026-07-14 leaned on control ids and
     titles that do not exist or were mislabeled, and nothing here would have
     caught the same mistake in our own prose.
  2. TITLE ACCURACY (blocking, structured files only): the `title` a spine
     closure or control map carries for an id matches the catalog title
     (normalized). Catches "AC-2(5) = Account Monitoring" when Rev 5 says
     AC-2(5) = Inactivity Logout.

Usage:
    python check_control_citations.py            # exit 1 on any violation
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
CATALOG = HERE / "reference" / "nist-800-53r5-controls.json"
SPINE = HERE / "aan-compliance-spine.yml"

FAMILIES = "AC|AT|AU|CA|CM|CP|IA|IR|MA|MP|PE|PL|PM|PS|PT|RA|SA|SC|SI|SR"
# (?<![-\w]) — a control citation is never the tail of a compound id: course
# codes ("SC-300"-style curricula are excluded by the number rule), exercise ids
# ("AAN-AT3-IR-2026"), and ScubaGear rule ids ("M365-CA-009") all collide with
# the family prefixes otherwise.
# Trailing (?!\w), NOT \b: after "SA-9(2)" the next char is often a quote or
# space — \b between ')' and '"' fails, the optional group backtracks away, and
# the citation is silently validated as its BASE control. Caught by the
# SA-9(99) negative test on 2026-07-14.
CTRL_RE = re.compile(rf"(?<![-\w])({FAMILIES})-(\d+)(\(\d+\))?(?!\w)")
# No Rev 5 base control number exceeds 60 (max today: PM-32, SC-51). Larger
# numbers are course codes / years, not citations.
MAX_BASE = 60

PROSE_GLOBS = [
    "Vol_*_Book_*.qmd",
    "AAN-Training-Program/**/*.qmd",
    "authorities/*.md",
    "AAN_Spine_Crosswalk.md",
    "AAN_Claim_Evidence_Test_Matrix.md",
    "federal-aan-conmon-gap-roadmap.md",
    "decks/*.yaml",
    "specs/*.yaml",
    "../../infoblox-ddi-book/*.md",
]
MAP_GLOBS = ["servicenow-day2/*-control-map.json", "x_ssa_fed_compliance/data/control-map.json"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))["controls"]
    errors: list[str] = []
    cited = 0

    # 1. ID validity across prose + structured files
    for pattern in PROSE_GLOBS + MAP_GLOBS + ["aan-compliance-spine.yml"]:
        for f in sorted(HERE.glob(pattern)):
            text = f.read_text(encoding="utf-8", errors="replace")
            for ln, line in enumerate(text.splitlines(), 1):
                for m in CTRL_RE.finditer(line):
                    if int(m.group(2)) > MAX_BASE:
                        continue  # course code / year, not a control citation
                    cited += 1
                    cid = m.group(0)
                    if cid not in catalog:
                        errors.append(f"{f.name}:{ln}: control id '{cid}' is not in the NIST 800-53 Rev 5 catalog")

    # 2. Title accuracy — spine closures
    spine = yaml.safe_load(SPINE.read_text(encoding="utf-8"))
    for i, c in enumerate(spine["closures"]):
        cid, title = c["control"], c["title"]
        official = catalog.get(cid)
        if official is None:
            continue  # already reported above
        claimed = title.split("|")[-1].strip() if "|" in title else title
        if _norm(claimed) != _norm(official):
            errors.append(
                f"aan-compliance-spine.yml closure[{i}] {cid}: title says '{claimed}', Rev 5 catalog says '{official}'"
            )

    # 2b. Title accuracy — control maps (maps carry item titles, not control
    # titles, so only the *control id* is checked there; nothing to compare).

    print("AAN control-citation check")
    print("=" * 44)
    print(f"Catalog ids: {len(catalog)} | citations scanned: {cited}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK — every cited control id exists; every spine title matches Rev 5.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
