#!/usr/bin/env python3
"""Regenerate missing local PNGs for .qmd image references using their fig-alt as the prompt.

Some .qmd pages have image markdown like:

    ![alt text](images/foo.png){#fig-foo fig-alt="long prompt here" width="85%"}

...where the placeholder syntax was already substituted to the final
markdown form but the underlying PNG was never generated (or was lost
before commit). This script finds those references, checks whether the
referenced PNG exists on disk, and if not — generates it via Gemini
using the `fig-alt` attribute as the prompt.

Complements:
- `generate_images.py` — handles `[IMAGE-NN: prompt]` placeholders (the
  pre-substitution form). Cannot help once the substitution has already
  happened with no surviving PNG.
- `generate_canon_images.py` — handles canon-side `UIAO-FIG-NNN` figures
  from `src/uiao/canon/image-prompts/`. Different concern entirely.

Requires GEMINI_API_KEY in environment. Never commit a key.

Usage:
    python scripts/regenerate_local_images_from_figalt.py docs/modernization/index.qmd
    python scripts/regenerate_local_images_from_figalt.py docs/modernization/
    python scripts/regenerate_local_images_from_figalt.py docs/modernization/ --dry-run
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

MODEL = "gemini-2.5-flash-image"

# Match: ![alt](path){...attrs...}
# Captures the path (relative to the .qmd) and the attr block.
# Permissive — image markdown can be very long and span lots of characters.
IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\{(?P<attrs>[^}]*)\}")

# Match fig-alt="..." inside an attr block, allowing escaped quotes.
FIG_ALT_RE = re.compile(r'fig-alt="(?P<figalt>(?:[^"\\]|\\.)*)"')


def expand_paths(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for p in paths:
        if p.is_dir():
            out.extend(sorted(p.glob("*.qmd")))
        elif p.is_file() and p.suffix == ".qmd":
            out.append(p)
        elif not p.exists():
            print(f"skip (does not exist): {p}", file=sys.stderr)
        else:
            print(f"skip (not a .qmd or dir): {p}", file=sys.stderr)
    return out


def find_image_refs(qmd: Path) -> list[tuple[Path, str]]:
    """Return [(absolute output path, prompt), ...] for each image ref needing generation.

    Skips refs whose target PNG already exists or whose fig-alt is empty
    (no prompt available).
    """
    text = qmd.read_text(encoding="utf-8")
    refs: list[tuple[Path, str]] = []
    for m in IMG_RE.finditer(text):
        path_str = m.group("path").strip()
        # Only handle local relative refs to images/ subdir; skip absolute URLs and non-image targets
        if path_str.startswith(("http://", "https://", "/")):
            continue
        out_path = (qmd.parent / path_str).resolve()
        if out_path.exists():
            continue
        attrs = m.group("attrs")
        fa = FIG_ALT_RE.search(attrs)
        if not fa:
            print(f"{qmd}: image {path_str} missing PNG and no fig-alt to regenerate from — skipping")
            continue
        prompt = fa.group("figalt")
        # Unescape any backslash-escaped quotes the markdown carries
        prompt = prompt.replace('\\"', '"').replace("\\'", "'")
        if not prompt.strip():
            continue
        refs.append((out_path, prompt))
    return refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to scan. Directories scanned non-recursively for *.qmd.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be generated without calling the API.",
    )
    args = parser.parse_args(argv)

    files = expand_paths(args.paths)
    if not files:
        print("no .qmd files to process", file=sys.stderr)
        return 1

    # Collect all (file, out_path, prompt) tuples first so the report is clean
    tasks: list[tuple[Path, Path, str]] = []
    for f in files:
        for out_path, prompt in find_image_refs(f):
            tasks.append((f, out_path, prompt))

    if not tasks:
        print("no missing local images to regenerate")
        return 0

    print(f"found {len(tasks)} missing local image(s) to regenerate:")
    for qmd, out_path, prompt in tasks:
        rel = out_path.relative_to(Path.cwd()) if out_path.is_relative_to(Path.cwd()) else out_path
        print(f"  {qmd.name} -> {rel} (prompt={len(prompt)} chars)")

    if args.dry_run:
        print("\n(dry-run; no API calls)")
        return 0

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("error: GEMINI_API_KEY not set in environment", file=sys.stderr)
        return 2

    from google import genai

    client = genai.Client(api_key=api_key)

    successes = 0
    for qmd, out_path, prompt in tasks:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"\n{qmd.name} -> {out_path.name}")
        try:
            response = client.models.generate_content(model=MODEL, contents=[prompt])
        except Exception as e:
            print(f"  API call failed: {e}")
            continue
        wrote = False
        for part in response.parts:
            if part.inline_data is not None:
                image = part.as_image()
                image.save(str(out_path))
                size = out_path.stat().st_size
                print(f"  saved {size:,} bytes")
                successes += 1
                wrote = True
                break
            if part.text is not None:
                print(f"  model text response: {part.text[:200]}")
        if not wrote:
            print("  no image data in response")

    print(f"\n{successes}/{len(tasks)} generated successfully")
    return 0 if successes == len(tasks) else 1


if __name__ == "__main__":
    sys.exit(main())
