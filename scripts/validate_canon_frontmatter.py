#!/usr/bin/env python3
"""Validate canon document frontmatter against src/uiao/schemas/metadata-schema.json.

Mirrors the inline body of .github/workflows/metadata-validator.yml so
pre-commit and CI run the exact same check.

Exit 0 on success, 1 if any UIAO_NNN-bearing frontmatter fails validation.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any

import yaml
from jsonschema import Draft202012Validator

SCHEMA_PATH = pathlib.Path("src/uiao/schemas/metadata-schema.json")
CANON_ROOT = pathlib.Path("src/uiao/canon")
FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)


def main() -> int:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    failures: list[str] = []

    for md in sorted(CANON_ROOT.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        m = FM_PATTERN.match(text)
        if not m:
            continue
        fm: dict[str, Any] = yaml.safe_load(m.group(1)) or {}
        if "document_id" not in fm:
            continue
        for err in validator.iter_errors(fm):
            loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
            failures.append(f"{md} [{loc}] {err.message}")

    if failures:
        for line in failures:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
