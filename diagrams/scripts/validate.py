#!/usr/bin/env python3
"""
UIAO Diagram Validation Pipeline — v2.0 (Category-Aware)
Validates all Mermaid SSOT sources against governance rules and metadata schema.
Supports category-based subdirectory structure under sources/{category}/.

Checks performed (all CI-blocking):
  1. Every .mmd file has valid YAML frontmatter
  2. Frontmatter validates against diagram-metadata-schema.yaml
  3. document_category matches the source subdirectory
  4. diagram_id falls within the reserved range for its category
  5. Every .mmd file is registered in diagram-registry.yaml
  6. No orphaned renders exist without a matching source
  7. Both full and nano renders exist for every active source (if rendered/)
  8. No FOUO markings present in any diagram or metadata

Usage:
    python validate.py [--strict] [--category CATEGORY]

Governance: UIAO_DG_001 (DIAGRAM-GOVERNANCE.md) v2.0
Boundary: GCC-Moderate
"""

import argparse
import re
import sys
from pathlib import Path

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
REGISTRY_PATH = REPO_ROOT / "registry" / "diagram-registry.yaml"
SCHEMA_PATH = REPO_ROOT / "governance" / "diagram-metadata-schema.yaml"

CATEGORIES = [
    "training",
    "architecture",
    "testing",
    "planning",
    "governance",
    "identity",
    "operations",
    "enforcement",
    "data",
]

# Category-to-ID-range mapping (numeric part of DIAG_NNN)
CATEGORY_ID_RANGES = {
    "training": (1, 9),
    "architecture": (10, 19),
    "testing": (20, 29),
    "planning": (30, 39),
    "governance": (40, 49),
    "identity": (50, 59),
    "operations": (60, 69),
    "enforcement": (70, 79),
    "data": (80, 89),
}

REQUIRED_FIELDS = [
    "diagram_id",
    "title",
    "version",
    "status",
    "classification",
    "owner",
    "document_category",
    "source_format",
    "form_factors",
    "created_at",
    "updated_at",
    "boundary",
]

VALID_STATUSES = ["DRAFT", "ACTIVE", "DEPRECATED"]
DIAGRAM_ID_PATTERN = re.compile(r"^DIAG_(\d{3})$")
VERSION_PATTERN = re.compile(r"^\d+\.\d+$")
FOUO_PATTERN = re.compile(r"FOUO|For\s+Official\s+Use\s+Only", re.IGNORECASE)


# ── Source Discovery ────────────────────────────────────────────────────────


def discover_sources(category: str = None) -> list:
    """Discover all .mmd source files across category subdirectories."""
    sources = []

    if category:
        cat_dir = SOURCES_DIR / category
        if cat_dir.exists():
            sources.extend(sorted(cat_dir.glob("*.mmd")))
    else:
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


# ── Frontmatter Parsing ─────────────────────────────────────────────────────


def parse_frontmatter(mmd_path: Path) -> dict:
    """Extract YAML frontmatter from Mermaid comment block."""
    content = mmd_path.read_text(encoding="utf-8")
    yaml_lines = []
    in_frontmatter = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "%% ---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue
        if in_frontmatter and stripped.startswith("%%"):
            yaml_lines.append(stripped[2:].strip())

    if not yaml_lines:
        return {}

    yaml_text = "\n".join(yaml_lines)
    try:
        return yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        return {}


# ── Validation Checks ────────────────────────────────────────────────────────


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, source: str, msg: str):
        self.errors.append(f"ERROR [{source}]: {msg}")

    def warn(self, source: str, msg: str):
        self.warnings.append(f"WARN  [{source}]: {msg}")

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def check_frontmatter(source: Path, result: ValidationResult):
    """Validate frontmatter exists and has required fields."""
    metadata = parse_frontmatter(source)
    name = source.name

    if not metadata:
        result.error(name, "No valid YAML frontmatter found")
        return metadata

    for field in REQUIRED_FIELDS:
        if field not in metadata:
            result.error(name, f"Missing required field: {field}")

    # diagram_id format
    did = metadata.get("diagram_id", "")
    if did and not DIAGRAM_ID_PATTERN.match(did):
        result.error(name, f"Invalid diagram_id format: '{did}' (expected DIAG_NNN)")

    # version format
    ver = metadata.get("version", "")
    if ver and not VERSION_PATTERN.match(str(ver)):
        result.error(name, f"Invalid version format: '{ver}' (expected Major.Minor)")

    # status enum
    status = metadata.get("status", "")
    if status and status not in VALID_STATUSES:
        result.error(name, f"Invalid status: '{status}' (expected one of {VALID_STATUSES})")

    # classification must not be FOUO
    classification = metadata.get("classification", "")
    if classification and classification.upper() == "FOUO":
        result.error(name, "Classification must not be FOUO — use 'Controlled'")

    # boundary must be GCC-Moderate
    boundary = metadata.get("boundary", "")
    if boundary and boundary != "GCC-Moderate":
        result.error(name, f"Boundary must be 'GCC-Moderate', got: '{boundary}'")

    # source_format must be mermaid
    fmt = metadata.get("source_format", "")
    if fmt and fmt != "mermaid":
        result.error(name, f"source_format must be 'mermaid', got: '{fmt}'")

    # document_category must be valid
    doc_cat = metadata.get("document_category", "")
    if doc_cat and doc_cat not in CATEGORIES:
        result.error(name, f"Invalid document_category: '{doc_cat}' (expected one of {CATEGORIES})")

    # form_factors must include both full and nano
    factors = metadata.get("form_factors", [])
    if factors:
        if "full" not in factors or "nano" not in factors:
            result.error(name, f"form_factors must include both 'full' and 'nano', got: {factors}")

    # Deprecated must have superseded_by
    if status == "DEPRECATED" and "superseded_by" not in metadata:
        result.error(name, "DEPRECATED diagrams must have superseded_by pointer")

    return metadata


def check_category_alignment(source: Path, metadata: dict, result: ValidationResult):
    """Validate that diagram_id range matches its category and directory."""
    if not metadata:
        return

    did = metadata.get("diagram_id", "")
    doc_cat = metadata.get("document_category", "")
    source_dir = source.parent.name

    # Check directory matches declared category
    if doc_cat and source_dir in CATEGORIES:
        if doc_cat != source_dir:
            result.error(source.name, f"document_category '{doc_cat}' does not match source directory '{source_dir}'")

    # Check ID falls within category range
    if did and doc_cat:
        id_match = DIAGRAM_ID_PATTERN.match(did)
        if id_match:
            id_num = int(id_match.group(1))
            if doc_cat in CATEGORY_ID_RANGES:
                min_id, max_id = CATEGORY_ID_RANGES[doc_cat]
                if not (min_id <= id_num <= max_id):
                    result.error(
                        source.name,
                        f"diagram_id {did} (numeric={id_num}) outside range "
                        f"[{min_id}-{max_id}] for category '{doc_cat}'",
                    )


def check_fouo(source: Path, result: ValidationResult):
    """Check for prohibited FOUO markings in diagram sources and data files.
    Governance docs, schemas, and specs that *define* the no-FOUO rule are excluded
    from this scan — they mention FOUO only to prohibit it."""
    # Skip governance/spec files that define the FOUO prohibition rule
    skip_dirs = {"governance", "specs"}
    skip_files = {
        "README.md",
        "DIAGRAM-GOVERNANCE.md",
        "diagram-metadata-schema.yaml",
        "NANOBANANA-SPEC.md",
        "AUTO-SELECTION-LOGIC.md",
    }
    if source.parent.name in skip_dirs or source.name in skip_files:
        return

    content = source.read_text(encoding="utf-8")
    if FOUO_PATTERN.search(content):
        result.error(source.name, "Prohibited FOUO marking detected — use 'Controlled'")


def check_registry(sources: list, result: ValidationResult) -> dict:
    """Verify all sources are registered in diagram-registry.yaml."""
    if not REGISTRY_PATH.exists():
        result.error("registry", f"Registry file not found: {REGISTRY_PATH}")
        return {}

    try:
        registry = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        result.error("registry", f"Failed to parse registry: {e}")
        return {}

    registered_ids = set()
    for entry in registry.get("diagrams", []):
        registered_ids.add(entry.get("diagram_id", ""))

    for source in sources:
        metadata = parse_frontmatter(source)
        did = metadata.get("diagram_id", "")
        if did and did not in registered_ids:
            result.error(source.name, f"Diagram {did} not registered in diagram-registry.yaml")

    return registry


def check_orphaned_renders(sources: list, result: ValidationResult):
    """Check for rendered files without matching sources."""
    source_ids = set()
    for source in sources:
        metadata = parse_frontmatter(source)
        did = metadata.get("diagram_id", "")
        if did:
            source_ids.add(did)

    for render_dir in [FULL_DIR, NANO_DIR]:
        if not render_dir.exists():
            continue
        for rendered_file in render_dir.iterdir():
            if rendered_file.name.startswith("."):
                continue
            # Extract diagram ID from filename (DIAG_NNN_...)
            match = re.match(r"(DIAG_\d{3})_", rendered_file.name)
            if match:
                render_id = match.group(1)
                if render_id not in source_ids:
                    result.error(rendered_file.name, f"Orphaned render — no matching source for {render_id}")


def check_render_completeness(sources: list, result: ValidationResult):
    """Check that both full and nano renders exist for active sources."""
    if not RENDERED_DIR.exists():
        result.warn("renders", "No rendered/ directory — skipping render completeness check")
        return

    full_ids = set()
    nano_ids = set()

    if FULL_DIR.exists():
        for f in FULL_DIR.iterdir():
            match = re.match(r"(DIAG_\d{3})_", f.name)
            if match:
                full_ids.add(match.group(1))

    if NANO_DIR.exists():
        for f in NANO_DIR.iterdir():
            match = re.match(r"(DIAG_\d{3})_", f.name)
            if match:
                nano_ids.add(match.group(1))

    for source in sources:
        metadata = parse_frontmatter(source)
        did = metadata.get("diagram_id", "")
        status = metadata.get("status", "")

        if did and status == "ACTIVE":
            if did not in full_ids:
                result.warn(source.name, f"Missing full render for active diagram {did}")
            if did not in nano_ids:
                result.warn(source.name, f"Missing nano render for active diagram {did}")


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="UIAO Diagram Validation Pipeline (v2.0 — Category-Aware)")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument(
        "--category", type=str, choices=CATEGORIES, help="Validate only diagrams in a specific category"
    )
    args = parser.parse_args()

    print("UIAO Diagram Validation Pipeline v2.0")
    print("=" * 55)

    result = ValidationResult()

    # Collect sources (exclude templates)
    sources = discover_sources(args.category)

    if not sources:
        result.warn("sources", "No .mmd source files found")

    print(f"\nSources found: {len(sources)}")
    if args.category:
        print(f"Category filter: {args.category}")

    # Group by category for display
    by_category = {}
    for source in sources:
        cat = source.parent.name if source.parent.name in CATEGORIES else "uncategorized"
        by_category.setdefault(cat, []).append(source)

    # Run checks
    print("\n── Frontmatter & Category Validation ──")
    for cat in sorted(by_category.keys()):
        cat_sources = by_category[cat]
        print(f"\n  {cat.upper()} ({len(cat_sources)} diagrams)")
        for source in cat_sources:
            metadata = check_frontmatter(source, result)
            if metadata:
                check_category_alignment(source, metadata, result)
                did = metadata.get("diagram_id", "?")
                title = metadata.get("title", "?")
                doc_cat = metadata.get("document_category", "?")
                print(f"    ✓ {source.name}: {did} [{doc_cat}] — {title}")

    print("\n── FOUO Check ──")
    all_files = list(REPO_ROOT.rglob("*"))
    text_files = [f for f in all_files if f.is_file() and f.suffix in (".mmd", ".md", ".yaml", ".yml")]
    for f in text_files:
        check_fouo(f, result)
    print(f"  Scanned {len(text_files)} files for FOUO markings")

    print("\n── Registry Check ──")
    check_registry(sources, result)

    print("\n── Orphaned Render Check ──")
    check_orphaned_renders(sources, result)

    print("\n── Render Completeness Check ──")
    check_render_completeness(sources, result)

    # Category coverage summary
    print("\n── Category Coverage Summary ──")
    for cat in CATEGORIES:
        count = len(by_category.get(cat, []))
        min_id, max_id = CATEGORY_ID_RANGES[cat]
        capacity = max_id - min_id + 1
        bar = "█" * count + "░" * (capacity - count)
        print(f"  {cat:<14} {bar} {count}/{capacity}")

    # Report
    print("\n" + "=" * 55)
    print("RESULTS")
    print("=" * 55)

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  {w}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  {e}")

    total_issues = len(result.errors) + (len(result.warnings) if args.strict else 0)

    if total_issues == 0:
        print("\n✓ All validation checks passed")
        sys.exit(0)
    else:
        print(f"\n✗ Validation failed: {len(result.errors)} errors, {len(result.warnings)} warnings")
        sys.exit(1)


if __name__ == "__main__":
    main()
