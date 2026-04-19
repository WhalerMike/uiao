#!/usr/bin/env python3
"""
UIAO Diagram Rendering Pipeline — v2.0 (Category-Aware)
Renders Mermaid SSOT sources into dual-form-factor outputs (Full/Banana + Compact/NanoBanana).
Supports category-based subdirectory structure under sources/{category}/.

Usage:
    python render.py [--source SOURCE_FILE] [--all] [--category CATEGORY]
                     [--format png|svg|pdf] [--form-factor full|nano|both]

Prerequisites:
    - Node.js with @mermaid-js/mermaid-cli installed
    - pip install pyyaml

Governance: UIAO_DG_001 (DIAGRAM-GOVERNANCE.md) v2.0
Spec: UIAO_DG_002 (NANOBANANA-SPEC.md)
Boundary: GCC-Moderate
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    sys.exit(1)

# ── Constants ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = REPO_ROOT / "sources"
RENDERED_DIR = REPO_ROOT / "rendered"
FULL_DIR = RENDERED_DIR / "full"
NANO_DIR = RENDERED_DIR / "nano"
GOVERNANCE_DIR = REPO_ROOT / "governance"
SCHEMA_PATH = GOVERNANCE_DIR / "diagram-metadata-schema.yaml"

MERMAID_CLI = "mmdc"  # mermaid-cli command
SUPPORTED_FORMATS = ["png", "svg", "pdf"]
LABEL_MAX_LENGTH = 15

CATEGORIES = [
    "training", "architecture", "testing", "planning",
    "governance", "identity", "operations", "enforcement", "data"
]


# ── Source Discovery ────────────────────────────────────────────────────────

def discover_sources(category: str = None) -> list:
    """
    Discover all .mmd source files across category subdirectories.
    Optionally filter by a single category.
    """
    sources = []

    if category:
        cat_dir = SOURCES_DIR / category
        if cat_dir.exists():
            sources.extend(sorted(cat_dir.glob("*.mmd")))
    else:
        # Walk all category subdirectories
        for cat in CATEGORIES:
            cat_dir = SOURCES_DIR / cat
            if cat_dir.exists():
                sources.extend(sorted(cat_dir.glob("*.mmd")))

        # Also check root for legacy flat-layout sources
        for f in sorted(SOURCES_DIR.glob("*.mmd")):
            if not f.name.startswith("_") and f not in sources:
                sources.append(f)

    # Exclude templates
    sources = [s for s in sources if not s.name.startswith("_")]
    return sources


# ── Metadata Parsing ────────────────────────────────────────────────────────

def parse_frontmatter(mmd_path: Path) -> dict:
    """Extract YAML frontmatter from Mermaid comment block."""
    content = mmd_path.read_text(encoding="utf-8")
    yaml_lines = []
    in_frontmatter = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "%% ---":
            if in_frontmatter:
                break  # End of frontmatter
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith("%%"):
            yaml_lines.append(stripped[2:].strip())

    if not yaml_lines:
        return {}

    yaml_text = "\n".join(yaml_lines)
    try:
        return yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as e:
        print(f"WARNING: Failed to parse frontmatter in {mmd_path.name}: {e}")
        return {}


def extract_mermaid_body(mmd_path: Path) -> str:
    """Extract the Mermaid diagram body (everything after frontmatter)."""
    content = mmd_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    body_lines = []
    frontmatter_ended = False
    frontmatter_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped == "%% ---":
            frontmatter_count += 1
            if frontmatter_count == 2:
                frontmatter_ended = True
            continue
        if frontmatter_ended or frontmatter_count == 0:
            # Skip comment-only metadata lines before body
            if not frontmatter_ended and stripped.startswith("%%") and ":" in stripped:
                continue
            body_lines.append(line)

    return "\n".join(body_lines)


# ── NanoBanana Transformation ───────────────────────────────────────────────

def abbreviate_label(label: str, max_len: int = LABEL_MAX_LENGTH) -> str:
    """Abbreviate a label for nano form factor."""
    if len(label) <= max_len:
        return label

    # Remove articles and prepositions
    stopwords = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "with", "by"}
    words = label.split()
    filtered = [w for w in words if w.lower() not in stopwords]

    result = " ".join(filtered)
    if len(result) <= max_len:
        return result

    # Truncate with abbreviation
    if len(filtered) > 1:
        result = filtered[0] + " " + filtered[1][:4] + "."
    else:
        result = filtered[0][:max_len - 1] + "."

    return result[:max_len]


def apply_nano_transform(mermaid_body: str, nano_config: dict) -> str:
    """
    Apply NanoBanana transformations to Mermaid source.

    Transformations:
    1. Collapse subgraphs listed in collapse_groups
    2. Abbreviate labels if label_mode is 'abbreviated'
    3. Remove annotation/note nodes if hide_annotations is True
    """
    transformed = mermaid_body
    collapse_groups = nano_config.get("collapse_groups", [])
    label_mode = nano_config.get("label_mode", "abbreviated")
    hide_annotations = nano_config.get("hide_annotations", True)

    # Remove annotation nodes (lines containing 'Note:' style nodes)
    if hide_annotations:
        lines = transformed.splitlines()
        filtered = []
        for line in lines:
            stripped = line.strip()
            # Skip note-style nodes and their styling
            if any(kw in stripped for kw in ["NOTE_", "Note:", "style NOTE_"]):
                continue
            filtered.append(line)
        transformed = "\n".join(filtered)

    # Collapse subgraphs — replace subgraph blocks with single summary nodes
    for group_id in collapse_groups:
        pattern = rf'subgraph\s+{re.escape(group_id)}\s+\["([^"]+)"\].*?end'
        match = re.search(pattern, transformed, re.DOTALL)
        if match:
            title = match.group(1)
            # Count internal nodes for the summary label
            block = match.group(0)
            node_count = len(re.findall(r'\w+\["', block)) + len(re.findall(r'\w+\[', block))
            summary_node = f'    {group_id}[/"{title} ({node_count})"/]'
            transformed = transformed[:match.start()] + summary_node + transformed[match.end():]

    # Abbreviate labels
    if label_mode == "abbreviated":
        def abbreviate_match(m):
            full_label = m.group(1)
            short = abbreviate_label(full_label)
            return f'["{short}"]'

        # Match ["Label text"] patterns
        transformed = re.sub(r'\["([^"]{16,})"\]', abbreviate_match, transformed)

    return transformed


# ── Rendering ────────────────────────────────────────────────────────────────

def render_mermaid(mermaid_content: str, output_path: Path, output_format: str = "png") -> bool:
    """Render Mermaid content to specified format using mermaid-cli."""
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write temp input file
    temp_input = output_path.parent / f"_temp_{output_path.stem}.mmd"
    try:
        temp_input.write_text(mermaid_content, encoding="utf-8")

        cmd = [
            MERMAID_CLI,
            "-i", str(temp_input),
            "-o", str(output_path),
            "-f", output_format,
            "--backgroundColor", "transparent",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode != 0:
            print(f"ERROR: Rendering failed for {output_path.name}")
            print(f"  stderr: {result.stderr}")
            return False

        print(f"  ✓ Rendered: {output_path}")
        return True

    except FileNotFoundError:
        print(f"ERROR: {MERMAID_CLI} not found. Install with: npm install -g @mermaid-js/mermaid-cli")
        return False
    except subprocess.TimeoutExpired:
        print(f"ERROR: Rendering timed out for {output_path.name}")
        return False
    finally:
        if temp_input.exists():
            temp_input.unlink()


def render_diagram(source_path: Path, output_format: str = "png", form_factor: str = "both") -> dict:
    """
    Render a single diagram source in the requested form factor(s).

    Returns dict with status per form factor.
    """
    metadata = parse_frontmatter(source_path)
    if not metadata:
        return {"error": f"No valid frontmatter in {source_path.name}"}

    diagram_id = metadata.get("diagram_id", source_path.stem)
    title = metadata.get("title", "Untitled")
    status = metadata.get("status", "DRAFT")

    if status == "DEPRECATED":
        print(f"  ⊘ Skipping deprecated diagram: {diagram_id}")
        return {"skipped": "DEPRECATED"}

    mermaid_body = extract_mermaid_body(source_path)
    results = {}

    # Full (Banana) rendering
    if form_factor in ("full", "both"):
        FULL_DIR.mkdir(parents=True, exist_ok=True)
        short_title = title.replace(" ", "_").replace("/", "-")
        output_name = f"{diagram_id}_{short_title}_full.{output_format}"
        output_path = FULL_DIR / output_name
        results["full"] = render_mermaid(mermaid_body, output_path, output_format)

    # Nano (NanoBanana) rendering
    if form_factor in ("nano", "both"):
        NANO_DIR.mkdir(parents=True, exist_ok=True)
        nano_config = metadata.get("nano_config", {})
        nano_body = apply_nano_transform(mermaid_body, nano_config)
        short_title = title.replace(" ", "_").replace("/", "-")
        output_name = f"{diagram_id}_{short_title}_nano.{output_format}"
        output_path = NANO_DIR / output_name
        results["nano"] = render_mermaid(nano_body, output_path, output_format)

    return results


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="UIAO Diagram Rendering Pipeline — Dual-form-factor Mermaid renderer (v2.0)"
    )
    parser.add_argument("--source", type=str, help="Specific .mmd source file to render")
    parser.add_argument("--all", action="store_true", help="Render all .mmd sources across all categories")
    parser.add_argument("--category", type=str, choices=CATEGORIES,
                        help="Render only diagrams in a specific category")
    parser.add_argument("--format", type=str, default="png", choices=SUPPORTED_FORMATS,
                        help="Output format (default: png)")
    parser.add_argument("--form-factor", type=str, default="both", choices=["full", "nano", "both"],
                        help="Form factor to render (default: both)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate without rendering")

    args = parser.parse_args()

    if not args.source and not args.all and not args.category:
        parser.error("Specify --source FILE, --all, or --category CATEGORY")

    # Collect sources
    sources = []
    if args.source:
        source_path = Path(args.source)
        if not source_path.exists():
            # Try finding in sources/ tree
            for candidate in SOURCES_DIR.rglob(args.source):
                source_path = candidate
                break
        if not source_path.exists():
            print(f"ERROR: Source file not found: {args.source}")
            sys.exit(1)
        sources = [source_path]
    else:
        sources = discover_sources(args.category)

    print(f"UIAO Diagram Pipeline v2.0 — {datetime.now().isoformat()}")
    print(f"  Sources:  {len(sources)}")
    if args.category:
        print(f"  Category: {args.category}")
    print(f"  Format:   {args.format}")
    print(f"  Factor:   {args.form_factor}")
    print(f"  Dry run:  {args.dry_run}")
    print()

    # Group by category for display
    by_category = {}
    for source in sources:
        cat = source.parent.name if source.parent.name in CATEGORIES else "uncategorized"
        by_category.setdefault(cat, []).append(source)

    success_count = 0
    error_count = 0

    for cat in sorted(by_category.keys()):
        cat_sources = by_category[cat]
        print(f"── {cat.upper()} ({len(cat_sources)} diagrams) ──")

        for source in cat_sources:
            print(f"  Processing: {source.name}")
            metadata = parse_frontmatter(source)

            if not metadata:
                print(f"    ✗ No valid frontmatter")
                error_count += 1
                continue

            if args.dry_run:
                print(f"    ✓ Validated: {metadata.get('diagram_id', 'UNKNOWN')} — {metadata.get('title', 'Untitled')}")
                success_count += 1
                continue

            results = render_diagram(source, args.format, args.form_factor)
            if "error" in results:
                print(f"    ✗ {results['error']}")
                error_count += 1
            elif "skipped" in results:
                pass
            else:
                success_count += 1

        print()

    print(f"Complete: {success_count} succeeded, {error_count} failed")
    sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
