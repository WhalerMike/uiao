#!/usr/bin/env python3
"""Prune `docs/**/*.qmd` pages marked `publish_to_site: false` before render.

The Quarto build (`.github/workflows/quarto.yml`) renders the whole `docs/`
tree by auto-discovery and the DOCX matrix enumerates every
`customer-documents/*.qmd`; neither honours `publish_to_site`. This helper runs
as a pre-render step in the ephemeral CI checkout and removes any `.qmd` whose
YAML frontmatter declares `publish_to_site` false, so pages declared off-surface
(e.g. reserved/stub adapter scaffolds — issue #639) never reach the published
HTML/DOCX site.

Design notes:
  - Pure standard library (regex frontmatter scan), so the render jobs need no
    extra pip install before invoking it.
  - Deletes from the working copy only. CI checkouts are throwaway; this never
    runs against an authored tree in normal local work (and `--dry-run` lets you
    preview safely).
  - Self-maintaining: the set of pruned pages follows the frontmatter, so newly
    suppressed adapters are dropped automatically with no list to update here.

Usage:
  python scripts/prune_unpublished_qmd.py            # prune docs/ under repo root
  python scripts/prune_unpublished_qmd.py --dry-run  # list, don't delete
  python scripts/prune_unpublished_qmd.py --root some/dir
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# Matches a leading YAML frontmatter block: --- ... --- at the top of the file.
_FRONTMATTER = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
# Matches a `publish_to_site: <value>` line within the frontmatter block.
_PUBLISH_LINE = re.compile(r"^\s*publish_to_site\s*:\s*(.+?)\s*$", re.MULTILINE)
# Frontmatter values that mean "do not publish".
_FALSE_VALUES = frozenset({"false", "no", "off", "0"})


def is_unpublished(text: str) -> bool:
    """True if the file's frontmatter sets publish_to_site to a false-y value."""
    fm = _FRONTMATTER.match(text)
    if not fm:
        return False
    match = _PUBLISH_LINE.search(fm.group(1))
    if not match:
        return False
    value = match.group(1).strip().strip("\"'").lower()
    return value in _FALSE_VALUES


def find_unpublished(root: pathlib.Path) -> list[pathlib.Path]:
    """Return every .qmd under root whose frontmatter is publish_to_site: false."""
    hits: list[pathlib.Path] = []
    for path in sorted(root.rglob("*.qmd")):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if is_unpublished(text):
            hits.append(path)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parent.parent / "docs",
        help="Directory to scan (default: docs/ at repo root).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pages that would be pruned without deleting them.",
    )
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"ERROR: --root {args.root} is not a directory", file=sys.stderr)
        return 2

    targets = find_unpublished(args.root)
    verb = "Would prune" if args.dry_run else "Pruned"
    for path in targets:
        rel = path.relative_to(args.root)
        if not args.dry_run:
            path.unlink()
        print(f"  {verb}: {rel}")

    print(f"{verb} {len(targets)} unpublished .qmd page(s) under {args.root}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
