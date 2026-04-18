#!/usr/bin/env python3
"""canon_validator.py - Validate canon documents against schema.

Loads tools/schema/canon_schema.json and validates the YAML frontmatter of
every Markdown file under canon/ (recursively). A file is considered a
canon document if its first non-empty line is the YAML frontmatter
delimiter (``---``).

Exit codes:
    0 - All canon documents pass schema validation.
    1 - One or more canon documents fail validation.
    2 - A fatal configuration problem (missing schema, unreadable files).

Usage:
    python tools/validators/canon_validator.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CORE_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = CORE_ROOT.parent
SCHEMA_PATH = CORE_ROOT / "tools" / "schema" / "canon_schema.json"
CANON_ROOT = REPO_ROOT / "src" / "uiao" / "canon"


def _load_schema() -> dict[str, Any]:
    """Load the canon schema JSON from disk."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_frontmatter(text: str) -> str | None:
    """Return raw YAML frontmatter (without delimiters) or None if absent.

    Recognises the conventional Jekyll-style frontmatter block: the file
    must start (after optional BOM / trailing CR) with ``---`` on its own
    line, and the frontmatter ends at the next ``---`` line.
    """
    # Normalize line endings without rewriting the file.
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return "\n".join(body)
        body.append(line)
    return None


def _iter_canon_markdown() -> list[Path]:
    """Return canon Markdown files (deterministic order)."""
    if not CANON_ROOT.exists():
        return []
    return sorted(p for p in CANON_ROOT.rglob("*.md") if p.is_file())


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
    """Validate canon documents. Returns 0 on success, 1 on failures, 2 on fatal errors."""
    if not SCHEMA_PATH.is_file():
        print(f"[canon_validator] FATAL: schema not found at {SCHEMA_PATH}", file=sys.stderr)
        return 2

    try:
        schema = _load_schema()
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[canon_validator] FATAL: cannot load schema: {exc}", file=sys.stderr)
        return 2

    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        print(
            "[canon_validator] FATAL: PyYAML is required (pip install pyyaml).",
            file=sys.stderr,
        )
        return 2

    files = _iter_canon_markdown()
    if not files:
        print("[canon_validator] No canon documents found; nothing to validate.")
        return 0

    failures = 0
    skipped = 0
    checked = 0
    for path in files:
        rel = path.relative_to(REPO_ROOT)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[canon_validator] FAIL {rel}: cannot read file: {exc}")
            failures += 1
            continue

        fm_raw = _extract_frontmatter(text)
        if fm_raw is None:
            print(f"[canon_validator] SKIP {rel}: no YAML frontmatter")
            skipped += 1
            continue

        try:
            metadata = yaml.safe_load(fm_raw)
        except yaml.YAMLError as exc:
            print(f"[canon_validator] FAIL {rel}: invalid YAML frontmatter: {exc}")
            failures += 1
            continue

        if not isinstance(metadata, dict):
            print(f"[canon_validator] FAIL {rel}: frontmatter is not a mapping")
            failures += 1
            continue

        errors = _validate_instance(metadata, schema)
        if errors:
            print(f"[canon_validator] FAIL {rel}:")
            for err in errors:
                print(f"    - {err}")
            failures += 1
        else:
            checked += 1

    print(
        f"[canon_validator] Summary: {checked} passed, {failures} failed, {skipped} skipped (no frontmatter)."
    )
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
