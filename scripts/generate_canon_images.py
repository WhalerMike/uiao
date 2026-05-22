#!/usr/bin/env python3
"""Generate canonical UIAO figure PNGs from prompts in src/uiao/canon/image-prompts/.

Reads the prompt body from each src/uiao/canon/image-prompts/UIAO-FIG-NNN.md
file, calls the Gemini image model, saves the PNG to docs/images/canonical/,
and updates the matching entry in src/uiao/canon/image-registry.yaml
(file_sha256 and generated_at fields).

Complements scripts/generate_images.py, which handles only doc-local
placeholders ([IMAGE-NN: prompt]) and updates `used_by` for canon refs
([IMAGE-REF: UIAO-FIG-NNN]) — but does NOT generate canonical PNGs
themselves. Canonical figures previously had no automated generation
path; this script closes that gap.

Requires GEMINI_API_KEY in the environment. Never commit a key.

Usage:
    python scripts/generate_canon_images.py UIAO-FIG-012 UIAO-FIG-013 UIAO-FIG-014
    python scripts/generate_canon_images.py --all-pending
    python scripts/generate_canon_images.py UIAO-FIG-012 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(os.environ.get("UIAO_REPO_ROOT") or SCRIPT_DIR.parent)
CANON_REGISTRY = REPO_ROOT / "src" / "uiao" / "canon" / "image-registry.yaml"
CANON_PROMPTS_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "image-prompts"
CANONICAL_OUTPUT_DIR = REPO_ROOT / "docs" / "images" / "canonical"
MODEL = "gemini-2.5-flash-image"
PLACEHOLDER_SHA = "0" * 64


def load_registry() -> dict:
    with open(CANON_REGISTRY, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_registry(data: dict) -> None:
    with open(CANON_REGISTRY, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True, width=1000)


def extract_prompt_body(prompt_md: Path) -> str:
    """Return the text after `## Prompt`, up to the next `##` or EOF."""
    text = prompt_md.read_text(encoding="utf-8")
    m = re.search(r"^##\s+Prompt\s*$(.*?)(?=^##\s|\Z)", text, re.MULTILINE | re.DOTALL)
    if not m:
        raise ValueError(f"No `## Prompt` section found in {prompt_md}")
    return m.group(1).strip()


def find_entry(registry: dict, fig_id: str) -> dict | None:
    for entry in registry.get("images", []):
        if entry.get("id") == fig_id:
            return entry
    return None


def all_pending_ids(registry: dict) -> list[str]:
    """IDs whose file_sha256 is the placeholder all-zeros value."""
    return [e["id"] for e in registry.get("images", []) if e.get("file_sha256") == PLACEHOLDER_SHA]


def output_path_for(entry: dict) -> Path:
    return CANONICAL_OUTPUT_DIR / f"{entry['id']}-{entry['slug']}.png"


def generate_one(client, fig_id: str, registry: dict, *, dry_run: bool) -> bool:
    entry = find_entry(registry, fig_id)
    if entry is None:
        print(f"{fig_id}: not in registry — skipping")
        return False

    prompt_md = CANON_PROMPTS_DIR / f"{fig_id}.md"
    if not prompt_md.exists():
        print(f"{fig_id}: prompt file missing at {prompt_md} — skipping")
        return False

    try:
        prompt_text = extract_prompt_body(prompt_md)
    except ValueError as e:
        print(f"{fig_id}: {e}")
        return False

    out_path = output_path_for(entry)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"{fig_id}: prompt={len(prompt_text)} chars; out -> {out_path.relative_to(REPO_ROOT)}")

    if dry_run:
        print("  (dry-run; no API call)")
        return True

    try:
        response = client.models.generate_content(model=MODEL, contents=[prompt_text])
    except Exception as e:
        print(f"  API call failed: {e}")
        return False

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            image.save(str(out_path))
            png_bytes = out_path.read_bytes()
            file_sha = hashlib.sha256(png_bytes).hexdigest()
            now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            entry["file_sha256"] = file_sha
            entry["generated_at"] = now_iso
            entry["status"] = "current"
            entry["generator"] = MODEL
            print(f"  saved {len(png_bytes)} bytes; sha256 {file_sha[:12]}...")
            return True
        if part.text is not None:
            print(f"  model text response: {part.text[:200]}")

    print("  no image data in response")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "ids",
        nargs="*",
        default=[],
        help="UIAO-FIG-NNN IDs to generate. Mutually exclusive with --all-pending.",
    )
    parser.add_argument(
        "--all-pending",
        action="store_true",
        help="Generate every registry entry whose file_sha256 is the placeholder all-zeros value.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't call the API; just report what would happen.",
    )
    args = parser.parse_args(argv)

    if args.ids and args.all_pending:
        parser.error("provide either IDs or --all-pending, not both")

    registry = load_registry()

    if args.all_pending:
        ids = all_pending_ids(registry)
        if not ids:
            print("no entries pending (no file_sha256 == 0*64)")
            return 0
        print(f"all-pending: {len(ids)} entries to generate")
    else:
        ids = args.ids
        if not ids:
            parser.error("provide UIAO-FIG-NNN IDs or use --all-pending")

    client = None
    if not args.dry_run:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("error: GEMINI_API_KEY not set in environment", file=sys.stderr)
            return 2
        from google import genai

        client = genai.Client(api_key=api_key)

    successes = 0
    for fig_id in ids:
        if generate_one(client, fig_id, registry, dry_run=args.dry_run):
            successes += 1

    if not args.dry_run and successes > 0:
        save_registry(registry)
        print(f"\nregistry updated for {successes} entry/entries")
    print(f"\n{successes}/{len(ids)} generated successfully")
    return 0 if successes == len(ids) else 1


if __name__ == "__main__":
    sys.exit(main())
