#!/usr/bin/env python3
"""
UIAO-Core KSI Tier 2 Enrichment Script
Applies category, validation_type, pass_criteria, and uiao_extensions
to all KSI YAML files based on their category directory.

Usage:
    python scripts/enrich_ksis.py
    python scripts/enrich_ksis.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Enrichment rules (mirrors rules/ksi/enrichment_rules.py for standalone use)
# ---------------------------------------------------------------------------
ENRICHMENT_RULES: dict[str, dict] = {
    "iam": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "100% of non-exempt accounts use phishing-resistant MFA and automated lifecycle management",
            "type": "percentage",
            "threshold": 100,
            "operator": "equals",
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "private_endpoint_enforcement": True,
            "zero_trust_telemetry": True,
            "sase_global_secure_access": True,
        },
    },
    "boundary-protection": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "All PaaS services use Private Endpoints only; public exposure minimized per hub-spoke model",
            "type": "boolean",
            "threshold": 1,
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "private_endpoint_enforcement": True,
            "dns_segmentation_required": True,
            "hub_spoke_model": True,
            "video_project_isolation": True,
        },
    },
    "monitoring-logging": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "All security-relevant events logged and auditable within 5 minutes",
            "type": "boolean",
            "threshold": 1,
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "zero_trust_telemetry": True,
        },
    },
    "configuration-management": {
        "validation_type": "automated",
        "pass_criteria": {
            "description": "Configuration drift < 5% across all systems; approved baselines enforced",
            "type": "threshold",
            "threshold": 5,
            "operator": "less_than",
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "zero_trust_telemetry": True,
        },
    },
    "incident-response": {
        "validation_type": "semi-automated",
        "pass_criteria": {
            "description": "All incidents detected and escalated within defined SLA windows",
            "type": "boolean",
            "threshold": 1,
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
            "zero_trust_telemetry": True,
        },
    },
    "planning-personnel": {
        "validation_type": "manual",
        "pass_criteria": {
            "description": "All personnel controls documented and verified through annual review",
            "type": "boolean",
            "threshold": 1,
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
        },
    },
    "other": {
        "validation_type": "semi-automated",
        "pass_criteria": {
            "description": "Control implementation verified through evidence sources",
            "type": "boolean",
            "threshold": 1,
        },
        "uiao_extensions": {
            "gcc_moderate_focus": True,
        },
    },
}


def enrich_ksi_file(path: Path, dry_run: bool = False) -> bool:
    """Apply Tier 2 enrichment to a single KSI YAML file. Returns True if changed."""
    category = path.parent.name
    rules = ENRICHMENT_RULES.get(category, ENRICHMENT_RULES["other"])

    with path.open("r", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    if data is None:
        print(f"  SKIP {path.name} (empty file)")
        return False

    # Check if already enriched
    if "category" in data and "validation_type" in data and "pass_criteria" in data:
        return False  # already enriched

    # Apply enrichment fields
    data["category"] = category
    data["validation_type"] = rules["validation_type"]
    data["pass_criteria"] = rules["pass_criteria"]
    data["uiao_extensions"] = rules["uiao_extensions"]

    if dry_run:
        print(f"  DRY-RUN {path.name} -> would add category={category}, validation_type={rules['validation_type']}")
        return True

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Tier 2 KSI enrichment")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    args = parser.parse_args()

    ksi_root = Path("rules/ksi")
    if not ksi_root.exists():
        print(f"ERROR: {ksi_root} not found. Run from repo root.", file=sys.stderr)
        return 1

    total = 0
    enriched = 0
    skipped = 0

    for category_dir in sorted(ksi_root.iterdir()):
        if not category_dir.is_dir():
            continue
        for ksi_file in sorted(category_dir.glob("ksi-*.yaml")):
            total += 1
            changed = enrich_ksi_file(ksi_file, dry_run=args.dry_run)
            if changed:
                enriched += 1
            else:
                skipped += 1

    mode = "DRY-RUN" if args.dry_run else "APPLIED"
    print(f"\nKSI Tier 2 Enrichment [{mode}]")
    print(f"  Total KSI files : {total}")
    print(f"  Enriched        : {enriched}")
    print(f"  Already done    : {skipped}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
