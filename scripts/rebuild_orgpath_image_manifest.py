#!/usr/bin/env python3
"""Rebuild the OrgPath narrative image-prompts.manifest.yaml from chapter scans.

The manifest at docs/customer-documents/orgpath-narrative/image-prompts.manifest.yaml
is a section-scoped registry of every figure in the OrgPath narrative. Each
entry pins together: chapter file, figure ID, file/sidecar paths, caption,
SHA-256s (PNG and prompt), generated-at timestamp, and the prompt body.

Until now this manifest has been hand-maintained: the original section build
created it via one-shot tooling that no longer exists in the repo, and
neither `generate_images.py` nor `regenerate_local_images_from_figalt.py`
updates it. This script automates the rebuild.

Sources of truth, by field:
    chapter file       Filename on disk under the section root
    series-order       YAML frontmatter `series-order:` (zero-padded if int)
    status             YAML frontmatter `status:`
    title              YAML frontmatter `title:`
    subtitle           YAML frontmatter `subtitle:`
    description        YAML frontmatter `description:`
    canon-source       YAML frontmatter `canon-source:`
    image id           `#fig-...` attribute in the .qmd figure block
    image file         markdown image path `images/<file>.png`
    image sidecar      derived: same path with `.png.json` extension
    image caption      markdown image alt text `![<caption>]`
    image fig-alt      `fig-alt="..."` attribute, unescaped (the prompt body)
    image width        `width="..."` attribute
    image placeholder  derived from filename: `<...>-diagram-NN-...` → `DIAGRAM-NN`,
                         `<...>-image-NN-...` → `IMAGE-NN`
    image slug         derived from filename: text between `-diagram-NN-` and `.png`
    image aspect       sidecar `aspect` field if present, else `"16:9"`
    image sha256       sidecar `sha256` field
    image prompt-sha256 sidecar `prompt_sha256` field
    image generated-at sidecar `generated_at` field

Two modes:

    --check (default)  Compute the fresh manifest in memory; compare against
                       the on-disk manifest; exit 0 if identical, 1 if
                       different. Prints a unified diff on mismatch. Safe to
                       run in CI.

    --write            Compute the fresh manifest and write it to disk.

Usage:
    python scripts/rebuild_orgpath_image_manifest.py
    python scripts/rebuild_orgpath_image_manifest.py --write
    python scripts/rebuild_orgpath_image_manifest.py --check
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

try:
    import yaml  # PyYAML — already required across the repo's image tooling
except ImportError:
    print("PyYAML is required: pip install PyYAML", file=sys.stderr)
    sys.exit(2)


SECTION_REL = Path("docs/customer-documents/orgpath-narrative")
MANIFEST_NAME = "image-prompts.manifest.yaml"

# Header block — preserved verbatim. The notes body documents the manifest's
# purpose and is the authoritative comment on the file.
HEADER = """schema-version: "1.0.0"
section: "orgpath-narrative"
generated-from: "docs/customer-documents/orgpath-narrative/"
generator: "gemini-2.5-flash-image"
notes: |
  Manifest of every figure in the OrgPath narrative section.
  Each image's prompt is the fig-alt from its chapter .qmd — the canonical
  prompt body the Nano Banana pipeline (scripts/generate_images.py) consumed.
  Sidecar metadata (sha256s, generator, generated-at) is mirrored from
  <image>.png.json next to each PNG.

  A PowerShell driver iterates chapters[].images[] and either:
    - regenerates a PNG when prompt-sha256 in the manifest differs from
      the sibling .png.json (force-regen flow), or
    - audits coverage (every chapter .qmd lists at least one image; every
      image on disk is referenced by a chapter).

  Manifest is rebuilt by scripts that scan the section; do not hand-edit.
chapters:
"""

# Figure block pattern — mirrors the audit script's Get-FigAltByIdFromQmd.
# Anchors closing brace on width="..." to tolerate { } inside alt text.
FIG_BLOCK_RE = re.compile(
    r'!\[(?P<caption>[^\]]*)\]\(images/(?P<file>[^)]+\.png)\)\{(?P<attrs>.*?width="(?P<width>[^"]+)"\s*)\}',
    re.DOTALL,
)
FIG_ID_RE = re.compile(r"#(?P<id>fig-[A-Za-z0-9\-]+)")
FIG_ALT_RE = re.compile(r'fig-alt="(?P<alt>(?:[^"\\]|\\.)*)"')

# Filename → placeholder-id and slug.
FILE_DECOMP_RE = re.compile(
    r"(?P<kind>diagram|image|figure)-(?P<num>\d{2,3})-(?P<slug>[a-z0-9-]+)\.png$",
    re.IGNORECASE,
)


def find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / ".git").is_dir():
            return parent
    raise RuntimeError(f"no .git directory found above {p}")


def parse_frontmatter(qmd_text: str) -> dict:
    if not qmd_text.startswith("---"):
        return {}
    end = qmd_text.find("\n---", 3)
    if end == -1:
        return {}
    block = qmd_text[3:end].strip()
    data = yaml.safe_load(block) or {}
    if not isinstance(data, dict):
        return {}
    return data


def fmt_series_order(value) -> str:
    """Series-order field: int 1..9 → "01".."09", int 10..99 → str, str → str."""
    if isinstance(value, int):
        return f"{value:02d}"
    return str(value)


def decompose_filename(file_name: str) -> tuple[str, str]:
    """Return (placeholder-id, slug). Raises if filename doesn't match."""
    m = FILE_DECOMP_RE.search(file_name)
    if not m:
        raise ValueError(f"cannot decompose image filename: {file_name}")
    placeholder = f"{m.group('kind').upper()}-{m.group('num')}"
    return placeholder, m.group("slug")


def yaml_dq(value: str) -> str:
    """Format a value as a YAML double-quoted scalar matching existing style.
    Existing manifest uses literal " quotes inside double-quoted strings, NOT
    \" escapes — which is invalid YAML strictly, but PyYAML and the audit
    script both tolerate it. We replicate the exact pattern."""
    return f'"{value}"'


def emit_chapter(file_name: str, fm: dict, images: list[dict]) -> str:
    lines: list[str] = []
    lines.append(f"  - file: {yaml_dq(file_name)}")
    lines.append(f"    series-order: {yaml_dq(fmt_series_order(fm.get('series-order', '')))}")
    lines.append(f"    status: {yaml_dq(str(fm.get('status', '')))}")
    lines.append(f"    title: {yaml_dq(str(fm.get('title', '')))}")
    lines.append(f"    subtitle: {yaml_dq(str(fm.get('subtitle', '')))}")
    lines.append(f"    description: {yaml_dq(str(fm.get('description', '')))}")
    lines.append(f"    canon-source: {yaml_dq(str(fm.get('canon-source', '')))}")
    lines.append("    images:")
    for img in images:
        lines.extend(emit_image(img))
    return "\n".join(lines) + "\n"


def emit_image(img: dict) -> list[str]:
    lines: list[str] = []
    lines.append(f"      - id: {yaml_dq(img['id'])}")
    lines.append(f"        placeholder-id: {yaml_dq(img['placeholder_id'])}")
    lines.append(f"        slug: {yaml_dq(img['slug'])}")
    lines.append(f"        file: {yaml_dq(img['file'])}")
    lines.append(f"        sidecar: {yaml_dq(img['sidecar'])}")
    lines.append(f"        caption: {yaml_dq(img['caption'])}")
    lines.append(f"        width: {yaml_dq(img['width'])}")
    lines.append(f"        aspect: {yaml_dq(img['aspect'])}")
    lines.append(f"        sha256: {yaml_dq(img['sha256'])}")
    lines.append(f"        prompt-sha256: {yaml_dq(img['prompt_sha256'])}")
    lines.append(f"        generated-at: {yaml_dq(img['generated_at'])}")
    lines.append("        prompt: |")
    # Single-line prompts use 10-space indent. Multi-line is not currently
    # used in the section but is handled if it appears.
    for prompt_line in img["prompt"].split("\n"):
        lines.append(f"          {prompt_line}" if prompt_line else "")
    return lines


def collect_images_for_chapter(qmd_path: Path) -> list[dict]:
    qmd_text = qmd_path.read_text(encoding="utf-8")
    images: list[dict] = []
    for m in FIG_BLOCK_RE.finditer(qmd_text):
        attrs = m.group("attrs")
        id_match = FIG_ID_RE.search(attrs)
        if not id_match:
            print(f"  WARN: figure in {qmd_path.name} has no #fig-... id", file=sys.stderr)
            continue
        alt_match = FIG_ALT_RE.search(attrs)
        if not alt_match:
            print(f"  WARN: figure {id_match.group('id')} has no fig-alt", file=sys.stderr)
            continue
        # Audit unescapes \" → " before comparing; do the same so the manifest
        # prompt matches what the audit will read from the .qmd.
        prompt = alt_match.group("alt").replace('\\"', '"').replace("\\'", "'")

        file_name = m.group("file")
        placeholder, slug = decompose_filename(file_name)

        sidecar_path = qmd_path.parent / "images" / f"{file_name}.json"
        if not sidecar_path.exists():
            print(f"  WARN: missing sidecar {sidecar_path.name}", file=sys.stderr)
            sidecar_data = {}
        else:
            sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))

        images.append(
            {
                "id": id_match.group("id"),
                "placeholder_id": placeholder,
                "slug": slug,
                "file": f"images/{file_name}",
                "sidecar": f"images/{file_name}.json",
                "caption": m.group("caption"),
                "width": m.group("width"),
                "aspect": sidecar_data.get("aspect", "16:9"),
                "sha256": sidecar_data.get("sha256", ""),
                "prompt_sha256": sidecar_data.get("prompt_sha256", ""),
                "generated_at": sidecar_data.get("generated_at", ""),
                "prompt": prompt,
            }
        )
    return images


def chapter_sort_key(p: Path) -> tuple[int, int, str]:
    """Sort by leading number, then alphabetic suffix (so 07 < 07a < 08)."""
    name = p.stem
    m = re.match(r"(\d+)([a-z]*)", name)
    if not m:
        return (9999, 0, name)
    num = int(m.group(1))
    suffix = m.group(2)
    suffix_rank = 0 if suffix == "" else 1
    return (num, suffix_rank, suffix)


def build_manifest(section: Path) -> str:
    chapter_qmds = sorted(
        [p for p in section.glob("*.qmd") if p.name != "index.qmd"],
        key=chapter_sort_key,
    )
    chapter_blocks: list[str] = []
    for qmd in chapter_qmds:
        fm = parse_frontmatter(qmd.read_text(encoding="utf-8"))
        images = collect_images_for_chapter(qmd)
        chapter_blocks.append(emit_chapter(qmd.name, fm, images))
    return HEADER + "".join(chapter_blocks)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", default=True, help="Compare computed manifest against on-disk file (default)."
    )
    mode.add_argument("--write", action="store_true", help="Write the computed manifest to disk.")
    args = parser.parse_args(argv)

    repo_root = find_repo_root(Path(__file__))
    section = repo_root / SECTION_REL
    manifest_path = section / MANIFEST_NAME

    fresh = build_manifest(section)

    if args.write:
        # Write with LF line endings to match repo convention
        with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(fresh)
        print(f"wrote {manifest_path.relative_to(repo_root)}")
        return 0

    # Default: --check
    existing = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""
    if fresh == existing:
        print(f"manifest is up to date ({manifest_path.relative_to(repo_root)})")
        return 0

    diff = difflib.unified_diff(
        existing.splitlines(keepends=True),
        fresh.splitlines(keepends=True),
        fromfile="manifest.yaml (on disk)",
        tofile="manifest.yaml (computed)",
        n=3,
    )
    sys.stdout.writelines(diff)
    print("\nmanifest is stale. Run with --write to update.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
