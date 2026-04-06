#!/usr/bin/env python3
"""UIAO-Core KSI Tier 2 Enrichment Script

Walks all KSI YAML files in rules/ksi/<category>/ subdirectories,
applies Tier 2 enrichment rules from enrichment_rules.py in-place,
and skips any file that already has enrichment applied.

Usage:
    python scripts/enrich_ksi_tier2.py [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rules.ksi.enrichment_rules import ENRICHMENT_RULES, get_enrichment_for_category


def enrich_ksi_file(file_path: Path, dry_run: bool = False) -> bool:
    """Enrich a single KSI YAML file with Tier 2 data in-place.

    Returns True if the file was (or would be) enriched, False if skipped.
    """
    with open(file_path, encoding="utf-8") as f:
        ksi = yaml.safe_load(f)

    if not isinstance(ksi, dict):
        print(f"  SKIP {file_path.name} — not a valid YAML mapping")
        return False

    # Idempotency: skip if already enriched
    if ksi.get("validation_type"):
        return False

    # Derive category from the parent directory name
    category = file_path.parent.name.lower()
    enrichment = get_enrichment_for_category(category)

    # Apply Tier 2 fields
    ksi["category"] = category
    ksi["validation_type"] = enrichment["validation_type"]
    ksi["pass_criteria"] = enrichment["pass_criteria"]

    if "uiao_extensions" not in ksi:
        ksi["uiao_extensions"] = {}
    ksi["uiao_extensions"].update(enrichment["uiao_extensions"])

    ksi["oscal_props"] = {
        "implementation_status_prop": "satisfied",
        "evidence_type": "observation",
    }
    ksi["last_updated"] = datetime.now().isoformat()[:10]

    if dry_run:
        print(f"  DRY-RUN: {file_path.name} (category: {category})")
        return True

    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(ksi, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    print(f"  Enriched: {file_path.name}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="UIAO-Core KSI Tier 2 Enrichment — walks rules/ksi/ and enriches in-place"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview enrichment without modifying files",
    )
    args = parser.parse_args()

    ksi_root = PROJECT_ROOT / "rules" / "ksi"
    if not ksi_root.exists():
        print(f"ERROR: KSI root directory not found: {ksi_root}")
        sys.exit(1)

    total = 0
    enriched = 0
    skipped = 0

    print("UIAO-Core KSI Tier 2 Enrichment")
    print("=" * 50)
    print(f"KSI root : {ksi_root}")
    print(f"Dry run  : {args.dry_run}")
    print(f"Rules    : {', '.join(ENRICHMENT_RULES.keys())}")
    print()

    # Walk every ksi-*.yaml file across all category subdirectories
    for file_path in sorted(ksi_root.rglob("ksi-*.yaml")):
        total += 1
        if enrich_ksi_file(file_path, dry_run=args.dry_run):
            enriched += 1
        else:
            skipped += 1

    print()
    print("=" * 50)
    print(f"Processed : {total}")
    print(f"Enriched  : {enriched}")
    print(f"Skipped   : {skipped} (already enriched or invalid)")
    if args.dry_run:
        print("DRY-RUN — no files were modified.")
    print("Done.")


if __name__ == "__main__":
    main()
