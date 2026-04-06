"""SSP (System Security Plan) generator.

Migrated from scripts/generate_ssp.py into the uiao_core package.
Builds OSCAL-compliant SSP JSON from canon YAML and data sources,
aligned with FedRAMP Rev 5 Sections 1-12 + Appendix A (Moderate).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from uiao_core.utils.context import get_settings, load_context


def _load_ssp_template(data_dir: Path) -> dict[str, Any]:
    """Load the FedRAMP Rev 5 SSP template structure from data directory."""
    template_path = data_dir / "fedramp_ssp_template_structure.yaml"
    if template_path.exists():
        with template_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _unwrap(val: Any, key: str) -> Any:
    """Unwrap a value that might be a dict wrapping a list/dict under its own key.

    When data files are loaded via ``load_context``, the entire YAML file is
    stored under a key derived from the filename.  For files whose top-level
    YAML key matches the filename-derived context key (e.g. ``control-planes.yml``
    → key ``control_planes`` → inner key also ``control_planes``), callers need
    to unwrap one level before iterating.
    """
    if isinstance(val, dict) and key in val:
        return val[key]
    return val


def build_set_parameters(
    context: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Build OSCAL set-parameters from data/parameters.yml."""
    params_cfg = _unwrap(context.get("parameters", {}), "parameters")
    if not isinstance(params_cfg, dict):
        return [], {}

    set_params: list[dict[str, Any]] = []
    ctrl_to_params: dict[str, list[str]] = {}

    for _category, items in params_cfg.items():
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


def _build_roles(template: dict[str, Any]) -> list[dict[str, Any]]:
    """Build FedRAMP Rev 5 required roles from template structure."""
    roles = template.get("required_roles", [])
    if not roles:
        return [
            {"id": "admin", "title": "System Administrator"},
            {"id": "agency-admin", "title": "Agency Administrator"},
        ]
    return [{"id": r["id"], "title": r["title"]} for r in roles if isinstance(r, dict)]


def _build_metadata_props(template: dict[str, Any], now_date: str, fedramp_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """Build FedRAMP Rev 5 required metadata props from template structure."""
    props = []
    for prop in template.get("required_metadata_props", []):
        if not isinstance(prop, dict):
            continue
        value = now_date if prop.get("value") == "PLACEHOLDER_DATE" else prop.get("value", "")
        props.append({"name": prop["name"], "value": value, "ns": prop.get("ns", "https://fedramp.gov/ns/oscal")})
    # Always include compliance-strategy from fedramp config
    props.append(
        {
            "name": "compliance-strategy",
            "value": fedramp_cfg.get("compliance_strategy", "OSCAL-based Telemetry Validation"),
            "ns": "https://fedramp.gov/ns/oscal",
        }
    )
    return props


def _build_system_characteristics_props(template: dict[str, Any]) -> list[dict[str, Any]]:
    """Build FedRAMP Rev 5 required system-characteristics props (cloud model, deployment)."""
    props = []
    for prop in template.get("required_system_props", []):
        if isinstance(prop, dict):
            props.append(
                {
                    "name": prop["name"],
                    "value": prop.get("value", ""),
                    "ns": prop.get("ns", "https://fedramp.gov/ns/oscal"),
                }
            )
    return props


def _build_back_matter(template: dict[str, Any]) -> dict[str, Any]:
    """Build OSCAL back-matter with laws/regulations resources (Section 12)."""
    resources = []
    for law in template.get("laws_and_regulations", []):
        if not isinstance(law, dict):
            continue
        resource: dict[str, Any] = {
            "uuid": str(uuid.uuid4()),
            "title": law.get("title", ""),
            "rlinks": [{"href": law.get("href", "")}],
        }
        if law.get("resource_id"):
            resource["props"] = [{"name": "resource-id", "value": law["resource_id"]}]
        resources.append(resource)
    return {"resources": resources} if resources else {}


def inventory_items_from_core_stack(
    core_stack: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert ``core-stack.yml`` components to inventory-item dicts.

    Each core-stack entry becomes an inventory item that links back to a
    control-plane component via ``implemented_components: [component-{pillar}]``.
    Items generated here are merged into the SSP inventory in
    :func:`build_ssp_skeleton`; manually defined entries in
    ``inventory-items.yml`` take precedence (keyed by ``id``).

    Args:
        core_stack: List of component dicts loaded from ``data/core-stack.yml``.

    Returns:
        List of inventory-item dicts compatible with :func:`build_ssp_skeleton`.
    """
    items: list[dict[str, Any]] = []
    for comp in core_stack:
        if not isinstance(comp, dict):
            continue
        comp_id = str(comp.get("id", "")).strip()
        name = str(comp.get("name", comp_id)).strip()
        pillar = str(comp.get("pillar", "")).strip()
        if not comp_id:
            continue
        item_props: list[dict[str, str]] = []
        if pillar:
            item_props.append({"name": "uiao-pillar", "value": pillar})
        vendor = str(comp.get("vendor", "")).strip()
        if vendor:
            item_props.append({"name": "vendor", "value": vendor})
        item: dict[str, Any] = {
            "id": f"inv-{comp_id.lower()}",
            "asset_type": comp.get("asset_type", "software"),
            "description": name,
            "responsible_party": comp.get("responsible_party", "agency-admin"),
            "implemented_components": [f"component-{pillar}"] if pillar else [],
            "props": item_props,
        }
        items.append(item)
    return items


def build_ssp_skeleton(
    context: dict[str, Any],
    data_dir: Path | None = None,
    enhanced: bool = False,
) -> dict[str, Any]:
    """Build the OSCAL SSP skeleton dict from context, aligned with FedRAMP Rev 5 Sections 1-12.

    Args:
        context: Merged context dict produced by ``load_context()``.
        data_dir: Path to the data directory. Defaults to ``settings.data_dir``.
        enhanced: When *True*, load control-library narratives from
            ``data/control-library/*.yml`` and inject them as OSCAL
            ``statements`` and ``by-components`` entries.  When *False*
            (default) the existing behaviour is preserved.
    """
    if data_dir is None:
        settings = get_settings()
        data_dir = settings.data_dir

    template = _load_ssp_template(Path(data_dir))
    briefing = _unwrap(context.get("leadership_briefing", {}), "leadership_briefing")
    # fedramp_20x_config may be nested under fedramp_20x (file-loaded) or flat (test context)
    fedramp_cfg = (
        context.get("fedramp_20x_config") or _unwrap(context.get("fedramp_20x", {}), "fedramp_20x_config") or {}
    )
    planes = _unwrap(context.get("control_planes", []), "control_planes")
    if not isinstance(planes, list):
        planes = []
    matrix = _unwrap(context.get("unified_compliance_matrix", []), "unified_compliance_matrix")
    if not isinstance(matrix, list):
        matrix = []
    inventory_items = _unwrap(context.get("inventory_items", []), "inventory_items")
    if not isinstance(inventory_items, list):
        inventory_items = []

    # Auto-generate inventory items from core-stack.yml and merge with explicit items.
    # Manually defined entries in inventory-items.yml win (deduplication by id).
    core_stack = _unwrap(context.get("core_stack", []), "core_stack")
    if not isinstance(core_stack, list):
        core_stack = []
    existing_inv_ids = {item.get("id") for item in inventory_items if isinstance(item, dict)}
    for cs_item in inventory_items_from_core_stack(core_stack):
        if cs_item.get("id") not in existing_inv_ids:
            inventory_items = list(inventory_items) + [cs_item]
            existing_inv_ids.add(cs_item["id"])

    set_params, ctrl_to_params = build_set_parameters(context)
    now_iso = datetime.now(timezone.utc).isoformat()
    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    oscal_version = template.get("oscal_version", "1.0.4")
    profile_href = template.get(
        "profile_href",
        "https://raw.githubusercontent.com/GSA/fedramp-automation/refs/heads/develop/src/content/rev5/baselines/json/FedRAMP_rev5_MODERATE-baseline_profile.json",
    )

    # Section 1: System Name and Title
    # Sections 3-6: Roles and Parties
    agency_party_uuid = str(uuid.uuid4())
    roles = _build_roles(template)

    # Section 8: Cloud model props
    sys_char_props = _build_system_characteristics_props(template)

    impact = template.get("impact_level", "moderate").capitalize()
    rev = template.get("fedramp_rev", "5")

    ssp: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        # Sections 3-6: metadata with all required roles and parties
        "metadata": {
            "title": f"{briefing.get('title', 'UIAO')} - System Security Plan (FedRAMP {impact} Rev {rev})",
            "published": now_iso,
            "last-modified": now_iso,
            "version": "1.0",
            "oscal-version": oscal_version,
            "props": _build_metadata_props(template, now_date, fedramp_cfg),
            "roles": roles,
            "parties": [
                {"uuid": agency_party_uuid, "type": "organization", "name": "UIAO Program Office"},
            ],
            # Sections 3-6: responsible-parties linking roles to parties
            "responsible-parties": [
                {"role-id": "system-owner", "party-uuids": [agency_party_uuid]},
                {"role-id": "authorizing-official", "party-uuids": [agency_party_uuid]},
                {"role-id": "prepared-by", "party-uuids": [agency_party_uuid]},
                {"role-id": "prepared-for", "party-uuids": [agency_party_uuid]},
                {"role-id": "information-system-security-officer", "party-uuids": [agency_party_uuid]},
            ],
        },
        # Appendix A: import FedRAMP Moderate Rev 5 baseline profile
        "import-profile": {"href": profile_href},
        # Sections 1, 2, 7, 8, 9, 10: system-characteristics
        "system-characteristics": {
            # Section 1: system identifier and name
            "system-ids": [{"id": "uiao-modernized-cloud"}],
            "system-name": "UIAO-Modernized Cloud Environment",
            "system-name-short": "UIAO",
            # Section 9: general description
            "description": briefing.get("overview", "Reference architecture for TIC 3.0 migration."),
            # Section 2: FIPS 199 information types and security categorization
            "system-information": {
                "information-types": [
                    {
                        "uuid": str(uuid.uuid4()),
                        "title": "Operational Information",
                        "description": "General operational data supporting UIAO TIC 3.0 mission.",
                        "categorizations": [
                            {
                                "system": "https://doi.org/10.6028/NIST.SP.800-60v2r1",
                                "information-type-ids": ["C.3.5.8"],
                            }
                        ],
                        "confidentiality-impact": {"base": "fips-199-moderate"},
                        "integrity-impact": {"base": "fips-199-moderate"},
                        "availability-impact": {"base": "fips-199-moderate"},
                    }
                ],
            },
            # Section 2: overall security impact level
            "security-impact-level": {
                "security-objective-confidentiality": "fips-199-moderate",
                "security-objective-integrity": "fips-199-moderate",
                "security-objective-availability": "fips-199-moderate",
            },
            # Section 7: operational status
            "status": {"state": "operational"},
            # Section 8: cloud model props
            "props": sys_char_props,
            # Section 9: authorization boundary
            "authorization-boundary": {
                "description": (
                    "Cloud-hosted UIAO architecture boundary spanning identity, addressing, and telemetry planes. "
                    "Includes all components operating under the UIAO FedRAMP authorization."
                ),
            },
            # Section 10: network architecture
            "network-architecture": {
                "description": (
                    "The UIAO network architecture implements a Zero Trust model with three primary planes: "
                    "Identity (Microsoft Entra ID / CyberArk), Addressing (Infoblox DDI), and "
                    "Overlay/Telemetry (Cisco SD-WAN / Microsoft Sentinel). "
                    "All inter-plane traffic is protected by mTLS. "
                    "The architecture aligns with CISA TIC 3.0 requirements."
                ),
            },
            # Section 10: data flow
            "data-flow": {
                "description": (
                    "Data flows originate at user endpoints, traverse the UIAO identity plane for "
                    "authentication and authorization, and are routed through the Cisco SD-WAN overlay. "
                    "All network flows are logged and aggregated in Microsoft Sentinel for continuous monitoring. "
                    "No data leaves the government-only community cloud boundary without explicit authorization."
                ),
            },
        },
        # Sections 11: system implementation (users, components, inventory)
        "system-implementation": {
            "users": [
                {"uuid": str(uuid.uuid4()), "title": "System Administrators", "role-ids": ["admin"]},
                {"uuid": str(uuid.uuid4()), "title": "Agency Administrators", "role-ids": ["agency-admin"]},
                {"uuid": str(uuid.uuid4()), "title": "Security Operations Center", "role-ids": ["agency-soc"]},
                {"uuid": str(uuid.uuid4()), "title": "Network Administrators", "role-ids": ["agency-network"]},
            ],
            "components": [],
        },
        # Appendix A: control-implementation
        "control-implementation": {
            "description": "Control implementations from UIAO components and compliance matrix (FedRAMP Moderate Rev 5 baseline)",
            "set-parameters": set_params,
            "implemented-requirements": [],
        },
    }

    # Section 11: Populate components from control_planes
    component_id_to_uuid: dict[str, str] = {}
    for plane in planes:
        comp_uuid = str(uuid.uuid4())
        plane_id = plane.get("id", "")
        component_id = f"component-{plane_id}"
        component_id_to_uuid[component_id] = comp_uuid

        props = [{"name": "pillar", "value": plane_id.upper(), "ns": "https://fedramp.gov/ns/oscal"}]
        subtitle = str(plane.get("subtitle", "")).strip()
        if subtitle:
            props.append({"name": "subtitle", "value": subtitle})
        props.append({"name": "component-id", "value": component_id})

        ssp["system-implementation"]["components"].append(
            {
                "uuid": comp_uuid,
                "type": "service",
                "title": plane.get("name", plane.get("id", "Unnamed Plane")),
                "description": plane.get("description", ""),
                "status": {"state": "operational"},
                "props": props,
            }
        )

    # Section 11: Populate inventory-items
    if inventory_items:
        oscal_inventory = []
        for item in inventory_items:
            if not isinstance(item, dict):
                continue
            item_props: list[dict[str, Any]] = [{"name": "asset-type", "value": item.get("asset_type", "software")}]
            for prop in item.get("props", []):
                if isinstance(prop, dict):
                    item_props.append({"name": prop.get("name", ""), "value": prop.get("value", "")})
            impl_components = []
            for comp_ref in item.get("implemented_components", []):
                comp_uuid = component_id_to_uuid.get(comp_ref)
                if comp_uuid:
                    impl_components.append({"component-uuid": comp_uuid})
            oscal_item: dict[str, Any] = {
                "uuid": str(uuid.uuid4()),
                "description": item.get("description", ""),
                "props": item_props,
                "responsible-parties": [
                    {
                        "role-id": item.get("responsible_party", "agency-admin"),
                        "party-uuids": [agency_party_uuid],
                    }
                ],
                "implemented-components": impl_components,
            }
            oscal_inventory.append(oscal_item)
        ssp["system-implementation"]["inventory-items"] = oscal_inventory

    # Appendix A: KSI mappings index
    ksi_mappings = _unwrap(context.get("ksi_mappings", []), "ksi_mappings")
    if not isinstance(ksi_mappings, list):
        ksi_mappings = []
    ksi_by_control: dict[str, Any] = {}
    for ksi in ksi_mappings:
        for ctrl in ksi.get("control_ids", []):
            if ctrl not in ksi_by_control:
                ksi_by_control[ctrl] = ksi

    # Appendix A: Build implemented-requirements for all matrix entries
    seen_control_ids: set[str] = set()
    for entry in matrix:
        ctrl_ids = entry.get("nist_controls", [])
        for ctrl_id in ctrl_ids:
            if ctrl_id in seen_control_ids:
                continue
            seen_control_ids.add(ctrl_id)
            base_remarks = f"Pillar: {entry.get('pillar', 'N/A')}"
            impact = entry.get("impact_statement", "")
            if impact:
                base_remarks = f"{base_remarks} | {impact}"
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

    # Enhanced mode: inject control-library narratives.
    if enhanced:
        from uiao_core.generators.narrative_loader import load_control_library

        narratives = load_control_library(data_dir=data_dir, context=context)

        # Index existing implemented-requirements by control-id for fast lookup.
        req_by_ctrl: dict[str, dict[str, Any]] = {}
        for req in ssp["control-implementation"]["implemented-requirements"]:
            req_by_ctrl[req["control-id"]] = req

        for ctrl_id, nar in narratives.items():
            rendered = nar.get("narrative", "")
            status = nar.get("status", "implemented")
            impl_by = nar.get("implemented_by", [])

            # Build OSCAL statements list.
            stmt_uuid = str(uuid.uuid4())
            statement: dict[str, Any] = {
                "statement-id": f"{ctrl_id}_smt",
                "uuid": stmt_uuid,
                "description": rendered,
            }

            # Build by-components entries.
            by_components: list[dict[str, Any]] = []
            for impl_item in impl_by:
                comp_name = impl_item.get("type", "")
                # Try to resolve to a component UUID via the existing mapping.
                # Components are registered as "component-{plane_id.lower()}".
                comp_key = f"component-{comp_name.lower()}"
                comp_uuid_val = component_id_to_uuid.get(comp_key)
                if comp_uuid_val:
                    bc: dict[str, Any] = {
                        "component-uuid": comp_uuid_val,
                        "uuid": str(uuid.uuid4()),
                        "description": impl_item.get("description", ""),
                    }
                    by_components.append(bc)

            if by_components:
                statement["by-components"] = by_components

            # Implementation-status prop.
            status_prop = {
                "name": "implementation-status",
                "value": status,
                "ns": "https://fedramp.gov/ns/oscal",
            }

            if ctrl_id in req_by_ctrl:
                # Enrich the existing requirement.
                existing_req = req_by_ctrl[ctrl_id]
                existing_req.setdefault("statements", [])
                if not existing_req["statements"]:
                    existing_req["statements"].append(statement)
                existing_req.setdefault("props", [])
                # Avoid duplicate implementation-status props.
                if not any(p.get("name") == "implementation-status" for p in existing_req["props"]):
                    existing_req["props"].append(status_prop)
            else:
                # Append a new implemented-requirement for controls only in
                # the control-library (not in the compliance matrix).
                new_req: dict[str, Any] = {
                    "uuid": str(uuid.uuid4()),
                    "control-id": ctrl_id,
                    "remarks": f"Narrative sourced from control-library/{ctrl_id}.yml",
                    "props": [status_prop],
                    "statements": [statement],
                }
                ssp["control-implementation"]["implemented-requirements"].append(new_req)

    # Section 12: back-matter with laws and regulations
    back_matter = _build_back_matter(template)
    if back_matter:
        ssp["back-matter"] = back_matter

    return ssp


def build_ssp(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output: str | Path | None = None,
    output_path: str | Path | None = None,
    enhanced: bool = False,
) -> Path:
    """Generate an OSCAL SSP JSON file from canon and data sources.

    Args:
        canon_path: Path to the canon YAML file.
        data_dir: Path to the data directory containing .yml files.
        output: Destination path for the generated SSP JSON. Takes
            precedence over ``output_path`` when both are provided.
        output_path: Deprecated alias for ``output``. Use ``output``
            instead.
        enhanced: When *True*, inject control-library narratives into the
            ``implemented-requirements`` entries.

    Returns:
        Path to the generated SSP JSON file.
    """
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    if data_dir is None:
        data_dir = settings.data_dir
    # ``output`` takes precedence; ``output_path`` kept for backwards compat
    resolved_output = output if output is not None else output_path
    if resolved_output is None:
        resolved_output = settings.exports_dir / "oscal" / "uiao-ssp-skeleton.json"

    context = load_context(canon_path=canon_path, data_dir=data_dir)
    ssp_data = build_ssp_skeleton(context, data_dir=Path(data_dir), enhanced=enhanced)

    out = Path(resolved_output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"system-security-plan": ssp_data}, f, indent=2)
    return out
