#!/usr/bin/env python3
"""UIAO-Core KSI Tier 2 Enrichment Script

Reads KSI index.yaml, applies enrichment rules from rules/ksi/enrichment_rules.py,
and outputs enriched KSI data for each control category.

Usage:
    python scripts/enrich_ksi_tier2.py [--dry-run] [--output-dir exports/ksi]
"""

import argparse
import json
import sys
import yaml
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from rules.ksi.enrichment_rules import ENRICHMENT_RULES, get_enrichment_for_category


def load_ksi_index(index_path: Path) -> dict:
    """Load the KSI index.yaml file."""
    if not index_path.exists():
        print(f"ERROR: KSI index not found at {index_path}")
        sys.exit(1)
    with open(index_path, 'r') as f:
        return yaml.safe_load(f)


def enrich_ksi_entry(entry: dict, category: str) -> dict:
    """Apply Tier 2 enrichment rules to a single KSI entry."""
    enrichment = get_enrichment_for_category(category)
    enriched = entry.copy()
    enriched['tier2_enrichment'] = {
        'validation_type': enrichment['validation_type'],
        'pass_criteria': enrichment['pass_criteria'],
        'uiao_extensions': enrichment['uiao_extensions'],
        'enrichment_applied': True,
        'enrichment_tier': 2
    }
    return enriched


def process_ksi_data(ksi_data: dict) -> dict:
    """Process all KSI entries and apply enrichment."""
    enriched_data = {}
    categories_processed = set()

    if isinstance(ksi_data, dict):
        for key, value in ksi_data.items():
            # Determine category from the key or nested structure
            category = key.lower().replace('_', '-')

            if isinstance(value, dict):
                enriched_data[key] = enrich_ksi_entry(value, category)
            elif isinstance(value, list):
                enriched_data[key] = [enrich_ksi_entry(item, category) if isinstance(item, dict) else item for item in value]
            else:
                enriched_data[key] = value

            categories_processed.add(category)

    return enriched_data, categories_processed


def write_output(enriched_data: dict, output_dir: Path, dry_run: bool = False):
    """Write enriched KSI data to output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'ksi_tier2_enriched.json'

    if dry_run:
        print("\n=== DRY RUN MODE ===")
        print(f"Would write to: {output_file}")
        print(f"Enriched entries: {len(enriched_data)}")
        print("\nSample output (first 2 entries):")
        sample = dict(list(enriched_data.items())[:2])
        print(json.dumps(sample, indent=2, default=str))
        return

    with open(output_file, 'w') as f:
        json.dump(enriched_data, f, indent=2, default=str)
    print(f"Enriched KSI data written to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='UIAO-Core KSI Tier 2 Enrichment')
    parser.add_argument('--dry-run', action='store_true', help='Preview enrichment without writing files')
    parser.add_argument('--output-dir', type=str, default='exports/ksi', help='Output directory for enriched data')
    parser.add_argument('--index', type=str, default='rules/ksi/index.yaml', help='Path to KSI index.yaml')
    args = parser.parse_args()

    index_path = PROJECT_ROOT / args.index
    output_dir = PROJECT_ROOT / args.output_dir

    print("UIAO-Core KSI Tier 2 Enrichment")
    print("=" * 40)
    print(f"Index: {index_path}")
    print(f"Output: {output_dir}")
    print(f"Dry run: {args.dry_run}")
    print()

    # Load KSI index
    ksi_data = load_ksi_index(index_path)
    print(f"Loaded {len(ksi_data) if ksi_data else 0} KSI entries")

    # Apply enrichment
    enriched_data, categories = process_ksi_data(ksi_data)
    print(f"Applied enrichment to {len(categories)} categories: {', '.join(sorted(categories))}")
    print(f"Available enrichment rules: {', '.join(ENRICHMENT_RULES.keys())}")

    # Write output
    write_output(enriched_data, output_dir, dry_run=args.dry_run)
    print("\nDone.")


if __name__ == '__main__':
    main()
