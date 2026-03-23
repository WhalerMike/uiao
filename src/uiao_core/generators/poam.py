"""OSCAL POA&M (Plan of Action & Milestones) generator.

Migrated from scripts/generate_poam.py into the uiao_core package.
Auto-detects gaps from unified_compliance_matrix and fedramp-20x
mandatory requirements, then exports OSCAL 1.0 POA&M JSON.
"""
from __future__ import annotations

import json
import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uiao_core.config import Settings


def _get_settings() -> Settings:
    """Get or create Settings instance."""
    try:
        return Settings()
    except Exception:
        return Settings(_env_file=None)


# ---------------------------------------------------------------------------
# Data loading (same pattern as oscal.py)
# ---------------------------------------------------------------------------

def load_context(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Load data/*.yml files and canon YAML into merged context."""
    settings = _get_settings()
    if canon_path is None:
        canon_path = settings.canon_dir / "uiao_leadership_briefing_v1.0.yaml"
    if data_dir is None:
        data_dir = settings.data_dir
    canon_path = Path(canon_path)
    data_dir = Path(data_dir)

    context: dict[str, Any] = {}
    if data_dir.exists():
        for yml_file in sorted(data_dir.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            if content and isinstance(content, dict):
                context.update(content)
                context[key] = content
    if canon_path.exists():
        with canon_path.open("r", encoding="utf-8") as f:
            canon = yaml.safe_load(f)
        if canon:
            context.update(canon)
    return context


# ---------------------------------------------------------------------------
# Gap detection
# ---------------------------------------------------------------------------

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
            gaps.append({
                "title": f"Low maturity: {entry.get('category', 'Unknown')}",
                "description": (
                    f"CISA maturity is '{maturity}' for category "
                    f"'{entry.get('category', 'N/A')}'. "
                    f"Controls: {entry.get('nist_controls', [])}"
                ),
                "risk_level": "moderate" if maturity == "Developing" else "high",
                "related_controls": entry.get("nist_controls", []),
            })

    # Detect missing KSI evidence
    for m in core_mappings:
        if not isinstance(m, dict):
            continue
        evidence = m.get("evidence_source", "")
        if not evidence or str(evidence).strip() == "":
            gaps.append({
                "title": f"Missing evidence: {m.get('concept', 'Unknown')}",
                "description": (
                    f"No evidence source defined for KSI concept "
                    f"'{m.get('concept', 'N/A')}' "
                    f"(control: {m.get('nist_rev5_control', 'N/A')})"
                ),
                "risk_level": "moderate",
                "related_controls": [m.get("nist_rev5_control", "")],
            })

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
        poam_items.append({
            "uuid": str(uuid.uuid4()),
            "title": gap.get("title", f"Finding {i}"),
            "description": gap.get("description", "No description"),
            "props": [
                {"name": "risk-level", "value": gap.get("risk_level", "moderate")},
                {"name": "finding-id", "value": f"POAM-{i:04d}"},
            ],
            "related-observations": [
                {"description": f"Related NIST controls: {', '.join(related)}"}
            ] if related else [],
        })

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
    settings = _get_settings()
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
