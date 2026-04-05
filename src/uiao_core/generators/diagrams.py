"""Diagram generator — PlantUML edition (replaces Mermaid/mmdc pipeline).

Reads .puml files from visuals/ and renders them to PNG via plantweb.
ADR-0005: Provides server-side PNG rendering for DOCX/PPTX/PDF exports.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from uiao_core.generators.plantuml import render_plantuml_file
from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

_DIAGRAMS_CANON = Path("generation-inputs/diagrams.yaml")
_DEFAULT_VISUALS_DIR = Path("visuals")
_DEFAULT_OUTPUT_DIR = Path("assets/images/mermaid")


def load_diagrams_canon(canon_path=None) -> dict[str, Any]:
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.project_root / _DIAGRAMS_CANON
    canon_path = Path(canon_path)
    if not canon_path.exists():
        logger.warning("Diagrams canon not found: %s", canon_path)
        return {}
    with canon_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    diagrams = data.get("diagrams", {})
    if not diagrams:
        logger.warning("No diagrams section found in %s", canon_path)
    return diagrams


def generate_diagrams_from_canon(
    canon_path=None,
    visuals_dir=None,
    output_dir=None,
    force: bool = False,
    strict: bool = False,
) -> list[Path]:
    """Render all .puml files from visuals/ to PNG in output_dir."""
    settings = get_settings()

    if visuals_dir is None:
        visuals_dir = settings.project_root / _DEFAULT_VISUALS_DIR
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR

    visuals_dir = Path(visuals_dir)
    output_dir = Path(output_dir)

    puml_files = sorted(visuals_dir.glob("*.puml"))
    if not puml_files:
        logger.warning("No .puml files found in %s", visuals_dir)
        return []

    logger.info("Rendering %d PlantUML diagram(s)...", len(puml_files))
    rendered: list[Path] = []
    failures: list[str] = []

    for puml_path in puml_files:
        png = render_plantuml_file(puml_path, output_dir=output_dir, force=force)
        if png:
            rendered.append(png)
            logger.info("  ✅ %s", puml_path.stem)
        else:
            logger.warning("  ❌ Failed: %s", puml_path.stem)
            failures.append(puml_path.stem)

    logger.info("Rendered %d/%d diagram(s).", len(rendered), len(puml_files))

    if strict and failures:
        raise RuntimeError(
            f"Failed to render {len(failures)} diagram(s): {', '.join(failures)}"
        )

    return rendered


def build_diagrams(
    canon_path=None,
    visuals_dir=None,
    output_dir=None,
    force: bool = False,
) -> Path:
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)
    generate_diagrams_from_canon(
        canon_path=canon_path,
        visuals_dir=visuals_dir,
        output_dir=output_dir,
        force=force,
    )
    return output_dir
