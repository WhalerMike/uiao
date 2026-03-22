"""OSCAL Component Definition Export for UIAO Canon.

Generates a machine-readable OSCAL 1.0 Component Definition JSON
from the UIAO YAML canon (control-planes, unified_compliance_matrix,
fedramp-20x config). Aligns with FedRAMP 20x Phase 2 Moderate.
"""
import yaml
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
OSCAL_OUT = ROOT / "exports" / "oscal"


def load_context():
    """Load all data/*.yml files + canon, same pattern as generate_docs.py."""
    context = {}
    if DATA_DIR.exists():
        for yml_file in sorted(DATA_DIR.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            if content and isinstance(content, dict):
                context.update(content)
                context[key] = content
    if CANON.exists():
        with CANON.open("r", encoding="utf-8") as f:
            canon = yaml.safe_load(f)
        if canon:
            context.update(canon)
    return context


def _as_dict(obj, name_key="name"):
    """Normalize a component entry that may be a str or dict."""
    if isinstance(obj, dict):
        return obj
    # If it's a plain string, wrap it as a minimal dict
    return {name_key: str(obj), "role": "", "capabilities": []}


def _safe_get(obj, key, default=""):
    """Get a value from obj whether it is a dict or a plain string."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def build_component_definition(context):
    """Build OSCAL Component Definition from UIAO canon data."""
    cfg = context.get("fedramp_20x_config", {})
    if not isinstance(cfg, dict):
        cfg = {}

    planes = context.get("control_planes", [])
    if not isinstance(planes, list):
        planes = []

    matrix = context.get("unified_compliance_matrix", [])
    if not isinstance(matrix, list):
        matrix = []

    core_mappings = cfg.get("core_mappings", []) if isinstance(cfg, dict) else []
    if not isinstance(core_mappings, list):
        core_mappings = []

    briefing = context.get("leadership_briefing", {})
    if not isinstance(briefing, dict):
        briefing = {}

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    cd = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": _safe_get(briefing, "title",
                               "UIAO Unified Identity-Addressing-Overlay Architecture"),
            "version": "1.0",
            "oscal-version": "1.0.4",
            "last-modified": now_iso,
                        "published": now_iso,
            "props": [
                {
                    "name": "fedramp-impact",
                    "value": cfg.get("authorization_level", "Moderate"),
                    "ns": "https://fedramp.gov/ns/oscal"
                },
                {
                    "name": "compliance-strategy",
                    "value": cfg.get("compliance_strategy",
                                     "OSCAL-based Telemetry Validation"),
                    "ns": "https://fedramp.gov/ns/oscal"
                },
                {
                    "name": "ksi-dashboard",
                    "value": cfg.get("ksi_dashboard_status", "Operational")
                },
                {
                    "name": "framework-version",
                    "value": cfg.get("framework_version", "2026.1")
                },
                {
                    "name": "markup-type",
                    "value": "json",
                    "ns": "https://fedramp.gov/ns/oscal"
                }
            ]
        },
        "components": [],
        "capabilities": []
    }

    # Build components from control_planes
    comp_uuids = {}
    for plane in planes:
        if not isinstance(plane, dict):
            print(f"  [WARN] Skipping non-dict plane entry: {plane!r}")
            continue
        comp_uuid = str(uuid.uuid4())
        plane_id = plane.get("id", "unknown")
        comp_uuids[plane_id] = comp_uuid

        # Build sub-component list from plane components
        raw_subs = plane.get("components", [])
        if not isinstance(raw_subs, list):
            raw_subs = []

        sub_components = []
        for raw_sub in raw_subs:
            sub = _as_dict(raw_sub)
            sub_components.append({
                "name": sub.get("name", ""),
                "role": sub.get("role", ""),
                "capabilities": sub.get("capabilities", [])
            })

        props = [{"name": "uiao-pillar", "value": str(plane_id).upper()}]
        subtitle = str(plane.get("subtitle", "")).strip()
        if subtitle:
            props.append({"name": "subtitle", "value": subtitle})
        props.append({"name": "component-id", "value": f"component-{plane_id}"})
        cd["components"].append({
            "uuid": comp_uuid,
            "type": "service",
            "title": plane.get("name", plane_id),
            "description": plane.get("description", ""),
            "props": props,
            "remarks": json.dumps(sub_components)
        })

    # Build control-implementations from unified_compliance_matrix
    control_implementations = []
    for entry in matrix:
        if not isinstance(entry, dict):
            continue
        imp_reqs = []
        for ctrl_id in entry.get("nist_controls", []):
            # Find matching KSI from core_mappings
            ksi_cat = "KSI-UNKNOWN"
            evidence = ""
            for m in core_mappings:
                if not isinstance(m, dict):
                    continue
                if ctrl_id in m.get("nist_rev5_control", ""):
                    ksi_cat = m.get("ksi_category", ksi_cat)
                    evidence = m.get("evidence_source", evidence)
                    break
            imp_reqs.append({
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_id,
                "description": entry.get("impact_statement", ""),
                "props": [
                    {"name": "ksi-category", "value": ksi_cat},
                    {"name": "cisa-maturity",
                     "value": entry.get("cisa_maturity", "Advanced")},
                    {"name": "evidence-source", "value": evidence}
                ]
            })
        if imp_reqs:
            control_implementations.append({
                "uuid": str(uuid.uuid4()),
                "source": (
                    "https://github.com/GSA/fedramp-automation/"
                    "raw/main/dist/content/rev5/baselines/json/"
                    "FedRAMP_rev5_MODERATE-baseline_profile.json"
                ),
                "description": f"UIAO {entry.get('pillar', '')} Pillar",
                "implemented-requirements": imp_reqs
            })

    # Attach control implementations to the first component (OSCAL requires
    # control-implementations to be nested inside a DefinedComponent, not at
    # the ComponentDefinition root level).
    if control_implementations and cd["components"]:
        cd["components"][0]["control-implementations"] = control_implementations

    # Add FedRAMP 20x core_mappings as a capability
    if core_mappings:
        cap_reqs = []
        for m in core_mappings:
            if not isinstance(m, dict):
                continue
            cap_reqs.append({
                "concept": m.get("concept", ""),
                "nist-control": m.get("nist_rev5_control", ""),
                "ksi-category": m.get("ksi_category", ""),
                "evidence-source": m.get("evidence_source", "")
            })
        cd["capabilities"].append({
            "uuid": str(uuid.uuid4()),
            "name": "FedRAMP 20x KSI Alignment",
            "description": "Key Security Indicator mappings from UIAO canon",
            "props": [{"name": "ksi-count", "value": str(len(core_mappings))}],
            "remarks": json.dumps(cap_reqs)
        })

    return cd


def validate_inventory_component_refs(context, cd):
    """Warn if any inventory item references a component-id not present in the Component Definition."""
    inventory_items = context.get("inventory_items", [])
    if not isinstance(inventory_items, list) or not inventory_items:
        return

    known_ids = set()
    for comp in cd.get("components", []):
        for prop in comp.get("props", []):
            if isinstance(prop, dict) and prop.get("name") == "component-id":
                known_ids.add(prop.get("value", ""))

    for item in inventory_items:
        if not isinstance(item, dict):
            continue
        for comp_ref in item.get("implemented_components", []):
            if comp_ref not in known_ids:
                print(
                    f"  [WARN] Inventory item '{item.get('id', '?')}' references "
                    f"unknown component '{comp_ref}' (not found in Component Definition)"
                )


def main():
    print("Loading UIAO context...")
    context = load_context()
    print(f"  control_planes entries : {len(context.get('control_planes', []))}")
    print(f"  compliance_matrix rows : {len(context.get('unified_compliance_matrix', []))}")
    print("Building OSCAL Component Definition...")
    cd = build_component_definition(context)
    print("Validating inventory cross-references...")
    validate_inventory_component_refs(context, cd)
    OSCAL_OUT.mkdir(parents=True, exist_ok=True)
    json_path = OSCAL_OUT / "uiao-component-definition.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"component-definition": cd}, f, indent=2)
    ctrl_impl_count = (
        len(cd["components"][0].get("control-implementations", []))
        if cd["components"] else 0
    )
    print(f"OSCAL Component Definition exported -> {json_path}")
    print(f"  Components             : {len(cd['components'])}")
    print(f"  Control Implementations: {ctrl_impl_count}")
    print(f"  Capabilities           : {len(cd['capabilities'])}")
    print("  Ready for FedRAMP 20x Moderate import")


if __name__ == "__main__":
    main()
