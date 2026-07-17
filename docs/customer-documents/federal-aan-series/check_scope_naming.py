#!/usr/bin/env python3
"""The ServiceNow scoped apps carry no agency identity.

The kits shipped as `x_ssa_day2_ops` and `x_ssa_fed_compliance`. A ServiceNow
scope is `x_<company>_<app>`, so the agency's name was baked into 244 references
across 48 files and six depths: the directory name, Script Include headers, ~41
`gs.getProperty()` calls, 14 cross-scope constructors, `<sys_scope>` in the ATF
XML, and six Python CI gates that hardcode the path.

They are now `x_fed_day2_ops` and `x_fed_compliance`. Note the second is not a
mechanical company swap — that would have produced `x_fed_fed_compliance`, since
the app itself was already called `fed_compliance`.

Why this needs a gate rather than a one-time sweep: a scope string is a pure
identifier that nothing validates. A partial rename does not fail at lint — it
fails at RUNTIME, when a cross-scope constructor cannot resolve or a property
returns empty and a client silently falls back to a default. Nothing in this repo
executes ServiceNow, so a half-renamed scope would sit here looking correct.

  1. NO AGENCY SCOPE — no `x_ssa_*` token anywhere in the live corpus.
  2. THE HISTORICAL RECORD IS EXEMPT — AAN_Corpus_Sweep_Findings.{json,md} is a
     CLOSED audit register. Its `x_ssa_*` hits are pointers to what was audited at
     the time; rewriting them would make the register claim it audited a path that
     did not exist when it ran. Historical accuracy beats pointer freshness for a
     closed record, so the old token is expected there and only there.

Usage:
    python check_scope_naming.py     # gate; exit 1 on any survivor
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

FORBIDDEN = re.compile(r"x_ssa_[a-z0-9_]*")

# The closed audit register — see invariant 2. Exempt by name, not by pattern, so
# a NEW file cannot quietly inherit the exemption.
HISTORICAL = {
    "AAN_Corpus_Sweep_Findings.json",
    "AAN_Corpus_Sweep_Findings.md",
}

SKIP_SUFFIX = {".zip", ".docx", ".pptx", ".png", ".jpg", ".pdf"}
SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__"}

# This checker names the forbidden token in its own docstring and pattern, so it
# matches itself. Exempt it by filename rather than by softening the pattern — a
# gate that cannot state what it forbids is a worse gate.
SELF = Path(__file__).name


def main() -> int:
    problems: list[str] = []
    scanned = 0
    for p in sorted(HERE.rglob("*")):
        if not p.is_file() or p.suffix.lower() in SKIP_SUFFIX:
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name in HISTORICAL or p.name == SELF:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        hits = sorted(set(FORBIDDEN.findall(text)))
        if hits:
            rel = p.relative_to(HERE)
            problems.append(
                f"  {rel}: {hits} — a partial rename does not fail at lint, it fails at runtime in a tenant"
            )

    print("AAN ServiceNow scope naming")
    print("=" * 68)
    print(f"text files scanned: {scanned} | historical records exempt: {len(HISTORICAL)}")
    if problems:
        print(f"\nFAIL — {len(problems)} file(s) still carry an agency scope:")
        print("\n".join(problems))
        return 1
    print("\nOK — no agency-named ServiceNow scope in the live corpus.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
