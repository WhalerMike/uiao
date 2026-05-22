#!/usr/bin/env python3
"""Add a `format: {html, docx}` block to .qmd files that don't already have one.

Reads each .qmd file under the given path(s), checks its YAML frontmatter for
a top-level `format:` key, and inserts the standard html+docx format block
before the closing `---` if absent. Idempotent — files that already declare
a format key are skipped.

The standard format block matches the per-page pattern customer-documents
pages use, producing both an HTML and a DOCX rendering:

    format:
      html:
        toc: true
        toc-depth: 3
      docx:
        toc: true

Use this to backfill canon-side .qmd pages that inherit the project default
(HTML only) so they get matching DOCX outputs and become eligible for the
section bundler. Reusable for future format-related backfills.

Usage:
    python scripts/add_qmd_format_block.py docs/modernization/
    python scripts/add_qmd_format_block.py docs/modernization/index.qmd
    python scripts/add_qmd_format_block.py docs/modernization/ --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FORMAT_BLOCK = """format:
  html:
    toc: true
    toc-depth: 3
  docx:
    toc: true
"""


def has_format_block(text: str) -> bool:
    """Return True if frontmatter already declares a top-level `format:` key."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False  # end of frontmatter, no format key seen
        if line.startswith("format:") or line.startswith("format :"):
            return True
    return False


def insert_format_block(text: str) -> str | None:
    """Insert FORMAT_BLOCK before the closing `---` of frontmatter.

    Returns the modified text, or None if no YAML frontmatter is found.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[:i] + [FORMAT_BLOCK] + lines[i:])
    return None


def expand_paths(paths: list[Path]) -> list[Path]:
    """Resolve directories to their *.qmd children (non-recursive); pass files through."""
    out: list[Path] = []
    for path in paths:
        if path.is_dir():
            out.extend(sorted(path.glob("*.qmd")))
        elif path.is_file() and path.suffix == ".qmd":
            out.append(path)
        elif not path.exists():
            print(f"skip (does not exist): {path}", file=sys.stderr)
        else:
            print(f"skip (not a .qmd or dir): {path}", file=sys.stderr)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to process. Directories are scanned non-recursively for *.qmd.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without modifying files.",
    )
    args = parser.parse_args(argv)

    files = expand_paths(args.paths)
    if not files:
        print("no .qmd files to process", file=sys.stderr)
        return 1

    changed = skipped_has = skipped_no_fm = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        if has_format_block(text):
            print(f"skip (has format): {f}")
            skipped_has += 1
            continue
        new = insert_format_block(text)
        if new is None:
            print(f"skip (no frontmatter): {f}")
            skipped_no_fm += 1
            continue
        if args.dry_run:
            print(f"would change: {f}")
        else:
            f.write_text(new, encoding="utf-8")
            print(f"changed: {f}")
        changed += 1

    print()
    print(f"summary: {changed} changed, {skipped_has} already had format, {skipped_no_fm} no frontmatter")
    return 0


if __name__ == "__main__":
    sys.exit(main())
