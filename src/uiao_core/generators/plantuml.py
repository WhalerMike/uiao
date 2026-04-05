"""PlantUML diagram renderer using plantweb (pure-Python, no Java/Node required)."""

from __future__ import annotations
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def render_plantuml_file(
    puml_path: Path,
    output_dir: Path,
    force: bool = False,
    fmt: str = "png",
) -> "Path | None":
    try:
        from plantweb.render import render
    except ImportError:
        logger.error("plantweb not installed. Run: pip install plantweb")
        return None

    png_path = output_dir / (puml_path.stem + f".{fmt}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if png_path.exists() and not force:
        logger.debug("Cached PNG found, skipping: %s", png_path)
        return png_path

    content = puml_path.read_text(encoding="utf-8")
    try:
        result = render(content, engine="plantuml", format=fmt)
        # plantweb returns (bytes, format_string) tuple — unpack it
        image_bytes = result[0] if isinstance(result, (tuple, list)) else result
        png_path.write_bytes(image_bytes)
        logger.info("Rendered: %s -> %s", puml_path.name, png_path)
        return png_path
    except Exception as exc:
        logger.warning("Failed to render %s: %s", puml_path.name, exc)
        return None


def render_plantuml_dir(
    puml_dir: Path,
    output_dir: Path,
    force: bool = False,
) -> list[Path]:
    """Render all .puml files in a directory to PNG."""
    rendered = []
    for puml_path in sorted(puml_dir.glob("*.puml")):
        png = render_plantuml_file(puml_path, output_dir=output_dir, force=force)
        if png:
            rendered.append(png)
    return rendered
