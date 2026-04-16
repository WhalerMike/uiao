#!/usr/bin/env python3
"""Control Library Analyzer - supports family subdirectories"""

from pathlib import Path
import yaml
from collections import defaultdict


def analyze_control_library(control_dir: str = "data/control-library"):
    control_dir = Path(control_dir)
    if not control_dir.exists():
        print(f"Directory not found: {control_dir}")
        return

    files = [f for f in control_dir.rglob("*.yml") if f.is_file() and f.name != "index.yaml"]
    family_counts = defaultdict(int)
    base_controls = enhancements = with_ksi = with_params = with_impl = 0

    for file in files:
        family = file.parent.name.lower()
        family_counts[family] += 1
        try:
            with open(file, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if "(" in file.stem:
                enhancements += 1
            else:
                base_controls += 1
            if data.get("ksi_rules") or data.get("ksi_id"):
                with_ksi += 1
            if data.get("parameters"):
                with_params += 1
            if data.get("implementation_statements"):
                with_impl += 1
        except Exception:
            pass

    total = len(files)
    print(f"Total control files: {total}")
    print(f"Base controls      : {base_controls}")
    print(f"Enhancements       : {enhancements}")
    print("\nFamily breakdown:")
    for fam in sorted(family_counts):
        print(f"  {fam.upper():4s}: {family_counts[fam]}")
    print(f"\nKSI coverage       : {with_ksi}/{total} ({with_ksi / total * 100:.1f}%)")
    print(f"Parameters defined : {with_params}/{total}")
    print(f"Impl statements    : {with_impl}/{total}")


if __name__ == "__main__":
    analyze_control_library()
