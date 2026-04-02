"""Mermaid-to-PNG server-side renderer.

ADR-0005: Provides static PNG rendering of Mermaid diagrams for embedding
in DOCX/PPTX artifacts where live JS rendering is unavailable.

Strategy:
  1. Primary: Use ``mmdc`` (Mermaid CLI via Node/npx) for headless rendering.
  2. Fallback: Use Playwright to render Mermaid in a headless browser.
  3. Cache: PNGs are cached in ``assets/images/mermaid/`` and only regenerated
     when the source ``.mermaid`` file changes or ``--force-visuals`` is set.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_VISUALS_DIR = Path("visuals")
_DEFAULT_OUTPUT_DIR = Path("assets/images/mermaid")
_HASH_FILE = ".mermaid_hashes.json"
_MERMAID_CONFIG = Path("data/mermaid-config.json")

# Canonical Mermaid theme used across all rendering backends.
# Must match the ``mermaid.theme`` value in ``_quarto.yml`` and the theme
# field in ``data/mermaid-config.json``.
MERMAID_THEME = "neutral"


# ---------------------------------------------------------------------------
# Hash-based cache
# ---------------------------------------------------------------------------
def _file_hash(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_hash_cache(output_dir: Path) -> dict[str, str]:
    """Load previously recorded hashes."""
    import json

    cache_path = output_dir / _HASH_FILE
    if cache_path.exists():
        return dict(json.loads(cache_path.read_text(encoding="utf-8")))
    return {}


def _save_hash_cache(output_dir: Path, cache: dict[str, str]) -> None:
    """Persist hash cache to disk."""
    import json

    cache_path = output_dir / _HASH_FILE
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Rendering backends
# ---------------------------------------------------------------------------
def _resolve_mermaid_config(config_file: Path | None) -> Path | None:
    """Return the resolved path to a Mermaid config file, or None if not found.

    When *config_file* is ``None`` the function tries the canonical path
    ``data/mermaid-config.json`` relative to the project root; if that file
    also does not exist it returns ``None`` and the caller falls back to the
    ``--theme`` flag.  When an explicit *config_file* is supplied and the file
    does not exist a warning is logged and ``None`` is returned.
    """
    if config_file is not None:
        if config_file.exists():
            return config_file
        logger.warning(
            "Mermaid config file not found at %s; falling back to --theme %s.",
            config_file,
            MERMAID_THEME,
        )
        return None
    # Look for the canonical config relative to the project root
    settings = get_settings()
    default = settings.project_root / _MERMAID_CONFIG
    return default if default.exists() else None


def _render_mmdc(mmd_path: Path, png_path: Path, config_file: Path | None = None) -> bool:
    """Render using Mermaid CLI (mmdc via npx or global install).

    Args:
        mmd_path: Path to the source ``.mermaid`` file.
        png_path: Destination PNG path.
        config_file: Optional path to a Mermaid JSON config file.  When
            ``None`` the function attempts to locate the canonical config at
            ``data/mermaid-config.json`` inside the project root.
    """
    import json
    import tempfile

    mmdc = shutil.which("mmdc")
    cmd: list[str]

    resolved_config = _resolve_mermaid_config(config_file)

    # Puppeteer/Chromium requires --no-sandbox on GitHub Actions and similar CI
    # environments where unprivileged user namespaces are restricted.
    puppeteer_cfg_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as pcfg:
            json.dump({"args": ["--no-sandbox", "--disable-setuid-sandbox"]}, pcfg)
            puppeteer_cfg_path = pcfg.name

        base_args = [
            "-i",
            str(mmd_path),
            "-o",
            str(png_path),
            "-b",
            "white",
            "-s",
            "2",
            "--puppeteerConfig",
            puppeteer_cfg_path,
        ]
        if resolved_config is not None:
            base_args += ["--configFile", str(resolved_config)]
        else:
            base_args += ["--theme", MERMAID_THEME]

        if mmdc:
            cmd = [mmdc, *base_args]
        else:
            npx = shutil.which("npx")
            if not npx:
                return False
            cmd = [npx, "--yes", "@mermaid-js/mermaid-cli", *base_args]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=60, check=False)
            if result.returncode == 0 and png_path.exists():
                return True
            logger.warning("mmdc returned %d: %s", result.returncode, result.stderr.decode())
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.debug("mmdc unavailable: %s", exc)
        return False
    finally:
        if puppeteer_cfg_path is not None:
            Path(puppeteer_cfg_path).unlink(missing_ok=True)


def _render_playwright(mmd_path: Path, png_path: Path) -> bool:
    """Render using Playwright headless Chromium."""
    try:
        from playwright.sync_api import sync_playwright  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("playwright not installed; skipping fallback.")
        return False

    mmd_text = mmd_path.read_text(encoding="utf-8")
    html = _mermaid_html(mmd_text)

    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
        f.write(html)
        html_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1200, "height": 800})
            page.goto(f"file://{html_path}")
            page.wait_for_selector(".mermaid svg", timeout=15000)
            element = page.query_selector(".mermaid")
            if element:
                element.screenshot(path=str(png_path))
                browser.close()
                return True
            browser.close()
    except Exception as exc:
        logger.warning("Playwright render failed: %s", exc)
    finally:
        Path(html_path).unlink(missing_ok=True)
    return False


def _mermaid_html(mmd_text: str) -> str:
    """Build a minimal HTML page that renders a Mermaid diagram.

    Uses :data:`MERMAID_THEME` so the Playwright fallback produces the same
    visual result as the ``mmdc`` primary path and the Quarto ``_quarto.yml``
    configuration.
    """
    return f"""<!DOCTYPE html>
<html><head>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'{MERMAID_THEME}'}});</script>
</head><body>
<div class="mermaid">{mmd_text}</div>
</body></html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def render_mermaid_file(
    mmd_path: Path,
    output_dir: Path | None = None,
    force: bool = False,
    config_file: Path | None = None,
) -> Path | None:
    """Render a single .mermaid file to PNG.

    Args:
        mmd_path: Path to the source ``.mermaid`` file.
        output_dir: Directory where the PNG is written.  Defaults to the
            project-level ``assets/images/mermaid/`` path from settings.
        force: When ``True`` the cache is bypassed and the diagram is
            re-rendered unconditionally.
        config_file: Optional path to a Mermaid JSON config file used by the
            ``mmdc`` backend.  When ``None`` the function tries the canonical
            ``data/mermaid-config.json`` inside the project root.

    Returns the Path to the PNG on success, or None on failure.
    """
    if output_dir is None:
        settings = get_settings()
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    png_name = mmd_path.stem + ".png"
    png_path = output_dir / png_name

    # Cache check
    if not force and png_path.exists():
        cache = _load_hash_cache(output_dir)
        current_hash = _file_hash(mmd_path)
        if cache.get(mmd_path.name) == current_hash:
            logger.info("Cache hit for %s — skipping render.", mmd_path.name)
            return png_path

    logger.info("Rendering %s -> %s", mmd_path.name, png_path)

    # Try mmdc first, then Playwright
    if _render_mmdc(mmd_path, png_path, config_file=config_file):
        _update_cache(mmd_path, output_dir)
        return png_path

    if _render_playwright(mmd_path, png_path):
        _update_cache(mmd_path, output_dir)
        return png_path

    logger.error(
        "Failed to render %s. Install mmdc (npm i -g @mermaid-js/mermaid-cli) "
        "or playwright (pip install playwright && playwright install chromium).",
        mmd_path.name,
    )
    return None


def _update_cache(mmd_path: Path, output_dir: Path) -> None:
    cache = _load_hash_cache(output_dir)
    cache[mmd_path.name] = _file_hash(mmd_path)
    _save_hash_cache(output_dir, cache)


def render_all_mermaid(
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Render all .mermaid files in visuals_dir to PNG.

    Returns list of successfully rendered PNG paths.
    """
    settings = get_settings()
    if visuals_dir is None:
        visuals_dir = settings.project_root / _DEFAULT_VISUALS_DIR
    visuals_dir = Path(visuals_dir)

    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)

    mermaid_files = sorted(visuals_dir.glob("*.mermaid"))
    if not mermaid_files:
        logger.warning("No .mermaid files found in %s", visuals_dir)
        return []

    logger.info("Found %d .mermaid files in %s", len(mermaid_files), visuals_dir)
    results: list[Path] = []
    for mmd in mermaid_files:
        png = render_mermaid_file(mmd, output_dir, force=force)
        if png:
            results.append(png)

    logger.info("Rendered %d/%d diagrams.", len(results), len(mermaid_files))
    return results


def build_mermaid_visuals(
    visuals_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> Path:
    """Entry point matching other generators' build_* pattern.

    Returns the output directory.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)

    render_all_mermaid(visuals_dir, output_dir, force=force)
    return output_dir
