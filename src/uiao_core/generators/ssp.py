"""SSP (System Security Plan) generator.

Migrated from scripts/generate_ssp.py into the uiao_core package.
Builds OSCAL-compliant SSP JSON from canon YAML and data sources.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from uiao_core.utils.context import get_settings, load_context


def build_set_parameters(
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Build OSCAL set-parameters from data/parameters.yml."""
    params_cfg = context.get("parameters", {})
    if not isinstance(params_cfg, dict):
        return [], {}

    set_params: list[dict[str, Any]] = []
    ctrl_to_params: dict[str, list[str]] = {}

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
            sp: dict[str, Any] = {
                "param-id": param_id,
                "values": [item.get("value", "")],
            }
            remarks_parts = []
            for key in ["name", "method", "scope", "retention", "lockout_duration", "evidence_source"]:
                val = item.get(key)
                if val:
                    remarks_parts.append(f"{key}: {val}")
            if remarks_parts:
                sp["remarks"] = " | ".join(remarks_parts)
            set_params.append(sp)
            for c in ctrl.split("/"):
                c = c.strip()
                if c:
                    ctrl_to_params.setdefault(c, []).append(param_id)

    return set_params, ctrl_to_params


def build_ssp_skeleton(context: dict[str, Any]) -> dict[str, Any]:
    """Build the OSCAL SSP skeleton dict from context."""
    briefing = context.get("leadership_briefing", {})
    fedramp_cfg = context.get("fedramp_20x_config", {})
    planes = context.get("control_planes", [])
    matrix = context.get("unified_compliance_matrix", [])
    inventory_items = context.get("inventory_items", [])
    if not isinstance(inventory_items, list):
        inventory_items = []

    set_params, ctrl_to_params = build_set_parameters(context)
    now_iso = datetime.now(timezone.utc).isoformat()
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    ssp: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": f"{briefing.get('title', 'UIAO')} - System Security Plan (FedRAMP Moderate Skeleton)",
            "published": now_iso,
            "last-modified": now_iso,
            "version": "1.0-skeleton",
            "oscal-version": "1.0.4",
            "props": [
                {"name": "impact-level", "value": "moderate", "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "publication-date", "value": now_date, "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "markup-type", "value": "json", "ns": "https://fedramp.gov/ns/oscal"},
                {"name": "compliance-strategy", "value": fedramp_cfg.get("compliance_strategy", "OSCAL-based Telemetry Validation"), "ns": "https://fedramp.gov/ns/oscal"},
            ],
        },
        "import-profile": {
            "href": "https://github.com/GSA/fedramp-automation/raw/fedramp-2.0.0-oscal-1.0.4/dist/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json"
        },
        "system-characteristics": {
            "system-ids": [{"id": "uiao-modernized-cloud"}],
            "system-name": "UIAO-Modernized Cloud Environment",
            "system-name-short": "UIAO",
            "description": briefing.get("overview", "Reference architecture for TIC 3.0 migration."),
            "system-information": {
                "information-types": [{
                    "title": "Operational Information",
                    "description": "General operational data supporting UIAO TIC 3.0 mission.",
                    "confidentiality-impact": {"base": "fips-199-moderate"},
                    "integrity-impact": {"base": "fips-199-moderate"},
                    "availability-impact": {"base": "fips-199-moderate"},
                }],
            },
            "security-impact-level": {
                "security-objective-confidentiality": "moderate",
                "security-objective-integrity": "moderate",
                "security-objective-availability": "moderate",
            },
            "status": {"state": "operational"},
            "authorization-boundary": {
                "description": "Cloud-hosted UIAO architecture boundary spanning identity, addressing, and telemetry planes.",
            },
        },
        "system-implementation": {
            "users": [{"uuid": str(uuid.uuid4()), "title": "System Administrators", "role-ids": ["admin"]}],
            "components": [],
        },
        "control-implementation": {
            "description": "Control implementations from UIAO components and compliance matrix",
            "set-parameters": set_params,
            "implemented-requirements": [],
        },
    }

    # Populate components from control_planes
    component_id_to_uuid: dict[str, str] = {}
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
            "props": props,
        })

    # Populate inventory-items
    if inventory_items:
        oscal_inventory = []
        for item in inventory_items:
            if not isinstance(item, dict):
                continue
            item_props = [{"name": "asset-type", "value": item.get("asset_type", "software")}]
            for prop in item.get("props", []):
                if isinstance(prop, dict):
                    item_props.append({"name": prop.get("name", ""), "value": prop.get("value", "")})
            impl_components = []
            for comp_ref in item.get("implemented_components", []):
                comp_uuid = component_id_to_uuid.get(comp_ref)
                if comp_uuid:
                    impl_components.append({"component-uuid": comp_uuid})
            oscal_item = {
                "uuid": str(uuid.uuid4()),
                "description": item.get("description", ""),
                "props": item_props,
                "responsible-parties": [{"role-id": item.get("responsible_party", "agency-admin")}],
                "implemented-components": impl_components,
            }
            oscal_inventory.append(oscal_item)
        ssp["system-implementation"]["inventory-items"] = oscal_inventory

    # Add roles and parties
    agency_party_uuid = str(uuid.uuid4())
    ssp["metadata"]["roles"] = [
        {"id": "admin", "title": "System Administrator"},
        {"id": "agency-admin", "title": "Agency Administrator"},
    ]
    ssp["metadata"]["parties"] = [
        {"uuid": agency_party_uuid, "type": "organization", "name": "UIAO Program Office"},
    ]
    for inv_item in ssp.get("system-implementation", {}).get("inventory-items", []):
        for rp in inv_item.get("responsible-parties", []):
            rp["party-uuids"] = [agency_party_uuid]

    # KSI mappings
    ksi_mappings = context.get("ksi_mappings", [])
    if not isinstance(ksi_mappings, list):
        ksi_mappings = []
    ksi_by_control: dict[str, Any] = {}
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
            req: dict[str, Any] = {
                "uuid": str(uuid.uuid4()),
                "control-id": ctrl_id,
                "remarks": (f"{base_remarks} | KSI Evidence: {ksi['evidence_source']}" if ksi else base_remarks),
            }
            if ksi:
                req["props"] = [{"name": "ksi-id", "value": ksi["ksi_id"], "ns": "https://fedramp.gov/ns/oscal"}]
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


def build_ssp(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Generate an OSCAL SSP JSON file from canon and data sources."""
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    if data_dir is None:
        data_dir = settings.data_dir
    if output_path is None:
        output_path = settings.exports_dir / "oscal" / "uiao-ssp-skeleton.json"

    context = load_context(canon_path=canon_path, data_dir=data_dir)
    ssp_data = build_ssp_skeleton(context)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"system-security-plan": ssp_data}, f, indent=2)
    return out
