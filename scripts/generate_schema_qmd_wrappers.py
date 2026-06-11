#!/usr/bin/env python3
"""Generate Quarto .qmd reference pages for every UIAO JSON Schema.

For each src/uiao/schemas/**/*.schema.json file, produces:

  - docs/reference/schemas/{stem}.qmd — a developer-reference page
    rendering the schema as: title, description, top-level property
    table (name/type/required/description), and a collapsible code
    block of the full raw schema.

Per ADR-072, schemas use `publication_style: reference` rather than
`include` because they are not markdown bodies — they are structured
JSON best surfaced as property tables for developer consumption.

Also writes:
  - docs/reference/schemas/index.qmd — aggregate index of all schemas
  - tools/publication-gaps/schema-sidebar-snippet.yaml — paste-ready
    YAML snippet for the docs/_quarto.yml sidebar entry

Usage:
  python scripts/generate_schema_qmd_wrappers.py
  python scripts/generate_schema_qmd_wrappers.py --dry-run
  python scripts/generate_schema_qmd_wrappers.py --force
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_SOURCE_DIR = REPO_ROOT / "src" / "uiao" / "schemas"
SCHEMA_OUTPUT_DIR = REPO_ROOT / "docs" / "reference" / "schemas"
SIDEBAR_SNIPPET = REPO_ROOT / "tools" / "publication-gaps" / "schema-sidebar-snippet.yaml"

# Schemas deliberately published under a different wrapper name than the source
# stem. Keyed by path relative to SCHEMA_SOURCE_DIR (posix); value is the
# output stem (wrapper filename without .qmd). These match the wrappers
# committed on main and registered in docs/_quarto.yml.
OUTPUT_STEM_OVERRIDES = {
    "mssql-rationalization/abbreviation-dictionary.schema.json": "mssql-rationalization-abbreviation-dictionary.schema",
    "mssql-rationalization/domain-catalog.schema.json": "mssql-rationalization-domain-catalog.schema",
    "mssql-rationalization/reference-data-patterns.schema.json": "mssql-rationalization-reference-data-patterns.schema",
}

# Schemas surfaced on a page outside docs/reference/schemas/. The
# publication-gap scanner matches these via link-back from that page; they get
# no wrapper, no index row, and no sidebar entry here.
EXCLUDED_SCHEMAS = {
    "migration-adapter-registry/migration-adapter-registry.schema.json": (
        "published via docs/customer-documents/reference-architecture/directory-migration.qmd"
    ),
}


def output_stem(schema_path: pathlib.Path) -> str:
    """Wrapper filename stem for a schema source, honoring committed overrides."""
    rel = schema_path.relative_to(SCHEMA_SOURCE_DIR).as_posix()
    return OUTPUT_STEM_OVERRIDES.get(rel, schema_path.stem)


def _format_type(prop: dict[str, Any]) -> str:
    """Render a JSON Schema type/oneOf/const into a short markdown string."""
    if "const" in prop:
        return f"`const: {prop['const']!r}`"
    if "enum" in prop:
        values = ", ".join(repr(v) for v in prop["enum"])
        return f"enum: {values}"
    if "$ref" in prop:
        return f"`$ref: {prop['$ref']}`"
    if "type" in prop:
        t = prop["type"]
        if isinstance(t, list):
            return " \\| ".join(t)
        if t == "array" and "items" in prop and isinstance(prop["items"], dict):
            inner = _format_type(prop["items"])
            return f"array&lt;{inner}&gt;"
        return str(t)
    if "oneOf" in prop or "anyOf" in prop:
        return "(union)"
    return "(any)"


def render_property_row(name: str, prop: dict[str, Any], required: set[str]) -> str:
    """Render one property as a markdown table row."""
    type_str = _format_type(prop)
    req_str = "✓" if name in required else ""
    desc = prop.get("description", "")
    # Collapse whitespace in description for table layout
    desc = " ".join(desc.split())
    # Escape pipes to keep markdown table intact
    desc = desc.replace("|", "\\|")
    name_escaped = name.replace("|", "\\|")
    return f"| `{name_escaped}` | {type_str} | {req_str} | {desc} |"


def render_schema_qmd(schema: dict[str, Any], schema_path: pathlib.Path) -> str:
    """Build the Quarto reference page content."""
    # Path from docs/reference/schemas/{stem}.qmd to the schema source
    # depth: docs(1)/reference(2)/schemas(3)/file → up 3 to root
    rel_to_source = pathlib.Path("../../..") / schema_path.relative_to(REPO_ROOT)
    rel_to_source_str = rel_to_source.as_posix()

    title = schema.get("title", schema_path.stem)
    description = schema.get("description", "_(no description provided)_")
    schema_id = schema.get("$id", "")
    schema_dialect = schema.get("$schema", "")

    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    # Render top-level property table
    if properties:
        rows = [render_property_row(name, prop, required) for name, prop in properties.items()]
        property_table = "| Property | Type | Required | Description |\n|---|---|:---:|---|\n" + "\n".join(rows)
    else:
        property_table = "_(no top-level properties defined)_"

    # Pretty-print the full schema for the appendix
    raw_schema = json.dumps(schema, indent=2)

    # Page title can contain quotes that break YAML — escape them
    page_title = title.replace('"', '\\"')

    # Renamed wrappers carry the family-qualified source name so the page
    # is unambiguous (e.g. mssql-rationalization/abbreviation-dictionary…).
    rel_in_schemas = schema_path.relative_to(SCHEMA_SOURCE_DIR).as_posix()
    display_name = rel_in_schemas if rel_in_schemas in OUTPUT_STEM_OVERRIDES else schema_path.name

    page_date = datetime.date.today().isoformat()

    return f"""---
title: "{page_title}"
subtitle: "Schema Reference · {display_name}"
date: {page_date}
---

::: {{.callout-note}}
## Developer Reference

This is a UIAO JSON Schema, rendered as a developer-reference page per
[ADR-072](../../adr/adr-072-canon-publication-policy.qmd).

- **Source:** [`{schema_path.relative_to(REPO_ROOT).as_posix()}`]({rel_to_source_str})
- **Dialect:** `{schema_dialect}`
- **`$id`:** `{schema_id}`
:::

## Description

{description}

## Top-Level Properties

{property_table}

## Full Schema

```{{.json filename="{schema_path.name}"}}
{raw_schema}
```
"""


def render_index_qmd(schemas: list[tuple[pathlib.Path, dict[str, Any]]]) -> str:
    """Build the docs/reference/schemas/index.qmd aggregate page."""
    rows = []
    for path, schema in sorted(schemas, key=lambda x: output_stem(x[0])):
        title = schema.get("title", path.stem)
        title_escaped = title.replace("|", "\\|")
        rows.append(f"| [{title_escaped}]({output_stem(path)}.qmd) | `{path.name}` |")
    table = "| Schema | File |\n|---|---|\n" + "\n".join(rows) if rows else "_(no schemas found)_"
    return f"""---
title: "JSON Schema Reference — Index"
subtitle: "All UIAO machine-readable schemas"
date: last-modified
---

::: {{.callout-note}}
The UIAO JSON schemas define the machine-readable contracts for
canon artifacts (orgpath registries, KSI evidence bundles, adapter
manifests, etc.). Every schema is published as a developer-reference
page per [ADR-072](../../adr/adr-072-canon-publication-policy.qmd).

The schemas are versioned alongside the canon they constrain. To
contribute a new schema, see the canon-change process declared in
[`AGENTS.md`](https://github.com/WhalerMike/uiao/blob/main/AGENTS.md).
:::

## All Schemas

{table}
"""


def generate_sidebar_snippet(stems: list[str]) -> str:
    """YAML snippet to paste into docs/_quarto.yml sidebar."""
    lines = [
        "# Generated by scripts/generate_schema_qmd_wrappers.py — paste into",
        "# docs/_quarto.yml under a 'Schema Reference' section (or merge into",
        "# an existing developer-reference sidebar).",
        "",
        "- id: schemas",
        '  title: "Schema Reference"',
        '  style: "docked"',
        "  background: light",
        "  contents:",
        '    - section: "JSON Schema Reference"',
        "      contents:",
        "        - reference/schemas/index.qmd",
    ]
    for stem in sorted(stems):
        lines.append(f"        - reference/schemas/{stem}.qmd")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be done; make no changes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite existing wrappers (default: skip if wrapper exists).",
    )
    args = parser.parse_args()

    if not SCHEMA_SOURCE_DIR.exists():
        print(f"ERROR: Schema source dir not found: {SCHEMA_SOURCE_DIR}", file=sys.stderr)
        return 1

    if not args.dry_run:
        SCHEMA_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        SIDEBAR_SNIPPET.parent.mkdir(parents=True, exist_ok=True)

    generated: list[str] = []
    skipped: list[tuple[str, str]] = []
    schemas: list[tuple[pathlib.Path, dict[str, Any]]] = []

    for schema_path in sorted(SCHEMA_SOURCE_DIR.rglob("*.schema.json")):
        rel = schema_path.relative_to(SCHEMA_SOURCE_DIR).as_posix()
        if rel in EXCLUDED_SCHEMAS:
            skipped.append((schema_path.name, f"excluded: {EXCLUDED_SCHEMAS[rel]}"))
            continue

        try:
            with schema_path.open(encoding="utf-8") as fh:
                schema = json.load(fh)
        except (OSError, json.JSONDecodeError) as e:
            skipped.append((schema_path.name, f"parse error: {e}"))
            continue

        schemas.append((schema_path, schema))
        wrapper_path = SCHEMA_OUTPUT_DIR / f"{output_stem(schema_path)}.qmd"

        if wrapper_path.exists() and not args.force:
            skipped.append((schema_path.name, "wrapper exists"))
            continue

        if not args.dry_run:
            wrapper_path.write_text(render_schema_qmd(schema, schema_path), encoding="utf-8", newline="\n")
        generated.append(schema_path.name)

    # Emit index + sidebar snippet
    if not args.dry_run:
        index_path = SCHEMA_OUTPUT_DIR / "index.qmd"
        index_path.write_text(render_index_qmd(schemas), encoding="utf-8", newline="\n")
        SIDEBAR_SNIPPET.write_text(
            generate_sidebar_snippet([output_stem(p) for p, _ in schemas]),
            encoding="utf-8",
            newline="\n",
        )

    print(f"Schema source dir:  {SCHEMA_SOURCE_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrapper output:     {SCHEMA_OUTPUT_DIR.relative_to(REPO_ROOT)}")
    print(f"Wrappers generated: {len(generated)}")
    print(f"Wrappers skipped:   {len(skipped)}")
    if not args.dry_run:
        print(f"Index page:         {(SCHEMA_OUTPUT_DIR / 'index.qmd').relative_to(REPO_ROOT)}")
        print(f"Sidebar snippet:    {SIDEBAR_SNIPPET.relative_to(REPO_ROOT)}")
    if args.dry_run:
        print("\n(dry-run: no files written)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
