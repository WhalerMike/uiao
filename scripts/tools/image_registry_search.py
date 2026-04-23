#!/usr/bin/env python3
"""image_registry_search.py — discover reusable canonical images.

Reads src/uiao/canon/image-registry.yaml and surfaces entries matching an
authoring query. Used when adding a new [IMAGE-NN:] placeholder to a doc:
before writing a fresh prompt, run this to see if a canonical image
already covers the subject — reuse via [IMAGE-REF: UIAO-FIG-NNN] is
preferred over bespoke generation.

USAGE
    # Free-text query across title/description/themes/keywords/tags
    python scripts/tools/image_registry_search.py "boundary impact"

    # Narrow to exec-brief-appropriate material
    python scripts/tools/image_registry_search.py --audience executive \\
                                                  --doc-type executive-brief \\
                                                  "drift"

    # Filter by visual style
    python scripts/tools/image_registry_search.py --style pipeline-flow

    # List every canonical image, grouped by reuse_score
    python scripts/tools/image_registry_search.py --list

    # JSON output for editor integrations
    python scripts/tools/image_registry_search.py --json "evidence"

    # Show full detail for one ID
    python scripts/tools/image_registry_search.py --show UIAO-FIG-007

Ranking: matches on tags > document_types > themes > keywords > title >
description. Ties broken by reuse_score descending, then ID ascending.

Exit codes:
    0 — at least one match (or --list / --show succeeded)
    1 — no matches (search mode only)
    2 — bad input / registry schema violation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "image-registry.yaml"

# Score weights per field. Higher = stronger match signal.
FIELD_WEIGHTS = {
    "tags": 5,
    "document_types": 4,
    "themes": 3,
    "keywords": 2,
    "title": 3,
    "slug": 2,
    "description": 1,
    "caption": 1,
    "alt_text": 1,
}

# Reuse-metadata fields — the optional-but-recommended additions added
# in the registry schema for maximum reuse. An entry is "reuse-complete"
# when every one of these carries a non-empty value.
REUSE_METADATA_FIELDS = (
    "tags",
    "audience",
    "document_types",
    "visual_style",
    "themes",
    "keywords",
    "alt_text",
    "caption",
)


@dataclass(frozen=True)
class Match:
    entry: dict[str, Any]
    score: int
    hit_fields: tuple[str, ...]


def load_registry(path: Path) -> dict[str, Any]:
    if not path.is_file():
        print(f"ERROR: registry not found: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        print(f"ERROR: registry YAML parse failed: {exc}", file=sys.stderr)
        sys.exit(2)
    if not isinstance(data, dict) or "images" not in data:
        print("ERROR: registry missing 'images' list", file=sys.stderr)
        sys.exit(2)
    return data


def _contains(haystack: Any, needle: str) -> bool:
    """Case-insensitive substring match against a string or list of strings."""
    needle_lc = needle.lower()
    if isinstance(haystack, str):
        return needle_lc in haystack.lower()
    if isinstance(haystack, list):
        return any(isinstance(h, str) and needle_lc in h.lower() for h in haystack)
    return False


def _score_entry(entry: dict[str, Any], query_terms: list[str]) -> tuple[int, list[str]]:
    """Sum weighted hits for each term across scored fields."""
    score = 0
    hit_fields: set[str] = set()
    for term in query_terms:
        for field, weight in FIELD_WEIGHTS.items():
            if _contains(entry.get(field), term):
                score += weight
                hit_fields.add(field)
    return score, sorted(hit_fields)


def search(
    data: dict[str, Any],
    query: str | None,
    audience: str | None,
    doc_type: str | None,
    style: str | None,
    status_filter: str | None,
) -> list[Match]:
    terms = [t for t in re.split(r"\s+", query or "") if t]
    results: list[Match] = []
    for entry in data.get("images", []):
        # Hard filters first.
        if audience and audience not in (entry.get("audience") or []):
            continue
        if doc_type and doc_type not in (entry.get("document_types") or []):
            continue
        if style and style != entry.get("visual_style"):
            continue
        if status_filter and status_filter != entry.get("status"):
            continue

        if terms:
            score, hits = _score_entry(entry, terms)
            if score == 0:
                continue
            results.append(Match(entry=entry, score=score, hit_fields=tuple(hits)))
        else:
            # No query: every entry that passed hard filters qualifies.
            results.append(Match(entry=entry, score=0, hit_fields=()))

    # Rank: score desc, reuse_score desc, id asc.
    results.sort(
        key=lambda m: (
            -m.score,
            -int(m.entry.get("reuse_score") or 0),
            m.entry.get("id", ""),
        )
    )
    return results


def format_text(matches: list[Match], verbose: bool) -> str:
    if not matches:
        return "(no matches)"
    lines: list[str] = []
    for m in matches:
        e = m.entry
        marker = f"[score={m.score}]" if m.score else "[listed]"
        reuse = e.get("reuse_score", 0)
        status = e.get("status", "?")
        lines.append(f"{e.get('id', '?')}  {e.get('title', '(untitled)')}  {marker}  reuse={reuse}  status={status}")
        if verbose:
            if e.get("description"):
                lines.append(f"    desc: {e['description']}")
            if e.get("tags"):
                lines.append(f"    tags: {', '.join(e['tags'])}")
            if e.get("document_types"):
                lines.append(f"    doc-types: {', '.join(e['document_types'])}")
            if e.get("visual_style"):
                lines.append(f"    style: {e['visual_style']}")
            if m.hit_fields:
                lines.append(f"    matched on: {', '.join(m.hit_fields)}")
            if e.get("file"):
                lines.append(f"    file: {e['file']}")
            lines.append(f"    ref: [IMAGE-REF: {e.get('id', '?')}]")
            lines.append("")
    return "\n".join(lines)


def show_entry(data: dict[str, Any], image_id: str) -> int:
    for entry in data.get("images", []):
        if entry.get("id") == image_id:
            print(yaml.safe_dump(entry, sort_keys=False, allow_unicode=True), end="")
            return 0
    print(f"ERROR: no entry with id={image_id}", file=sys.stderr)
    return 1


def _is_populated(value: Any) -> bool:
    """A field counts as populated if it is non-empty (string / list / etc)."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def audit_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Report which reuse-metadata fields are populated vs missing."""
    populated = [f for f in REUSE_METADATA_FIELDS if _is_populated(entry.get(f))]
    missing = [f for f in REUSE_METADATA_FIELDS if f not in populated]
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "status": entry.get("status"),
        "populated": populated,
        "missing": missing,
        "complete": len(missing) == 0,
        "coverage": f"{len(populated)}/{len(REUSE_METADATA_FIELDS)}",
    }


def audit_registry(data: dict[str, Any], status_filter: str | None = None) -> list[dict[str, Any]]:
    """Audit every entry (optionally filtered by status) for reuse-metadata coverage."""
    reports: list[dict[str, Any]] = []
    for entry in data.get("images", []):
        if status_filter and entry.get("status") != status_filter:
            continue
        reports.append(audit_entry(entry))
    # Sort worst-coverage first so authoring attention lands where it's needed.
    reports.sort(key=lambda r: (len(r["populated"]), r["id"] or ""))
    return reports


def format_audit_text(reports: list[dict[str, Any]]) -> str:
    if not reports:
        return "(no entries to audit)"
    lines: list[str] = []
    complete = sum(1 for r in reports if r["complete"])
    lines.append(f"Reuse-metadata audit — {complete}/{len(reports)} entries are reuse-complete")
    lines.append("")
    for r in reports:
        flag = "OK " if r["complete"] else "GAP"
        lines.append(f"[{flag}] {r['id']}  {r['title'] or '(untitled)'}  coverage={r['coverage']}")
        if r["missing"]:
            lines.append(f"      missing: {', '.join(r['missing'])}")
    return "\n".join(lines)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Search the UIAO canonical image registry for reusable images.",
        epilog="See src/uiao/canon/image-registry.yaml for schema.",
    )
    p.add_argument("query", nargs="?", help="Free-text search query")
    p.add_argument("--audience", help="Filter by audience (executive, technical, assessor, ...)")
    p.add_argument("--doc-type", help="Filter by document_types (e.g., executive-brief)")
    p.add_argument("--style", help="Filter by visual_style (e.g., pipeline-flow)")
    p.add_argument("--status", default="current", help="Filter by status (default: current)")
    p.add_argument("--list", action="store_true", help="List all entries (no query required)")
    p.add_argument("--show", metavar="UIAO-FIG-NNN", help="Print full YAML for one entry")
    p.add_argument(
        "--audit",
        action="store_true",
        help="Report reuse-metadata coverage per entry (missing tags/audience/etc.)",
    )
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument("-v", "--verbose", action="store_true", help="Include descriptions, tags, refs")
    p.add_argument(
        "--registry",
        type=Path,
        default=REGISTRY_PATH,
        help=f"Registry path (default: {REGISTRY_PATH.relative_to(REPO_ROOT)})",
    )
    args = p.parse_args()

    data = load_registry(args.registry)

    if args.show:
        return show_entry(data, args.show)

    if args.audit:
        status_filter = None if args.status == "any" else args.status
        reports = audit_registry(data, status_filter=status_filter)
        if args.json:
            print(json.dumps(reports, indent=2))
        else:
            print(format_audit_text(reports))
        # Exit 0 if everything passes; 1 if any entry has gaps (so CI can gate).
        any_gap = any(not r["complete"] for r in reports)
        return 1 if any_gap else 0

    if not args.list and not args.query:
        p.print_usage(sys.stderr)
        print("\nSupply a query, or pass --list / --show / --audit.", file=sys.stderr)
        return 2

    # --list collapses to no-query search with default status filter.
    matches = search(
        data,
        query=args.query,
        audience=args.audience,
        doc_type=args.doc_type,
        style=args.style,
        status_filter=args.status,
    )

    if args.json:
        out = [
            {
                "id": m.entry.get("id"),
                "title": m.entry.get("title"),
                "score": m.score,
                "hit_fields": list(m.hit_fields),
                "reuse_score": m.entry.get("reuse_score", 0),
                "status": m.entry.get("status"),
                "file": m.entry.get("file"),
                "ref": f"[IMAGE-REF: {m.entry.get('id')}]" if m.entry.get("id") else None,
            }
            for m in matches
        ]
        print(json.dumps(out, indent=2))
    else:
        print(format_text(matches, verbose=args.verbose))

    return 0 if matches else 1


if __name__ == "__main__":
    sys.exit(main())
