#!/usr/bin/env python3
"""Regenerate missing local PNGs for .qmd image references using their fig-alt as the prompt.

Some .qmd pages have image markdown like:

    ![alt text](images/foo.png){#fig-foo fig-alt="long prompt here" width="85%"}

...where the placeholder syntax was already substituted to the final
markdown form but the underlying PNG was never generated (or was lost
before commit). This script finds those references, checks whether the
referenced PNG exists on disk, and if not — generates it via Gemini
using the `fig-alt` attribute as the prompt.

For every regenerated PNG this script also writes the sibling
`<image>.png.json` sidecar (placeholder_id, slug, sha256, prompt_sha256,
generated_at, etc.) so the result matches what `generate_images.py`
would have produced and the orgpath manifest audit stays clean. The
placeholder_id and slug are derived from the PNG filename's
`<...>-(diagram|image|figure)-NN-<slug>.png` shape; if the filename
doesn't conform, the sidecar write is skipped with a warning.

Complements:
- `generate_images.py` — handles `[IMAGE-NN: prompt]` placeholders (the
  pre-substitution form). Cannot help once the substitution has already
  happened with no surviving PNG.
- `generate_canon_images.py` — handles canon-side `UIAO-FIG-NNN` figures
  from `src/uiao/canon/image-prompts/`. Different concern entirely.
- `rebuild_orgpath_image_manifest.py` — rebuilds the section's
  `image-prompts.manifest.yaml` from chapter scans. Run after this
  script to refresh the manifest with the new entry.

Requires GEMINI_API_KEY in environment. Never commit a key.

Usage:
    python scripts/regenerate_local_images_from_figalt.py docs/customer-documents/reference-architecture/index.qmd
    python scripts/regenerate_local_images_from_figalt.py docs/customer-documents/reference-architecture/
    python scripts/regenerate_local_images_from_figalt.py docs/customer-documents/reference-architecture/ --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MODEL = "gemini-2.5-flash-image"

# Decompose <slug>-<diagram|image|figure>-NN-<rest>.png to recover the
# original placeholder kind+number (e.g. "DIAGRAM-02") and the prompt slug.
_FILE_DECOMP_RE = re.compile(
    r"(?P<kind>diagram|image|figure)-(?P<num>\d{2,3})-(?P<slug>[a-z0-9-]+)\.png$",
    re.IGNORECASE,
)


def _find_repo_root(start: Path) -> Path | None:
    """Walk up from `start` looking for .git/. Returns None if not found."""
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").is_dir():
            return parent
    return None


def _sha256_text_lf(text: str) -> str:
    """SHA-256 of UTF-8 text, LF-normalized first. Matches the contract used
    by `generate_images.py` and the orgpath audit script's prompt comparison."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_sidecar(out_path: Path, prompt: str, qmd: Path) -> Path | None:
    """Write the <png>.png.json sidecar next to the PNG. Returns the sidecar
    path on success, None if the filename can't be decomposed.

    Schema mirrors what `generate_images.py` writes and what
    `Invoke-OrgPathImageAudit.ps1` reads. Fields:
        aspect, canonical_id, document, generated_at, generator,
        placeholder_id, prompt_sha256, sha256, slug, used_by, version
    """
    m = _FILE_DECOMP_RE.search(out_path.name)
    if not m:
        print(f"  warn: cannot derive placeholder_id/slug from {out_path.name}; skipping sidecar")
        return None
    placeholder_id = f"{m.group('kind').upper()}-{m.group('num')}"
    slug = m.group("slug")

    # Match existing sidecars: Windows-style separators in the document field
    repo_root = _find_repo_root(qmd)
    document = str(qmd.resolve().relative_to(repo_root)).replace("/", "\\") if repo_root is not None else qmd.name

    payload = {
        "aspect": "16:9",
        "canonical_id": None,
        "document": document,
        "generated_at": _now_iso_utc(),
        "generator": MODEL,
        "placeholder_id": placeholder_id,
        "prompt_sha256": _sha256_text_lf(prompt),
        "sha256": _sha256_file(out_path),
        "slug": slug,
        "used_by": [],
        "version": "1.0",
    }
    sidecar_path = out_path.with_suffix(".png.json")
    with open(sidecar_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return sidecar_path


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
                sidecar = _write_sidecar(out_path, prompt, qmd)
                if sidecar is not None:
                    print(f"  wrote sidecar {sidecar.name}")
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
