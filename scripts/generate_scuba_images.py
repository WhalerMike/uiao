#!/usr/bin/env python3
"""Generate SCuBA Technical Specification images via Gemini NanoBanana.

Ingests an IMAGE-PROMPTS markdown file, parses each image prompt,
and calls the Gemini NanoBanana image generation API to produce PNGs.

This follows the same pattern used for Doc 01 Executive Brief images.

Prerequisites:
    pip install google-genai
    export GEMINI_API_KEY="your-api-key"

Usage:
    # Generate all 4 SCuBA diagram images
    python scripts/generate_scuba_images.py

    # Use a specific prompts file
    python scripts/generate_scuba_images.py --prompts visuals/IMAGE-PROMPTS-SCUBA.md

    # Generate a single image by number
    python scripts/generate_scuba_images.py --image 1

    # Force regeneration (ignore cache)
    python scripts/generate_scuba_images.py --force

    # Use a different NanoBanana model
    python scripts/generate_scuba_images.py --model gemini-2.5-flash-image

    # Dry-run: print parsed prompts without calling API
    python scripts/generate_scuba_images.py --dry-run

Output:
    assets/images/gemini/scuba/image-01-pipeline-architecture.png
    assets/images/gemini/scuba/image-02-module-dependencies.png
    assets/images/gemini/scuba/image-03-three-hop-mapping.png
    assets/images/gemini/scuba/image-04-evidence-integrity-chain.png
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_PROMPTS_FILE = "visuals/IMAGE-PROMPTS-SCUBA.md"
DEFAULT_OUTPUT_DIR = Path("assets/images/gemini/scuba")
HASH_FILE = ".image_hashes.json"

# Gemini NanoBanana model options:
#   "gemini-2.0-flash-exp"              — Nano Banana (original)
#   "gemini-2.5-flash-image"            — Nano Banana (stable)
#   "gemini-3.1-flash-image-preview"    — Nano Banana 2 (latest, 4K)
#   "gemini-3-pro-image-preview"        — Nano Banana Pro (highest quality)
DEFAULT_MODEL = "gemini-2.0-flash-exp"


# ---------------------------------------------------------------------------
# Markdown prompt parser
# ---------------------------------------------------------------------------
def parse_image_prompts(md_path: str | Path) -> list[dict[str, str]]:
    """Parse an IMAGE-PROMPTS.md file into a list of image specs.

    Each spec dict contains:
        - number: image number (1, 2, 3, ...)
        - title: heading text (e.g., "Four-Plane Pipeline Architecture")
        - placement: where the image goes in the document
        - prompt: the full prompt text for the image generator

    The parser looks for ## Image N: <title> headings, then extracts
    **Placement:** and **Prompt:** blocks.
    """
    md_path = Path(md_path)
    if not md_path.exists():
        logger.error("Prompts file not found: %s", md_path)
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8")
    images: list[dict[str, str]] = []

    # Split on image headings: ## Image N: <title>
    pattern = r"##\s+Image\s+(\d+):\s*(.+?)(?=\n)"
    sections = re.split(pattern, content)

    # sections[0] = preamble, then groups of (number, title, body)
    i = 1
    while i < len(sections) - 2:
        number = sections[i].strip()
        title = sections[i + 1].strip()
        body = sections[i + 2]

        # Extract placement
        placement_match = re.search(r"\*\*Placement:\*\*\s*(.+?)(?=\n\n|\n\*\*)", body, re.DOTALL)
        placement = placement_match.group(1).strip() if placement_match else ""

        # Extract prompt — everything after **Prompt:**
        prompt_match = re.search(r"\*\*Prompt:\*\*\s*\n(.+?)(?=\n---|\n##|\Z)", body, re.DOTALL)
        prompt = prompt_match.group(1).strip() if prompt_match else ""

        if prompt:
            images.append(
                {
                    "number": number,
                    "title": title,
                    "placement": placement,
                    "prompt": prompt,
                }
            )
            logger.info(
                "Parsed Image %s: %s (%d chars)",
                number,
                title,
                len(prompt),
            )
        else:
            logger.warning("No prompt found for Image %s: %s", number, title)

        i += 3

    return images


def slugify(title: str) -> str:
    """Convert a title to a filename-safe slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


# ---------------------------------------------------------------------------
# Hash-based cache
# ---------------------------------------------------------------------------
def _prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _load_cache(output_dir: Path) -> dict[str, str]:
    cache_path = output_dir / HASH_FILE
    if cache_path.exists():
        return dict(json.loads(cache_path.read_text(encoding="utf-8")))
    return {}


def _save_cache(output_dir: Path, cache: dict[str, str]) -> None:
    cache_path = output_dir / HASH_FILE
    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gemini NanoBanana API
# ---------------------------------------------------------------------------
def call_nanobanana(
    prompt: str,
    output_path: Path,
    model: str = DEFAULT_MODEL,
) -> bool:
    """Call Gemini NanoBanana to generate an image from a text prompt.

    Uses the google-genai SDK with response_modalities=["IMAGE", "TEXT"]
    to invoke Gemini's native image generation capability.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        logger.error(
            "GEMINI_API_KEY not set.\n  export GEMINI_API_KEY='your-key'\n  Or set it as a GitHub Secret for CI."
        )
        return False

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.error("google-genai not installed.\n  pip install google-genai")
        return False

    try:
        client = genai.Client(api_key=api_key)
        logger.info("  Model: %s", model)
        logger.info("  Generating...")

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image bytes from response
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                image_bytes = part.inline_data.data
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(image_bytes)
                size_kb = len(image_bytes) / 1024
                logger.info("  Saved: %s (%.1f KB)", output_path, size_kb)
                return True

        logger.warning("  No image data in Gemini response.")
        return False

    except Exception as exc:
        logger.error("  Gemini API error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate images from IMAGE-PROMPTS.md via Gemini NanoBanana. "
            "Parses the markdown file, extracts each prompt, and calls "
            "the Gemini image generation API."
        )
    )
    parser.add_argument(
        "--prompts",
        default=DEFAULT_PROMPTS_FILE,
        help=f"Path to IMAGE-PROMPTS markdown file (default: {DEFAULT_PROMPTS_FILE})",
    )
    parser.add_argument(
        "--image",
        type=int,
        help="Generate a single image by number (e.g., --image 1)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all images (ignore cache)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini NanoBanana model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and print prompts without calling the API",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse prompts from markdown
    logger.info("Parsing prompts from: %s", args.prompts)
    images = parse_image_prompts(args.prompts)

    if not images:
        logger.error("No image prompts found in %s", args.prompts)
        sys.exit(1)

    logger.info("Found %d image prompt(s)\n", len(images))

    # Filter to single image if requested
    if args.image:
        images = [img for img in images if img["number"] == str(args.image)]
        if not images:
            logger.error("Image %d not found in prompts file.", args.image)
            sys.exit(1)

    cache = _load_cache(output_dir)
    generated = 0
    failed = 0
    cached = 0

    for img in images:
        num = img["number"]
        title = img["title"]
        prompt = img["prompt"]
        slug = slugify(title)
        filename = f"image-{num.zfill(2)}-{slug}.png"
        png_path = output_dir / filename
        phash = _prompt_hash(prompt)
        cache_key = f"image-{num}"

        logger.info("=== Image %s: %s ===", num, title)
        logger.info("  Output: %s", png_path)

        if args.dry_run:
            logger.info("  Placement: %s", img["placement"])
            logger.info("  Prompt (%d chars):\n%s\n", len(prompt), prompt)
            continue

        # Cache check
        if not args.force and png_path.exists():
            if cache.get(cache_key) == phash:
                logger.info("  Cache hit — skipping\n")
                cached += 1
                continue

        # Generate
        if call_nanobanana(prompt, png_path, model=args.model):
            cache[cache_key] = phash
            _save_cache(output_dir, cache)
            generated += 1
        else:
            failed += 1

        logger.info("")

    if not args.dry_run:
        logger.info(
            "=== Complete: %d generated, %d failed, %d cached ===",
            generated,
            failed,
            cached,
        )
        if failed:
            sys.exit(1)


if __name__ == "__main__":
    main()
