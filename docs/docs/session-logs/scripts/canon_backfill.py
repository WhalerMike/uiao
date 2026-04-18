#!/usr/bin/env python3
# =============================================================================
# canon_backfill.py — Phase D Stage 5, Batch 5.1.7
# -----------------------------------------------------------------------------
# Prepends canonical YAML frontmatter to every canon/ .md file that currently
# lacks it, and emits a canon/document-registry.yaml listing every allocated
# UIAO_NNN identifier.
#
# Assignment plan (hardcoded — reviewable in ASSIGNMENTS below):
#   UIAO_001           -> canon/UIAO-SSOT.md
#   UIAO_003           -> canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md
#   UIAO_100 - UIAO_120 -> canon/specs/*.md (alphabetical by filename)
#
#   UIAO_002 is skipped — it already claims document_id and needs surgical
#   field renames, not a stub prepend. That is Batch 5.1.8.
#
# Flags:
#   --canon-dir PATH      (required) Absolute path to the canon/ directory.
#   --registry-out PATH   (required) Where to write document-registry.yaml.
#   --only REL_PATH       Optional — run on a single file for canary.
#   --dry-run             Print intended actions without writing.
# =============================================================================
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

# (relative_path_under_canon, document_id, fallback_title_if_no_H1)
ASSIGNMENTS: list[tuple[str, str, str]] = [
    ("UIAO-SSOT.md",                                      "UIAO_001", "UIAO Single Source of Truth"),
    ("UIAO_003_Adapter_Segmentation_Overview_v1.0.md",    "UIAO_003", "UIAO Adapter Segmentation Overview"),
    ("specs/Compliance-Orchestrator.md",                  "UIAO_100", "Compliance Orchestrator"),
    ("specs/Platform-Overview.md",                        "UIAO_101", "Platform Overview"),
    ("specs/Platform-Services-Layer.md",                  "UIAO_102", "Platform Services Layer"),
    ("specs/UIAO-Spec-Test-Enforcement.md",               "UIAO_103", "UIAO Spec Test Enforcement"),
    ("specs/UIAO-Test-Harness-CI-Enforcement.md",         "UIAO_104", "UIAO Test Harness CI Enforcement"),
    ("specs/api-contract.md",                             "UIAO_105", "API Contract"),
    ("specs/cli.md",                                      "UIAO_106", "CLI"),
    ("specs/collector-interface.md",                      "UIAO_107", "Collector Interface"),
    ("specs/cql.md",                                      "UIAO_108", "CQL"),
    ("specs/data-lake.md",                                "UIAO_109", "Data Lake"),
    ("specs/drift.md",                                    "UIAO_110", "Drift"),
    ("specs/enforcement-runtime.md",                      "UIAO_111", "Enforcement Runtime"),
    ("specs/governance.md",                               "UIAO_112", "Governance"),
    ("specs/graph-schema.md",                             "UIAO_113", "Graph Schema"),
    ("specs/ha.md",                                       "UIAO_114", "High Availability"),
    ("specs/performance.md",                              "UIAO_115", "Performance"),
    ("specs/policy.md",                                   "UIAO_116", "Policy"),
    ("specs/recovery.md",                                 "UIAO_117", "Recovery"),
    ("specs/release.md",                                  "UIAO_118", "Release"),
    ("specs/tenancy.md",                                  "UIAO_119", "Tenancy"),
    ("specs/zero-trust.md",                               "UIAO_120", "Zero Trust"),
]

H1_RE = re.compile(r"^#\s+(.+?)\s*$")


def extract_h1(content: str, fallback: str) -> str:
    """Return the text of the first `# ...` heading, else the fallback."""
    for line in content.splitlines():
        m = H1_RE.match(line.strip())
        if m:
            return m.group(1).strip()
    return fallback


def escape_yaml_double_quoted(s: str) -> str:
    """Minimal escaping for YAML double-quoted scalar values."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_frontmatter(doc_id: str, title: str, today: str) -> str:
    t = escape_yaml_double_quoted(title)
    return (
        "---\n"
        f"document_id: {doc_id}\n"
        f'title: "{t}"\n'
        'version: "1.0"\n'
        "status: Current\n"
        "classification: CANONICAL\n"
        'owner: "Michael Stratton"\n'
        f'created_at: "{today}"\n'
        f'updated_at: "{today}"\n'
        'boundary: "GCC-Moderate"\n'
        "---\n\n"
    )


def build_registry(entries: list[tuple[str, str, str]], today: str) -> str:
    lines: list[str] = [
        "# UIAO Document Registry",
        "# ======================",
        "# Canonical source of truth for UIAO_NNN document identifier",
        "# allocations. Every artifact under canon/ that bears a",
        "# document_id must be registered here. Future allocations:",
        "# add a new entry in the appropriate reserved range, commit",
        "# alongside the artifact itself.",
        "#",
        "# Reserved ranges:",
        "#   UIAO_001          Single Source of Truth (SSOT)",
        "#   UIAO_002-UIAO_099 Top-level canon documents (technical",
        "#                     specifications, architecture overviews)",
        "#   UIAO_100-UIAO_199 canon/specs/ subsystem specifications",
        "#   UIAO_200-UIAO_299 Reserved for future operational/runtime",
        "#                     artifacts",
        "#   UIAO_900-UIAO_999 Reserved for test fixtures",
        "#",
        "# Pair registries (adapters, not documents):",
        "#   canon/adapter-registry.yaml",
        "#   canon/modernization-registry.yaml",
        "",
        'schema-version: "1.0.0"',
        f'updated: "{today}"',
        "",
        "documents:",
    ]
    # Sort by doc_id for a deterministic, reviewable registry
    for doc_id, rel, title in sorted(entries, key=lambda e: e[0]):
        t = escape_yaml_double_quoted(title)
        lines.append(f"  - id: {doc_id}")
        lines.append(f"    path: canon/{rel}")
        lines.append(f'    title: "{t}"')
        lines.append("    status: Current")
        lines.append("    classification: CANONICAL")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Canon frontmatter backfill")
    parser.add_argument("--canon-dir", required=True, type=Path)
    parser.add_argument("--registry-out", required=True, type=Path)
    parser.add_argument("--only", help="Process only this relative path (canary)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    canon: Path = args.canon_dir
    if not canon.is_dir():
        print(f"ERROR: canon dir not found: {canon}", file=sys.stderr)
        return 2

    today = date.today().isoformat()
    processed: list[tuple[str, str, str]] = []
    skipped: list[tuple[str, str]] = []

    for rel, doc_id, fallback_title in ASSIGNMENTS:
        if args.only and rel != args.only:
            continue
        path = canon / rel
        if not path.exists():
            print(f"SKIP  missing file       : {rel}")
            skipped.append((rel, "missing"))
            continue
        content = path.read_text(encoding="utf-8")
        if content.startswith("---"):
            print(f"SKIP  already has YAML fm: {rel}")
            skipped.append((rel, "has-frontmatter"))
            continue

        title = extract_h1(content, fallback_title)
        fm = build_frontmatter(doc_id, title, today)
        new_content = fm + content

        if args.dry_run:
            print(f"[DRY] {doc_id}  {rel:<55}  title={title!r}")
        else:
            path.write_text(new_content, encoding="utf-8")
            print(f"[OK]  {doc_id}  {rel:<55}  title={title!r}")
        processed.append((doc_id, rel, title))

    # Only write the registry on full runs (not --only, not --dry-run)
    if not args.only and not args.dry_run:
        # Include previously-assigned IDs that exist but were skipped
        # (e.g., UIAO_002 already has frontmatter — record it too)
        # Also include the canary if a prior run did only one file.
        # For simplicity: registry covers everything in ASSIGNMENTS that exists.
        all_entries: list[tuple[str, str, str]] = []
        for rel, doc_id, fallback_title in ASSIGNMENTS:
            path = canon / rel
            if not path.exists():
                continue
            # If it's one we just processed, use the live title.
            match = next((p for p in processed if p[1] == rel), None)
            if match:
                all_entries.append(match)
            else:
                # Skipped: try to recover title from H1, else fallback.
                content = path.read_text(encoding="utf-8")
                title = extract_h1(content, fallback_title)
                all_entries.append((doc_id, rel, title))
        # Also record UIAO_002 explicitly — it exists and has an assigned id
        u002_rel = "UIAO_002_SCuBA_Technical_Specification_v1.0.md"
        u002_path = canon / u002_rel
        if u002_path.exists() and not any(e[0] == "UIAO_002" for e in all_entries):
            content = u002_path.read_text(encoding="utf-8")
            title = extract_h1(content, "UIAO SCuBA Technical Specification")
            all_entries.append(("UIAO_002", u002_rel, title))

        args.registry_out.parent.mkdir(parents=True, exist_ok=True)
        args.registry_out.write_text(
            build_registry(all_entries, today), encoding="utf-8"
        )
        print(f"\nWrote registry: {args.registry_out} ({len(all_entries)} entries)")

    print(f"\nProcessed: {len(processed)}  Skipped: {len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
