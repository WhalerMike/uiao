#!/usr/bin/env python3
"""
UIAO-Core Control Library Analyzer
Analyzes data/control-library/ and provides summary + report
"""

from pathlib import Path
import yaml
from collections import defaultdict
import re
from datetime import datetime

def analyze_control_library(control_dir: str = "data/control-library"):
    control_path = Path(control_dir)
    if not control_path.exists():
        print(f"❌ Directory not found: {control_path}")
        return

    # Get all YAML files (exclude dir.txt)
    files = [f for f in control_path.glob("*.y*ml") if f.name != "dir.txt"]
    print(f"✅ Total control files found: {len(files)}\n")

    control_pattern = re.compile(r"^([A-Z]{2}-\d+)(?:\((\d+)\))?\.ya?ml$")

    families = defaultdict(list)
    base_controls = 0
    enhancements = 0
    control_details = []

    for file_path in sorted(files):
        match = control_pattern.match(file_path.name)
        if match:
            base_id = match.group(1)
            enh_num = match.group(2)
            if enh_num:
                enhancements += 1
                families[base_id].append(f"{base_id}({enh_num})")
            else:
                base_controls += 1
                family_code = base_id.split('-')[0]
                families[family_code].append(base_id)

        # Basic YAML structure check
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            has_ksi = any("ksi" in str(k).lower() for k in data.keys()) if isinstance(data, dict) else False
            has_params = "parameters" in data if isinstance(data, dict) else False
            has_impl = any(word in str(data).lower() for word in ["implementation", "statement"])
        except:
            has_ksi = has_params = has_impl = False

        control_details.append({
            "file": file_path.name,
            "has_ksi": has_ksi,
            "has_params": has_params,
            "has_impl": has_impl
        })

    # Summary
    print("=== CONTROL LIBRARY SUMMARY ===")
    print(f"Base controls          : {base_controls}")
    print(f"Enhancements           : {enhancements}")
    print(f"Total granular controls: {base_controls + enhancements}\n")

    print("=== FAMILY BREAKDOWN ===")
    family_counts = defaultdict(int)
    for fam_list in families.values():
        for item in fam_list:
            fam = item.split('-')[0]
            family_counts[fam] += 1

    for fam in sorted(family_counts.keys()):
        print(f"{fam:>3}: {family_counts[fam]:3d} files")

    with_ksi = sum(1 for d in control_details if d["has_ksi"])
    with_params = sum(1 for d in control_details if d["has_params"])
    with_impl = sum(1 for d in control_details if d["has_impl"])

    print("\n=== QUALITY METRICS ===")
    print(f"KSI rules present      : {with_ksi:3d} / {len(files)} ({with_ksi/len(files)*100:5.1f}%)")
    print(f"Parameters defined     : {with_params:3d} / {len(files)} ({with_params/len(files)*100:5.1f}%)")
    print(f"Implementation statements: {with_impl:3d} / {len(files)} ({with_impl/len(files)*100:5.1f}%)")

    # Save Markdown report
    report_path = control_path / "control_library_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# uiao-core Control Library Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(f"**Total files**: {len(files)}\n")
        f.write(f"**Base controls**: {base_controls}\n")
        f.write(f"**Enhancements**: {enhancements}\n")
        f.write(f"**Granular controls**: {base_controls + enhancements}\n\n")

        f.write("## Family Breakdown\n")
        for fam in sorted(family_counts.keys()):
            f.write(f"- **{fam}**: {family_counts[fam]} files\n")

        f.write("\n## Quality Metrics\n")
        f.write(f"- KSI coverage: **{with_ksi}** / {len(files)} files ({with_ksi/len(files)*100:.1f}%)\n")
        f.write(f"- Parameters: **{with_params}** files\n")
        f.write(f"- Implementation statements: **{with_impl}** files\n\n")

        f.write("## Next Steps\n")
        f.write("- Focus KSI rule population on AC, SC, IA, AU, and CM families first.\n")
        f.write("- Aim for >80% KSI coverage before starting SCuBA importer (Phase 1).\n")

    print(f"\n✅ Report saved to: {report_path.resolve()}")

if __name__ == "__main__":
    analyze_control_library()
