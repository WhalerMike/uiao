#!/usr/bin/env python3
"""Generate UIAO control-to-KSI crosswalk mapping.

Reads all KSI YAML files from rules/ksi/<category>/,
extracts control references, and writes the master crosswalk
to rules/ksi/uiao-control-to-ksi-mapping.yaml.
"""

from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KSI_DIR = REPO_ROOT / "rules" / "ksi"
OUTPUT_FILE = KSI_DIR / "uiao-control-to-ksi-mapping.yaml"

CATEGORIES = [
    "iam",
    "boundary-protection",
    "configuration-management",
    "incident-response",
    "monitoring-logging",
    "planning-personnel",
    "other",
]

def load_all_ksis() -> list[dict]:
    ksis = []
    for category in CATEGORIES:
        subdir = KSI_DIR / category
        if not subdir.exists():
            continue
        for f in sorted(subdir.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                data["_category"] = category
                data["_file"] = f"rules/ksi/{category}/{f.name}"
                ksis.append(data)
            except Exception as e:
                print(f"  WARNING: Could not parse {f.name}: {e}")
    return ksis

def build_crosswalk(ksis: list[dict]) -> dict:
    mappings = {}
    ksi_summary = {}

    for ksi in ksis:
        ksi_id = ksi.get("ksi_id", "UNKNOWN")
        category = ksi.get("_category", "other")
        file_path = ksi.get("_file", "")
        severity = ksi.get("severity", "moderate")
        family = ksi.get("family", "")
        controls = ksi.get("controls", [])
        title = ksi.get("title", "")
        data_sources = ksi.get("data_sources", [])

        # KSI summary entry
        ksi_summary[ksi_id] = {
            "title": title,
            "category": category,
            "family": family,
            "severity": severity,
            "file": file_path,
            "control_count": len(controls),
            "controls": controls,
            "data_sources": data_sources,
        }

        # Per-control mapping entries
        for control in controls:
            mappings[control] = {
                "ksi_id": ksi_id,
                "ksi_title": title,
                "category": category,
                "family": family,
                "severity": severity,
                "file": file_path,
            }

    return mappings, ksi_summary

def main():
    print("Loading KSI files...")
    ksis = load_all_ksis()
    print(f"  Loaded {len(ksis)} KSI files")

    mappings, ksi_summary = build_crosswalk(ksis)
    total_controls = len(mappings)
    print(f"  Mapped {total_controls} unique NIST controls to KSIs")

    # Category counts
    from collections import Counter
    cat_counts = Counter(v["category"] for v in ksi_summary.values())

    output = {
        "version": "1.0",
        "generated": "2026-04-04",
        "description": "UIAO-Core master crosswalk: NIST SP 800-53 controls to KSI identifiers",
        "stats": {
            "total_ksis": len(ksi_summary),
            "total_controls_mapped": total_controls,
            "categories": dict(sorted(cat_counts.items())),
        },
        "control_to_ksi": dict(sorted(mappings.items())),
        "ksi_summary": dict(sorted(ksi_summary.items())),
    }

    OUTPUT_FILE.write_text(
        yaml.dump(output, default_flow_style=False, sort_keys=False,
                  allow_unicode=True, width=120),
        encoding="utf-8"
    )
    print(f"\nDone: crosswalk written to {OUTPUT_FILE}")
    print(f"  {len(ksi_summary)} KSIs | {total_controls} controls mapped")

if __name__ == "__main__":
    main()
