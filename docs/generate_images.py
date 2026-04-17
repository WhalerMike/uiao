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
