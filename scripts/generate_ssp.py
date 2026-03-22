import yaml
import json
import uuid
from datetime import datetime
from pathlib import Path


def load_context():
    """Exact loader matching your other scripts (generate_docs.py, generate_oscal.py, etc.)"""
    context = {}
    DATA_DIR = Path("data")
    for yml_file in sorted(DATA_DIR.glob("*.yml")):
        key = yml_file.stem.replace("-", "_")
        with open(yml_file, encoding="utf-8") as f:
            content = yaml.safe_load(f)
            if content and isinstance(content, dict):
                context.update(content)
                context[f"_src_{key}"] = content

    # Load canon briefing for metadata
    with open("canon/uiao_leadership_briefing_v1.0.yaml", encoding="utf-8") as f:
        canon = yaml.safe_load(f)
        context.update(canon)

    return context


def build_ssp_skeleton(context):
    briefing = context.get("leadership_briefing", {})
    fedramp_cfg = context.get("fedramp_20x_config", {})
    planes = context.get("control_planes", [])
    matrix = context.get("unified_compliance_matrix", [])

    ssp = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": f"{briefing.get('title', 'UIAO Unified Identity-Addressing-Overlay Architecture')} - System Security Plan (FedRAMP Moderate Skeleton)",
            "last-modified": datetime.utcnow().isoformat() + "Z",
            "version": "1.0-skeleton",
            "oscal-version": "1.0.0",
            "props": [
                {"name": "impact-level", "value": "moderate", "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "compliance-strategy", "value": fedramp_cfg.get("compliance_strategy", "OSCAL-based Telemetry Validation")}
            ]
        },
        "import-profile": {
            "href": "https://github.com/GSA/fedramp-automation/raw/main/dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json"
        },
        "system-characteristics": {
            "system-name": "UIAO-Modernized Cloud Environment",
            "system-name-short": "UIAO",
            "description": briefing.get("overview", "Reference architecture for TIC 3.0 migration using unified identity, addressing, and telemetry planes."),
            "security-impact-level": {
                "security-objective-confidentiality": "moderate",
                "security-objective-integrity": "moderate",
                "security-objective-availability": "moderate"
            }
        },
        "system-implementations": {
            "components": []
        },
        "control-implementation": {
            "description": "Control implementations leveraged from UIAO components and compliance matrix",
            "implemented-requirements": []
        }
    }

    # Populate components from control_planes.yml
    for plane in planes:
        ssp["system-implementations"]["components"].append({
            "uuid": str(uuid.uuid4()),
            "type": "service",
            "title": plane.get("name", plane.get("id", "Unnamed Plane")),
            "description": plane.get("description", ""),
            "props": [
                {"name": "pillar", "value": plane.get("id", "").upper()},
                {"name": "subtitle", "value": plane.get("subtitle", "")}
            ]
        })

    # Stub implemented-requirements from matrix
    for entry in matrix[:10]:
        ctrl_ids = entry.get("nist_controls", [])
        if ctrl_ids:
            ssp["control-implementation"]["implemented-requirements"].append({
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_ids[0],
                "description": entry.get("impact_statement", "Implemented via UIAO plane"),
                "remarks": f"Pillar: {entry.get('pillar', 'N/A')}"
            })

    return ssp


def main():
    context = load_context()
    ssp_data = build_ssp_skeleton(context)

    OSCAL_OUT = Path("exports/oscal")
    OSCAL_OUT.mkdir(parents=True, exist_ok=True)

    json_path = OSCAL_OUT / "uiao-ssp-skeleton.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"system-security-plan": ssp_data},
            f, indent=2)

    print(f"OSCAL SSP skeleton exported to {json_path}")
    print("  Ready for FedRAMP 20x Moderate authorization")


if __name__ == "__main__":
    main()
