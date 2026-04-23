#!/usr/bin/env python3
"""
UIAO Diagram Injection Script (Option A)
=========================================
Scans Markdown (.md) and Quarto (.qmd) files for UIAO-DIAGRAM directives
and inserts or updates SVG image references below each directive.

Directive syntax:
    <!-- UIAO-DIAGRAM: DIAG_NNN form_factor=full|nano|auto -->

The script:
  1. Finds all directive comments in target files
  2. Resolves the diagram ID to a rendered SVG path
  3. Inserts (or updates) an image reference immediately after the directive
  4. Uses sentinel markers to identify previously injected lines

Usage:
    python inject.py                        # Scan entire repo
    python inject.py --scope docs/          # Scan only docs/
    python inject.py --scope canon/ --dry-run  # Preview changes
    python inject.py --default-form full    # Override default form factor

Boundary: GCC-Moderate
"""

import argparse
import os
import re
import sys
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # diagrams/scripts/ -> repo root
RENDERED_DIR = REPO_ROOT / "diagrams" / "rendered"
REGISTRY_PATH = REPO_ROOT / "diagrams" / "registry" / "diagram-registry.yaml"
SOURCES_DIR = REPO_ROOT / "diagrams" / "sources"

# Regex for the directive comment
DIRECTIVE_RE = re.compile(
    r"^(\s*)<!--\s*UIAO-DIAGRAM:\s*(DIAG_\d{3})"
    r"(?:\s+form_factor\s*=\s*(full|nano|auto))?"
    r'(?:\s+caption\s*=\s*"([^"]*)")?'
    r"\s*-->",
    re.IGNORECASE,
)

# Sentinel wrapping injected image lines — allows update-in-place
SENTINEL_START = "<!-- UIAO-INJECT-START -->"
SENTINEL_END = "<!-- UIAO-INJECT-END -->"
SENTINEL_BLOCK_RE = re.compile(
    r"^(\s*)<!-- UIAO-INJECT-START -->.*?<!-- UIAO-INJECT-END -->\s*$", re.MULTILINE | re.DOTALL
)

# File extensions to scan
SCANNABLE_EXTENSIONS = {".md", ".qmd"}

# Directories to skip
SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "_site",
    ".quarto",
    "rendered",  # Don't scan rendered output dir
}


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


def load_registry():
    """Load the diagram registry and return a dict keyed by diagram_id."""
    if not REGISTRY_PATH.exists():
        print(f"  WARNING: Registry not found at {REGISTRY_PATH}", file=sys.stderr)
        return {}
    with open(REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    registry = {}
    for entry in data.get("diagrams", []):
        did = entry.get("diagram_id", "")
        registry[did.upper()] = entry
    return registry


# ---------------------------------------------------------------------------
# SVG path resolver
# ---------------------------------------------------------------------------


def resolve_svg_path(diagram_id: str, form_factor: str, file_path: Path) -> str | None:
    """
    Resolve the rendered SVG path relative to the file being injected into.
    Returns a relative path string, or None if the SVG doesn't exist.
    """
    svg_dir = RENDERED_DIR / form_factor
    # Convention: rendered files are named DIAG_NNN.svg
    svg_file = svg_dir / f"{diagram_id}.svg"

    if not svg_file.exists():
        # Also check for full-name files: DIAG_NNN_Title.svg
        candidates = list(svg_dir.glob(f"{diagram_id}*.svg"))
        if candidates:
            svg_file = candidates[0]
        else:
            return None

    # Compute relative path from the file being edited to the SVG
    try:
        rel = os.path.relpath(svg_file, file_path.parent)
        return rel.replace("\\", "/")  # Normalize for markdown
    except ValueError:
        # Different drives on Windows — fall back to absolute
        return str(svg_file).replace("\\", "/")


def resolve_svg_path_or_placeholder(
    diagram_id: str, form_factor: str, file_path: Path, registry: dict
) -> tuple[str, str]:
    """
    Returns (image_path, alt_text). If the SVG doesn't exist yet,
    returns a placeholder path with a note.
    """
    entry = registry.get(diagram_id.upper(), {})
    title = entry.get("title", diagram_id)
    alt_text = f"{diagram_id}: {title}"

    svg_path = resolve_svg_path(diagram_id, form_factor, file_path)
    if svg_path:
        return svg_path, alt_text

    # SVG not yet rendered — provide placeholder path so the reference
    # is structurally correct and will resolve after CI renders
    placeholder_dir = os.path.relpath(RENDERED_DIR / form_factor, file_path.parent).replace("\\", "/")
    return f"{placeholder_dir}/{diagram_id}.svg", alt_text


# ---------------------------------------------------------------------------
# Injection engine
# ---------------------------------------------------------------------------


def build_inject_block(image_path: str, alt_text: str, caption: str | None, indent: str) -> str:
    """Build the sentinel-wrapped image block."""
    cap = caption or alt_text
    lines = [
        f"{indent}{SENTINEL_START}",
        f'{indent}![{alt_text}]({image_path} "{cap}")',
        f"{indent}{SENTINEL_END}",
    ]
    return "\n".join(lines)


def process_file(file_path: Path, registry: dict, default_form: str, dry_run: bool) -> dict:
    """
    Process a single file: find directives, inject/update image references.
    Returns a stats dict: {directives_found, injected, updated, skipped, errors}.
    """
    stats = {"directives_found": 0, "injected": 0, "updated": 0, "skipped": 0, "errors": []}

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        stats["errors"].append(f"Read error: {e}")
        return stats

    lines = content.split("\n")
    new_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]
        m = DIRECTIVE_RE.match(line)

        if not m:
            new_lines.append(line)
            i += 1
            continue

        # Found a directive
        stats["directives_found"] += 1
        indent = m.group(1) or ""
        diagram_id = m.group(2).upper()
        form_factor = (m.group(3) or default_form).lower()
        caption = m.group(4)

        if form_factor == "auto":
            form_factor = "full"

        # Keep the directive line
        new_lines.append(line)
        i += 1

        # Check if the next block is an existing sentinel block — skip it
        if i < len(lines) and SENTINEL_START in lines[i]:
            # Skip existing sentinel block
            while i < len(lines) and SENTINEL_END not in lines[i]:
                i += 1
            if i < len(lines):
                i += 1  # Skip the END sentinel line too
            stats["updated"] += 1
        else:
            stats["injected"] += 1

        # Build and insert the new block
        image_path, alt_text = resolve_svg_path_or_placeholder(diagram_id, form_factor, file_path, registry)
        block = build_inject_block(image_path, alt_text, caption, indent)
        new_lines.append(block)

    new_content = "\n".join(new_lines)

    if new_content != content:
        if not dry_run:
            file_path.write_text(new_content, encoding="utf-8")
        action = "would update" if dry_run else "updated"
        total = stats["injected"] + stats["updated"]
        print(f"  {action}: {file_path}  ({total} diagram(s))")
    elif stats["directives_found"] > 0:
        print(f"  unchanged: {file_path}  ({stats['directives_found']} diagram(s), already current)")

    return stats


def find_files(scope: Path) -> list[Path]:
    """Recursively find all scannable files under scope."""
    files = []
    for root, dirs, filenames in os.walk(scope):
        # Prune skip directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in filenames:
            if Path(fn).suffix.lower() in SCANNABLE_EXTENSIONS:
                files.append(Path(root) / fn)
    return sorted(files)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="UIAO Diagram Injection — insert rendered SVGs into documents")
    parser.add_argument(
        "--scope", type=str, default=".", help="Directory to scan (relative to repo root). Default: entire repo."
    )
    parser.add_argument(
        "--default-form",
        choices=["full", "nano"],
        default="full",
        help="Default form factor when directive omits form_factor. Default: full.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files.")
    args = parser.parse_args()

    scope = REPO_ROOT / args.scope
    if not scope.exists():
        print(f"ERROR: Scope directory not found: {scope}", file=sys.stderr)
        sys.exit(1)

    print("UIAO Diagram Injection Pipeline")
    print("=" * 55)
    if args.dry_run:
        print("  MODE: dry-run (no files will be modified)\n")
    print(f"  Scope:        {scope}")
    print(f"  Default form: {args.default_form}")

    registry = load_registry()
    print(f"  Registry:     {len(registry)} diagrams loaded\n")

    files = find_files(scope)
    print(f"  Scanning {len(files)} files...\n")

    totals = {"directives_found": 0, "injected": 0, "updated": 0, "skipped": 0, "errors": []}

    for fp in files:
        stats = process_file(fp, registry, args.default_form, args.dry_run)
        for k in ("directives_found", "injected", "updated", "skipped"):
            totals[k] += stats[k]
        totals["errors"].extend(stats["errors"])

    print(f"\n{'=' * 55}")
    print(f"  Directives found: {totals['directives_found']}")
    print(f"  New injections:   {totals['injected']}")
    print(f"  Updated in-place: {totals['updated']}")
    if totals["errors"]:
        print(f"  Errors:           {len(totals['errors'])}")
        for e in totals["errors"]:
            print(f"    - {e}")

    if totals["errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
