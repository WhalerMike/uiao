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
SCRIPT_DIR = Path(__file__).resolve().parent  # docs/
REPO_ROOT = Path(os.environ.get("UIAO_REPO_ROOT") or SCRIPT_DIR.parent)
PROMPTS_FILE = SCRIPT_DIR / "prompts.json"
LEGACY_OUTPUT_DIR = SCRIPT_DIR / "images"
CANONICAL_OUTPUT_DIR = SCRIPT_DIR / "images" / "canonical"
CANON_REGISTRY = REPO_ROOT / "src" / "uiao" / "canon" / "image-registry.yaml"
CANON_PROMPTS_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "image-prompts"
MANIFEST_PATH = SCRIPT_DIR / "images" / ".image-manifest.json"
MANIFEST_SCHEMA_VERSION = "1.0.0"
MODEL = "gemini-2.5-flash-image"
DELAY_SECONDS = 2.0
SCAN_ROOTS = [
    REPO_ROOT / "docs",
    REPO_ROOT / "src" / "uiao" / "canon" / "specs",
    REPO_ROOT / "src" / "uiao" / "canon" / "adr",
]
SCAN_EXTS = (".qmd", ".md")
EXCLUDE_PATH_PARTS = {
    "_site",
    "_freeze",
    ".quarto",
    "node_modules",
    ".venv",
    "__pycache__",
    "session-logs",  # working dev logs, not rendered site content
    "inbox",  # raw intake drops; may contain example placeholders
}
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

    document: Path  # repo-relative-ish; resolved Path()
    placeholder_id: str  # e.g. "IMAGE-03"
    body: str  # raw text between ':' and ']'
    line_number: int  # 1-indexed
    is_auto: bool  # True iff body == "AUTO"


@dataclass(frozen=True)
class CanonRefPlaceholder:
    """A [IMAGE-REF: UIAO-FIG-NNN] reference."""

    document: Path
    canon_id: str
    line_number: int


@dataclass
class RegistryEntry:
    """Mutable view of one entry from src/uiao/canon/image-registry.yaml."""

    id: str
    slug: str
    status: str  # draft | current | deprecated
    prompt_file: Path  # absolute
    file: Path  # absolute
    prompt_sha256: str
    file_sha256: str
    version: str
    generator: str
    used_by: list[dict]  # [{document: str, placeholder_id: str}]
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
    auto_placeholders_skipped: int = 0  # Part-3 feature; skipped in v1
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
# Registry loader / writer. Operates on src/uiao/canon/image-registry.yaml.
# The `raw` dict on each RegistryEntry preserves original field
# ordering so re-emit doesn't shuffle the file.
# ──────────────────────────────────────────────────────────────
def _require_yaml() -> None:
    if yaml is None:
        print(
            "Error: PyYAML is required for harvest mode. Install with:\n  pip install PyYAML",
            file=sys.stderr,
        )
        sys.exit(2)


def load_registry() -> tuple[dict, list[RegistryEntry]]:
    """Read src/uiao/canon/image-registry.yaml.

    Returns ({}, []) if the registry is absent or has an empty `images:`
    list. That's the normal initial state after X1a merged.
    """
    _require_yaml()
    if not CANON_REGISTRY.exists():
        return ({}, [])
    with open(CANON_REGISTRY, encoding="utf-8") as f:
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
            doc,
            f,
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


def _fenced_code_ranges(text: str) -> list[tuple[int, int]]:
    """Return [(start, end), ...] byte ranges of fenced code blocks
    (delimited by ``` lines). Placeholders inside these ranges are
    treated as illustrative syntax, not harvested."""
    ranges: list[tuple[int, int]] = []
    offset = 0
    in_fence = False
    fence_start = 0
    for line in text.split("\n"):
        line_bytes = len(line) + 1  # +1 for the newline we split on
        stripped = line.lstrip()
        if stripped.startswith("```"):
            if not in_fence:
                fence_start = offset
                in_fence = True
            else:
                ranges.append((fence_start, offset + line_bytes))
                in_fence = False
        offset += line_bytes
    if in_fence:  # unclosed fence — treat the rest of the file as code
        ranges.append((fence_start, len(text)))
    return ranges


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

        def line_of(offset: int, line_starts: list[int] = line_starts) -> int:
            lo, hi = 0, len(line_starts) - 1
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if line_starts[mid] <= offset:
                    lo = mid
                else:
                    hi = mid - 1
            return lo + 1

        # Compute fenced-code ranges so placeholders inside ``` ... ``` are
        # treated as illustrative, not harvested.
        fence_ranges = _fenced_code_ranges(text)

        def in_fence(offset: int, fence_ranges: list = fence_ranges) -> bool:
            for start, end in fence_ranges:
                if start <= offset < end:
                    return True
            return False

        for m in PLACEHOLDER_LOCAL_RE.finditer(text):
            if in_fence(m.start()):
                continue
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
            if in_fence(m.start()):
                continue
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


def doc_local_output_path(document: Path, placeholder_id: str, slug: str) -> Path:
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
def generate_image(client, prompt_text: str, output_path: Path, model: str = MODEL) -> bool:
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


# ──────────────────────────────────────────────────────────────
# Canon-reference resolver. For every [IMAGE-REF: UIAO-FIG-NNN],
# verify the entry exists and is `current`; update the entry's
# `used_by` list to record this document reference.
# ──────────────────────────────────────────────────────────────
def resolve_canon_refs(
    refs: list[CanonRefPlaceholder],
    entries: list[RegistryEntry],
    report: RunReport,
) -> None:
    """Validate each canon reference; mutate entries' used_by in place.
    Does NOT write the registry — the caller decides when to persist."""
    entries_by_id = {e.id: e for e in entries}
    for ref in refs:
        report.canon_refs_seen += 1
        entry = entries_by_id.get(ref.canon_id)
        if entry is None:
            report.canon_refs_missing.append(
                f"{ref.document.relative_to(REPO_ROOT)}:{ref.line_number} → {ref.canon_id}"
            )
            continue
        if entry.status == "deprecated":
            report.canon_refs_deprecated.append(
                f"{ref.document.relative_to(REPO_ROOT)}:{ref.line_number} → {ref.canon_id} (deprecated)"
            )
        # Update used_by (append if this document/placeholder pair isn't there)
        doc_rel = str(ref.document.relative_to(REPO_ROOT))
        # We don't know placeholder_id from a canon-ref (it's just UIAO-FIG-NNN
        # inline; the placeholder_id is the ref itself). Record the
        # document path; placeholder_id defaults to IMAGE-REF for refs.
        new_entry = {"document": doc_rel, "placeholder_id": "IMAGE-REF"}
        if new_entry not in entry.used_by:
            entry.used_by.append(new_entry)
            report.registry_used_by_updates += 1


# ──────────────────────────────────────────────────────────────
# Doc-local processor. For every [IMAGE-NN: <prompt>] placeholder
# with a real prompt body (not AUTO), decide whether to regenerate
# (cache miss) or skip (cache hit by sidecar prompt_sha256). Writes
# sidecar + PNG tEXt on successful generation.
# ──────────────────────────────────────────────────────────────
def process_doc_local_placeholders(
    placeholders: list[DocLocalPlaceholder],
    client,
    report: RunReport,
    dry_run: bool = False,
) -> None:
    for p in placeholders:
        # AUTO placeholders are a Part-3 feature (pipeline drafts the prompt
        # via a secondary Gemini call). Skipped in this v1 pipeline; the
        # author is expected to provide Type A or Type C handling manually.
        if p.is_auto:
            report.auto_placeholders_skipped += 1
            continue

        slug = _slugify(p.body.split(".")[0], maxlen=32) or "image"
        output_path = doc_local_output_path(p.document, p.placeholder_id, slug)
        sidecar_path = output_path.with_suffix(output_path.suffix + ".json")

        # Cache-by-hash: if the prompt hasn't changed AND the PNG exists,
        # skip the API call. Drift-free, cost-free re-runs.
        prompt_sha = sha256_text(p.body)
        if sidecar_path.exists() and output_path.exists() and not dry_run:
            try:
                with open(sidecar_path, encoding="utf-8") as f:
                    existing = json.load(f)
                if existing.get("prompt_sha256") == prompt_sha:
                    report.doc_local_cached += 1
                    print(f"  [cache] {p.document.relative_to(REPO_ROOT)}:{p.placeholder_id} → {output_path.name}")
                    continue
            except (OSError, json.JSONDecodeError):
                pass

        if dry_run:
            print(f"  [dry-run] {p.document.relative_to(REPO_ROOT)}:{p.placeholder_id} → {output_path.name}")
            continue

        print(f"  Generating: {p.document.relative_to(REPO_ROOT)}:{p.placeholder_id} → {output_path.name}")
        ok = generate_image(client, p.body, output_path)
        if not ok:
            report.doc_local_failed += 1
            continue

        file_sha = sha256_file(output_path)
        now = _now_iso_utc()
        write_sidecar(
            output_path,
            document=p.document,
            placeholder_id=p.placeholder_id,
            canonical_id=None,
            slug=slug,
            prompt_sha256=prompt_sha,
            generator=MODEL,
            file_sha256=file_sha,
        )
        embed_png_metadata(
            output_path,
            canonical_id=None,
            prompt_sha256=prompt_sha,
            generator=MODEL,
            generated_at=now,
            description=p.body[:120],
        )
        report.doc_local_generated += 1
        report.sidecars_written += 1
        time.sleep(DELAY_SECONDS)


# ──────────────────────────────────────────────────────────────
# Legacy prompts.json path — preserved so existing uiao-pipeline-test
# and similar entries still generate without edits.
# ──────────────────────────────────────────────────────────────
def load_legacy_prompts(prompts_file: Path) -> list[dict]:
    if not prompts_file.exists():
        return []
    with open(prompts_file, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def process_legacy_prompts(prompts: list[dict], client, report: RunReport, dry_run: bool = False) -> None:
    LEGACY_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for i, item in enumerate(prompts, 1):
        prompt_id = item.get("id", f"legacy-{i}")
        filename = item.get("filename", f"{prompt_id}.png")
        prompt_text = item.get("prompt", "")
        output_path = LEGACY_OUTPUT_DIR / filename
        if dry_run:
            print(f"  [dry-run legacy] {prompt_id} → {filename}")
            continue
        print(f"  [legacy] {prompt_id} → {filename}")
        if generate_image(client, prompt_text, output_path):
            report.doc_local_generated += 1
        else:
            report.doc_local_failed += 1
        if i < len(prompts):
            time.sleep(DELAY_SECONDS)


# ──────────────────────────────────────────────────────────────
# Main orchestrator.
# ──────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate UIAO images from placeholders + prompts (Gemini Nano Banana).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scan and report what would happen; make no API calls.",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Scan placeholders and print the report; skip all generation.",
    )
    parser.add_argument(
        "--mode",
        choices=("both", "legacy", "harvest"),
        default="both",
        help="Input mode. 'both' (default) runs legacy prompts.json AND harvest; "
        "'legacy' only reads prompts.json; 'harvest' only scans .qmd/.md.",
    )
    args = parser.parse_args()

    print(f"Repo root:        {REPO_ROOT}")
    print(f"Script dir:       {SCRIPT_DIR}")
    print(f"Canon registry:   {CANON_REGISTRY}")
    print()

    report = RunReport()

    # Always scan — cheap, informs the report, and enables canon-ref
    # validation even in --scan-only mode.
    files = iter_source_files()
    print(f"Scanning {len(files)} .qmd / .md files under SCAN_ROOTS...")
    locals_, refs = scan_placeholders(files)
    report.placeholders_scanned = len(locals_) + len(refs)
    print(f"Found {len(locals_)} doc-local placeholder(s) and {len(refs)} canon-ref placeholder(s).")

    # Load registry (may be empty — that's fine for v1)
    registry_doc, entries = load_registry()
    if entries:
        print(f"Loaded {len(entries)} registry entrie(s).")
    else:
        print("Registry is empty (expected at X1a initial state).")

    # Resolve canon refs — mutates entries[].used_by in place
    resolve_canon_refs(refs, entries, report)

    # Short-circuit modes that don't generate
    if args.scan_only:
        manifest = build_manifest(entries, refs)
        write_manifest(manifest)
        print(f"\nManifest written to {_repo_rel(MANIFEST_PATH)}")
        _print_report(report)
        return 0 if not report.canon_refs_missing else 1

    # API key is required from here on (unless dry-run)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: GEMINI_API_KEY is not set in the environment.", file=sys.stderr)
        return 2

    client = None
    if not args.dry_run:
        from google import genai

        client = genai.Client(api_key=api_key)

    if args.mode in ("both", "legacy"):
        legacy = load_legacy_prompts(PROMPTS_FILE)
        if legacy:
            print(f"\nProcessing {len(legacy)} legacy prompt(s) from prompts.json...")
            process_legacy_prompts(legacy, client, report, dry_run=args.dry_run)

    if args.mode in ("both", "harvest"):
        if locals_:
            print(f"\nProcessing {len(locals_)} doc-local placeholder(s)...")
            process_doc_local_placeholders(
                locals_,
                client,
                report,
                dry_run=args.dry_run,
            )
        else:
            print("\nNo doc-local placeholders found. Skipping harvest generation.")

    # Persist used_by updates (only if the registry had entries and we
    # actually made changes). Never overwrite an empty registry.
    if entries and report.registry_used_by_updates > 0 and not args.dry_run:
        save_registry(registry_doc, entries)
        print(f"\nRegistry updated: {report.registry_used_by_updates} used_by addition(s).")

    # Always rebuild the manifest at the end — cheap, deterministic,
    # and gives downstream consumers (editors, LFS audit, render) one
    # authoritative file to consult.
    manifest = build_manifest(entries, refs)
    write_manifest(manifest)
    print(f"\nManifest written to {_repo_rel(MANIFEST_PATH)}")

    _print_report(report)
    return 0 if report.doc_local_failed == 0 and not report.canon_refs_missing else 1


# ──────────────────────────────────────────────────────────────
# Top-level manifest. Aggregates every sidecar on disk plus the
# canon-ref resolution from this run into one discoverable JSON
# document at docs/images/.image-manifest.json. Consumers: editor
# integrations, LFS audits, the Quarto render pipeline.
# ──────────────────────────────────────────────────────────────
def _repo_rel(path: Path) -> str:
    """Best-effort repo-relative path (POSIX separators) for stable output."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _iter_sidecars() -> list[Path]:
    """Find every *.png.json sidecar under the scanned doc trees
    plus the canonical image directory. Stable-sorted output."""
    roots = [REPO_ROOT / "docs", CANONICAL_OUTPUT_DIR]
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.png.json"):
            if _is_excluded(p):
                continue
            resolved = p.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
    return sorted(seen)


def _read_sidecar(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_manifest(
    registry_entries: list[RegistryEntry],
    canon_refs: list[CanonRefPlaceholder],
) -> dict:
    """Assemble the top-level manifest document.

    The manifest is a pure aggregation — running it repeatedly produces
    the same output given the same on-disk state. It never calls an API.
    """
    # Doc-local entries come from sidecar files on disk.
    doc_local: list[dict] = []
    for sidecar_path in _iter_sidecars():
        payload = _read_sidecar(sidecar_path)
        if not payload:
            continue
        image_path = sidecar_path.with_suffix("")
        if image_path.suffix != ".png":
            continue
        doc_local.append(
            {
                "document": payload.get("document"),
                "placeholder_id": payload.get("placeholder_id"),
                "canonical_id": payload.get("canonical_id"),
                "image_file": _repo_rel(image_path),
                "sidecar": _repo_rel(sidecar_path),
                "prompt_sha256": payload.get("prompt_sha256"),
                "sha256": payload.get("sha256"),
                "generator": payload.get("generator"),
                "generated_at": payload.get("generated_at"),
                "version": payload.get("version"),
                "aspect": payload.get("aspect"),
            }
        )

    # Canon-ref entries come from the current scan (they're cross-document
    # links, not disk artifacts).
    refs_by_id: dict[str, RegistryEntry] = {e.id: e for e in registry_entries}
    canon_entries: list[dict] = []
    for ref in canon_refs:
        entry = refs_by_id.get(ref.canon_id)
        canon_entries.append(
            {
                "document": _repo_rel(ref.document),
                "placeholder_id": f"IMAGE-REF:{ref.canon_id}",
                "canon_id": ref.canon_id,
                "file": _repo_rel(entry.file) if entry else None,
                "status": entry.status if entry else "missing",
                "line_number": ref.line_number,
            }
        )

    # Registry snapshot — small, cheap, and lets consumers verify canon
    # state without re-parsing the YAML.
    status_counts: dict[str, int] = {}
    for e in registry_entries:
        status_counts[e.status] = status_counts.get(e.status, 0) + 1

    unique_canon = sorted({c["canon_id"] for c in canon_entries if c["canon_id"]})
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at": _now_iso_utc(),
        "registry": {
            "path": _repo_rel(CANON_REGISTRY),
            "total_entries": len(registry_entries),
            "by_status": dict(sorted(status_counts.items())),
        },
        "doc_local": sorted(
            doc_local,
            key=lambda d: (d.get("document") or "", d.get("placeholder_id") or ""),
        ),
        "canon_refs": sorted(
            canon_entries,
            key=lambda d: (d.get("document") or "", d.get("line_number") or 0),
        ),
        "stats": {
            "doc_local_count": len(doc_local),
            "canon_refs_count": len(canon_entries),
            "unique_canon_images_referenced": len(unique_canon),
            "canon_refs_missing_count": sum(
                1 for c in canon_entries if c["status"] == "missing"
            ),
        },
    }


def write_manifest(manifest: dict, path: Path = MANIFEST_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=False)
        f.write("\n")
    return path


def _print_report(report: RunReport) -> None:
    print("\n=== Run report ===")
    print(f"Placeholders scanned:    {report.placeholders_scanned}")
    print(f"Canon refs seen:         {report.canon_refs_seen}")
    if report.canon_refs_missing:
        print(f"Canon refs MISSING:      {len(report.canon_refs_missing)}")
        for line in report.canon_refs_missing[:10]:
            print(f"  - {line}")
        if len(report.canon_refs_missing) > 10:
            print(f"  ... and {len(report.canon_refs_missing) - 10} more")
    if report.canon_refs_deprecated:
        print(f"Canon refs DEPRECATED:   {len(report.canon_refs_deprecated)}")
        for line in report.canon_refs_deprecated[:10]:
            print(f"  - {line}")
    print(f"Doc-local generated:     {report.doc_local_generated}")
    print(f"Doc-local cached (hit):  {report.doc_local_cached}")
    print(f"Doc-local failed:        {report.doc_local_failed}")
    print(f"AUTO placeholders (v2):  {report.auto_placeholders_skipped}")
    print(f"Sidecars written:        {report.sidecars_written}")
    print(f"Registry used_by adds:   {report.registry_used_by_updates}")


if __name__ == "__main__":
    sys.exit(main())
