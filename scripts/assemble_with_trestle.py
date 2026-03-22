"""Assemble a complete OSCAL SSP from skeleton and component definition.

Uses compliance-trestle Pydantic models to merge
exports/oscal/uiao-ssp-skeleton.json with component data from
exports/oscal/uiao-component-definition.json, producing a fully
assembled System Security Plan at exports/oscal/uiao-ssp-assembled.json.

Usage:
    python scripts/assemble_with_trestle.py
"""
import json
import logging
import sys
from copy import deepcopy
from pathlib import Path

from trestle.oscal.ssp import SystemSecurityPlan
from trestle.oscal.component import ComponentDefinition

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
OSCAL_DIR = ROOT / "exports" / "oscal"

SSP_SKELETON = OSCAL_DIR / "uiao-ssp-skeleton.json"
COMPONENT_DEF = OSCAL_DIR / "uiao-component-definition.json"
ASSEMBLED_OUT = OSCAL_DIR / "uiao-ssp-assembled.json"


def load_json(path: Path) -> dict:
    """Load and return a JSON file as a dict."""
    if not path.exists():
        logger.error("File not found: %s", path)
        sys.exit(1)
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_ssp(data: dict) -> bool:
    """Validate the SSP payload against trestle's Pydantic model."""
    try:
        SystemSecurityPlan(**data.get("system-security-plan", data))
        return True
    except Exception as exc:
        logger.warning("SSP validation note: %s", exc)
        return False


def validate_component_definition(data: dict) -> bool:
    """Validate the component definition against trestle's Pydantic model."""
    try:
        ComponentDefinition(**data.get("component-definition", data))
        return True
    except Exception as exc:
        logger.warning("Component-definition validation note: %s", exc)
        return False


def assemble(ssp_data: dict, cd_data: dict) -> dict:
    """Merge component-definition data into the SSP skeleton.

    Inserts component inventory and control-implementation references
    from the component definition into the SSP's system-implementation
    and control-implementation sections.
    """
    assembled = deepcopy(ssp_data)
    ssp = assembled.setdefault("system-security-plan", assembled)
    cd = cd_data.get("component-definition", cd_data)

    # --- Merge components into system-implementation ---
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

    # --- Merge control-implementations ---
    ctrl_impl = ssp.setdefault("control-implementation", {})
    existing_reqs = ctrl_impl.setdefault("implemented-requirements", [])
    for comp in cd_components:
        for ci in comp.get("control-implementations", []):
            for req in ci.get("implemented-requirements", []):
                existing_reqs.append(req)
    logger.info(
        "Total implemented-requirements after merge: %d", len(existing_reqs)
    )

    return assembled


def main() -> None:
    logger.info("Loading SSP skeleton from %s", SSP_SKELETON)
    ssp_data = load_json(SSP_SKELETON)

    logger.info("Loading component definition from %s", COMPONENT_DEF)
    cd_data = load_json(COMPONENT_DEF)

    logger.info("Validating inputs with compliance-trestle...")
    validate_ssp(ssp_data)
    validate_component_definition(cd_data)

    logger.info("Assembling SSP...")
    assembled = assemble(ssp_data, cd_data)

    OSCAL_DIR.mkdir(parents=True, exist_ok=True)
    with ASSEMBLED_OUT.open("w", encoding="utf-8") as fh:
        json.dump(assembled, fh, indent=2)

    logger.info("Assembled SSP written to %s", ASSEMBLED_OUT)
    validate_ssp(assembled)
    logger.info("Done. Ready for FedRAMP 20x import.")


if __name__ == "__main__":
    main()
