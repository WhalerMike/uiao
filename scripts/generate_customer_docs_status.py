#!/usr/bin/env python3
"""Regenerate the per-document status surface for customer-documents/ROADMAP.qmd.

Walks ``docs/customer-documents/**/*.qmd``, classifies each file by line
count and frontmatter shape, checks image-reference integrity, and emits
a Markdown report that the ROADMAP includes via Quarto's
``{{< include >}}`` shortcode.

The ROADMAP previously hand-maintained a phased "Stub / Partial / Authored"
status grid that fell out of sync as authoring landed. This generator
replaces that grid with a regenerable surface so the published roadmap
matches the tree.

Classification heuristic
------------------------
Line count is used as a proxy for authoring depth. The thresholds were
calibrated against the actual 2026-05 customer-documents tree (frontmatter
stubs land around 25-35 lines; substantive briefs at 80-150; long-form
whitepapers / narratives at 250+).

  Stub          ≤ 40 lines     frontmatter + one "in preparation" callout
  Brief         41–99 lines    short landing page or one-page brief
  Authored      100–249 lines  full document body
  Substantial   ≥ 250 lines    long-form (whitepaper, narrative, runbook)

Section ``index.qmd`` files are classified separately as **Navigation hub**.
They are deliberately thin nav surfaces, not authoring backlog. Calling
them "stubs" was the original bug in the hand-maintained roadmap.

CI / drift
----------
The output is committed to the tree so a CI step can re-run the script
and ``git diff --exit-code`` to detect customer-documents added (or
removed) without a corresponding status refresh. See
``.github/workflows/customer-docs-status.yml``.

Usage
-----
::

    python scripts/generate_customer_docs_status.py \\
        --output docs/data/customer-documents-status.md

Or to stdout::

    python scripts/generate_customer_docs_status.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CUSTOMER_DOCS = REPO_ROOT / "docs" / "customer-documents"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "data" / "customer-documents-status.md"

GITHUB_BLOB_BASE = "https://github.com/WhalerMike/uiao/blob/main"

# Files that live under customer-documents/ but are not authoring units:
# the roadmap itself, the document index, and any auto-generated artifact
# included via shortcode.
EXCLUDED_NAMES = {"ROADMAP.qmd", "document-index.qmd"}

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(?P<body>.*?)\n---\s*\n", re.DOTALL)

# Markdown image refs: ![alt](src ...attrs)
# We strip everything after the first whitespace inside the parens to drop
# Quarto's {#fig-...} / width= attributes.
_IMAGE_REF_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DocEntry:
    """One customer-document with its classification and integrity signals."""

    rel_path: Path
    section: str
    lines: int
    classification: str
    has_frontmatter: bool
    aspirational: bool
    image_refs_total: int
    image_refs_missing: int
    missing_image_refs: list[str] = field(default_factory=list)
    is_index: bool = False


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(lines: int, is_index: bool) -> str:
    """Bucket a document into one of five classifications.

    See module docstring for the rationale behind the line-count thresholds.
    ``index.qmd`` files are classified as Navigation hubs regardless of size
    — they are nav surfaces, not authoring units.
    """
    if is_index:
        return "Navigation hub"
    if lines <= 40:
        return "Stub"
    if lines < 100:
        return "Brief"
    if lines < 250:
        return "Authored"
    return "Substantial"


CLASSIFICATION_ORDER = ["Stub", "Brief", "Authored", "Substantial", "Navigation hub"]


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------


def _section_of(rel: Path) -> str:
    """Top-level directory under ``customer-documents/``.

    For ``docs/customer-documents/architecture-series/foo.qmd`` returns
    ``architecture-series``. For files directly under
    ``customer-documents/`` returns ``(root)``.
    """
    parts = rel.parts
    # parts[0] = 'docs', parts[1] = 'customer-documents', parts[2] = section
    if len(parts) >= 4:
        return parts[2]
    return "(root)"


def _parse_frontmatter(text: str) -> dict | None:
    """Return the parsed YAML frontmatter as a dict, or None if absent.

    Malformed YAML returns None — the metadata-validator CI gate catches
    that separately; this script just reports "no frontmatter detected"
    rather than blowing up.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        loaded = yaml.safe_load(m.group("body"))
    except yaml.YAMLError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _image_refs(path: Path, text: str) -> tuple[int, list[str]]:
    """Count Markdown image refs and return any that resolve to missing files.

    Skips absolute URLs (``http://``, ``https://``, ``/``-rooted). All other
    refs are resolved relative to the file's parent directory, matching
    Quarto's default behavior.
    """
    total = 0
    missing: list[str] = []
    for m in _IMAGE_REF_RE.finditer(text):
        # First token inside the parens — strip Quarto attribute tail.
        ref = m.group(1).split()[0].strip()
        if not ref:
            continue
        if ref.startswith(("http://", "https://", "data:", "/")):
            continue
        total += 1
        target = (path.parent / ref).resolve()
        if not target.exists():
            missing.append(ref)
    return total, missing


def collect_entries() -> list[DocEntry]:
    """Walk customer-documents/ and produce one DocEntry per .qmd."""
    entries: list[DocEntry] = []
    for path in sorted(CUSTOMER_DOCS.rglob("*.qmd")):
        if path.name in EXCLUDED_NAMES:
            continue
        rel = path.relative_to(REPO_ROOT)
        text = path.read_text(encoding="utf-8")
        # Count newlines + handle trailing-newline-or-not so the line count
        # matches `wc -l`-style intuition.
        lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        is_index = path.name == "index.qmd"
        fm = _parse_frontmatter(text)
        aspirational = bool(fm.get("aspirational")) if fm else False
        total, missing = _image_refs(path, text)
        entries.append(
            DocEntry(
                rel_path=rel,
                section=_section_of(rel),
                lines=lines,
                classification=classify(lines, is_index),
                has_frontmatter=fm is not None,
                aspirational=aspirational,
                image_refs_total=total,
                image_refs_missing=len(missing),
                missing_image_refs=missing,
                is_index=is_index,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _blob_link(rel_path: Path) -> str:
    posix = rel_path.as_posix()
    return f"[`{posix}`]({GITHUB_BLOB_BASE}/{posix})"


def _section_summary_table(entries: list[DocEntry]) -> str:
    """Per-section counts by classification."""
    by_section: dict[str, Counter] = defaultdict(Counter)
    for e in entries:
        by_section[e.section][e.classification] += 1

    sections = sorted(by_section)
    lines = [
        "| Section | Stub | Brief | Authored | Substantial | Nav hubs | Total |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    grand = Counter()
    for s in sections:
        c = by_section[s]
        total = sum(c.values())
        grand.update(c)
        lines.append(
            f"| `{s}/` | {c['Stub']} | {c['Brief']} | {c['Authored']} "
            f"| {c['Substantial']} | {c['Navigation hub']} | {total} |"
        )
    grand_total = sum(grand.values())
    lines.append(
        f"| **Total** | **{grand['Stub']}** | **{grand['Brief']}** "
        f"| **{grand['Authored']}** | **{grand['Substantial']}** "
        f"| **{grand['Navigation hub']}** | **{grand_total}** |"
    )
    return "\n".join(lines)


def _section_detail_table(section: str, entries: list[DocEntry]) -> str:
    """Per-file detail for one section."""
    relevant = [e for e in entries if e.section == section]
    relevant.sort(key=lambda e: e.rel_path.as_posix())
    lines = [
        "| Document | Lines | Classification | Frontmatter | Images | Notes |",
        "|---|---:|---|:---:|:---:|---|",
    ]
    for e in relevant:
        fm_marker = "✅" if e.has_frontmatter else "—"
        if e.image_refs_total == 0:
            img_cell = "—"
        elif e.image_refs_missing:
            img_cell = f"⚠️ {e.image_refs_total - e.image_refs_missing}/{e.image_refs_total}"
        else:
            img_cell = f"{e.image_refs_total}/{e.image_refs_total}"
        notes_bits: list[str] = []
        if e.aspirational:
            notes_bits.append("aspirational")
        if e.image_refs_missing:
            notes_bits.append(f"{e.image_refs_missing} missing image ref(s)")
        if not e.has_frontmatter and not e.is_index:
            notes_bits.append("no frontmatter")
        notes = "; ".join(notes_bits) or "—"
        lines.append(
            f"| {_blob_link(e.rel_path)} | {e.lines} | {e.classification} | {fm_marker} | {img_cell} | {notes} |"
        )
    return "\n".join(lines)


def _health_section(entries: list[DocEntry]) -> str:
    """Surface broken image refs and other integrity warnings."""
    out: list[str] = []
    missing_images = [e for e in entries if e.image_refs_missing]
    no_frontmatter = [e for e in entries if not e.has_frontmatter and not e.is_index]

    if not missing_images and not no_frontmatter:
        out.append("All customer-documents pass image-ref and frontmatter integrity checks.")
        return "\n".join(out)

    if missing_images:
        out.append("### Documents with missing image references")
        out.append("")
        out.append(
            "Each row points to a `.qmd` that references one or more PNGs that "
            "are not present on disk. Regenerate via `python scripts/generate_images.py` "
            "after adding the missing prompts to `docs/data/image-registry.yaml`."
        )
        out.append("")
        out.append("| Document | Missing references |")
        out.append("|---|---|")
        for e in missing_images:
            joined = "<br>".join(f"`{ref}`" for ref in e.missing_image_refs)
            out.append(f"| {_blob_link(e.rel_path)} | {joined} |")
        out.append("")

    if no_frontmatter:
        out.append("### Non-index documents missing YAML frontmatter")
        out.append("")
        out.append(
            "Every authored customer-document must carry YAML frontmatter per the "
            "Authoring contract in `ROADMAP.qmd` (`metadata-validator` CI gate). "
            "These pages currently do not:"
        )
        out.append("")
        out.append("| Document | Lines |")
        out.append("|---|---:|")
        for e in no_frontmatter:
            out.append(f"| {_blob_link(e.rel_path)} | {e.lines} |")
        out.append("")

    return "\n".join(out)


def render(entries: list[DocEntry]) -> str:
    """Render the full Markdown report."""
    out: list[str] = []
    out.append("<!-- GENERATED by scripts/generate_customer_docs_status.py — do not hand-edit. -->")
    out.append(
        "<!-- Regenerate: python scripts/generate_customer_docs_status.py "
        "--output docs/data/customer-documents-status.md -->"
    )
    out.append("")
    out.append(f"**{len(entries)} customer-documents tracked** (excluding `ROADMAP.qmd` and `document-index.qmd`).")
    out.append("")
    out.append("## Status by section")
    out.append("")
    out.append(_section_summary_table(entries))
    out.append("")

    out.append("## Section detail")
    out.append("")
    sections = sorted({e.section for e in entries})
    for s in sections:
        out.append(f"### `{s}/`")
        out.append("")
        out.append(_section_detail_table(s, entries))
        out.append("")

    out.append("## Integrity")
    out.append("")
    out.append(_health_section(entries))
    out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Write output to this path (default: stdout). Conventional location: "
            f"{DEFAULT_OUTPUT.relative_to(REPO_ROOT)}"
        ),
    )
    args = parser.parse_args(argv)

    entries = collect_entries()
    rendered = render(entries)

    if args.output is None:
        sys.stdout.write(rendered)
    else:
        out_path = args.output.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        try:
            shown = out_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = out_path
        print(f"wrote {len(entries)} entries to {shown}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
