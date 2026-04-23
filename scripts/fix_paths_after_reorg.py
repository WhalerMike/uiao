#!/usr/bin/env python3
"""
fix_paths_after_reorg.py — update hardcoded core/ paths to src/uiao/ after
the canon/schemas/rules/ksi reorganization (commit 21455ebb).

Idempotent: re-running is safe. Each file is checked for the old pattern
before rewriting; if the pattern is absent, the file is left alone.

Usage (from the monorepo root):

    python scripts/fix_paths_after_reorg.py --dry-run
    python scripts/fix_paths_after_reorg.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Straight string substitutions applied to these files.
SUBS = [
    ("core/canon/", "src/uiao/canon/"),
    ("core/schemas/", "src/uiao/schemas/"),
    ("core/rules/", "src/uiao/rules/"),
    ("core/ksi/", "src/uiao/ksi/"),
]

SIMPLE_TARGETS = [
    ".github/workflows/metadata-validator.yml",
    ".github/workflows/schema-validation.yml",
    ".github/workflows/substrate-drift.yml",
    "scripts/validate_schemas.py",
    "scripts/bootstrap.sh",
]

# canon_validator.py needs a targeted structural edit, not a blind
# substitution, because it uses REPO_ROOT as a computed Path. We replace
# the three definition lines as a block.
CANON_VALIDATOR = "core/tools/validators/canon_validator.py"
CV_OLD = (
    "REPO_ROOT = Path(__file__).resolve().parents[2]\n"
    'SCHEMA_PATH = REPO_ROOT / "tools" / "schema" / "canon_schema.json"\n'
    'CANON_ROOT = REPO_ROOT / "canon"'
)
CV_NEW = (
    "CORE_ROOT = Path(__file__).resolve().parents[2]\n"
    "REPO_ROOT = CORE_ROOT.parent\n"
    'SCHEMA_PATH = CORE_ROOT / "tools" / "schema" / "canon_schema.json"\n'
    'CANON_ROOT = REPO_ROOT / "src" / "uiao" / "canon"'
)


def apply_subs_to_file(rel_path: str, dry_run: bool) -> bool:
    path = REPO_ROOT / rel_path
    if not path.exists():
        print(f"  skip (missing): {rel_path}")
        return False
    text = path.read_text(encoding="utf-8")
    new_text = text
    for old, new in SUBS:
        new_text = new_text.replace(old, new)
    if new_text == text:
        print(f"  no change: {rel_path}")
        return False
    print(f"  update: {rel_path}")
    if not dry_run:
        path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def fix_canon_validator(dry_run: bool) -> bool:
    path = REPO_ROOT / CANON_VALIDATOR
    if not path.exists():
        print(f"  skip (missing): {CANON_VALIDATOR}")
        return False
    text = path.read_text(encoding="utf-8")
    if CV_NEW in text:
        print(f"  no change (already patched): {CANON_VALIDATOR}")
        return False
    if CV_OLD not in text:
        print(f"  WARNING: expected block not found in {CANON_VALIDATOR} — please inspect manually.")
        return False
    print(f"  update: {CANON_VALIDATOR} (REPO_ROOT + CANON_ROOT)")
    if not dry_run:
        path.write_text(text.replace(CV_OLD, CV_NEW), encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write.")
    args = parser.parse_args()

    print(f"=== fix_paths_after_reorg — repo root: {REPO_ROOT} ===")
    if args.dry_run:
        print("[DRY RUN — no files will be written]\n")

    changed = 0
    for rel in SIMPLE_TARGETS:
        if apply_subs_to_file(rel, args.dry_run):
            changed += 1
    if fix_canon_validator(args.dry_run):
        changed += 1

    verb = "would change" if args.dry_run else "updated"
    print(f"\n{changed} file(s) {verb}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
