"""PlantUML diagram renderer.

Primary: calls `java -jar plantuml.jar` locally (no network, fully offline).
Fallback: if no JAR is found, falls back to plantweb (public plantuml.com server).

Configure the JAR path via the `UIAO_PLANTUML_JAR` environment variable or
by placing `plantuml.jar` in the repo root or `tools/` directory.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Candidate locations to search for plantuml.jar (in priority order)
_JAR_CANDIDATES = [
    Path("plantuml.jar"),
    Path("tools/plantuml.jar"),
    Path("tools/plantuml/plantuml.jar"),
]


def _find_jar() -> "Path | None":
    """Return the path to plantuml.jar if it exists, else None."""
    import os
    env_jar = os.environ.get("UIAO_PLANTUML_JAR")
    if env_jar:
        p = Path(env_jar)
        if p.exists():
            return p
        logger.warning("UIAO_PLANTUML_JAR set to %s but file not found", env_jar)

    for candidate in _JAR_CANDIDATES:
        if candidate.exists():
            return candidate

    return None


def _java_available() -> bool:
    """Return True if java is on PATH."""
    return shutil.which("java") is not None


def render_plantuml_file(
    puml_path: Path,
    output_dir: Path,
    force: bool = False,
    fmt: str = "png",
) -> "Path | None":
    """Render a single .puml file to PNG (or other format).

    Uses local plantuml.jar via Java subprocess when available.
    Falls back to plantweb (public plantuml.com) if no JAR is found.
    """
    png_path = output_dir / (puml_path.stem + f".{fmt}")
    output_dir.mkdir(parents=True, exist_ok=True)

    if png_path.exists() and not force:
        logger.debug("Cached PNG found, skipping: %s", png_path)
        return png_path

    jar = _find_jar()

    if jar and _java_available():
        return _render_with_jar(puml_path, output_dir, jar, fmt)
    else:
        if jar and not _java_available():
            logger.warning("plantuml.jar found at %s but java is not on PATH — falling back to plantweb", jar)
        else:
            logger.debug("plantuml.jar not found — falling back to plantweb (public server)")
        return _render_with_plantweb(puml_path, output_dir, fmt)


def _render_with_jar(
    puml_path: Path,
    output_dir: Path,
    jar: Path,
    fmt: str = "png",
) -> "Path | None":
    """Render using local plantuml.jar via java subprocess."""
    png_path = output_dir / (puml_path.stem + f".{fmt}")
    cmd = [
        "java", "-jar", str(jar),
        f"-t{fmt}",
        "-o", str(output_dir.resolve()),
        str(puml_path.resolve()),
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.warning(
                "plantuml.jar exited %d for %s: %s",
                result.returncode, puml_path.name, result.stderr.strip()
            )
            return None
        logger.info("Rendered (JAR): %s -> %s", puml_path.name, png_path)
        return png_path if png_path.exists() else None
    except subprocess.TimeoutExpired:
        logger.warning("plantuml.jar timed out rendering %s", puml_path.name)
        return None
    except Exception as exc:
        logger.warning("plantuml.jar failed for %s: %s", puml_path.name, exc)
        return None


def _render_with_plantweb(
    puml_path: Path,
    output_dir: Path,
    fmt: str = "png",
) -> "Path | None":
    """Render using plantweb (calls public plantuml.com server)."""
    png_path = output_dir / (puml_path.stem + f".{fmt}")
    try:
        from plantweb.render import render
    except ImportError:
        logger.error("plantweb not installed and plantuml.jar not found.")
        logger.error("Install plantweb:  pip install plantweb")
        logger.error("Or download JAR:   https://plantuml.com/download")
        logger.error("Then set:          UIAO_PLANTUML_JAR=/path/to/plantuml.jar")
        return None

    content = puml_path.read_text(encoding="utf-8")
    try:
        result = render(content, engine="plantuml", format=fmt)
        image_bytes = result[0] if isinstance(result, (tuple, list)) else result
        png_path.write_bytes(image_bytes)
        logger.info("Rendered (plantweb): %s -> %s", puml_path.name, png_path)
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
