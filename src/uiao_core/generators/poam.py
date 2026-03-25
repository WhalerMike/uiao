"""OSCAL POA&M (Plan of Action & Milestones) generator.

Migrated from scripts/generate_poam.py into the uiao_core package.
Auto-detects gaps from unified_compliance_matrix and fedramp-20x
mandatory requirements, then exports OSCAL 1.0 POA&M JSON.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao_core.utils.context import get_settings, load_context


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------
def detect_inventory_gaps(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Detect POA&M gaps from core-stack.yml inventory against known control planes.

    Returns a gap entry for every core-stack component whose ``pillar`` field
    does not match any known control-plane ``id``.  These gaps indicate that a
    concrete system component has no associated OSCAL SSP component and cannot
    be linked in the system inventory.

    Args:
        context: Merged UIAO context dict (from :func:`load_context`).

    Returns:
        List of gap dicts compatible with :func:`detect_gaps`.
    """
    gaps: list[dict[str, Any]] = []

    core_stack = context.get("core_stack", [])
    if isinstance(core_stack, dict):
        core_stack = core_stack.get("core_stack", [])
    if not isinstance(core_stack, list):
        return gaps

    planes = context.get("control_planes", [])
    if isinstance(planes, dict):
        planes = planes.get("control_planes", [])
    if not isinstance(planes, list):
        planes = []
    known_plane_ids: set[str] = {p.get("id", "") for p in planes if isinstance(p, dict)}

    for comp in core_stack:
        if not isinstance(comp, dict):
            continue
        pillar = str(comp.get("pillar", "")).strip()
        comp_id = str(comp.get("id", "?"))
        name = str(comp.get("name", comp_id))
        if pillar and pillar not in known_plane_ids:
            gaps.append(
                {
                    "title": f"Inventory component links to unknown plane: {comp_id}",
                    "description": (
                        f"Core-stack component '{name}' (id: {comp_id}) references pillar '{pillar}' "
                        f"which does not match any known control-plane id. "
                        f"Known planes: {sorted(known_plane_ids)}"
                    ),
                    "risk_level": "moderate",
                    "related_controls": ["CM-8"],
                    "source": "inventory",
                }
            )

    return gaps


def detect_gaps(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Auto-detect gaps from canon data."""
    gaps: list[dict[str, Any]] = []

    matrix = context.get("unified_compliance_matrix", [])
    if not isinstance(matrix, list):
        matrix = []

    fedramp = context.get("fedramp_20x_config", {})
    if not isinstance(fedramp, dict):
        fedramp = {}
    core_mappings = fedramp.get("core_mappings", [])
    if not isinstance(core_mappings, list):
        core_mappings = []

    # Detect incomplete maturity levels
    for entry in matrix:
        if not isinstance(entry, dict):
            continue
        maturity = entry.get("cisa_maturity", "")
        if maturity in ("Initial", "Developing", ""):
            gaps.append(
                {
                    "title": f"Low maturity: {entry.get('category', 'Unknown')}",
                    "description": (
                        f"CISA maturity is '{maturity}' for category "
                        f"'{entry.get('category', 'N/A')}'. "
                        f"Controls: {entry.get('nist_controls', [])}"
                    ),
                    "risk_level": "moderate" if maturity == "Developing" else "high",
                    "related_controls": entry.get("nist_controls", []),
                }
            )

    # Detect missing KSI evidence
    for m in core_mappings:
        if not isinstance(m, dict):
            continue
        evidence = m.get("evidence_source", "")
        if not evidence or str(evidence).strip() == "":
            gaps.append(
                {
                    "title": f"Missing evidence: {m.get('concept', 'Unknown')}",
                    "description": (
                        f"No evidence source defined for KSI concept "
                        f"'{m.get('concept', 'N/A')}' "
                        f"(control: {m.get('nist_rev5_control', 'N/A')})"
                    ),
                    "risk_level": "moderate",
                    "related_controls": [m.get("nist_rev5_control", "")],
                }
            )

    # Detect inventory gaps from core-stack.yml vs control planes
    gaps.extend(detect_inventory_gaps(context))

    return gaps


# ---------------------------------------------------------------------------
# POA&M builder
# ---------------------------------------------------------------------------
def build_poam(
    context: dict[str, Any],
    manual_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build OSCAL POA&M from detected gaps and optional manual findings."""
    now_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    gaps = detect_gaps(context)
    if manual_findings:
        gaps.extend(manual_findings)

    poam_items: list[dict[str, Any]] = []
    for i, gap in enumerate(gaps, start=1):
        related = gap.get("related_controls", [])
        poam_items.append(
            {
                "uuid": str(uuid.uuid4()),
                "title": gap.get("title", f"Finding {i}"),
                "description": gap.get("description", "No description"),
                "props": [
                    {"name": "risk-level", "value": gap.get("risk_level", "moderate")},
                    {"name": "finding-id", "value": f"POAM-{i:04d}"},
                ],
                "related-observations": [{"description": f"Related NIST controls: {', '.join(related)}"}]
                if related
                else [],
            }
        )

    poam: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "metadata": {
            "title": "UIAO Plan of Action & Milestones",
            "version": "1.0",
            "oscal-version": "1.0.4",
            "last-modified": now_iso,
            "published": now_iso,
        },
        "poam-items": poam_items,
    }
    return poam


def build_poam_export(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    manual_findings: list[dict[str, Any]] | None = None,
) -> Path:
    """Build and export POA&M JSON. Returns path to generated file."""
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / "exports" / "oscal"
    output_dir = Path(output_dir)

    context = load_context(canon_path, data_dir)
    poam = build_poam(context, manual_findings)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "uiao-poam.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"plan-of-action-and-milestones": poam}, f, indent=2)
    return json_path
