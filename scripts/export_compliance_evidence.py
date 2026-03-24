import csv
import warnings
from datetime import datetime

import yaml

warnings.warn(
    "scripts/export_compliance_evidence.py is deprecated. Use `uiao` CLI instead.",
    DeprecationWarning,
    stacklevel=1,
)


def export_master_evidence():
    # Load multiple data sources for cross-referencing
    sources = {"matrix": "data/unified_compliance_matrix.yml", "cisa": "data/cisa_zt_mapping.yml"}
    data_context = {}
    for key, path in sources.items():
        with open(path) as f:
            data_context[key] = yaml.safe_load(f)

    output_file = "exports/uiao_master_compliance_report.csv"
    headers = ["Pillar", "Visual_ID", "CISA_Maturity", "NIST_Controls", "Status", "Last_Audit_Sync"]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()

        # Merge logic: Use the Matrix as the primary driver
        for entry in data_context["matrix"]["unified_compliance_matrix"]:
            writer.writerow(
                {
                    "Pillar": entry["pillar"],
                    "Visual_ID": entry["visual_ref"],
                    "CISA_Maturity": entry["cisa_maturity"],
                    "NIST_Controls": "; ".join(entry["nist_controls"]),
                    "Status": "DRAFT - Pending Visual Upload" if entry["visual_ref"] != "V1" else "VERIFIED",
                    "Last_Audit_Sync": datetime.now().strftime("%Y-%m-%d"),
                }
            )

    print(f"Master Evidence Report synchronized: {output_file}")


if __name__ == "__main__":
    export_master_evidence()
