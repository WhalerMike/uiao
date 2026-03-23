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


def build_set_parameters(context):
    """Build OSCAL set-parameters from data/parameters.yml.

    Returns a list of set-parameter dicts and a mapping of
    nist_control -> list[param_id] for per-requirement linkage.
    """
    params_cfg = context.get("parameters", {})
    if not isinstance(params_cfg, dict):
        return [], {}

    set_params = []
    ctrl_to_params = {}  # nist_control -> [param-id, ...]

    for category, items in params_cfg.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            param_id = item.get("id", "")
            if not param_id:
                continue
            ctrl = item.get("nist_control", "")
            # Build the OSCAL set-parameter entry
            sp = {
                "param-id": param_id,
                "values": [item.get("value", "")]
            }
            # Add remarks with all extra metadata
            remarks_parts = []
            for key in ["name", "method", "scope", "retention",
                        "lockout_duration", "evidence_source"]:
                val = item.get(key)
                if val:
                    remarks_parts.append(f"{key}: {val}")
            if remarks_parts:
                sp["remarks"] = " | ".join(remarks_parts)
            set_params.append(sp)

            # Map each referenced control to this param
            for c in ctrl.split("/"):
                c = c.strip()
                if c:
                    ctrl_to_params.setdefault(c, []).append(param_id)

    return set_params, ctrl_to_params


def build_ssp_skeleton(context):
    briefing = context.get("leadership_briefing", {})
    fedramp_cfg = context.get("fedramp_20x_config", {})
    planes = context.get("control_planes", [])
    matrix = context.get("unified_compliance_matrix", [])
    inventory_items = context.get("inventory_items", [])
    if not isinstance(inventory_items, list):
        inventory_items = []

    # Build set-parameters from parameters.yml
    set_params, ctrl_to_params = build_set_parameters(context)

    now_iso = datetime.utcnow().isoformat() + "Z"
    now_date = datetime.utcnow().strftime("%Y-%m-%d")

    ssp = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": f"{briefing.get('title', 'UIAO Unified Identity-Addressing-Overlay Architecture')} - System Security Plan (FedRAMP Moderate Skeleton)",
            "published": now_iso,
            "last-modified": now_iso,
            "version": "1.0-skeleton",
            "oscal-version": "1.0.4",
            "props": [
                {"name": "impact-level", "value": "moderate", "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "publication-date", "value": now_date, "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "markup-type", "value": "json", "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "compliance-strategy", "value": fedramp_cfg.get("compliance_strategy", "OSCAL-based Telemetry Validation"), "ns": "https://fedramp.gov/ns/oscal"}
            ]
        },
        "import-profile": {
            "href": "https://github.com/GSA/fedramp-automation/raw/fedramp-2.0.0-oscal-1.0.4/dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json"
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
            "set-parameters": set_params,
            "implemented-requirements": []
        }
    }

    # Populate components from control_planes.yml
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

    # Populate inventory-items from inventory-items.yml
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
        ssp["system-implementation"]["inventory-items"] = oscal_inventory

    # Add minimal parties/roles for OSCAL validation
    agency_party_uuid = str(uuid.uuid4())
    ssp["metadata"]["roles"] = [
        {"id": "admin", "title": "System Administrator"},
        {"id": "agency-admin", "title": "Agency Administrator"}
    ]
    ssp["metadata"]["parties"] = [
        {"uuid": agency_party_uuid, "type": "organization", "name": "UIAO Program Office"}
    ]
    for inv_item in ssp.get("system-implementation", {}).get("inventory-items", []):
        for rp in inv_item.get("responsible-parties", []):
            rp["party-uuids"] = [agency_party_uuid]

    # Build a lookup: control-id -> KSI mapping
    ksi_mappings = context.get("ksi_mappings", [])
    if not isinstance(ksi_mappings, list):
        ksi_mappings = []
    ksi_by_control = {}
    for ksi in ksi_mappings:
        for ctrl in ksi.get("control_ids", []):
            if ctrl not in ksi_by_control:
                ksi_by_control[ctrl] = ksi

    # Stub implemented-requirements from matrix with per-requirement set-parameters
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
            # Attach per-requirement set-parameters if any params map to this control
            req_params = ctrl_to_params.get(ctrl_id, [])
            if req_params:
                req["set-parameters"] = [
                    {"param-id": pid, "values": [sp["values"][0]]}
                    for pid in req_params
                    for sp in set_params
                    if sp["param-id"] == pid
                ]
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

    inventory = ssp_data.get("system-implementation", {}).get("inventory-items", [])
    set_params = ssp_data.get("control-implementation", {}).get("set-parameters", [])
    print(f"OSCAL SSP skeleton exported to {json_path}")
    print(f"  System inventory items : {len(inventory)}")
    print(f"  Set-parameters         : {len(set_params)}")
    print("  Ready for FedRAMP 20x Moderate authorization")


if __name__ == "__main__":
    main()
