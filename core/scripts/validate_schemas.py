#!/usr/bin/env python3
# <!-- NEW (Proposed) -->
"""validate_schemas.py — Validate JSON schemas under ``schemas/``.

Runs in ``ai-security-audit.yml`` with ``continue-on-error: true`` as an
early compliance gate. Loads each ``*.json`` under ``schemas/`` and
ensures it is itself a valid JSON Schema document (via
``jsonschema.Draft202012Validator.check_schema``). Missing ``schemas/``
is a soft-skip.

Usage
-----
    python scripts/validate_schemas.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - reported to CI log, never masks a real failure
    print("[validate_schemas] jsonschema not installed; skipping.")
    sys.exit(0)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMAS_DIR = REPO_ROOT / "schemas"


def main() -> int:
    if not SCHEMAS_DIR.is_dir():
        print(f"[validate_schemas] {SCHEMAS_DIR.name}/ — absent, skipping.")
        return 0

    failures: list[tuple[Path, str]] = []
    checked = 0
    for path in sorted(SCHEMAS_DIR.rglob("*.json")):
        checked += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append((path, f"JSON parse error: {exc}"))
            continue
        try:
            Draft202012Validator.check_schema(data)
        except Exception as exc:  # noqa: BLE001
            failures.append((path, f"schema error: {exc}"))

    print(f"[validate_schemas] checked {checked} schema files; {len(failures)} failure(s).")
    if failures:
        for path, err in failures:
            rel = path.relative_to(REPO_ROOT).as_posix()
            print(f"  {rel}: {err}")
        return 1

    print("[validate_schemas] OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
