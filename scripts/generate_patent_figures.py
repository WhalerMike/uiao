#!/usr/bin/env python3
# Generate the 9 patent figures referenced by the UIAO provisional patent
# application markdown using Google Gemini's Nano Banana image model.
#
# This is a focused one-shot generator distinct from
# scripts/generate_images.py — the harvester. The harvester excludes
# inbox/ from its scan; this script targets a single PROMPTS.md inside
# inbox/drafts/patent-figures/ and is invoked manually when the patent
# spec needs a refresh.
#
# Usage:
#   export GEMINI_API_KEY="<your-key>"
#   python scripts/generate_patent_figures.py            # generate missing
#   python scripts/generate_patent_figures.py --regenerate  # force regen
#   python scripts/generate_patent_figures.py --dry-run     # report only

from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("UIAO_REPO_ROOT") or SCRIPT_DIR.parent)
PROMPTS_PATH = REPO_ROOT / "inbox" / "drafts" / "patent-figures" / "PROMPTS.md"
OUTPUT_DIR = PROMPTS_PATH.parent
MODEL = "gemini-2.5-flash-image"

# Match each figure block in PROMPTS.md. The block header is:
#   ## FIG-NN — `figure-NN.png`
# Followed by metadata and a "**Prompt:**" line, then a blockquote prompt.
FIGURE_HEADING_RE = re.compile(
    r"^##\s+FIG-(?P<num>\d{2})\s+—\s+`(?P<filename>figure-\d{2}\.png)`\s*$",
    re.MULTILINE,
)
PROMPT_BLOCKQUOTE_RE = re.compile(
    r"\*\*Prompt:\*\*\s*\n\n(?P<body>(?:>\s.*\n?)+)",
)
# The first blockquote in the file (before any ## FIG- heading) is the
# shared "patent-figure visual language" preamble. We inline it in place
# of the "[Base style block above.]" placeholder in each prompt.
BASE_STYLE_BLOCKQUOTE_RE = re.compile(
    r"\*\*Patent-figure visual language\.\*\*.*?\n\n(?P<body>(?:>\s.*\n?)+)",
    re.DOTALL,
)
BASE_STYLE_PLACEHOLDER = "[Base style block above.]"


def _blockquote_to_paragraph(blockquote_text: str) -> str:
    lines = [ln.lstrip(">").strip() for ln in blockquote_text.splitlines()]
    return " ".join(ln for ln in lines if ln).strip()


def extract_base_style(text: str) -> str:
    """Extract the shared 'patent-figure visual language' blockquote.
    Returns empty string if not present (so the placeholder simply
    becomes empty rather than failing the run).
    """
    m = BASE_STYLE_BLOCKQUOTE_RE.search(text)
    return _blockquote_to_paragraph(m.group("body")) if m else ""


def extract_figure_blocks(text: str) -> list[tuple[str, str, str]]:
    """Return [(figure_number, filename, prompt_text), ...] in order.
    Each prompt has the [Base style block above.] placeholder expanded
    to the actual base-style paragraph from the file header.
    """
    base_style = extract_base_style(text)
    out: list[tuple[str, str, str]] = []
    matches = list(FIGURE_HEADING_RE.finditer(text))
    for i, m in enumerate(matches):
        num = m.group("num")
        filename = m.group("filename")
        block_start = m.end()
        block_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[block_start:block_end]
        pm = PROMPT_BLOCKQUOTE_RE.search(block)
        if not pm:
            print(f"  Warning: FIG-{num} has no Prompt blockquote; skipping.")
            continue
        prompt = _blockquote_to_paragraph(pm.group("body"))
        prompt = prompt.replace(BASE_STYLE_PLACEHOLDER, base_style)
        out.append((num, filename, prompt))
    return out


def generate_one(client, model: str, prompt: str, output_path: Path) -> bool:
    """Single Gemini call. Returns True on success."""
    try:
        from google.genai import types  # type: ignore
    except ImportError:
        print(
            "  Error: google-genai is required. Install with:\n"
            "    pip install google-genai Pillow"
        )
        return False

    try:
        from PIL import Image  # type: ignore
    except ImportError:
        print("  Error: Pillow is required. Install with: pip install Pillow")
        return False

    try:
        response = client.models.generate_content(
            model=model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )
    except Exception as e:
        print(f"  Error: {e}")
        return False

    for cand in response.candidates or []:
        for part in cand.content.parts or []:
            if part.text:
                print(f"  Model text: {part.text.strip()[:120]}")
            if part.inline_data and part.inline_data.data:
                image = Image.open(io.BytesIO(part.inline_data.data))
                image.save(str(output_path))
                return True
    print("  Error: no image part in response.")
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts and target paths; do not call the API.",
    )
    parser.add_argument(
        "--regenerate",
        action="store_true",
        help="Re-call the API for figures whose PNG already exists. Default "
        "behavior is to skip existing files (cache hit).",
    )
    args = parser.parse_args()

    if not PROMPTS_PATH.is_file():
        print(f"Error: prompts file not found at {PROMPTS_PATH}")
        return 1

    text = PROMPTS_PATH.read_text(encoding="utf-8")
    blocks = extract_figure_blocks(text)
    if not blocks:
        print("No figure blocks found in PROMPTS.md.")
        return 1

    print(f"Prompts file:    {PROMPTS_PATH.relative_to(REPO_ROOT)}")
    print(f"Output dir:      {OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"Model:           {MODEL}")
    print(f"Figures to scan: {len(blocks)}\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not args.dry_run:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print(
                "Error: GEMINI_API_KEY is not set. Export it or use --dry-run."
            )
            return 1
        try:
            from google import genai  # type: ignore
        except ImportError:
            print(
                "Error: google-genai is required. Install with:\n"
                "  pip install google-genai Pillow"
            )
            return 1
        client = genai.Client(api_key=api_key)
    else:
        client = None

    generated = 0
    cached = 0
    failed = 0

    for num, filename, prompt in blocks:
        output_path = OUTPUT_DIR / filename
        if output_path.exists() and not args.regenerate:
            print(f"  [cache] FIG-{num} → {filename}")
            cached += 1
            continue
        if args.dry_run:
            preview = prompt[:120] + ("..." if len(prompt) > 120 else "")
            print(f"  [dry-run] FIG-{num} → {filename}")
            print(f"            prompt: {preview}")
            continue
        print(f"  Generating FIG-{num} → {filename}")
        ok = generate_one(client, MODEL, prompt, output_path)
        if ok:
            generated += 1
        else:
            failed += 1

    print("\n=== Run report ===")
    print(f"Figures total:    {len(blocks)}")
    print(f"Generated:        {generated}")
    print(f"Cached (hit):     {cached}")
    print(f"Failed:           {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
