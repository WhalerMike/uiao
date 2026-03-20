#!/usr/bin/env python3
"""
export_compliance_evidence.py
Reads the unified_compliance_matrix.yml and exports it as a CSV
for ingestion into GRC tools (eMASS, Archer, CSAM).
"""

import csv
import yaml
from pathlib import Path

def export_to_csv():
    data_dir = Path(__file__).resolve().parent.parent / "data"
    exports_dir = Path(__file__).resolve().parent.parent / "exports"
    exports_dir.mkdir(exist_ok=True)

    input_file = data_dir / "unified_compliance_matrix.yml"
    output_file = exports_dir / "uiao_compliance_evidence.csv"

    with open(input_file, "r") as f:
        data = yaml.safe_load(f)

    matrix = data.get("unified_compliance_matrix", [])

    headers = [
        "Pillar",
        "Visual_Ref",
        "CISA_Pillar",
        "CISA_Maturity",
        "NIST_Controls",
        "Impact_Statement",
    ]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        for entry in matrix:
            writer.writerow({
                "Pillar": entry.get("pillar"),
                "Visual_Ref": entry.get("visual_ref"),
                "CISA_Pillar": entry.get("cisa_pillar"),
                "CISA_Maturity": entry.get("cisa_maturity"),
                "NIST_Controls": ", ".join(entry.get("nist_controls", [])),
                "Impact_Statement": entry.get("impact_statement"),
            })

    print(f"Success! Compliance evidence exported to {output_file}")


if __name__ == "__main__":
    export_to_csv()
