"""Diagram generator from canon YAML.

Loads diagram definitions from ``generation-inputs/diagrams.yaml``, writes each diagram's
PlantUML source to ``visuals/<key>.puml``, and renders each to PNG in
``assets/images/plantuml/`` via the existing :func:`render_plantuml_file` helper.

ADR-0005: Provides server-side PNG rendering for DOCX/PPTX/PDF exports where
live JavaScript rendering is unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from uiao_core.generators.mermaid import render_plantuml_file
from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

_DIAGRAMS_CANON = Path("generation-inputs/diagrams.yaml")
_DEFAULT_VISUALS_DIR = Path("visuals")
_DEFAULT_OUTPUT_DIR = Path("assets/images/plantuml")


# ---------------------------------------------------------------------------
# Canon loading
# ---------------------------------------------------------------------------
def load_diagrams_canon(
    canon_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load and return the ``diagrams`` section from the canon YAML.

    Args:
        canon_path: Path to ``diagrams.yaml``. Defaults to
            ``<project_root>/generation-inputs/diagrams.yaml``.

    Returns:
        Dictionary mapping diagram key -> diagram metadata dict.
        Returns an empty dict if the file does not exist or contains no diagrams.
    """
    settings = get_settings()
    if canon_path is None:
        canon_path = settings.project_root / _DIAGRAMS_CANON
    canon_path = Path(canon_path)

    if not canon_path.exists():
        logger.warning("Diagrams canon not found: %s", canon_path)
        return {}

    with canon_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    diagrams: dict[str, Any] = data.get("diagrams", {})
    if not diagrams:
        logger.warning("No 'diagrams' section found in %s", canon_path)
    return diagrams


# ---------------------------------------------------------------------------
# PlantUML file writing
# ---------------------------------------------------------------------------
def write_plantuml_file(
    key: str,
    content: str,
    visuals_dir: Path,
) -> Path:
    """Write PlantUML source to ``visuals/<key>.puml``.

    Args:
        key: Diagram identifier (used as the filename stem).
        content: PlantUML diagram source text.
        visuals_dir: Directory to write the ``.puml`` file into.

    Returns:
        Path to the written ``.puml`` file.
    """
    visuals_dir.mkdir(parents=True, exist_ok=True)
    mmd_path = visuals_dir / f"{key}.puml"
    mmd_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    logger.debug("Wrote PlantUML source: %s", mmd_path)
    return mmd_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def generate_diagrams_from_canon(
    canon_path: str | Path | None = None,
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
    strict: bool = False,
) -> list[Path]:
    """Generate ``.puml`` files and render them to PNG from canon YAML.

    For each diagram defined in ``generation-inputs/diagrams.yaml``:
    1. Writes the PlantUML source to ``visuals/<key>.puml``.
    2. Calls :func:`render_plantuml_file` to produce a PNG in *output_dir*.

    Args:
        canon_path: Path to the diagrams canon YAML. Defaults to
            ``<project_root>/generation-inputs/diagrams.yaml``.
        visuals_dir: Directory to write ``.puml`` source files.
            Defaults to ``<project_root>/visuals``.
        output_dir: Directory for rendered PNG files.
            Defaults to ``<project_root>/assets/images/plantuml``.
        force: If ``True``, re-render even if a cached PNG exists.
        strict: If ``True``, raise :exc:`RuntimeError` when any diagram
            fails to render (useful for CI pipelines). Defaults to ``False``
            so that missing renderers are treated as non-fatal warnings.

    Returns:
        List of successfully rendered PNG :class:`~pathlib.Path` objects.

    Raises:
        RuntimeError: When *strict* is ``True`` and at least one diagram
            fails to render.
    """
    settings = get_settings()

    if visuals_dir is None:
        visuals_dir = settings.project_root / _DEFAULT_VISUALS_DIR
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR

    visuals_dir = Path(visuals_dir)
    output_dir = Path(output_dir)

    diagrams = load_diagrams_canon(canon_path)
    if not diagrams:
        logger.warning("No diagrams found; skipping generation.")
        return []

    logger.info("Generating %d diagram(s) from canon.", len(diagrams))
    rendered: list[Path] = []
    failures: list[str] = []

    for key, meta in diagrams.items():
        content: str = meta.get("content", "")
        if not content.strip():
            logger.warning("Diagram '%s' has no content — skipping.", key)
            continue

        mmd_path = write_plantuml_file(key, content, visuals_dir)

        png_path = render_plantuml_file(mmd_path, output_dir=output_dir, force=force)
        if png_path:
            rendered.append(png_path)
        else:
            logger.warning("Failed to render diagram '%s'.", key)
            failures.append(key)

    logger.info("Rendered %d/%d diagram(s).", len(rendered), len(diagrams))

    if strict and failures:
        raise RuntimeError(
            f"Failed to render {len(failures)} diagram(s): {', '.join(failures)}. "
            "Install mmdc (`npm i -g plantuml/plantuml`) or playwright "
            "(`pip install playwright && playwright install chromium`)."
        )

    return rendered


# ---------------------------------------------------------------------------
# build_* entry point (follows repo pattern)
# ---------------------------------------------------------------------------
def build_diagrams(
    canon_path: str | Path | None = None,
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Build all diagrams from canon and return the PNG output directory.

    This is the canonical ``build_*`` entry point consumed by
    :func:`uiao_core.generators.docs.build_docs` and the
    ``generate-diagrams`` CLI command.

    Returns:
        The PNG output directory :class:`~pathlib.Path`.
    """
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
