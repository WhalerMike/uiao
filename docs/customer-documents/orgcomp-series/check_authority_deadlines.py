#!/usr/bin/env python3
"""Gate 1 — federal deadline claims vs the authority registry.

aan-authority-deadlines.yml is the SSOT for every binding federal date the
series cites, each entry carrying the issuing-agency source and last_verified.
This checker enforces two things:

  1. CONSISTENCY (blocking): any corpus line that names a registered event
     (entry `keywords`) alongside a prose date must carry the registry's date.
     A book saying "Class B + C opens Sep 15, 2026" while the registry says
     2026-08-31 fails.
  2. FRESHNESS (warning; --strict-fresh makes it blocking): last_verified older
     than --max-age days. The scheduled workflow runs --strict-fresh weekly, so
     "nobody has re-checked the agencies lately" is a red build, not a silent
     decay. Verification itself is a human/agent act against the issuing
     source; this gate only makes skipping it visible.

Also reports (warning) prose deadline-ish claims that match NO registry entry —
candidates for registration, not failures, because prose mentions history too.

Usage:
    python check_authority_deadlines.py                # consistency + fresh warn
    python check_authority_deadlines.py --strict-fresh # stale last_verified fails
    python check_authority_deadlines.py --max-age 30
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "aan-authority-deadlines.yml"

# Files that carry deadline prose. Generated artifacts are excluded (they are
# projections of sources already scanned); kit code is excluded (no dates).
SCAN_GLOBS = [
    "Vol_*_Book_*.qmd",
    "federal-orgcomp-conmon-gap-roadmap.md",
    "OrgComp-Training-Program/**/*.qmd",
    "decks/*.yaml",
    "specs/*.yaml",
]

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
MONTHS_ABBR = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
DATE_RE = re.compile(rf"\b(?:{MONTHS}|{MONTHS_ABBR})\.?\s+(\d{{1,2}}),?\s+(20\d\d)\b")
CUE_RE = re.compile(
    r"deadline|due|opens?|in force|mandatory|no later than|historical list|window|binds|must (?:convert|adopt|begin)",
    re.I,
)
_MONTH_NUM = {m: i % 12 + 1 for i, m in enumerate((MONTHS + "|" + MONTHS_ABBR).split("|"))}


def _parse_date(text: str, m: re.Match) -> dt.date | None:
    month_word = re.match(rf"({MONTHS}|{MONTHS_ABBR})", text[m.start() :]).group(1)
    try:
        return dt.date(int(m.group(2)), _MONTH_NUM[month_word], int(m.group(1)))
    except (ValueError, KeyError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--max-age", type=int, default=30, help="days before last_verified is stale")
    ap.add_argument("--strict-fresh", action="store_true", help="stale last_verified is a failure")
    args = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    reg = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))["deadlines"]
    for e in reg:
        e["_kw"] = [re.compile(k) for k in e["keywords"]]

    errors: list[str] = []
    warnings: list[str] = []
    today = dt.date.today()

    # Freshness
    for e in reg:
        lv = e["last_verified"]
        if isinstance(lv, str):
            lv = dt.date.fromisoformat(lv)
        age = (today - lv).days
        if age > args.max_age:
            msg = (
                f"{e['id']}: last_verified {lv} is {age}d old (max {args.max_age}) — "
                f"re-verify against {e['source']} and bump last_verified"
            )
            (errors if args.strict_fresh else warnings).append(msg)

    # Consistency
    matched = 0
    unregistered: list[str] = []
    for pattern in SCAN_GLOBS:
        for f in sorted(HERE.glob(pattern)):
            for ln, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                dm = list(DATE_RE.finditer(line))
                if not dm:
                    continue
                hit_entry = None
                for e in reg:
                    if any(k.search(line) for k in e["_kw"]):
                        hit_entry = e
                        break
                if hit_entry:
                    # A line may carry several deadlines (summary tables, figure
                    # alt-text timelines). The claim is wrong only if NO date on
                    # the line matches the entry's date.
                    dates = [d for d in (_parse_date(line, m) for m in dm) if d]
                    matched += 1
                    # Timeline alt-text writes year-less dates ("August 3 Class A
                    # opens"); accept a month+day match for the entry's date.
                    ed = hit_entry["date"]
                    month_full = ed.strftime("%B")
                    pat = "(?:" + month_full + "|" + month_full[:3] + ")\\.?\\s+" + str(ed.day) + "(?!\\d)"
                    yearless_ok = bool(re.search(pat, line))
                    if dates and ed not in dates and not yearless_ok:
                        errors.append(
                            f"{f.name}:{ln}: [{hit_entry['id']}] prose dates {sorted(set(str(x) for x in dates))} "
                            f"do not include registry date {hit_entry['date']} ({hit_entry['source']})"
                        )
                elif CUE_RE.search(line):
                    unregistered.append(f"{f.name}:{ln}: {line.strip()[:110]}")

    print("AAN authority-deadline check")
    print("=" * 44)
    print(f"Registry entries: {len(reg)} | prose claims matched to registry: {matched}")
    if warnings:
        print("\nFRESHNESS WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
    if unregistered:
        print(f"\nUNREGISTERED deadline-shaped claims ({len(unregistered)}) — register or confirm historical:")
        for u in unregistered[:15]:
            print(f"  ? {u}")
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK — every matched deadline claim agrees with the registry.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
