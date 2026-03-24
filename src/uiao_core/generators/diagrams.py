"""Diagram generator from canon YAML.

Loads diagram definitions from ``canon/diagrams.yaml``, writes each diagram's
Mermaid source to ``visuals/<key>.mermaid``, and renders each to PNG in
``assets/images/mermaid/`` via the existing :func:`render_mermaid_file` helper.

ADR-0005: Provides server-side PNG rendering for DOCX/PPTX/PDF exports where
live JavaScript rendering is unavailable.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from uiao_core.generators.mermaid import render_mermaid_file
from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

_DIAGRAMS_CANON = Path("canon/diagrams.yaml")
_DEFAULT_VISUALS_DIR = Path("visuals")
_DEFAULT_OUTPUT_DIR = Path("assets/images/mermaid")


# ---------------------------------------------------------------------------
# Canon loading
# ---------------------------------------------------------------------------
def load_diagrams_canon(
    canon_path: str | Path | None = None,
) -> dict[str, Any]:
    """Load and return the ``diagrams`` section from the canon YAML.

    Args:
        canon_path: Path to ``diagrams.yaml``. Defaults to
            ``<project_root>/canon/diagrams.yaml``.

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
# Mermaid file writing
# ---------------------------------------------------------------------------
def write_mermaid_file(
    key: str,
    content: str,
    visuals_dir: Path,
) -> Path:
    """Write Mermaid source to ``visuals/<key>.mermaid``.

    Args:
        key: Diagram identifier (used as the filename stem).
        content: Mermaid diagram source text.
        visuals_dir: Directory to write the ``.mermaid`` file into.

    Returns:
        Path to the written ``.mermaid`` file.
    """
    visuals_dir.mkdir(parents=True, exist_ok=True)
    mmd_path = visuals_dir / f"{key}.mermaid"
    mmd_path.write_text(content.rstrip() + "\n", encoding="utf-8")
    logger.debug("Wrote Mermaid source: %s", mmd_path)
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
    """Generate ``.mermaid`` files and render them to PNG from canon YAML.

    For each diagram defined in ``canon/diagrams.yaml``:
    1. Writes the Mermaid source to ``visuals/<key>.mermaid``.
    2. Calls :func:`render_mermaid_file` to produce a PNG in *output_dir*.

    Args:
        canon_path: Path to the diagrams canon YAML. Defaults to
            ``<project_root>/canon/diagrams.yaml``.
        visuals_dir: Directory to write ``.mermaid`` source files.
            Defaults to ``<project_root>/visuals``.
        output_dir: Directory for rendered PNG files.
            Defaults to ``<project_root>/assets/images/mermaid``.
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

        mmd_path = write_mermaid_file(key, content, visuals_dir)

        png_path = render_mermaid_file(mmd_path, output_dir=output_dir, force=force)
        if png_path:
            rendered.append(png_path)
        else:
            logger.warning("Failed to render diagram '%s'.", key)
            failures.append(key)

    logger.info("Rendered %d/%d diagram(s).", len(rendered), len(diagrams))

    if strict and failures:
        raise RuntimeError(
            f"Failed to render {len(failures)} diagram(s): {', '.join(failures)}. "
            "Install mmdc (`npm i -g @mermaid-js/mermaid-cli`) or playwright "
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
