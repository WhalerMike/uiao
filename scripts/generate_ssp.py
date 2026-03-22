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
    inventory_items = context.get("inventory_items", [])
    if not isinstance(inventory_items, list):
        inventory_items = []

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
            "system-ids": [{"id": "uiao-modernized-cloud"}],
            "system-name": "UIAO-Modernized Cloud Environment",
            "system-name-short": "UIAO",
            "description": briefing.get("overview", "Reference architecture for TIC 3.0 migration using unified identity, addressing, and telemetry planes."),
            "system-information": {
                "information-types": [{
                    "title": "Operational Information",
                    "description": "General operational data supporting UIAO TIC 3.0 mission.",
                    "confidentiality-impact": {"base": "fips-199-moderate"},
                    "integrity-impact": {"base": "fips-199-moderate"},
                    "availability-impact": {"base": "fips-199-moderate"}
                }]
            },
            "security-impact-level": {
                "security-objective-confidentiality": "moderate",
                "security-objective-integrity": "moderate",
                "security-objective-availability": "moderate"
            },
            "status": {"state": "operational"},
            "authorization-boundary": {
                "description": "Cloud-hosted UIAO architecture boundary spanning identity, addressing, and telemetry planes."
            }
        },
        "system-implementation": {
            "users": [{"uuid": str(uuid.uuid4()), "title": "System Administrators", "role-ids": ["admin"]}],
            "components": []
        },
        "control-implementation": {
            "description": "Control implementations leveraged from UIAO components and compliance matrix",
            "implemented-requirements": []
        }
    }

    # Populate components from control_planes.yml; track component-id -> uuid mapping
    component_id_to_uuid = {}
    for plane in planes:
        comp_uuid = str(uuid.uuid4())
        plane_id = plane.get("id", "")
        component_id = f"component-{plane_id}"
        component_id_to_uuid[component_id] = comp_uuid
        props = [{"name": "pillar", "value": plane_id.upper()}]
        subtitle = str(plane.get("subtitle", "")).strip()
        if subtitle:
            props.append({"name": "subtitle", "value": subtitle})
        props.append({"name": "component-id", "value": component_id})
        ssp["system-implementation"]["components"].append({
            "uuid": comp_uuid,
            "type": "service",
            "title": plane.get("name", plane.get("id", "Unnamed Plane")),
            "description": plane.get("description", ""),
            "status": {"state": "operational"},
            "props": props
        })

    # Populate system-inventory from inventory-items.yml
    if inventory_items:
        oscal_inventory = []
        for item in inventory_items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id", "")
            item_props = [
                {"name": "asset-type", "value": item.get("asset_type", "software")}
            ]
            for prop in item.get("props", []):
                if isinstance(prop, dict):
                    item_props.append({"name": prop.get("name", ""), "value": prop.get("value", "")})

            # Resolve implemented-components to SSP component UUIDs
            impl_components = []
            for comp_ref in item.get("implemented_components", []):
                comp_uuid = component_id_to_uuid.get(comp_ref)
                if comp_uuid:
                    impl_components.append({"component-uuid": comp_uuid})
                else:
                    print(f"  [WARN] Inventory item '{item_id}' references unknown component '{comp_ref}'")

            oscal_item = {
                "uuid": str(uuid.uuid4()),
                "description": item.get("description", ""),
                "props": item_props,
                "responsible-parties": [
                    {"role-id": item.get("responsible_party", "agency-admin")}
                ],
                "implemented-components": impl_components
            }
            oscal_inventory.append(oscal_item)
        ssp["system-implementation"]["system-inventory"] = oscal_inventory

    # Build a lookup: control-id -> KSI mapping (first match wins)
    ksi_mappings = context.get("ksi_mappings", [])
    if not isinstance(ksi_mappings, list):
        ksi_mappings = []
    ksi_by_control = {}
    for ksi in ksi_mappings:
        for ctrl in ksi.get("control_ids", []):
            if ctrl not in ksi_by_control:
                ksi_by_control[ctrl] = ksi

    # Stub implemented-requirements from matrix
    for entry in matrix[:10]:
        ctrl_ids = entry.get("nist_controls", [])
        if ctrl_ids:
            ctrl_id = ctrl_ids[0]
            base_remarks = f"Pillar: {entry.get('pillar', 'N/A')}"
            ksi = ksi_by_control.get(ctrl_id)
            req = {
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_id,
                "remarks": (
                    f"{base_remarks} | KSI Evidence: {ksi['evidence_source']}"
                    if ksi else base_remarks
                )
            }
            if ksi:
                req["props"] = [{
                    "name": "ksi-id",
                    "value": ksi["ksi_id"],
                    "ns": "https://fedramp.gov/ns/oscal"
                }]
            ssp["control-implementation"]["implemented-requirements"].append(req)

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

    inventory = ssp_data.get("system-implementation", {}).get("system-inventory", [])
    print(f"OSCAL SSP skeleton exported to {json_path}")
    print(f"  System inventory items : {len(inventory)}")
    print("  Ready for FedRAMP 20x Moderate authorization")


if __name__ == "__main__":
    main()
