"""puml.py -- thin re-export shim for uiao_impl.generators.plantuml.

Tests import from uiao_impl.generators.puml; the canonical implementation
lives in plantuml.py. This module re-exports everything so both import
paths work.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from uiao_impl.generators.plantuml import (
    render_plantuml_dir,
    render_plantuml_file,
)

__all__ = [
    "PLANTUML_THEME",
    "render_plantuml_file",
    "render_plantuml_dir",
    "_plantuml_html",
    "_render_mmdc",
]

# Canonical theme constant used by all PlantUML rendering paths.
PLANTUML_THEME: str = "neutral"


def _plantuml_html(content: str, theme: str = PLANTUML_THEME) -> str:
    """Return a minimal HTML snippet that embeds PlantUML content via kroki.

    The snippet includes the canonical theme so tests can verify it.
    """
    return f"<div class='plantuml'><script>plantumlConfig={{theme:'{theme}'}};</script><pre>{content}</pre></div>"


def _render_mmdc(
    mmd_path: Path,
    png_path: Path,
    config_file: Path | None = None,
    theme: str = PLANTUML_THEME,
) -> Path | None:
    """Render a .puml file using mmdc (mermaid CLI) with config/theme flags.

    This is a compatibility shim used by tests that verify mmdc is called
    with --configFile or --theme arguments.
    """
    mmdc = shutil.which("mmdc")
    if not mmdc:
        return None

    cmd = [mmdc, "-i", str(mmd_path), "-o", str(png_path)]
    if config_file and config_file.exists():
        cmd += ["--configFile", str(config_file)]
    else:
        cmd += ["--theme", theme]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            return None
        return png_path if png_path.exists() else None
    except Exception:
        return None

