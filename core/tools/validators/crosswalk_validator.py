#!/usr/bin/env python3
"""crosswalk_validator.py - Validate crosswalk entries against schema.

Loads tools/schema/crosswalk_schema.json and validates the crosswalk index
document at canon/data/crosswalk-index.yml.

Exit codes:
    0 - Crosswalk index conforms to schema.
    1 - Crosswalk index fails validation.
    2 - A fatal configuration problem (missing schema, unreadable files).

Usage:
    python tools/validators/crosswalk_validator.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "tools" / "schema" / "crosswalk_schema.json"
CROSSWALK_PATH = REPO_ROOT / "canon" / "data" / "crosswalk-index.yml"


def _load_schema() -> dict[str, Any]:
    """Load the crosswalk schema JSON from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _validate_instance(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty on success)."""
    try:
        from jsonschema import Draft7Validator  # type: ignore[import-not-found]
    except ImportError:
        return ["jsonschema package not installed; skipping schema validation"]

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return [
        f"{'.'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in errors
    ]


def main() -> int:
    """Validate crosswalk index. Returns 0 on success, 1 on failures, 2 on fatal errors."""
    if not SCHEMA_PATH.is_file():
        print(
            f"[crosswalk_validator] FATAL: schema not found at {SCHEMA_PATH}",
            file=sys.stderr,
        )
        return 2

    try:
        schema = _load_schema()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[crosswalk_validator] FATAL: cannot load schema: {exc}", file=sys.stderr)
        return 2

    if not CROSSWALK_PATH.is_file():
        print(
            f"[crosswalk_validator] No crosswalk index at {CROSSWALK_PATH.relative_to(REPO_ROOT)}; nothing to validate."
        )
        return 0

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[crosswalk_validator] FATAL: PyYAML is required (pip install pyyaml).",
            file=sys.stderr,
        )
        return 2

    try:
        text = CROSSWALK_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"[crosswalk_validator] FATAL: cannot read crosswalk index: {exc}", file=sys.stderr)
        return 2

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        print(f"[crosswalk_validator] FAIL: invalid YAML: {exc}")
        return 1

    if not isinstance(data, dict):
        print("[crosswalk_validator] FAIL: top-level document is not a mapping")
        return 1

    errors = _validate_instance(data, schema)
    if errors:
        rel = CROSSWALK_PATH.relative_to(REPO_ROOT)
        print(f"[crosswalk_validator] FAIL {rel}:")
        for err in errors:
            print(f"    - {err}")
        return 1

    plane_count = len(data.get("plane_crosswalk", []) or [])
    dep_count = len(data.get("cross_plane_dependencies", []) or [])
    print(
        f"[crosswalk_validator] OK: crosswalk index conforms to schema "
        f"({plane_count} planes, {dep_count} cross-plane dependencies)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
