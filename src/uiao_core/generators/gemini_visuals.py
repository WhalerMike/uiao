"""Gemini API on-demand image generation for UIAO artifacts.

ADR-0005: Uses Google Gemini (generative AI) to produce high-quality
architectural and compliance visuals on demand. Images are cached in
``assets/images/gemini/`` and only regenerated with ``--force-visuals``.

The API key is read from the ``GEMINI_API_KEY`` environment variable
(stored as a GitHub Secret for CI). No runtime API calls appear in
final artifacts -- all images are pre-generated static PNGs.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path

from uiao_core.utils.context import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
_DEFAULT_OUTPUT_DIR = Path("assets/images/gemini")
_PROMPT_REGISTRY_FILE = "gemini_prompts.json"
_HASH_FILE = ".gemini_hashes.json"
_DEFAULT_MODEL = "gemini-2.0-flash-exp"

# ---------------------------------------------------------------------------
# Built-in prompt registry
# ---------------------------------------------------------------------------
_BUILTIN_PROMPTS: dict[str, str] = {
    "zero-trust-architecture": (
        "Create a professional, clean infographic diagram showing a "
        "Zero Trust Architecture for a US federal agency. Include four "
        "labeled control planes: Identity (Azure AD/Entra ID), "
        "Addressing (Infoblox DDI/IPAM), Overlay (SD-WAN/ZTNA with "
        "micro-segmentation), and Telemetry (Splunk/Azure Monitor with "
        "KSI Dashboard). Use a dark blue and white color scheme with "
        "government-appropriate styling. Show data flows between planes "
        "with labeled arrows. Include FedRAMP Moderate badge. "
        "No text smaller than 12pt. PNG format, 1920x1080."
    ),
    "fedramp-compliance-flow": (
        "Create a professional flowchart showing the FedRAMP 20x "
        "continuous compliance process. Include stages: Canon YAML Data "
        "Ingestion, OSCAL Component Definition Generation, SSP Skeleton "
        "Build, KSI Evidence Collection, Telemetry Validation, and "
        "Continuous Authorization Dashboard. Use indigo and green color "
        "scheme. Government-appropriate styling with clean lines. "
        "PNG format, 1920x1080."
    ),
    "uiao-pillar-overview": (
        "Create a professional architectural diagram showing the UIAO "
        "(Unified Identity-Addressing-Overlay) framework pillars. "
        "Show three main pillars: Identity (authentication, MFA, "
        "conditional access), Addressing (DNS, IPAM, DDI), and "
        "Overlay (SD-WAN, ZTNA, micro-segmentation). Add a cross-cutting "
        "Telemetry layer at the bottom connecting all three. Use "
        "indigo/navy color scheme. Federal government styling. "
        "PNG format, 1920x1080."
    ),
    "modernization-roadmap": (
        "Create a professional timeline/roadmap infographic showing a "
        "4-phase federal IT modernization journey: Phase 1 Foundation "
        "(Identity + IPAM baseline), Phase 2 Integration (SD-WAN + ZTNA "
        "overlay), Phase 3 Automation (OSCAL + continuous monitoring), "
        "Phase 4 Optimization (AI-driven telemetry + predictive KSIs). "
        "Use a horizontal timeline with milestone markers. Indigo and "
        "white color scheme. Government-appropriate. PNG, 1920x1080."
    ),
}


# ---------------------------------------------------------------------------
# Hash-based cache
# ---------------------------------------------------------------------------
def _prompt_hash(prompt: str) -> str:
    """Return SHA-256 hex digest of a prompt string."""
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _load_hash_cache(output_dir: Path) -> dict[str, str]:
    cache_path = output_dir / _HASH_FILE
    if cache_path.exists():
        return dict(json.loads(cache_path.read_text(encoding="utf-8")))
    return {}


def _save_hash_cache(output_dir: Path, cache: dict[str, str]) -> None:
    cache_path = output_dir / _HASH_FILE
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gemini API interaction
# ---------------------------------------------------------------------------
def _get_api_key() -> str | None:
    """Read GEMINI_API_KEY from environment."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key if key else None


def _generate_image(
    prompt: str,
    output_path: Path,
    model: str = _DEFAULT_MODEL,
) -> bool:
    """Call Gemini API to generate an image from a text prompt."""
    api_key = _get_api_key()
    if not api_key:
        logger.error("GEMINI_API_KEY not set. Set it via environment variable or GitHub Secret.")
        return False

    try:
        from google import genai  # type: ignore[import-untyped]
        from google.genai import types  # type: ignore[import-untyped]
    except ImportError:
        logger.error("google-genai not installed. Run: pip install google-genai")
        return False

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_bytes)
                logger.info("Generated image: %s", output_path)
                return True

        logger.warning("No image data in Gemini response for prompt.")
        return False

    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_gemini_image(
    name: str,
    prompt: str | None = None,
    output_dir: Path | None = None,
    force: bool = False,
    model: str = _DEFAULT_MODEL,
) -> Path | None:
    """Generate a single Gemini image by name.

    If *prompt* is None, looks up the built-in prompt registry.
    Returns path to PNG on success, None on failure.
    """
    if output_dir is None:
        settings = get_settings()
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    if prompt is None:
        prompt = _BUILTIN_PROMPTS.get(name)
        if prompt is None:
            logger.error("No built-in prompt for '%s'.", name)
            return None

    png_path = output_dir / f"{name}.png"
    phash = _prompt_hash(prompt)

    # Cache check
    if not force and png_path.exists():
        cache = _load_hash_cache(output_dir)
        if cache.get(name) == phash:
            logger.info("Cache hit for '%s' -- skipping generation.", name)
            return png_path

    logger.info("Generating Gemini image: %s", name)
    if _generate_image(prompt, png_path, model=model):
        cache = _load_hash_cache(output_dir)
        cache[name] = phash
        _save_hash_cache(output_dir, cache)
        return png_path

    return None


def generate_all_gemini_images(
    output_dir: str | Path | None = None,
    force: bool = False,
    model: str = _DEFAULT_MODEL,
    prompts: dict[str, str] | None = None,
) -> list[Path]:
    """Generate all registered Gemini images.

    Uses built-in prompts merged with any custom *prompts* dict.
    Returns list of successfully generated PNG paths.
    """
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)

    # Merge built-in with custom prompts
    all_prompts = dict(_BUILTIN_PROMPTS)
    if prompts:
        all_prompts.update(prompts)

    # Also load external prompt registry if it exists
    registry_path = settings.project_root / _PROMPT_REGISTRY_FILE
    if registry_path.exists():
        try:
            external = json.loads(registry_path.read_text(encoding="utf-8"))
            if isinstance(external, dict):
                all_prompts.update(external)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load %s: %s", registry_path, exc)

    if not all_prompts:
        logger.warning("No prompts to generate.")
        return []

    logger.info("Generating %d Gemini image(s)...", len(all_prompts))
    results: list[Path] = []
    for name, prompt in sorted(all_prompts.items()):
        png = generate_gemini_image(
            name,
            prompt=prompt,
            output_dir=output_dir,
            force=force,
            model=model,
        )
        if png:
            results.append(png)

    logger.info(
        "Generated %d/%d Gemini image(s).",
        len(results),
        len(all_prompts),
    )
    return results


def build_gemini_visuals(
    output_dir: str | Path | None = None,
    force: bool = False,
    model: str = _DEFAULT_MODEL,
) -> Path:
    """Entry point matching other generators' build_* pattern."""
    settings = get_settings()
    if output_dir is None:
        output_dir = settings.project_root / _DEFAULT_OUTPUT_DIR
    output_dir = Path(output_dir)

    generate_all_gemini_images(output_dir, force=force, model=model)
    return output_dir
