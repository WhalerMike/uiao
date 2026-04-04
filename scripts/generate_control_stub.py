#!/usr/bin/env python3
"""Generate NIST 800-53 Rev 5 control YAML stubs for the UIAO control library.

Usage:
    python scripts/generate_control_stub.py AC-9 AC-13 PL-3 PL-5
    python scripts/generate_control_stub.py --batch 1   # PL, PS, RA, MA
    python scripts/generate_control_stub.py --list-missing

Writes files to data/control-library/{FAMILY}-{NUMBER}.yml
"""

import argparse
import os
import sys
from pathlib import Path

CONTROL_LIBRARY = Path(__file__).resolve().parent.parent / "data" / "control-library"

# NIST SP 800-53 Rev 5 family names
FAMILY_NAMES = {
    "AC": "Access Control",
    "AT": "Awareness and Training",
    "AU": "Audit and Accountability",
    "CA": "Assessment, Authorization, and Monitoring",
    "CM": "Configuration Management",
    "CP": "Contingency Planning",
    "IA": "Identification and Authentication",
    "IR": "Incident Response",
    "MA": "Maintenance",
    "MP": "Media Protection",
    "PE": "Physical and Environmental Protection",
    "PL": "Planning",
    "PM": "Program Management",
    "PS": "Personnel Security",
    "PT": "Personally Identifiable Information Processing and Transparency",
    "RA": "Risk Assessment",
    "SA": "System and Services Acquisition",
    "SC": "System and Communications Protection",
    "SI": "System and Information Integrity",
    "SR": "Supply Chain Risk Management",
}

# FedRAMP Moderate baseline controls (323 controls)
# Source: NIST SP 800-53B + FedRAMP Rev 5 Moderate Baseline
FEDRAMP_MODERATE = {
    "AC": ["1", "2", "2(1)", "2(2)", "2(3)", "2(4)", "2(5)", "2(9)", "2(10)",
           "3", "4", "5", "5(5)", "6", "7", "8", "10", "11", "11(1)", "12",
           "14", "17", "18", "19", "20", "21", "22"],
    "AT": ["1", "2", "2(2)", "2(3)", "3", "4"],
    "AU": ["1", "2", "3", "3(1)", "4", "5", "6", "6(1)", "6(3)", "7",
           "8", "9", "9(4)", "11", "12", "12(1)", "12(3)"],
    "CA": ["1", "2", "2(1)", "3", "5", "6", "7", "7(1)", "8", "8(2)", "9"],
    "CM": ["1", "2", "2(2)", "3", "3(2)", "4", "5", "6", "6(1)", "7",
           "7(1)", "7(2)", "8", "8(1)", "8(3)", "9", "10", "12", "12(1)"],
    "CP": ["1", "2", "2(1)", "2(3)", "2(5)", "2(8)", "3", "4", "4(1)",
           "6", "7", "8", "9", "9(1)", "10"],
    "IA": ["1", "2", "2(1)", "2(2)", "2(8)", "2(12)", "3", "4", "5",
           "5(1)", "5(2)", "5(6)", "6", "7", "8", "8(1)", "8(2)", "8(4)",
           "11", "12", "12(2)", "12(3)"],
    "IR": ["1", "2", "2(1)", "3", "4", "4(1)", "5", "6", "6(1)", "6(3)",
           "7", "8"],
    "MA": ["1", "2", "2(2)", "3", "3(1)", "3(2)", "5", "5(1)", "6"],
    "MP": ["1", "2", "3", "4", "5", "6", "6(2)", "7"],
    "PE": ["1", "2", "3", "3(1)", "4", "5", "6", "6(1)", "8", "9",
           "10", "11", "12", "13", "14", "15", "16", "17"],
    "PL": ["1", "2", "4", "4(1)", "10", "11"],
    "PS": ["1", "2", "3", "4", "5", "6", "7", "8", "9"],
    "RA": ["1", "2", "3", "3(1)", "5", "5(2)", "5(5)", "5(11)", "7", "9"],
    "SA": ["1", "2", "3", "4", "4(1)", "4(2)", "4(5)", "4(9)", "4(10)",
           "5", "8", "9", "9(2)", "10", "11", "15", "15(5)", "22"],
    "SC": ["1", "2", "4", "5", "7", "7(3)", "7(4)", "7(5)", "7(7)", "7(8)",
           "7(18)", "8", "8(1)", "10", "12", "13", "15", "18", "20",
           "28", "28(1)", "39"],
    "SI": ["1", "2", "2(2)", "2(6)", "3", "4", "4(2)", "4(4)", "4(5)",
           "4(18)", "5", "5(1)", "7", "8", "8(1)", "8(2)", "10", "12", "16"],
}


def get_existing_controls() -> set:
    """Return set of control IDs that already have files."""
    existing = set()
    for f in CONTROL_LIBRARY.glob("[A-Z][A-Z]-*.yml"):
        # Parse filename: AC-1.yml -> AC-1, SC-7(3).yml -> SC-7(3)
        control_id = f.stem
        existing.add(control_id)
    return existing


def get_missing_controls() -> list:
    """Return sorted list of missing FedRAMP Moderate controls."""
    existing = get_existing_controls()
    missing = []
    for family, numbers in sorted(FEDRAMP_MODERATE.items()):
        for num in numbers:
            control_id = f"{family}-{num}"
            # Check both with and without parentheses in filename
            filename_id = control_id.replace("(", "").replace(")", "")
            if control_id not in existing and filename_id not in existing:
                missing.append(control_id)
    return missing


def generate_stub(control_id: str) -> str:
    """Generate a YAML stub for a control."""
    parts = control_id.split("-", 1)
    family_code = parts[0]
    number = parts[1]
    family_name = FAMILY_NAMES.get(family_code, family_code)
    
    # Determine if this is an enhancement
    is_enhancement = "(" in number
    _ = number.split("(")[0] if is_enhancement else number  # noqa: F841
    
    return f"""# NIST SP 800-53 Rev 5 - Control Narrative
# Control ID : {control_id}
# Title      : [TITLE REQUIRED]
# Schema     : data/control-library (uiao-core canonical format)

control_id: {control_id}
title: "[TITLE REQUIRED]"
family: {family_name}
status: not-implemented

implemented_by: []

evidence: []

parameters: []

narrative: |
  [NARRATIVE REQUIRED - Describe the implementation of {control_id}
  in the context of the UIAO system. Reference specific technologies,
  policies, and procedures. Include FedRAMP Moderate parameters.]

related_controls: []
"""


def write_stub(control_id: str, force: bool = False) -> bool:
    """Write a control stub file. Returns True if written."""
    # Sanitize filename for enhancements: SC-7(3) -> SC-7(3).yml
    filename = f"{control_id}.yml"
    filepath = CONTROL_LIBRARY / filename
    
    if filepath.exists() and not force:
        print(f"  SKIP: {filename} (already exists)")
        return False
    
    content = generate_stub(control_id)
    filepath.write_text(content, encoding="utf-8")
    print(f"  CREATED: {filename}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Generate NIST 800-53 control stubs")
    parser.add_argument("controls", nargs="*", help="Control IDs to generate (e.g., AC-9 PL-3)")
    parser.add_argument("--list-missing", action="store_true", help="List all missing FedRAMP Moderate controls")
    parser.add_argument("--batch", type=int, choices=[1, 2, 3, 4, 5, 6], help="Generate a predefined batch")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    if args.list_missing:
        missing = get_missing_controls()
        print(f"Missing FedRAMP Moderate controls: {len(missing)}")
        for c in missing:
            print(f"  {c}")
        return

    # Batch definitions
    batches = {
        1: ["PL", "PS", "RA", "MA"],
        2: ["IR", "CP", "MP"],
        3: ["CA", "CM", "AT"],
        4: ["SC", "SI"],
        5: ["AC", "AU", "IA"],
        6: ["PE", "SA", "SR"],
    }

    controls = list(args.controls)
    
    if args.batch:
        families = batches[args.batch]
        missing = get_missing_controls()
        controls = [c for c in missing if c.split("-")[0] in families]
        print(f"Batch {args.batch}: {len(controls)} missing controls in {', '.join(families)}")

    if not controls:
        parser.print_help()
        return

    created = 0
    for control_id in controls:
        if write_stub(control_id, args.force):
            created += 1
    
    print(f"\nCreated {created} stub files in {CONTROL_LIBRARY}")


if __name__ == "__main__":
    main()
