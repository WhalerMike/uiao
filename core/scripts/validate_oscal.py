#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_oscal.py — Validate generated OSCAL artifacts.

Runs in ``ai-security-audit.yml`` after the build-readiness gate. OSCAL
generation lives in ``uiao-impl`` post split; this repository ships the
canon inputs only. The script therefore:

* Looks for generated OSCAL under ``exports/oscal/`` (where uiao-impl
  places them when the two repos are checked out side-by-side in CI).
* Parses every ``*.json`` under that root and confirms it declares a
  recognised OSCAL model root key (``system-security-plan``,
  ``component-definition``, ``profile``, ``catalog``, or ``oscal``).
* When the directory is absent, the script logs and exits 0 — uiao-core
  PRs that don't touch impl code should not fail this gate.

Usage
-----
    python scripts/validate_oscal.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OSCAL_DIR = REPO_ROOT / "exports" / "oscal"
KNOWN_ROOTS = {
    "system-security-plan",
    "component-definition",
    "profile",
    "catalog",
    "assessment-plan",
    "assessment-results",
    "plan-of-action-and-milestones",
    "oscal",
}


def main() -> int:
    if not OSCAL_DIR.is_dir():
        print(f"[validate_oscal] {OSCAL_DIR.relative_to(REPO_ROOT)}/ — absent, skipping.")
        return 0

    failures: list[tuple[Path, str]] = []
    checked = 0
    for path in sorted(OSCAL_DIR.rglob("*.json")):
        checked += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append((path, f"JSON parse error: {exc}"))
            continue
        if not isinstance(data, dict):
            failures.append((path, "top level is not an object"))
            continue
        if not KNOWN_ROOTS.intersection(data.keys()):
            failures.append((path, f"no known OSCAL root key; got {sorted(data.keys())[:3]}"))

    print(f"[validate_oscal] checked {checked} OSCAL artifact(s); {len(failures)} failure(s).")
    if failures:
        for path, err in failures:
            rel = path.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}: {err}")
        return 1

    print("[validate_oscal] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
