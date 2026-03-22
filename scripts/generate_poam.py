"""OSCAL POA&M Template with Intelligent Gap Detection.

Auto-detects gaps from unified_compliance_matrix (cisa_maturity),
fedramp-20x mandatory requirements, and optional manual findings.
Exports OSCAL 1.0 Plan of Action & Milestones JSON.
"""
import yaml
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
OSCAL_OUT = ROOT / "exports" / "oscal"


def load_context():
    """Same loader pattern as generate_oscal.py / generate_docs.py."""
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


def detect_gaps(context):
    """Auto-detect gaps from canon data."""
    gaps = []
    matrix = context.get("unified_compliance_matrix", [])
    if not isinstance(matrix, list):
        matrix = []
    fedramp = context.get("fedramp_20x_config", {})
    if not isinstance(fedramp, dict):
        fedramp = {}
    core_mappings = fedramp.get("core_mappings", [])
    if not isinstance(core_mappings, list):
        core_mappings = []
    mandatory = fedramp.get("mandatory_2026_requirements", [])
    if not isinstance(mandatory, list):
        mandatory = []

    # 1. Matrix gaps: cisa_maturity != Optimal
    for entry in matrix:
        if not isinstance(entry, dict):
            continue
        maturity = entry.get("cisa_maturity", "Advanced")
        statement = entry.get("impact_statement", "")
        pillar = entry.get("pillar", "Unknown")
        if maturity != "Optimal":
            gaps.append({
                "title": f"{pillar} pillar at {maturity} maturity",
                "control-ids": entry.get("nist_controls", []),
                "description": f"Impact: {str(statement)[:150]}",
                "severity": "high" if maturity == "Advanced"
                else "medium",
                "remediation": f"Elevate {pillar} to Optimal "
                "maturity per CISA Zero Trust guidance",
                "source": "unified_compliance_matrix"
            })
        # Weak statement heuristic
        if isinstance(statement, str) and len(statement.split()) < 15:
            gaps.append({
                "title": f"Weak narrative in {pillar}",
                "control-ids": entry.get("nist_controls", []),
                "description": statement,
                "severity": "medium",
                "remediation": "Strengthen impact statement "
                "with specific evidence sources",
                "source": "unified_compliance_matrix"
            })

    # 2. FedRAMP 20x mandatory requirements
    for req in mandatory:
        if not isinstance(req, dict):
            continue
        if req.get("status") == "Required":
            gaps.append({
                "title": f"Mandatory 2026: {req.get('name')}",
                "control-ids": ["CA-7", "CM-2"],
                "description": f"Deadline: {req.get('deadline')}",
                "severity": "high",
                "remediation": f"Implement {req.get('name')} "
                "by deadline",
                "source": "fedramp-20x_config"
            })

    # 3. Core mappings without evidence
    for mapping in core_mappings:
        if not isinstance(mapping, dict):
            continue
        if not mapping.get("evidence_source"):
            gaps.append({
                "title": f"Missing evidence: "
                f"{mapping.get('concept')}",
                "control-ids": [
                    mapping.get("nist_rev5_control", "UNKNOWN")],
                "description": "No telemetry/evidence source",
                "severity": "medium",
                "remediation": "Add telemetry feed",
                "source": "fedramp-20x_config"
            })

    # 4. KSI mappings with status != "Implemented"
    # context[key] = content in the loader overwrites the list set by
    # context.update(content) when the YAML top-level key matches the file
    # stem (e.g. ksi-mappings.yml → key "ksi_mappings"). Unwrap if needed.
    ksi_raw = context.get("ksi_mappings", [])
    ksi_mappings = (
        ksi_raw.get("ksi_mappings", []) if isinstance(ksi_raw, dict)
        else ksi_raw if isinstance(ksi_raw, list) else []
    )
    for ksi in ksi_mappings:
        if not isinstance(ksi, dict):
            continue
        status = ksi.get("status", "Planned")
        if status != "Implemented":
            gaps.append({
                "title": f"KSI Gap: {ksi.get('title', ksi.get('ksi_id'))}",
                "control-ids": ksi.get("control_ids", []),
                "description": ksi.get("description", ""),
                "severity": "high" if status == "Partial" else "medium",
                "remediation": (
                    f"Implement {ksi.get('ksi_id')} to achieve "
                    "FedRAMP 20x KSI compliance"
                ),
                "source": "ksi_mappings",
                "ksi_id": ksi.get("ksi_id"),
                "evidence_source": ksi.get("evidence_source", "")
            })

    # 5. Optional manual findings
    manual_file = DATA_DIR / "poam-findings.yml"
    if manual_file.exists():
        with manual_file.open("r", encoding="utf-8") as f:
            manual = yaml.safe_load(f)
        if manual and isinstance(manual, list):
            gaps.extend(manual)

    return gaps


def build_poam_template(context):
    """Build OSCAL POA&M from detected gaps."""
    gaps = detect_gaps(context)
    briefing = context.get("leadership_briefing", {})
    now = datetime.now(timezone.utc)

    poam = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": "UIAO Modernization POA&M - "
            "Auto-Detected Gaps (FedRAMP Moderate)",
            "last-modified": now.isoformat().replace("+00:00", "Z"),
            "version": "1.0",
            "oscal-version": "1.0.0",
            "props": [
                {"name": "impact-level", "value": "moderate",
                 "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "generated-from",
                 "value": "UIAO Canon Gap Detection"}
            ]
        },
        "import": {
            "href": "../oscal/uiao-component-definition.json"
        },
        "poam-items": []
    }

    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        item = {
            "uuid": str(uuid.uuid4()),
            "title": gap.get("title", "Unknown gap"),
            "description": gap.get("description", ""),
            "related-controls": {
                "control-ids": gap.get("control-ids", [])},
            "risk": {
                "rating": gap.get("severity", "medium"),
                "description": f"Detected via {gap.get('source', 'unknown')}"
            },
            "remediations": [{
                "uuid": str(uuid.uuid4()),
                "description": gap.get("remediation", ""),
                "schedule": {
                    "expected-completion":
                    (now + timedelta(days=90)
                     ).isoformat().replace("+00:00", "Z")
                },
                "status": {"state": "planned"}
            }],
            "remarks": f"Auto-generated from canon on "
            f"{now.date()}"
        }
        if gap.get("ksi_id"):
            item["props"] = [{
                "name": "ksi-id",
                "value": gap["ksi_id"],
                "ns": "https://fedramp.gov/ns/oscal"
            }]
        poam["poam-items"].append(item)

    return poam


def main():
    context = load_context()
    poam_data = build_poam_template(context)

    OSCAL_OUT.mkdir(parents=True, exist_ok=True)
    json_path = OSCAL_OUT / "uiao-poam-template.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"plan-of-action-and-milestones": poam_data},
            f, indent=2)

    count = len(poam_data["poam-items"])
    print(f"OSCAL POA&M exported with {count} "
          f"auto-detected gaps -> {json_path}")
    print("  Ready for FedRAMP 20x Moderate "
          "continuous monitoring")


if __name__ == "__main__":
    main()
