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
