"""OSCAL SSP assembly using compliance-trestle models.

Migrated from scripts/assemble_with_trestle.py into the uiao_core package.
Merges SSP skeleton with component-definition data to produce a fully
assembled System Security Plan.

References: ADR-0004
"""
from __future__ import annotations
import json
import logging
from copy import deepcopy
from pathlib import Path

from trestle.oscal.ssp import SystemSecurityPlan
from trestle.oscal.component import ComponentDefinition
from trestle.oscal.poam import PlanOfActionAndMilestones

from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    """Load and return a JSON file as a dict."""
    if not path.exists():
        raise FileNotFoundError(f"Required OSCAL file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_ssp(data: dict) -> bool:
    """Validate the SSP payload against trestle's Pydantic model."""
    try:
        SystemSecurityPlan(**data.get("system-security-plan", data))
        return True
    except Exception as exc:
        logger.warning("SSP validation note: %s", exc)
        return False


def _validate_component_definition(data: dict) -> bool:
    """Validate the component definition against trestle's Pydantic model."""
    try:
        ComponentDefinition(**data.get("component-definition", data))
        return True
    except Exception as exc:
        logger.warning("Component-definition validation note: %s", exc)
        return False


def _assemble(ssp_data: dict, cd_data: dict) -> dict:
    """Merge component-definition data into the SSP skeleton."""
    assembled = deepcopy(ssp_data)
    ssp = assembled.setdefault("system-security-plan", assembled)
    cd = cd_data.get("component-definition", cd_data)

    # Merge components into system-implementation
    sys_impl = ssp.setdefault("system-implementation", {})
    existing_components = sys_impl.setdefault("components", [])
    cd_components = cd.get("components", [])

    for comp in cd_components:
        existing_components.append({
            "uuid": comp.get("uuid", ""),
            "type": comp.get("type", "service"),
            "title": comp.get("title", ""),
            "description": comp.get("description", ""),
            "props": comp.get("props", []),
            "status": {"state": "operational"},
        })
    logger.info("Merged %d components into system-implementation.", len(cd_components))

    # Merge control-implementations
    ctrl_impl = ssp.setdefault("control-implementation", {})
    existing_reqs = ctrl_impl.setdefault("implemented-requirements", [])
    for comp in cd_components:
        for ci in comp.get("control-implementations", []):
            for req in ci.get("implemented-requirements", []):
                existing_reqs.append(req)
    logger.info("Total implemented-requirements after merge: %d", len(existing_reqs))

    return assembled


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def assemble_ssp(
    *,
    ssp_skeleton: Path | None = None,
    component_def: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    """Assemble a complete OSCAL SSP and return the output path.

    All path arguments default to values derived from ``Settings``.
    """
    settings = get_settings()
    oscal_dir = settings.exports_dir / "oscal"

    ssp_skeleton = ssp_skeleton or oscal_dir / "uiao-ssp-skeleton.json"
    component_def = component_def or oscal_dir / "uiao-component-definition.json"
    output_path = output_path or oscal_dir / "uiao-ssp-assembled.json"

    logger.info("Loading SSP skeleton from %s", ssp_skeleton)
    ssp_data = _load_json(ssp_skeleton)

    logger.info("Loading component definition from %s", component_def)
    cd_data = _load_json(component_def)

    logger.info("Validating inputs with compliance-trestle...")
    _validate_ssp(ssp_data)
    _validate_component_definition(cd_data)

    logger.info("Assembling SSP...")
    assembled = _assemble(ssp_data, cd_data)

    oscal_dir.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(assembled, fh, indent=2)
    logger.info("Assembled SSP written to %s", output_path)

    _validate_ssp(assembled)
    logger.info("Done. Ready for FedRAMP 20x import.")
    return output_path



# ---------------------------------------------------------------------------
# Artifact model map
# ---------------------------------------------------------------------------

ARTIFACT_MODELS: dict[str, type] = {
    "component-definition": ComponentDefinition,
    "system-security-plan": SystemSecurityPlan,
    "plan-of-action-and-milestones": PlanOfActionAndMilestones,
}


def validate_oscal_artifacts(
    oscal_dir: Path | None = None,
) -> int:
    """Validate all OSCAL JSON artifacts against trestle Pydantic models.

    Returns the number of failures (0 means all passed).
    """
    if oscal_dir is None:
        oscal_dir = get_settings().exports_dir / "oscal"

    json_files = sorted(oscal_dir.glob("*.json"))
    if not json_files:
        logger.info("No JSON files found in %s – skipping validation.", oscal_dir)
        return 0

    failures = 0
    for json_path in json_files:
        try:
            data = _load_json(json_path)
        except (json.JSONDecodeError, FileNotFoundError) as exc:
            logger.error("FAIL: %s – %s", json_path.name, exc)
            failures += 1
            continue

        if not isinstance(data, dict) or not data:
            logger.error("FAIL: %s – not a JSON object or empty", json_path.name)
            failures += 1
            continue

        root_key = next(iter(data))
        model_class = ARTIFACT_MODELS.get(root_key)

        if model_class is None:
            logger.info("SKIP: %s – unknown OSCAL type '%s'", json_path.name, root_key)
            continue

        try:
            model_class.parse_obj(data[root_key])
            logger.info("PASS: %s", json_path.name)
        except Exception as exc:
            logger.error("FAIL: %s", json_path.name)
            logger.error("  %s", exc)
            failures += 1

    total = len(json_files)
    logger.info("Trestle validation complete: %d file(s), %d failure(s)", total, failures)
    return failures
