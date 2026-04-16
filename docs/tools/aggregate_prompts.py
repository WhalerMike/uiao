#!/usr/bin/env python3
"""
aggregate_prompts.py — Walk every IMAGE-PROMPTS.md and emit a single
image-manifest.json for downstream image generation.

Scans the two adapter documentation trees (ATS + AVS) plus any extension
trees configured below, reads per-adapter IMAGE-PROMPTS.md files, parses
out each [IMAGE-NN] / [DIAGRAM-NN] block with its prompt body, and emits
a deterministic JSON manifest with:

  - adapter-id
  - tree-key (ats | avs | ...)
  - placeholder tag (IMAGE-01, DIAGRAM-03, etc.)
  - target filename (derived from tag)
  - target path (relative to uiao-docs repo root)
  - prompt text
  - content-hash (sha256 over prompt body)

Downstream: `generate_images.py` consumes this manifest, calls the image
model only for entries whose content-hash doesn't match a cached state,
and writes outputs into `<adapter-folder>/images/<target-filename>`.

USAGE (typical):
    python tools/aggregate_prompts.py \\
        --docs-root . \\
        --output data/image-manifest.json

Exit codes:
    0  — manifest written, nothing unusual
    1  — manifest written, but at least one IMAGE-PROMPTS.md failed to parse
         (still safe: malformed entries are skipped and reported)
    2  — fatal (missing tree, invalid --output path, etc.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

# ------------------------------------------------------------------
# Tree configuration — which trees to walk and what their "tree-key" is
# ------------------------------------------------------------------

TREES = [
    ("docs/customer-documents/adapter-technical-specifications", "ats"),
    ("docs/customer-documents/adapter-validation-suites",       "avs"),
    # Canon-level IMAGE-PROMPTS.md files for specification-level diagrams
    # (UIAO_003 DIAGRAM-01/02/03, IMAGE-05, etc.) that aren't adapter-
    # specific but still need to flow through the image pipeline.
    # These sit alongside per-adapter IMAGE-PROMPTS.md in the ATS tree
    # and are picked up by the ats walk. This entry is a documentation
    # marker; no additional tree path is needed since canon-level prompts
    # were co-located in the terraform ATS folder as a pragmatic choice
    # (see PR #29 commit note). A future extension could add a dedicated
    # canon IMAGE-PROMPTS tree under docs/canon-images/.
]

# Regex for [IMAGE-NN: ...] or [DIAGRAM-NN: ...] tags, possibly spanning
# multiple lines. Lazy match on the body.
PLACEHOLDER_RE = re.compile(
    r"\[(?P<tag>(IMAGE|DIAGRAM)-\d+)\s*:\s*(?P<body>.+?)\]",
    re.DOTALL,
)

# Regex for heading-style prompt sections (fallback when authors use
# ## IMAGE-01 headings with prose below, which is what sync_canon.py
# seeds).
HEADING_RE = re.compile(
    r"^##\s+(?P<tag>(IMAGE|DIAGRAM)-\d+)\s*$",
    re.MULTILINE,
)


@dataclass
class PromptEntry:
    adapter_id: str
    tree_key: str
    tag: str
    target_filename: str
    target_path: str
    prompt: str
    content_hash: str
    source_file: str


@dataclass
class AggregateReport:
    docs_root: str
    output_path: str
    trees_scanned: int = 0
    adapters_scanned: int = 0
    prompts_found: int = 0
    files_failed: int = 0
    entries: list[PromptEntry] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def exit_code(self) -> int:
        return 1 if self.files_failed else 0


def compute_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]


def parse_image_prompts_file(path: Path) -> list[tuple[str, str]]:
    """Extract (tag, prompt_body) pairs from an IMAGE-PROMPTS.md file.

    Supports two author styles:
      1. Bracket placeholders:  [IMAGE-01: ...prompt text...]
      2. Heading + prose:       ## IMAGE-01\n\nprompt text here\n\n## ...
    """
    text = path.read_text(encoding="utf-8")
    entries: list[tuple[str, str]] = []

    # Style 1 — bracket placeholders
    for m in PLACEHOLDER_RE.finditer(text):
        tag = m.group("tag")
        body = m.group("body").strip()
        entries.append((tag, body))

    # Style 2 — heading prose (only kick in if no bracket entries found)
    if not entries:
        headings = list(HEADING_RE.finditer(text))
        for i, m in enumerate(headings):
            tag = m.group("tag")
            start = m.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            # Drop leading quoted TODO lines like "_TODO — ..._"
            if body.startswith("_TODO") or body.startswith("*TODO"):
                continue
            if body:
                entries.append((tag, body))

    return entries


def tag_to_filename(tag: str, adapter_id: str, tree_key: str) -> str:
    """Canonical target filename for a given tag.

    Format: <tree>-<adapter>-<tag-lower>.png
    Example: ats-entra-id-image-01.png
    """
    return f"{tree_key}-{adapter_id}-{tag.lower()}.png"


def scan_tree(docs_root: Path, rel_tree: str, tree_key: str, report: AggregateReport) -> None:
    tree = docs_root / rel_tree
    if not tree.is_dir():
        report.errors.append(f"Tree missing: {tree}")
        return
    report.trees_scanned += 1

    for adapter_folder in sorted(tree.iterdir()):
        if not adapter_folder.is_dir():
            continue
        if adapter_folder.name.startswith("_"):
            continue
        adapter_id = adapter_folder.name
        report.adapters_scanned += 1

        prompts_file = adapter_folder / "IMAGE-PROMPTS.md"
        if not prompts_file.is_file():
            continue

        try:
            pairs = parse_image_prompts_file(prompts_file)
        except Exception as exc:
            report.files_failed += 1
            report.errors.append(f"Failed to parse {prompts_file}: {exc}")
            continue

        for tag, prompt in pairs:
            fname = tag_to_filename(tag, adapter_id, tree_key)
            target_rel = str((adapter_folder / "images" / fname).relative_to(docs_root))
            entry = PromptEntry(
                adapter_id=adapter_id,
                tree_key=tree_key,
                tag=tag,
                target_filename=fname,
                target_path=target_rel,
                prompt=prompt,
                content_hash=compute_hash(prompt),
                source_file=str(prompts_file.relative_to(docs_root)),
            )
            report.entries.append(entry)
            report.prompts_found += 1


def build_manifest(report: AggregateReport) -> dict:
    """Build the JSON manifest. Entries are sorted for determinism."""
    entries_sorted = sorted(
        report.entries,
        key=lambda e: (e.tree_key, e.adapter_id, e.tag),
    )
    return {
        "schema-version": "1.0",
        "docs-root": report.docs_root,
        "trees-scanned": report.trees_scanned,
        "adapters-scanned": report.adapters_scanned,
        "prompts-found": report.prompts_found,
        "files-failed": report.files_failed,
        "errors": report.errors,
        "entries": [asdict(e) for e in entries_sorted],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs-root", default=".", help="Root of uiao-docs repo (default: cwd)")
    ap.add_argument("--output",    default="data/image-manifest.json", help="Output JSON path")
    ap.add_argument("--verbose",   action="store_true", help="Print per-entry summary to stderr")
    args = ap.parse_args()

    docs_root = Path(args.docs_root).resolve()
    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = docs_root / output_path

    report = AggregateReport(
        docs_root=str(docs_root),
        output_path=str(output_path),
    )

    for rel_tree, tree_key in TREES:
        scan_tree(docs_root, rel_tree, tree_key, report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(report)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"aggregate_prompts.py — {args.output}", file=sys.stderr)
    print(f"  trees scanned:     {report.trees_scanned}", file=sys.stderr)
    print(f"  adapters scanned:  {report.adapters_scanned}", file=sys.stderr)
    print(f"  prompts found:     {report.prompts_found}", file=sys.stderr)
    print(f"  files failed:      {report.files_failed}", file=sys.stderr)
    if report.errors:
        print(f"  errors:", file=sys.stderr)
        for e in report.errors:
            print(f"    - {e}", file=sys.stderr)
    if args.verbose:
        for entry in manifest["entries"]:
            print(f"  [{entry['tree_key']}] {entry['adapter_id']} {entry['tag']} → {entry['target_filename']} ({entry['content_hash']})", file=sys.stderr)

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
