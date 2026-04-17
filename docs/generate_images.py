#!/usr/bin/env python3
# Generate images from prompts using Google Gemini's Nano Banana model.
#
# Two input modes, both supported in this version:
#
#   A. Legacy (prompts.json): backward-compatible. If docs/prompts.json
#      exists and is non-empty, each entry {id, filename, prompt} is
#      generated straight into docs/images/.
#
#   B. Harvested (default for new content): the pipeline scans every
#      .qmd and .md file under the rendered roots for three placeholder
#      types per UIAO_202 and the Academy image-pipeline guide:
#
#        [IMAGE-NN: <prompt>]       doc-local, prompt provided
#        [IMAGE-REF: UIAO-FIG-NNN]  canon reuse
#        [IMAGE-NN: AUTO]           pipeline-drafted (Part-3 feature)
#
#      For every doc-local placeholder with a prompt, the pipeline
#      writes/refreshes the sibling IMAGE-PROMPTS.md block, generates
#      the PNG, writes a sidecar JSON, embeds PNG tEXt metadata, and
#      updates the canonical image-registry.yaml `used_by` list for any
#      [IMAGE-REF:] reference it sees.
#
# Requires GEMINI_API_KEY set in the environment. Never commit a key.
#
# Usage (run from any cwd inside the repo):
#   export GEMINI_API_KEY="<your-key>"
#   python docs/generate_images.py                 # harvest + legacy
#   python docs/generate_images.py --dry-run       # report; no API calls
#   python docs/generate_images.py --mode legacy   # prompts.json only
#   python docs/generate_images.py --mode harvest  # scanner only
#   python docs/generate_images.py --scan-only     # placeholders; no gen
#
# Environment variables:
#   GEMINI_API_KEY   Required unless --dry-run / --scan-only
#   UIAO_REPO_ROOT   Optional override of repo root detection. Defaults
#                    to the git toplevel containing this script.

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - yaml is a tiny dep; install on demand
    yaml = None  # Flagged at runtime; harvest mode requires yaml.


# ──────────────────────────────────────────────────────────────
# CONFIGURATION — env-driven. Key MUST come from environment.
# ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent                 # docs/
REPO_ROOT = Path(os.environ.get("UIAO_REPO_ROOT") or SCRIPT_DIR.parent)
PROMPTS_FILE = SCRIPT_DIR / "prompts.json"
LEGACY_OUTPUT_DIR = SCRIPT_DIR / "images"
CANONICAL_OUTPUT_DIR = SCRIPT_DIR / "images" / "canonical"
CANON_REGISTRY = REPO_ROOT / "core" / "canon" / "image-registry.yaml"
CANON_PROMPTS_DIR = REPO_ROOT / "core" / "canon" / "image-prompts"
MODEL = "gemini-2.5-flash-image"
DELAY_SECONDS = 2.0
SCAN_ROOTS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "core" / "canon" / "specs",
    REPO_ROOT / "core" / "canon" / "adr",
]
SCAN_EXTS = (".qmd", ".md")
EXCLUDE_PATH_PARTS = {"_site", "_freeze", ".quarto", "node_modules", ".venv", "__pycache__"}
# ──────────────────────────────────────────────────────────────


# ──────────────────────────────────────────────────────────────
# Placeholder grammar per UIAO_202 §"Three placeholder types":
#
#   Type A:  [IMAGE-03: A 16:9 schematic ...]          local + prompt
#   Type B:  [IMAGE-REF: UIAO-FIG-007]                 canon reuse
#   Type C:  [IMAGE-03: AUTO]                          pipeline drafts
#
# We also tolerate DIAGRAM-NN and FIGURE-NN as local variants.
# ──────────────────────────────────────────────────────────────
PLACEHOLDER_LOCAL_RE = re.compile(
    r"\[(?P<kind>IMAGE|DIAGRAM|FIGURE)-(?P<num>\d{2,3}):\s*(?P<body>[^\]]+)\]",
    re.MULTILINE,
)
PLACEHOLDER_REF_RE = re.compile(
    r"\[IMAGE-REF:\s*(?P<id>UIAO-FIG-\d{3})\s*\]",
    re.MULTILINE,
)
AUTO_MARKER = "AUTO"
CANON_ID_RE = re.compile(r"^UIAO-FIG-\d{3}$")


# ──────────────────────────────────────────────────────────────
# Dataclasses. Intentionally small & immutable so the scanner can
# produce them cheaply and the orchestrator can consume them in any
# order.
# ──────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class DocLocalPlaceholder:
    """A [IMAGE-NN: prompt] or [IMAGE-NN: AUTO] in some .qmd/.md file."""
    document: Path              # repo-relative-ish; resolved Path()
    placeholder_id: str         # e.g. "IMAGE-03"
    body: str                   # raw text between ':' and ']'
    line_number: int            # 1-indexed
    is_auto: bool               # True iff body == "AUTO"


@dataclass(frozen=True)
class CanonRefPlaceholder:
    """A [IMAGE-REF: UIAO-FIG-NNN] reference."""
    document: Path
    canon_id: str
    line_number: int


@dataclass
class RegistryEntry:
    """Mutable view of one entry from core/canon/image-registry.yaml."""
    id: str
    slug: str
    status: str                 # draft | current | deprecated
    prompt_file: Path           # absolute
    file: Path                  # absolute
    prompt_sha256: str
    file_sha256: str
    version: str
    generator: str
    used_by: list[dict]         # [{document: str, placeholder_id: str}]
    raw: dict = field(default_factory=dict)  # full YAML dict, for roundtrip


@dataclass
class RunReport:
    """What happened during this pipeline run. Prints at the end."""
    placeholders_scanned: int = 0
    canon_refs_seen: int = 0
    canon_refs_missing: list[str] = field(default_factory=list)
    canon_refs_deprecated: list[str] = field(default_factory=list)
    doc_local_generated: int = 0
    doc_local_cached: int = 0
    doc_local_failed: int = 0
    auto_placeholders_skipped: int = 0   # Part-3 feature; skipped in v1
    sidecars_written: int = 0
    registry_used_by_updates: int = 0


# ──────────────────────────────────────────────────────────────
# Hash utilities. Provenance per UIAO_202 is anchored by two
# SHA-256 values: one over the prompt file text, one over the
# rendered PNG bytes. Single place in the module that computes
# them so the contract lives in one spot.
# ──────────────────────────────────────────────────────────────
def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    """SHA-256 of UTF-8 text. Normalizes to LF line endings first so
    Windows vs Unix checkouts don't produce false-positive drift."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return sha256_bytes(normalized.encode("utf-8"))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_prompt_file(path: Path) -> str:
    return sha256_text(path.read_text(encoding="utf-8"))


def _today_iso_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ──────────────────────────────────────────────────────────────
# Registry loader / writer. Operates on core/canon/image-registry.yaml.
# The `raw` dict on each RegistryEntry preserves original field
# ordering so re-emit doesn't shuffle the file.
# ──────────────────────────────────────────────────────────────
def _require_yaml() -> None:
    if yaml is None:
        print(
            "Error: PyYAML is required for harvest mode. Install with:\n"
            "  pip install PyYAML",
            file=sys.stderr,
        )
        sys.exit(2)


def load_registry() -> tuple[dict, list[RegistryEntry]]:
    """Read core/canon/image-registry.yaml.

    Returns ({}, []) if the registry is absent or has an empty `images:`
    list. That's the normal initial state after X1a merged.
    """
    _require_yaml()
    if not CANON_REGISTRY.exists():
        return ({}, [])
    with open(CANON_REGISTRY, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    raw_images = doc.get("images") or []
    entries: list[RegistryEntry] = []
    for row in raw_images:
        if not isinstance(row, dict):
            continue
        try:
            entries.append(
                RegistryEntry(
                    id=row["id"],
                    slug=row["slug"],
                    status=row.get("status", "draft"),
                    prompt_file=(REPO_ROOT / row["prompt_file"]).resolve(),
                    file=(REPO_ROOT / row["file"]).resolve(),
                    prompt_sha256=row.get("prompt_sha256", ""),
                    file_sha256=row.get("file_sha256", ""),
                    version=row.get("version", "1.0"),
                    generator=row.get("generator", ""),
                    used_by=list(row.get("used_by") or []),
                    raw=row,
                )
            )
        except KeyError as e:
            print(f"Warning: registry entry skipped — missing key {e}: {row!r}")
    return (doc, entries)


def save_registry(doc: dict, entries: list[RegistryEntry]) -> None:
    """Write back the registry. Updates each image entry's `used_by`,
    hashes, generator fields, and the top-level `updated` date."""
    _require_yaml()
    refreshed: list[dict] = []
    for e in entries:
        row = dict(e.raw) if e.raw else {}
        row["id"] = e.id
        row["slug"] = e.slug
        row["status"] = e.status
        row["version"] = e.version
        row["generator"] = e.generator
        row["prompt_file"] = str(e.prompt_file.relative_to(REPO_ROOT))
        row["prompt_sha256"] = e.prompt_sha256
        row["file"] = str(e.file.relative_to(REPO_ROOT))
        row["file_sha256"] = e.file_sha256
        row["used_by"] = list(e.used_by)
        refreshed.append(row)
    doc["images"] = refreshed
    doc["updated"] = _today_iso_date()
    with open(CANON_REGISTRY, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            doc, f,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=100,
        )


# ──────────────────────────────────────────────────────────────
# Sidecar JSON writer. Every rendered PNG gets a sibling
# <filename>.png.json. Authoritative metadata for doc-local
# images (not in the canonical registry); mirrors the registry
# entry for canon images so PNGs travel with their provenance.
# ──────────────────────────────────────────────────────────────
def write_sidecar(
    png_path: Path,
    *,
    document: Optional[Path],
    placeholder_id: str,
    canonical_id: Optional[str],
    slug: str,
    prompt_sha256: str,
    generator: str,
    file_sha256: str,
    version: str = "1.0",
    aspect: str = "16:9",
    used_by: Optional[list[str]] = None,
) -> Path:
    sidecar_path = png_path.with_suffix(png_path.suffix + ".json")
    payload = {
        "document": str(document.relative_to(REPO_ROOT)) if document else None,
        "placeholder_id": placeholder_id,
        "canonical_id": canonical_id,
        "slug": slug,
        "prompt_sha256": prompt_sha256,
        "generator": generator,
        "generated_at": _now_iso_utc(),
        "sha256": file_sha256,
        "version": version,
        "aspect": aspect,
        "used_by": used_by or [],
    }
    with open(sidecar_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    return sidecar_path


# ──────────────────────────────────────────────────────────────
# PNG tEXt metadata embedding. The PNG becomes self-describing —
# canonical ID + prompt hash + generator + timestamp survive when
# the image is detached (emailed, pasted into a deck, SharePoint).
# ──────────────────────────────────────────────────────────────
def embed_png_metadata(
    png_path: Path,
    *,
    canonical_id: Optional[str],
    prompt_sha256: str,
    generator: str,
    generated_at: str,
    version: str = "1.0",
    description: str = "",
) -> None:
    """Re-save the PNG with tEXt chunks. No-op if Pillow isn't installed."""
    try:
        from PIL import Image, PngImagePlugin
    except ImportError:
        print("  Warning: Pillow not installed; skipping PNG tEXt metadata.")
        return
    try:
        image = Image.open(png_path)
        meta = PngImagePlugin.PngInfo()
        if canonical_id:
            meta.add_text("UIAO:canonical_id", canonical_id)
        meta.add_text("UIAO:prompt_sha256", prompt_sha256)
        meta.add_text("UIAO:generator", generator)
        meta.add_text("UIAO:generated_at", generated_at)
        meta.add_text("UIAO:version", version)
        if description:
            meta.add_text("Description", description)
        image.save(png_path, pnginfo=meta)
    except Exception as e:
        print(f"  Warning: couldn't embed PNG metadata: {e}")


# ──────────────────────────────────────────────────────────────
# Placeholder scanner. Walks .qmd / .md under SCAN_ROOTS, extracts
# all three placeholder types. Skips _site/, _freeze/, .quarto/,
# node_modules/, __pycache__/ and anything under EXCLUDE_PATH_PARTS.
# ──────────────────────────────────────────────────────────────
def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDE_PATH_PARTS for part in path.parts)


def iter_source_files() -> list[Path]:
    """Yield every .qmd / .md file under SCAN_ROOTS, filtered for excludes."""
    seen: set[Path] = set()
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for ext in SCAN_EXTS:
            for p in root.rglob(f"*{ext}"):
                if _is_excluded(p):
                    continue
                resolved = p.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
    # Stable order for reproducible runs.
    return sorted(seen)


def scan_placeholders(
    files: list[Path],
) -> tuple[list[DocLocalPlaceholder], list[CanonRefPlaceholder]]:
    """Extract both placeholder types from every file. Returns
    (doc-local list, canon-ref list). Both are ordered stably by
    (document path, line number)."""
    locals_: list[DocLocalPlaceholder] = []
    refs: list[CanonRefPlaceholder] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Track line numbers by pre-computing newline offsets once.
        line_starts = [0]
        for idx, ch in enumerate(text):
            if ch == "\n":
                line_starts.append(idx + 1)

        def line_of(offset: int) -> int:
            # bisect equivalent, small loop is fine at this scale
            lo, hi = 0, len(line_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_starts[mid] <= offset:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1

        for m in PLACEHOLDER_LOCAL_RE.finditer(text):
            body = m.group("body").strip()
            # Skip matches that are actually [IMAGE-REF: ...] (belt & suspenders
            # since the ref regex handles them — but our local regex kind='IMAGE'
            # could match [IMAGE-REF: ...] structurally, we want that filtered).
            if body.upper().startswith("UIAO-FIG-"):
                continue
            kind = m.group("kind")
            placeholder_id = f"{kind}-{m.group('num')}"
            is_auto = body.strip().upper() == AUTO_MARKER
            locals_.append(
                DocLocalPlaceholder(
                    document=path,
                    placeholder_id=placeholder_id,
                    body=body,
                    line_number=line_of(m.start()),
                    is_auto=is_auto,
                )
            )

        for m in PLACEHOLDER_REF_RE.finditer(text):
            refs.append(
                CanonRefPlaceholder(
                    document=path,
                    canon_id=m.group("id"),
                    line_number=line_of(m.start()),
                )
            )

    locals_.sort(key=lambda p: (str(p.document), p.line_number))
    refs.sort(key=lambda p: (str(p.document), p.line_number))
    return (locals_, refs)


# ──────────────────────────────────────────────────────────────
# Doc-local output path resolver. Given the owning document and
# the placeholder ID, produces the on-disk PNG path that the
# rendered image will occupy.
#
# Example:
#   document       = docs/publications/01-executive-brief/UIAO-Executive-Brief.qmd
#   placeholder_id = IMAGE-03
#   slug           = monitoring-loop
#   → docs/publications/01-executive-brief/images/doc-01-image-03-monitoring-loop.png
# ──────────────────────────────────────────────────────────────
def _slugify(text: str, maxlen: int = 40) -> str:
    """Derive a kebab-case slug from free-form text (e.g., the first
    line of the prompt). Used for filenames when no explicit slug is
    given. Keeps [a-z0-9-] only; collapses whitespace to '-'."""
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"[\s-]+", "-", s).strip("-")
    return (s[:maxlen] or "image").rstrip("-")


def doc_local_output_path(
    document: Path, placeholder_id: str, slug: str
) -> Path:
    """Compute the sibling images/ path for a doc-local image."""
    doc_dir = document.parent
    images_dir = doc_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    doc_slug = _slugify(document.stem, maxlen=32)
    return images_dir / f"{doc_slug}-{placeholder_id.lower()}-{slug}.png"


# ──────────────────────────────────────────────────────────────
# Image generator. Wraps the Gemini client call. Centralized so
# error handling, retry, and rate limiting have one home.
# ──────────────────────────────────────────────────────────────
def generate_image(
    client, prompt_text: str, output_path: Path, model: str = MODEL
) -> bool:
    """Generate a single image from a prompt; save to output_path.
    Returns True on success. Prints diagnostic text responses on partial
    failure (e.g., the model replied with refusal text instead of an
    image)."""
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
        print("  Warning: No image data returned for this prompt.")
        return False
    except Exception as e:
        print(f"  Error generating image: {e}")
        return False
