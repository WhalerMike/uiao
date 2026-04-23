#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_build_readiness.py — Safety gate for AI Security Audit.

Purpose
-------
Runs inside ``.github/workflows/ai-security-audit.yml`` as the
"build-readiness safety gate" step. Its job is to answer the question
"is this PR safe to proceed through the security pipeline?" — meaning
the canon YAMLs/JSONs it depends on parse cleanly and the minimum
required directories exist.

This is the initial post-split scaffold. It walks ``canon/`` and
``generation-inputs/`` (when present) and validates that every ``*.yml``
/ ``*.yaml`` / ``*.json`` file parses. Missing directories are treated
as soft-skip (branches legitimately touch only one side of canon). Full
gate logic (control-library coverage, schema cross-refs, blocking
findings budget) is tracked separately; this entrypoint lets
ai-security-audit pass on a clean tree until that lands.

Usage
-----
    python scripts/validate_build_readiness.py

Exit codes
----------
0 — tree is ready (or relevant dirs absent).
1 — a canon file failed to parse.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
ROOTS = ("canon", "generation-inputs", "schemas", "rules")


def check_file(path: Path) -> str | None:
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return f"read error: {exc}"
    try:
        if path.suffix == ".json":
            json.loads(text)
        else:
            yaml.safe_load(text)
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        return f"parse error: {exc}"
    return None


def main() -> int:
    total = 0
    failures: list[tuple[Path, str]] = []
    for name in ROOTS:
        root = REPO_ROOT / name
        if not root.exists():
            print(f"[validate_build_readiness] {name}/ — absent, skipping.")
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in (".yml", ".yaml", ".json"):
                continue
            total += 1
            err = check_file(path)
            if err is not None:
                failures.append((path, err))

    print(f"[validate_build_readiness] parsed {total} canon files; {len(failures)} failure(s).")
    if failures:
        for path, err in failures:
            rel = path.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}: {err}")
        return 1

    print("[validate_build_readiness] OK — safe to proceed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
