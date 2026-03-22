"""OSCAL Component Definition Export for UIAO Canon.

Generates a machine-readable OSCAL 1.0 Component Definition JSON
from the UIAO YAML canon (control-planes, unified_compliance_matrix,
fedramp-20x config). Aligns with FedRAMP 20x Phase 2 Moderate.
"""
import yaml
import json
import uuid
from datetime import datetime
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


def build_component_definition(context):
    """Build OSCAL Component Definition from UIAO canon data."""
    cfg = context.get("fedramp_20x_config", {})
    planes = context.get("control_planes", [])
    matrix = context.get("unified_compliance_matrix", [])
    core_mappings = cfg.get("core_mappings", [])
    briefing = context.get("leadership_briefing", {})

    cd = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": briefing.get("title",
                "UIAO Unified Identity-Addressing-Overlay Architecture"),
            "version": "1.0",
            "oscal-version": "1.0.0",
            "last-modified": datetime.utcnow().isoformat() + "Z",
            "props": [
                {"name": "fedramp-impact", "value":
                    cfg.get("authorization_level", "Moderate"),
                    "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "compliance-strategy", "value":
                    cfg.get("compliance_strategy",
                        "OSCAL-based Telemetry Validation")},
                {"name": "ksi-dashboard", "value":
                    cfg.get("ksi_dashboard_status", "Operational")},
                {"name": "framework-version", "value":
                    cfg.get("framework_version", "2026.1")}
            ]
        },
        "components": [],
        "capabilities": []
    }

    # Build components from control_planes
    comp_uuids = {}
    for plane in planes:
        comp_uuid = str(uuid.uuid4())
        plane_id = plane.get("id", "unknown")
        comp_uuids[plane_id] = comp_uuid

        # Build sub-component list from plane components
        sub_components = []
        for sub in plane.get("components", []):
            sub_components.append({
                "name": sub.get("name", ""),
                "role": sub.get("role", ""),
                "capabilities": sub.get("capabilities", [])
            })

        cd["components"].append({
            "uuid": comp_uuid,
            "type": "service",
            "title": plane.get("name", plane_id),
            "description": plane.get("description", ""),
            "props": [
                {"name": "uiao-pillar", "value": plane_id.upper()},
                {"name": "subtitle", "value":
                    plane.get("subtitle", "")}
            ],
            "remarks": json.dumps(sub_components)
        })

    # Build control-implementations from unified_compliance_matrix
    control_implementations = []
    for entry in matrix:
        imp_reqs = []
        for ctrl_id in entry.get("nist_controls", []):
            # Find matching KSI from core_mappings
            ksi_cat = "KSI-UNKNOWN"
            evidence = ""
            for m in core_mappings:
                if ctrl_id in m.get("nist_rev5_control", ""):
                    ksi_cat = m.get("ksi_category", ksi_cat)
                    evidence = m.get("evidence_source", evidence)
                    break

            imp_reqs.append({
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_id,
                "description":
                    entry.get("impact_statement", ""),
                "props": [
                    {"name": "ksi-category", "value": ksi_cat},
                    {"name": "cisa-maturity", "value":
                        entry.get("cisa_maturity", "Advanced")},
                    {"name": "evidence-source", "value": evidence}
                ]
            })

        if imp_reqs:
            control_implementations.append({
                "uuid": str(uuid.uuid4()),
                "source": "https://github.com/GSA/fedramp-automation/"
                    "raw/main/dist/content/rev5/baselines/json/"
                    "FedRAMP_rev5_MODERATE-baseline_profile.json",
                "description":
                    f"UIAO {entry.get('pillar', '')} Pillar",
                "implemented-requirements": imp_reqs
            })

    cd["control-implementations"] = control_implementations

    # Add FedRAMP 20x core_mappings as a capability
    if core_mappings:
        cap_reqs = []
        for m in core_mappings:
            cap_reqs.append({
                "concept": m.get("concept", ""),
                "nist-control": m.get("nist_rev5_control", ""),
                "ksi-category": m.get("ksi_category", ""),
                "evidence-source": m.get("evidence_source", "")
            })
        cd["capabilities"].append({
            "uuid": str(uuid.uuid4()),
            "name": "FedRAMP 20x KSI Alignment",
            "description":
                "Key Security Indicator mappings from UIAO canon",
            "props": [{"name": "ksi-count",
                "value": str(len(core_mappings))}],
            "remarks": json.dumps(cap_reqs)
        })

    return cd


def main():
    context = load_context()
    cd = build_component_definition(context)

    OSCAL_OUT.mkdir(parents=True, exist_ok=True)
    json_path = OSCAL_OUT / "uiao-component-definition.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"component-definition": cd}, f, indent=2)

    print(f"OSCAL Component Definition exported -> {json_path}")
    print(f"  Components: {len(cd['components'])}")
    print(f"  Control Implementations: "
          f"{len(cd['control-implementations'])}")
    print(f"  Capabilities: {len(cd['capabilities'])}")
    print("  Ready for FedRAMP 20x Moderate import")


if __name__ == "__main__":
    main()
