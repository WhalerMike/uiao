#!/usr/bin/env python3
"""Regenerate the per-document status table for substrate-status.qmd.

Reads `src/uiao/canon/document-registry.yaml` and, for each registered
UIAO_NNN document, opens the referenced canonical artifact, parses its
YAML frontmatter, and emits a Markdown table that lists every registered
document with the canon-derived metadata available today.

The substrate-status.qmd page hand-curates a richer Spec/Impl/Deployed
classification for the 38 documents enumerated as of 2026-04-17. That
hand-curation cannot be regenerated mechanically — there is no
deterministic signal in canon that distinguishes "spec only" from "impl
shipped" without a per-document mapping table. What this script
*does* close is the "completeness" gap: it guarantees every registered
document appears in the rendered status surface, with the canon-derived
fields (title, status, classification, version, updated_at) filled in.

The hand-curated impl/deployed columns remain a per-document audit
responsibility, but they are now layered on top of an authoritative,
regenerable bones table rather than being the bones themselves.

Usage
-----
    python scripts/generate_substrate_status_table.py \\
        > docs/data/substrate-document-status.md

Or write directly:
    python scripts/generate_substrate_status_table.py \\
        --output docs/data/substrate-document-status.md

CI / drift
----------
The output is committed to the tree so a `scripts/check_substrate_status.sh`
CI helper can re-run the script and `git diff --exit-code` to detect
documents added without a corresponding status-table refresh.

Output format
-------------
GitHub-flavored Markdown with three sections:

1. Summary counts (total registered, by status).
2. Per-range tables (UIAO_001-099, UIAO_100-199, UIAO_200-299).
3. Documents with frontmatter parse failures (so authors can fix them).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "src" / "uiao" / "canon" / "document-registry.yaml"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "data" / "substrate-document-status.md"

GITHUB_BLOB_BASE = "https://github.com/WhalerMike/uiao/blob/main"


@dataclass
class DocEntry:
    """One registered UIAO_NNN document with parsed canonical metadata."""

    uiao_id: str
    registry_path: str
    registry_title: str
    registry_status: str
    registry_classification: str
    frontmatter_status: str | None = None
    frontmatter_version: str | None = None
    frontmatter_updated_at: str | None = None
    frontmatter_owner: str | None = None
    frontmatter_boundary: str | None = None
    parse_error: str | None = None
    path_exists: bool = True


def load_registry() -> list[dict[str, Any]]:
    """Load the document registry. Errors out loudly if the file is malformed
    — the registry is canonical, so we don't paper over schema drift."""
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict) or "documents" not in data:
        raise SystemExit("document-registry.yaml missing 'documents' key")
    return data["documents"]


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<body>.*?)\n---\s*\n",
    re.DOTALL,
)


def parse_frontmatter(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Parse canonical metadata from a registered document.

    Two shapes are supported:

    1. Markdown / Quarto file with ``---\\n...\\n---`` YAML frontmatter at
       the top. The frontmatter body is parsed and returned.
    2. YAML file (``.yaml`` / ``.yml``) where the entire body is YAML.
       The top-level ``metadata`` mapping (UIAO_200/201/202 convention)
       is returned if present; otherwise the top-level mapping itself.

    Returns ``(metadata_dict, error_msg)``. One of the two is always None.
    Files without parseable metadata return ``({}, None)`` — a legitimate
    state for very old canon docs that pre-date the metadata convention.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return None, f"read failed: {e}"

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            loaded = yaml.safe_load(text)
        except yaml.YAMLError as e:
            return None, f"yaml parse failed: {e}"
        if loaded is None:
            return {}, None
        if not isinstance(loaded, dict):
            return None, f"yaml top-level is not a mapping (got {type(loaded).__name__})"
        # UIAO_200/201/202 convention: nest under `metadata:`.
        meta = loaded.get("metadata")
        if isinstance(meta, dict):
            return meta, None
        return loaded, None

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, None
    try:
        loaded = yaml.safe_load(m.group("body"))
    except yaml.YAMLError as e:
        return None, f"yaml parse failed: {e}"
    if loaded is None:
        return {}, None
    if not isinstance(loaded, dict):
        return None, f"frontmatter is not a mapping (got {type(loaded).__name__})"
    return loaded, None


def collect_entries() -> list[DocEntry]:
    """Walk the registry, parse each artifact's frontmatter, and return one
    DocEntry per registered document."""
    entries: list[DocEntry] = []
    for raw in load_registry():
        uiao_id = raw.get("id", "?")
        rel_path = raw.get("path", "")
        title = raw.get("title", "")
        status = raw.get("status", "")
        classification = raw.get("classification", "")
        full_path = REPO_ROOT / rel_path

        entry = DocEntry(
            uiao_id=uiao_id,
            registry_path=rel_path,
            registry_title=title,
            registry_status=status,
            registry_classification=classification,
        )

        if not full_path.exists():
            entry.path_exists = False
            entry.parse_error = "registered path does not exist on disk"
            entries.append(entry)
            continue

        fm, err = parse_frontmatter(full_path)
        if err is not None:
            entry.parse_error = err
        elif fm is not None:
            entry.frontmatter_status = _stringify(fm.get("status"))
            entry.frontmatter_version = _stringify(fm.get("version"))
            entry.frontmatter_updated_at = _stringify(fm.get("updated_at"))
            entry.frontmatter_owner = _stringify(fm.get("owner"))
            entry.frontmatter_boundary = _stringify(fm.get("boundary"))

        entries.append(entry)
    return entries


def _stringify(value: Any) -> str | None:
    """Coerce a YAML value into a plain string, preserving None as None."""
    if value is None:
        return None
    return str(value)


def _range_for(uiao_id: str) -> str:
    """Bucket a UIAO_NNN id into its reserved range per UIAO_001 doctrine."""
    m = re.match(r"UIAO_(\d{3})", uiao_id)
    if not m:
        return "Other"
    n = int(m.group(1))
    if n == 1:
        return "UIAO_001 — SSOT"
    if 2 <= n <= 99:
        return "UIAO_002–099 — Top-level canon"
    if 100 <= n <= 199:
        return "UIAO_100–199 — Subsystem specs"
    if 200 <= n <= 299:
        return "UIAO_200–299 — Operational/runtime"
    if 900 <= n <= 999:
        return "UIAO_900–999 — Test fixtures"
    return "Other"


def _link(rel_path: str) -> str:
    """Render a Markdown link to the canonical artifact on GitHub."""
    if not rel_path:
        return ""
    return f"[`{rel_path}`]({GITHUB_BLOB_BASE}/{rel_path})"


def render(entries: list[DocEntry]) -> str:
    """Render the full Markdown report. Caller writes to disk or stdout."""
    out: list[str] = []
    out.append("<!-- GENERATED by scripts/generate_substrate_status_table.py — do not hand-edit. -->")
    out.append("<!-- Regenerate: python scripts/generate_substrate_status_table.py --output docs/data/substrate-document-status.md -->")
    out.append("")
    out.append("# Substrate document status (regenerated)")
    out.append("")
    out.append(_summary(entries))
    out.append("")

    by_range: dict[str, list[DocEntry]] = {}
    for e in entries:
        by_range.setdefault(_range_for(e.uiao_id), []).append(e)

    range_order = [
        "UIAO_001 — SSOT",
        "UIAO_002–099 — Top-level canon",
        "UIAO_100–199 — Subsystem specs",
        "UIAO_200–299 — Operational/runtime",
        "UIAO_900–999 — Test fixtures",
        "Other",
    ]
    for label in range_order:
        bucket = by_range.get(label, [])
        if not bucket:
            continue
        out.append(f"## {label}")
        out.append("")
        out.append(_table(bucket))
        out.append("")

    failed = [e for e in entries if e.parse_error is not None]
    if failed:
        out.append("## Documents requiring author attention")
        out.append("")
        out.append("These entries have parse failures or missing artifacts. Each is a")
        out.append("`DRIFT-PROVENANCE` finding waiting to fire — fix at source.")
        out.append("")
        out.append("| UIAO_NNN | Path | Issue |")
        out.append("|---|---|---|")
        for e in sorted(failed, key=lambda x: x.uiao_id):
            out.append(f"| {e.uiao_id} | `{e.registry_path}` | {e.parse_error} |")
        out.append("")

    return "\n".join(out) + "\n"


def _summary(entries: list[DocEntry]) -> str:
    total = len(entries)
    by_status: dict[str, int] = {}
    for e in entries:
        by_status[e.registry_status or "(unset)"] = by_status.get(e.registry_status or "(unset)", 0) + 1
    failed = sum(1 for e in entries if e.parse_error is not None)
    missing = sum(1 for e in entries if not e.path_exists)
    lines: list[str] = []
    lines.append(f"**{total} documents registered.**")
    lines.append("")
    lines.append("| Registry status | Count |")
    lines.append("|---|---:|")
    for status, count in sorted(by_status.items()):
        lines.append(f"| `{status}` | {count} |")
    if failed:
        lines.append(f"| _(parse failures — see end of page)_ | {failed} |")
    if missing:
        lines.append(f"| _(registered path missing on disk)_ | {missing} |")
    return "\n".join(lines)


def _table(entries: list[DocEntry]) -> str:
    lines: list[str] = []
    lines.append("| UIAO_NNN | Title | Registry status | Frontmatter status | Updated | Path |")
    lines.append("|---|---|---|---|---|---|")
    for e in sorted(entries, key=lambda x: x.uiao_id):
        title = e.registry_title or "—"
        reg_status = e.registry_status or "—"
        fm_status = e.frontmatter_status or "—"
        updated = e.frontmatter_updated_at or "—"
        path = _link(e.registry_path) if e.path_exists else f"`{e.registry_path}` _(missing)_"
        lines.append(f"| {e.uiao_id} | {title} | {reg_status} | {fm_status} | {updated} | {path} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Write output to this path (default: stdout). Conventional location: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)}",
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
