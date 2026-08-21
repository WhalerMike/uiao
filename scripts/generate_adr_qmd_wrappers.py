#!/usr/bin/env python3
"""Generate Quarto .qmd wrapper pages for every UIAO ADR.

For each src/uiao/canon/adr/adr-NNN-*.md file, produces:

  - docs/adr/adr-NNN-*.qmd — a thin wrapper that uses Quarto's
    {{< include >}} shortcode to embed the canonical ADR markdown body
    verbatim. Adds frontmatter (title, subtitle, date) and a callout
    that links back to the canonical source.

  - Optional in-place backfill of the source ADR frontmatter to declare
    publish_to_site, publication_style, and published_at per ADR-068.

Skips:
  - adr-000-adr-process.md (ADR-068 exclusion: process meta-document)
  - any ADR whose corresponding wrapper already exists (idempotent)

Also writes:
  - tools/publication-gaps/adr-sidebar-snippet.yaml — paste-ready YAML
    snippet for the docs/_quarto.yml sidebar entry that lists every
    generated wrapper.

Usage:
  python scripts/generate_adr_qmd_wrappers.py
  python scripts/generate_adr_qmd_wrappers.py --dry-run
  python scripts/generate_adr_qmd_wrappers.py --no-backfill
  python scripts/generate_adr_qmd_wrappers.py --force  # rewrite existing wrappers
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from typing import Any

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# Section .docx bundles are published as GitHub Release assets, not to Pages
# (PR #1421). The release tag is owned by the deploy workflow; read it from
# there rather than keeping a second copy that can silently drift — which is
# exactly what happened: #1421 hand-edited the 85 generated pages but not this
# generator, so re-running it reverted the change (issue #1429).
QUARTO_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "quarto.yml"
DOWNLOADS_RELEASE_TAG_FALLBACK = "downloads-latest"
RELEASE_ASSET_BASE = "https://github.com/WhalerMike/uiao/releases/download"


def downloads_release_tag() -> str:
    """Read the release tag the deploy workflow publishes bundles under."""
    try:
        text = QUARTO_WORKFLOW.read_text(encoding="utf-8")
    except OSError:
        return DOWNLOADS_RELEASE_TAG_FALLBACK
    match = re.search(r"^\s*tag_name:\s*(\S+)\s*$", text, re.M)
    return match.group(1) if match else DOWNLOADS_RELEASE_TAG_FALLBACK


def bundle_url(name: str) -> str:
    """Absolute Release-asset URL for a section bundle, e.g. adr-bundle.docx."""
    return f"{RELEASE_ASSET_BASE}/{downloads_release_tag()}/{name}"


ADR_SOURCE_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "adr"
ADR_OUTPUT_DIR = REPO_ROOT / "docs" / "adr"
SIDEBAR_SNIPPET = REPO_ROOT / "tools" / "publication-gaps" / "adr-sidebar-snippet.yaml"

EXCLUDED_BASENAMES = {"adr-000-adr-process.md", "adr-review-protocol.md"}

FM_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*(?:\n|$)", re.DOTALL)
ADR_ID_VALUE_PATTERN = re.compile(r"^ADR-\d{3}$|^adr-\d{3}$")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], int]:
    """Return (frontmatter dict, body offset).

    Body offset is the character index where the body begins (after
    the closing ``---``). Returns ({}, 0) if no frontmatter present.
    """
    m = FM_PATTERN.match(text)
    if not m:
        return ({}, 0)
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return ({}, 0)
    return (loaded or {}, m.end())


def extract_adr_metadata(fm: dict[str, Any], stem: str) -> dict[str, str]:
    """Best-effort extraction of title, status, date across heterogeneous ADR frontmatter.

    The ADR corpus has at least three frontmatter conventions:
      - id: ADR-NNN, status: accepted (lowercase)
      - adr: ADR-NNN, status: Proposed
      - adr_id: adr-NNN, status: ACCEPTED, decided: YYYY-MM-DD

    This function normalizes them into a uniform dict.
    """
    # Title is consistent across all conventions
    title = fm.get("title", stem.replace("-", " ").title())

    # Status is messy — normalize case
    status = (fm.get("status") or "Unknown").strip()
    status = {
        "accepted": "ACCEPTED",
        "proposed": "PROPOSED",
        "superseded": "SUPERSEDED",
        "deprecated": "DEPRECATED",
    }.get(status.lower(), status)

    # Date: try several keys
    date = fm.get("decided") or fm.get("date") or fm.get("created_at") or "unknown"
    if isinstance(date, str):
        date = date[:10]  # truncate to YYYY-MM-DD

    # ID: try the three known field names; fall back to filename
    adr_id = (
        (fm.get("adr_id") or fm.get("id") or fm.get("adr") or stem).upper().replace("ADR-", "ADR-")
    )  # normalize to ADR-NNN

    return {
        "adr_id": adr_id,
        "title": title,
        "status": status,
        "date": str(date),
    }


def render_wrapper_qmd(meta: dict[str, str], adr_path: pathlib.Path) -> str:
    """Build the Quarto wrapper page content."""
    # Relative path used by the {{< include >}} shortcode, which must resolve
    # on disk at render time.
    # depth: docs(1)/adr(2)/file → up 2 to root, then into src/uiao/canon/adr/
    rel_to_canon = f"../../src/uiao/canon/adr/{adr_path.name}"

    # The callout's "authoritative source" link points at the canon .md, which
    # does NOT publish to the site (src/ is not in the render tree), so a
    # relative link would 404. Use the repo's GitHub-blob convention instead
    # (lychee excludes github.com/WhalerMike/uiao/blob/, #757).
    blob_to_canon = f"https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/{adr_path.name}"

    # Page title: use the full ADR title (the wrapper's frontmatter title
    # becomes the rendered page title; the canon body's H1 becomes a
    # section heading at depth 1, which is acceptable).
    page_title = meta["title"].replace('"', '\\"')

    return f"""---
title: "{page_title}"
subtitle: "Architecture Decision Record · {meta["adr_id"]} · {meta["status"]}"
date: {meta["date"]}
---

::: {{.callout-note}}
## Architecture Decision Record

**{meta["adr_id"]}** — status: **{meta["status"]}** — decided: **{meta["date"]}**

This page renders the canonical ADR source verbatim. The authoritative
source is at [`src/uiao/canon/adr/{adr_path.name}`]({blob_to_canon}).
Any change to this ADR's content happens in the source file; this
wrapper is regenerated by `scripts/generate_adr_qmd_wrappers.py` per
[ADR-072](adr-072-canon-publication-policy.qmd).
:::

{{{{< include {rel_to_canon} >}}}}
"""


def needs_backfill(fm: dict[str, Any]) -> bool:
    """True if the source ADR is missing any of the ADR-068 publication fields."""
    return not ("publish_to_site" in fm and "publication_style" in fm and "published_at" in fm)


def backfill_frontmatter(adr_path: pathlib.Path) -> bool:
    """Add publish_to_site/publication_style/published_at to source ADR.

    Returns True if the file was modified.
    """
    text = adr_path.read_text(encoding="utf-8")
    fm, body_offset = parse_frontmatter(text)
    if not fm:
        # No frontmatter at all — add a minimal block
        new_fm_block = (
            "---\n"
            "publish_to_site: true\n"
            "publication_style: include\n"
            f"published_at: docs/adr/{adr_path.stem}.html\n"
            "---\n\n"
        )
        adr_path.write_text(new_fm_block + text, encoding="utf-8")
        return True

    if not needs_backfill(fm):
        return False

    # Build the new frontmatter line-by-line to preserve existing key order
    # and avoid YAML round-trip reformatting (which can lose comments and
    # change quoting).
    fm_text = text[:body_offset]  # includes the trailing ---\n
    body_text = text[body_offset:]

    # Find the closing --- and inject our new keys before it.
    # The frontmatter block looks like: ---\n<keys>\n---\n
    # We want to insert before the closing ---.
    closing_marker_match = re.search(r"\n---\s*\n?$", fm_text)
    if not closing_marker_match:
        # Unexpected shape; fall back to YAML round-trip
        fm["publish_to_site"] = True
        fm["publication_style"] = "include"
        fm["published_at"] = f"docs/adr/{adr_path.stem}.html"
        new_fm_block = "---\n" + yaml.safe_dump(fm, sort_keys=False) + "---\n"
        adr_path.write_text(new_fm_block + body_text, encoding="utf-8")
        return True

    insertion_point = closing_marker_match.start()
    new_keys = f"\npublish_to_site: true\npublication_style: include\npublished_at: docs/adr/{adr_path.stem}.html"
    new_fm_text = fm_text[:insertion_point] + new_keys + fm_text[insertion_point:]
    adr_path.write_text(new_fm_text + body_text, encoding="utf-8")
    return True


def generate_sidebar_snippet(stems: list[str]) -> str:
    """YAML snippet to paste into docs/_quarto.yml sidebar."""
    lines = [
        "# Generated by scripts/generate_adr_qmd_wrappers.py — paste into",
        "# docs/_quarto.yml under the 'Modernization Canon' or a dedicated",
        "# 'Architecture Decision Records' section.",
        "",
        '- section: "Architecture Decision Records"',
        "  contents:",
        "    - adr/adr-index.qmd",
    ]
    for stem in sorted(stems):
        lines.append(f"    - adr/{stem}.qmd")
    return "\n".join(lines) + "\n"


def render_adr_index(adr_metadata: list[dict[str, str]]) -> str:
    """Build a docs/adr/adr-index.qmd aggregate index page.

    ADRs without a published wrapper page (``publish_to_site: false`` in the
    canon frontmatter) are listed for completeness but link to the
    authoritative GitHub source instead of a wrapper .qmd that does not
    exist on the site — a relative page link would 404.
    """
    rows = []
    for meta in sorted(adr_metadata, key=lambda m: m["adr_id"]):
        escaped_title = meta["title"].replace("|", "\\|")
        if meta.get("published", True):
            target = f"{meta['stem']}.qmd"
        else:
            target = f"https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/{meta['stem']}.md"
        # A PROPOSED ADR legitimately has decided: null — show an em dash
        # rather than the extraction fallback string "unknown".
        date = meta["date"] if meta["date"] not in ("unknown", "None") else "—"
        rows.append(f"| [{meta['adr_id']}]({target}) | {escaped_title} | {meta['status']} | {date} |")
    table = "\n".join(rows)
    return f"""---
title: "Architecture Decision Records — Index"
subtitle: "All UIAO ADRs (canonical decisions and their rationale)"
date: 2026-05-14
---

<!-- orgpath-slot-allow-file: rows carry each ADR's title verbatim, and the
     historical ones name the slots they bound (ADR-063, "OrgPath Storage Slot
     — extensionAttribute1 Binding"). Renaming a decided ADR to satisfy a lint
     would falsify the record; this page asserts no live binding of its own. -->

::: {{.callout-tip}}
## Download the full section
**[adr-bundle.docx]({bundle_url("adr-bundle.docx")})** — every ADR in this section concatenated
into one Word document. Regenerated on every site deploy. Each ADR below is also
downloadable individually as its own `.docx` from its page.
:::

::: {{.callout-note}}
The UIAO Architecture Decision Records (ADRs) are the canonical
record of architectural decisions, their context, and their
consequences. Each ADR is published verbatim from its canonical
source under [`src/uiao/canon/adr/`](https://github.com/WhalerMike/uiao/tree/main/src/uiao/canon/adr).

The publication mechanism — `{{{{< include >}}}}` wrappers + this index
— is governed by [ADR-072](adr-072-canon-publication-policy.qmd).
:::

| ADR | Title | Status | Decided |
|---|---|---|---|
{table}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done; make no changes.",
    )
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="Skip the in-place frontmatter backfill on source ADRs.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite existing wrappers (default: skip if wrapper exists).",
    )
    args = parser.parse_args()

    if not ADR_SOURCE_DIR.exists():
        print(f"ERROR: ADR source directory not found: {ADR_SOURCE_DIR}", file=sys.stderr)
        return 1

    if not args.dry_run:
        ADR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        SIDEBAR_SNIPPET.parent.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    skipped: list[tuple[str, str]] = []
    backfilled: list[str] = []
    metadata: list[dict[str, str]] = []

    for adr_path in sorted(ADR_SOURCE_DIR.glob("adr-*.md")):
        if adr_path.name in EXCLUDED_BASENAMES:
            skipped.append((adr_path.name, "excluded by ADR-068"))
            continue

        text = adr_path.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        meta = extract_adr_metadata(fm, adr_path.stem)
        meta["stem"] = adr_path.stem

        wrapper_path = ADR_OUTPUT_DIR / f"{adr_path.stem}.qmd"

        # publish_to_site: false (ADR-072) means no wrapper page — unless a
        # wrapper already exists on disk, in which case the committed state
        # wins and the flag mismatch is for a human to reconcile.
        publish = fm.get("publish_to_site") is not False or wrapper_path.exists()
        meta["published"] = publish
        metadata.append(meta)

        if not publish:
            skipped.append((adr_path.name, "publish_to_site: false (no wrapper page)"))
        elif wrapper_path.exists() and not args.force:
            skipped.append((adr_path.name, "wrapper exists (use --force to overwrite)"))
        else:
            if not args.dry_run:
                wrapper_content = render_wrapper_qmd(meta, adr_path)
                wrapper_path.write_text(wrapper_content, encoding="utf-8")
            generated.append(adr_path.name)

        if not args.no_backfill and needs_backfill(fm):
            if not args.dry_run:
                if backfill_frontmatter(adr_path):
                    backfilled.append(adr_path.name)
            else:
                backfilled.append(adr_path.name)

    # Generate the index and sidebar snippet
    if not args.dry_run:
        index_path = ADR_OUTPUT_DIR / "adr-index.qmd"
        index_path.write_text(render_adr_index(metadata), encoding="utf-8")
        SIDEBAR_SNIPPET.write_text(
            generate_sidebar_snippet([m["stem"] for m in metadata if m.get("published", True)]),
            encoding="utf-8",
        )

    # Report
    print(f"ADR source dir:    {ADR_SOURCE_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrapper output:    {ADR_OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrappers generated: {len(generated)}")
    print(f"Wrappers skipped:   {len(skipped)}")
    print(f"Frontmatter backfilled: {len(backfilled)}")
    if not args.dry_run:
        print(f"Index page:         {(ADR_OUTPUT_DIR / 'adr-index.qmd').relative_to(REPO_ROOT)}")
        print(f"Sidebar snippet:    {SIDEBAR_SNIPPET.relative_to(REPO_ROOT)}")
    if args.dry_run:
        print("\n(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
