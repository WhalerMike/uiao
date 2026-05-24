#!/usr/bin/env python3
"""Backfill the ADR-082 `lifecycle:` frontmatter field + replace hand-authored
"Aspirational" callout blocks with the `{{< lifecycle-banner >}}` shortcode.

Two changes per .qmd file, both idempotent:

  1. **Frontmatter:** if `lifecycle:` is absent, insert it (plus optional
     `tiers_adopted:`, `lifecycle_review:`) before the closing `---`.
     Files that already declare `lifecycle:` are skipped at this step.

  2. **Body callout:** find the canonical hand-authored aspirational block

         ::: {.callout-warning}
         ## Aspirational — canonically declared, not yet fully adopted

         <any body text>
         :::

     and replace it with `{{< lifecycle-banner >}}`. Other callouts
     (different `callout-*` classes, different titles, longer bodies)
     are NOT matched — those need human review.

The two changes are independent: a file may get the frontmatter
without the callout swap (if the callout pattern doesn't match), or
the callout swap without the frontmatter (if `lifecycle:` was already
declared). Either change alone is a no-op for the other.

Default lifecycle values follow ADR-082's "Defaults when `lifecycle:`
is absent" table: canon → `aspirational`; customer-docs → `adopted`
with `tiers_adopted: [1]`. Pass `--lifecycle adopted --tiers 1`
explicitly to apply the customer-doc default.

Usage:
  # ADR-082 Phase 4 — canon /customer-documents/reference-architecture/ backfill (aspirational)
  python scripts/add_lifecycle_to_qmd.py docs/customer-documents/reference-architecture/ \\
      --lifecycle aspirational --review 2026-11-22

  # ADR-082 Phase 5 — customer-doc backfill (adopted at Tier 1)
  python scripts/add_lifecycle_to_qmd.py docs/customer-documents/ \\
      --lifecycle adopted --tiers 1 --review 2026-11-22

  # Single file or dry run
  python scripts/add_lifecycle_to_qmd.py docs/customer-documents/reference-architecture/index.qmd \\
      --lifecycle aspirational --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VALID_LIFECYCLE = {"aspirational", "adopted", "superseded", "deprecated"}
VALID_TIERS = {1, 2, 3, 4, 5}

# Paths to skip when walking recursively. Mirror the convention used by
# scripts/scan_lifecycle_consistency.py.
EXCLUDE_PARTS = {"_site", "_freeze", ".quarto", "_extensions", "node_modules", ".venv", "__pycache__"}

# Canonical hand-authored Aspirational callout. Conservative match: exact
# title, callout-warning class, body until the closing `:::`. Files with
# divergent wording need human attention and are NOT auto-replaced.
ASPIRATIONAL_BLOCK_RE = re.compile(
    r"^::: \{\.callout-warning\}\s*\n"
    r"## Aspirational — canonically declared, not yet fully adopted\s*\n"
    r".*?\n"
    r":::\s*\n",
    re.MULTILINE | re.DOTALL,
)

SHORTCODE_REPLACEMENT = "{{< lifecycle-banner >}}\n"


def has_lifecycle_field(text: str) -> bool:
    """Return True if frontmatter already declares a top-level `lifecycle:` key."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    for line in lines[1:]:
        if line.strip() == "---":
            return False
        if line.startswith("lifecycle:") or line.startswith("lifecycle :"):
            return True
    return False


def insert_lifecycle_fields(
    text: str,
    lifecycle: str,
    tiers_adopted: list[int] | None,
    lifecycle_review: str | None,
) -> str | None:
    """Insert lifecycle fields before the closing `---` of frontmatter.

    Returns the modified text, or None if no YAML frontmatter is found.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            block = [f"lifecycle: {lifecycle}\n"]
            if tiers_adopted:
                block.append(f"tiers_adopted: {tiers_adopted}\n")
            if lifecycle_review:
                block.append(f"lifecycle_review: {lifecycle_review}\n")
            return "".join(lines[:i] + block + lines[i:])
    return None


def replace_aspirational_block(text: str) -> tuple[str, bool]:
    """Replace the first canonical Aspirational callout with the shortcode.

    Returns (text, replaced_bool).
    """
    new_text, n = ASPIRATIONAL_BLOCK_RE.subn(SHORTCODE_REPLACEMENT, text, count=1)
    return new_text, n > 0


def expand_paths(paths: list[Path], recursive: bool = False) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            files = p.rglob("*.qmd") if recursive else p.glob("*.qmd")
            for f in sorted(files):
                if any(part in EXCLUDE_PARTS for part in f.parts):
                    continue
                out.append(f)
        elif p.is_file() and p.suffix == ".qmd":
            out.append(p)
        elif not p.exists():
            print(f"skip (does not exist): {p}", file=sys.stderr)
        else:
            print(f"skip (not a .qmd or dir): {p}", file=sys.stderr)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to process. Directories scanned non-recursively by default; use --recursive for *.qmd everywhere under the directory.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Walk directories recursively (rglob). Skips build outputs (_site, _freeze, .quarto, _extensions, node_modules, .venv, __pycache__).",
    )
    parser.add_argument(
        "--lifecycle",
        required=True,
        choices=sorted(VALID_LIFECYCLE),
        help="Lifecycle value to insert (required).",
    )
    parser.add_argument(
        "--tiers",
        default="",
        help="Comma-separated tier numbers (1-5) for tiers_adopted. Required when --lifecycle adopted.",
    )
    parser.add_argument(
        "--review",
        default=None,
        help="ISO 8601 date for lifecycle_review (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without modifying files.",
    )
    args = parser.parse_args(argv)

    # Parse tiers
    tiers: list[int] = []
    if args.tiers:
        try:
            tiers = [int(t.strip()) for t in args.tiers.split(",") if t.strip()]
        except ValueError as e:
            parser.error(f"--tiers must be comma-separated integers: {e}")
        for t in tiers:
            if t not in VALID_TIERS:
                parser.error(f"--tiers value '{t}' must be in {sorted(VALID_TIERS)}")

    if args.lifecycle == "adopted" and not tiers:
        parser.error("--lifecycle adopted requires --tiers (e.g., --tiers 1,3)")

    if args.review:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", args.review):
            parser.error(f"--review must be ISO 8601 YYYY-MM-DD; got '{args.review}'")

    files = expand_paths(args.paths, recursive=args.recursive)
    if not files:
        print("no .qmd files to process", file=sys.stderr)
        return 1

    fm_changed = body_changed = skipped_fm = skipped_body = no_fm = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        new_text = text
        report_lines: list[str] = []

        # Step 1: frontmatter
        if has_lifecycle_field(new_text):
            report_lines.append("frontmatter: skipped (lifecycle already present)")
            skipped_fm += 1
        else:
            inserted = insert_lifecycle_fields(
                new_text,
                lifecycle=args.lifecycle,
                tiers_adopted=tiers if tiers else None,
                lifecycle_review=args.review,
            )
            if inserted is None:
                report_lines.append("frontmatter: skipped (no YAML frontmatter found)")
                no_fm += 1
            else:
                new_text = inserted
                report_lines.append(f"frontmatter: added lifecycle={args.lifecycle}")
                fm_changed += 1

        # Step 2: body callout replacement
        new_text, replaced = replace_aspirational_block(new_text)
        if replaced:
            report_lines.append("body: replaced Aspirational callout with shortcode")
            body_changed += 1
        else:
            report_lines.append("body: skipped (no canonical Aspirational callout matched)")
            skipped_body += 1

        # Apply or report
        if new_text != text:
            if args.dry_run:
                print(f"would change: {f}")
            else:
                f.write_text(new_text, encoding="utf-8")
                print(f"changed: {f}")
            for line in report_lines:
                print(f"  {line}")
        else:
            print(f"unchanged: {f}")
            for line in report_lines:
                print(f"  {line}")

    print()
    print(
        f"summary: frontmatter {fm_changed} added, {skipped_fm} skipped (already had), {no_fm} no-FM; "
        f"body {body_changed} replaced, {skipped_body} skipped (no match)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
