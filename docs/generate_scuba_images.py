#!/usr/bin/env python3
# Generate SCuBA Technical Specification images using Google Gemini's Nano Banana model.
#
# This follows the exact same pattern as generate_images.py (Doc 01).
# Reads scuba_prompts.json, calls Gemini NanoBanana, saves PNGs to images/.
#
# Usage (just run from anywhere):
#   python C:\Users\whale\uiao-docs\generate_scuba_images.py
#   python C:\Users\whale\uiao-docs\generate_scuba_images.py --dry-run

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ──────────────────────────────────────────────────────────────
# CONFIGURATION — edit these to match your setup
# ──────────────────────────────────────────────────────────────
API_KEY = "AIzaSyCQ-BRx8IuLV23ybUjluLY1WfT6mxS9-jQ"
SCRIPT_DIR = Path(r"C:\Users\whale\uiao-docs")
PROMPTS_FILE = SCRIPT_DIR / "scuba_prompts.json"
OUTPUT_DIR = SCRIPT_DIR / "images"
MODEL = "gemini-2.5-flash-image"
DELAY_SECONDS = 2.0
# ──────────────────────────────────────────────────────────────


def load_prompts(prompts_file: Path) -> list[dict]:
    """Load prompts from a JSON file."""
    if not prompts_file.exists():
        print(f"Error: Prompts file not found at:\n  {prompts_file}")
        sys.exit(1)
    with open(prompts_file, "r", encoding="utf-8") as f:
        prompts = json.load(f)
    print(f"Loaded {len(prompts)} prompt(s) from:\n  {prompts_file}")
    return prompts


def generate_image(client, prompt_text: str, output_path: Path, model: str) -> bool:
    """Generate a single image from a prompt and save it."""
    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt_text],
        )

        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                image.save(str(output_path))
                return True
            elif part.text is not None:
                print(f"  Model text response: {part.text[:200]}")

        print(f"  Warning: No image data returned for this prompt.")
        return False

    except Exception as e:
        print(f"  Error generating image: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate SCuBA images from prompts via Nano Banana (Gemini API)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without generating images")
    args = parser.parse_args()

    # Change to the script directory
    print(f"Working directory: {SCRIPT_DIR}")
    os.chdir(SCRIPT_DIR)

    # Resolve API key
    api_key = API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: No API key provided. Set API_KEY in the script or GEMINI_API_KEY env var.")
        sys.exit(1)

    # Load prompts
    prompts = load_prompts(PROMPTS_FILE)

    if args.dry_run:
        print("\n=== DRY RUN — No images will be generated ===\n")
        for i, item in enumerate(prompts, 1):
            print(f"[{i}/{len(prompts)}] {item['id']} -> {item['filename']}")
            print(f"  Placement: {item['placement']}")
            print(f"  Prompt: {item['prompt'][:120]}...\n")
        return

    # Set up output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}")

    # Initialize the Gemini client
    from google import genai
    client = genai.Client(api_key=api_key)

    print(f"\nGenerating {len(prompts)} image(s) using model: {MODEL}\n")

    succeeded = 0
    failed = 0

    for i, item in enumerate(prompts, 1):
        prompt_id = item["id"]
        filename = item["filename"]
        prompt_text = item["prompt"]
        output_path = OUTPUT_DIR / filename

        print(f"[{i}/{len(prompts)}] Generating: {prompt_id} -> {filename}")

        if generate_image(client, prompt_text, output_path, MODEL):
            file_size = output_path.stat().st_size / 1024
            print(f"  Saved: {output_path} ({file_size:.0f} KB)")
            succeeded += 1
        else:
            failed += 1

        # Rate-limit pause between requests (skip after the last one)
        if i < len(prompts):
            time.sleep(DELAY_SECONDS)

    print(f"\nDone! {succeeded} succeeded, {failed} failed.")
    print(f"Images saved to: {OUTPUT_DIR}")
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
