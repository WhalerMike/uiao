#!/usr/bin/env python3
"""
generate_images_from_prompts.py
================================
Reads IMAGE-PROMPTS-*.md, generates each image via Google's Nano Banana Pro
(gemini-3-pro-image-preview) or Nano Banana 2 (gemini-3.1-flash-image-preview),
and caches results so unchanged prompts are not regenerated.

Cache strategy
--------------
Each prompt's body is SHA-256 hashed. The resulting hash is stored alongside the
output PNG in a manifest.json next to the images. On subsequent runs, prompts
whose hash matches the stored hash are skipped. Edit a prompt -> hash changes ->
that one image regenerates; everything else stays cached.

API key
-------
Read from the GEMINI_API_KEY environment variable. Never hard-coded.
On Windows PowerShell:    $env:GEMINI_API_KEY = "..."
In a CI secret:           pass through the workflow environment.

Usage
-----
    python generate_images_from_prompts.py
        # Default: reads IMAGE-PROMPTS-fedramp-moderate.md, writes to images/

    python generate_images_from_prompts.py --prompts IMAGE-PROMPTS-default.md
    python generate_images_from_prompts.py --model flash       # use Nano Banana 2
    python generate_images_from_prompts.py --force fig_combined_03
        # force regenerate one specific image regardless of cache
    python generate_images_from_prompts.py --force-all
        # ignore cache entirely
    python generate_images_from_prompts.py --dry-run
        # parse + report what would be generated, no API calls

Prompt-file format
------------------
The parser looks for ## headings of the form `## <id> — <title>` (em-dash) and
extracts the body of the **Prompt:** block that follows. The first block of
prose under "**Prompt:**" up to the next `---` divider or `##` heading becomes
the prompt body.
"""

from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

# --- Model registry --------------------------------------------------------
MODELS = {
    "pro":   "gemini-3-pro-image-preview",     # Nano Banana Pro - best for diagrams
    "flash": "gemini-3.1-flash-image-preview", # Nano Banana 2 - faster, cheaper
}
DEFAULT_MODEL = "pro"


# --- Prompt parser ---------------------------------------------------------
HEADING_RE = re.compile(r'^##\s+([a-z0-9_]+)\s+[—\-]\s+(.+?)\s*$', re.IGNORECASE)
PROMPT_HEADER_RE = re.compile(r'^\*\*Prompt:\*\*\s*$')
DIVIDER_RE = re.compile(r'^---\s*$')

def parse_prompts(md_path: Path) -> list[dict]:
    """
    Returns a list of {id, title, prompt} dicts in document order.
    """
    text = md_path.read_text(encoding="utf-8").splitlines()
    entries = []
    i, n = 0, len(text)
    current = None
    while i < n:
        line = text[i]
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                entries.append(current)
            current = {"id": m.group(1), "title": m.group(2).strip(), "prompt": ""}
            i += 1
            continue
        if current is not None and PROMPT_HEADER_RE.match(line):
            # Collect prompt body until next ## heading or --- divider
            i += 1
            body = []
            while i < n:
                if HEADING_RE.match(text[i]) or DIVIDER_RE.match(text[i]):
                    break
                body.append(text[i])
                i += 1
            current["prompt"] = "\n".join(body).strip()
            continue
        i += 1
    if current is not None:
        entries.append(current)
    # Drop any heading entries whose prompt body is empty (defensive)
    return [e for e in entries if e["prompt"]]


# --- Hashing + manifest ----------------------------------------------------
def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def load_manifest(manifest_path: Path) -> dict:
    if manifest_path.exists():
        try:
            return json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"[warn] manifest at {manifest_path} is corrupt; starting fresh")
    return {"images": {}}

def save_manifest(manifest_path: Path, manifest: dict) -> None:
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


# --- Gemini call -----------------------------------------------------------
def generate_one(prompt_text: str, model_id: str, out_path: Path) -> None:
    """
    Calls the Gemini image API and writes a PNG to out_path.

    Lazy import: only fail with a useful message if google-genai isn't installed.
    """
    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError:
        print(
            "[fatal] google-genai SDK not installed.\n"
            "        Install with: pip install google-genai pillow\n",
            file=sys.stderr,
        )
        sys.exit(2)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("[fatal] GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(2)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model_id,
        contents=[prompt_text],
        config=types.GenerateContentConfig(response_modalities=["IMAGE"]),
    )

    # Extract the first inline image part and write it.
    for part in response.parts:
        if getattr(part, "inline_data", None) is not None:
            img = part.as_image()
            img.save(str(out_path))
            return
    raise RuntimeError("Gemini response contained no inline image data")


# --- Main ------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--prompts",
        default="IMAGE-PROMPTS-fedramp-moderate.md",
        help="Path to the IMAGE-PROMPTS-*.md file (default: %(default)s)",
    )
    parser.add_argument(
        "--out-dir",
        default="images",
        help="Directory to write PNGs into (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        choices=list(MODELS.keys()),
        default=DEFAULT_MODEL,
        help="Which Gemini image model to use (default: %(default)s)",
    )
    parser.add_argument(
        "--force",
        action="append",
        default=[],
        metavar="ID",
        help="Force-regenerate the named image ID (may be repeated)",
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Ignore cache and regenerate every image",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and report; do not call the API",
    )
    parser.add_argument(
        "--retry",
        type=int,
        default=2,
        help="Retries per image on transient failure (default: %(default)s)",
    )
    args = parser.parse_args()

    prompts_path = Path(args.prompts)
    if not prompts_path.exists():
        print(f"[fatal] prompts file not found: {prompts_path}", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest = load_manifest(manifest_path)

    entries = parse_prompts(prompts_path)
    if not entries:
        print(f"[fatal] no prompts parsed out of {prompts_path}", file=sys.stderr)
        return 2

    model_id = MODELS[args.model]
    forced = set(args.force)

    print(f"[info] prompts file:  {prompts_path}")
    print(f"[info] output dir:    {out_dir}")
    print(f"[info] model:         {args.model} ({model_id})")
    print(f"[info] entries found: {len(entries)}")
    print()

    n_skipped = n_generated = n_failed = 0

    for entry in entries:
        eid = entry["id"]
        title = entry["title"]
        prompt = entry["prompt"]
        prompt_hash = sha256_hex(prompt)
        out_path = out_dir / f"{eid}.png"
        cached = manifest["images"].get(eid, {})
        cached_hash = cached.get("hash")

        force_this = args.force_all or (eid in forced)

        if (
            not force_this
            and cached_hash == prompt_hash
            and out_path.exists()
        ):
            print(f"[skip]   {eid}  (cache hit)  -> {out_path.name}")
            n_skipped += 1
            continue

        if args.dry_run:
            reason = (
                "force" if force_this
                else "missing file" if not out_path.exists()
                else "hash changed"
            )
            print(f"[plan]   {eid}  (would generate; {reason})")
            n_generated += 1
            continue

        # Actually generate, with retry
        attempt = 0
        last_err: Exception | None = None
        while attempt <= args.retry:
            attempt += 1
            try:
                t0 = time.time()
                generate_one(prompt, model_id, out_path)
                dt = time.time() - t0
                print(f"[ok]     {eid}  ({dt:.1f}s)  -> {out_path.name}")
                manifest["images"][eid] = {
                    "hash": prompt_hash,
                    "title": title,
                    "model": model_id,
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                save_manifest(manifest_path, manifest)
                n_generated += 1
                break
            except Exception as e:  # noqa: BLE001 -- generic by intent at the retry boundary
                last_err = e
                print(f"[retry]  {eid}  attempt {attempt} failed: {e}")
                time.sleep(2 * attempt)
        else:
            print(f"[fail]   {eid}  giving up: {last_err}")
            n_failed += 1

    print()
    print(f"[done] generated={n_generated}  skipped={n_skipped}  failed={n_failed}")
    return 0 if n_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
