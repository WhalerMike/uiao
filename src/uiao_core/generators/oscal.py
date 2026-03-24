"""OSCAL Component Definition generator.

Migrated from scripts/generate_oscal.py into the uiao_core package.
Builds OSCAL 1.0 Component Definition JSON from UIAO YAML canon data,
aligned with FedRAMP 20x Phase 2 Moderate.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao_core.utils.context import get_settings, load_context


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _as_dict(obj: Any, name_key: str = "name") -> dict[str, Any]:
    """Normalize a component entry that may be a str or dict."""
    if isinstance(obj, dict):
        return obj
    return {name_key: str(obj), "role": "", "capabilities": []}


def _safe_get(obj: Any, key: str, default: str = "") -> str:
    """Get a value from obj whether it is a dict or a plain string."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _unwrap(val: Any, key: str) -> Any:
    """Unwrap a value that might be a dict wrapping a list under its own key."""
    if isinstance(val, dict) and key in val:
        return val[key]
    return val


def _nonempty(val: Any, fallback: str = "N/A") -> str:
    """Ensure a string is non-empty for OSCAL regex compliance."""
    s = str(val).strip()
    return s if s else fallback


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------
def build_component_definition(
    context: dict[str, Any],
) -> dict[str, Any]:
    """Build OSCAL Component Definition from UIAO canon data."""
    cfg = context.get("fedramp_20x_config", {})
    if not isinstance(cfg, dict):
        cfg = {}

    planes = _unwrap(context.get("control_planes", []), "control_planes")
    if not isinstance(planes, list):
        planes = []

    matrix = _unwrap(
        context.get("unified_compliance_matrix", []),
        "unified_compliance_matrix",
    )
    if not isinstance(matrix, list):
        matrix = []

    core_mappings = cfg.get("core_mappings", []) if isinstance(cfg, dict) else []
    if not isinstance(core_mappings, list):
        core_mappings = []

    briefing = context.get("leadership_briefing", {})
    if not isinstance(briefing, dict):
        briefing = {}

    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    cd: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": _safe_get(
                briefing,
                "title",
                "UIAO Unified Identity-Addressing-Overlay Architecture",
            ),
            "version": "1.0",
            "oscal-version": "1.0.4",
            "last-modified": now_iso,
            "published": now_iso,
            "props": [
                {
                    "name": "fedramp-impact",
                    "value": cfg.get("authorization_level", "Moderate"),
                    "ns": "https://fedramp.gov/ns/oscal",
                },
                {
                    "name": "compliance-strategy",
                    "value": cfg.get(
                        "compliance_strategy",
                        "OSCAL-based Telemetry Validation",
                    ),
                    "ns": "https://fedramp.gov/ns/oscal",
                },
                {
                    "name": "ksi-dashboard",
                    "value": cfg.get("ksi_dashboard_status", "Operational"),
                },
                {
                    "name": "framework-version",
                    "value": cfg.get("framework_version", "2026.1"),
                },
                {
                    "name": "markup-type",
                    "value": "json",
                    "ns": "https://fedramp.gov/ns/oscal",
                },
            ],
        },
        "components": [],
        "capabilities": [],
    }

    # Build components from control_planes
    for plane in planes:
        if not isinstance(plane, dict):
            continue
        comp_uuid = str(uuid.uuid4())
        plane_id = plane.get("id", "unknown")

        raw_subs = plane.get("components", [])
        if not isinstance(raw_subs, list):
            raw_subs = []
        sub_components = []
        for raw_sub in raw_subs:
            sub = _as_dict(raw_sub)
            sub_components.append(
                {
                    "name": sub.get("name", ""),
                    "role": sub.get("role", ""),
                    "capabilities": sub.get("capabilities", []),
                }
            )

        props: list[dict[str, str]] = [
            {"name": "uiao-pillar", "value": str(plane_id).upper()},
        ]
        subtitle = str(plane.get("subtitle", "")).strip()
        if subtitle:
            props.append({"name": "subtitle", "value": subtitle})
        props.append({"name": "component-id", "value": f"component-{plane_id}"})

        control_imps: list[dict[str, Any]] = []
        for entry in matrix:
            if not isinstance(entry, dict):
                continue
            imp_reqs: list[dict[str, Any]] = []
            for ctrl_id in entry.get("nist_controls", []):
                ksi_cat = "KSI-UNKNOWN"
                evidence = "N/A"
                for m in core_mappings:
                    if not isinstance(m, dict):
                        continue
                    if ctrl_id in m.get("nist_rev5_control", ""):
                        ksi_cat = m.get("ksi_category", ksi_cat)
                        ev = m.get("evidence_source", "")
                        if ev and str(ev).strip():
                            evidence = str(ev).strip()
                        break
                imp_reqs.append(
                    {
                        "uuid": str(uuid.uuid4()),
                        "control-id": ctrl_id,
                        "description": _nonempty(
                            entry.get("impact_statement", ""),
                            f"Control {ctrl_id} implementation",
                        ),
                        "props": [
                            {"name": "ksi-category", "value": _nonempty(ksi_cat)},
                            {
                                "name": "cisa-maturity",
                                "value": _nonempty(
                                    entry.get("cisa_maturity", "Advanced"),
                                ),
                            },
                            {"name": "evidence-source", "value": _nonempty(evidence)},
                        ],
                        "remarks": f"Implemented by {plane.get('name', plane_id)}",
                    }
                )
            if imp_reqs:
                control_imps.append(
                    {
                        "uuid": str(uuid.uuid4()),
                        "source": (
                            "https://github.com/GSA/fedramp-automation/"
                            "raw/main/dist/content/rev5/baselines/json/"
                            "FedRAMP_rev5_MODERATE-baseline_profile.json"
                        ),
                        "description": (f"Control implementations for {plane.get('name', plane_id)}"),
                        "implemented-requirements": imp_reqs,
                    }
                )

        cd["components"].append(
            {
                "uuid": comp_uuid,
                "type": "service",
                "title": _nonempty(plane.get("name", plane_id)),
                "description": _nonempty(
                    plane.get("description", ""),
                    f"UIAO {plane.get('name', plane_id)} control plane",
                ),
                "props": props,
                "remarks": json.dumps(sub_components),
                "control-implementations": control_imps,
            }
        )

    # Add FedRAMP 20x core_mappings as a capability
    if core_mappings:
        cap_reqs = []
        for m in core_mappings:
            if not isinstance(m, dict):
                continue
            cap_reqs.append(
                {
                    "concept": m.get("concept", ""),
                    "nist-control": m.get("nist_rev5_control", ""),
                    "ksi-category": m.get("ksi_category", ""),
                    "evidence-source": m.get("evidence_source", ""),
                }
            )
        cd["capabilities"].append(
            {
                "uuid": str(uuid.uuid4()),
                "name": "FedRAMP 20x KSI Alignment",
                "description": "Key Security Indicator mappings from UIAO canon",
                "props": [{"name": "ksi-count", "value": str(len(core_mappings))}],
                "remarks": json.dumps(cap_reqs),
            }
        )

    return cd


def validate_inventory_component_refs(
    context: dict[str, Any],
    cd: dict[str, Any],
) -> list[str]:
    """Check inventory items for unknown component refs. Returns warnings."""
    warnings: list[str] = []
    inventory_items = context.get("inventory_items", [])
    if not isinstance(inventory_items, list) or not inventory_items:
        return warnings
    known_ids: set[str] = set()
    for comp in cd.get("components", []):
        for prop in comp.get("props", []):
            if isinstance(prop, dict) and prop.get("name") == "component-id":
                known_ids.add(prop.get("value", ""))
    for item in inventory_items:
        if not isinstance(item, dict):
            continue
        for comp_ref in item.get("implemented_components", []):
            if comp_ref not in known_ids:
                warnings.append(f"Inventory item '{item.get('id', '?')}' references unknown component '{comp_ref}'")
    return warnings


def build_oscal(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    """Build and export OSCAL Component Definition JSON.

    Returns path to the generated JSON file.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / "exports" / "oscal"
    output_dir = Path(output_dir)

    context = load_context(canon_path, data_dir)
    cd = build_component_definition(context)
    validate_inventory_component_refs(context, cd)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "uiao-component-definition.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"component-definition": cd}, f, indent=2)
    return json_path
