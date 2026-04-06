"""PlantUML diagram renderer — replaces the former Mermaid renderer.

Mermaid has been removed from this project. All diagram source files are now
PlantUML (.puml). This module re-exports the PlantUML rendering API under the
old names so any remaining callers continue to work during the transition, and
to provide a clear deprecation boundary.

Replaced: ADR-0005 (Mermaid-to-PNG). New canonical renderer: plantuml.py.
"""

from __future__ import annotations

import logging
from pathlib import Path

from uiao_core.generators.plantuml import (
    render_plantuml_dir as _render_plantuml_dir,
)
from uiao_core.generators.plantuml import (
    render_plantuml_file as _render_plantuml_file,
)
from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults (kept for backward compatibility; now point at plantuml paths)
# ---------------------------------------------------------------------------
_DEFAULT_VISUALS_DIR = Path("visuals")
_DEFAULT_OUTPUT_DIR = Path("assets/images/plantuml")

# ---------------------------------------------------------------------------
# Public API — thin wrappers delegating to plantuml.py
# ---------------------------------------------------------------------------


def render_plantuml_file(
    puml_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
) -> Path | None:
    """Render a single .puml file to PNG via PlantUML."""
    if output_dir is None:
        settings = get_settings()
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    return _render_plantuml_file(puml_path, output_dir, force=force)


def render_all_plantuml(
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Render all .puml files in visuals_dir to PNG."""
    settings = get_settings()
    if visuals_dir is None:
        visuals_dir = settings.project_root / _DEFAULT_VISUALS_DIR
    visuals_dir = Path(visuals_dir)
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)
    return _render_plantuml_dir(visuals_dir, output_dir, force=force)


def build_plantuml_visuals(
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Entry point matching other generators' build_* pattern. Returns the output directory."""
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)
    render_all_plantuml(visuals_dir, output_dir, force=force)
    return output_dir


# ---------------------------------------------------------------------------
# Deprecated aliases (removed Mermaid names — raise at call-time)
# ---------------------------------------------------------------------------


def build_mermaid_visuals(*args: object, **kwargs: object) -> Path:
    """Removed. Use build_plantuml_visuals() instead."""
    raise RuntimeError(
        "build_mermaid_visuals() has been removed. Use build_plantuml_visuals() from uiao_core.generators.plantuml."
    )


def render_mermaid_file(*args: object, **kwargs: object) -> Path | None:
    """Removed. Use render_plantuml_file() instead."""
    raise RuntimeError(
        "render_mermaid_file() has been removed. Use render_plantuml_file() from uiao_core.generators.plantuml."
    )


def render_all_mermaid(*args: object, **kwargs: object) -> list[Path]:
    """Removed. Use render_all_plantuml() instead."""
    raise RuntimeError(
        "render_all_mermaid() has been removed. Use render_all_plantuml() from uiao_core.generators.plantuml."
    )
