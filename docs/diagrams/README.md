# UIAO Diagrams — Quarto Integration Guide

**Boundary:** GCC-Moderate · **Version:** 1.0

## Overview

UIAO diagrams are embedded into documentation through **two complementary pipelines**:

| Pipeline | When It Runs | What It Does | Target Files |
|---|---|---|---|
| **Option A — inject.py** | Pre-commit or CI | Scans `.md`/`.qmd` files for directives, inserts `![](...)` image references | All `.md` and `.qmd` in the repo |
| **Option B — Quarto filter** | At Quarto render time | Resolves directives in the Pandoc AST, emits `<figure>` elements or placeholders | `.qmd` files rendered by Quarto |

Both pipelines use the **same directive syntax** — you write the directive once, and whichever pipeline runs will resolve it.

## Embedding a Diagram

### Method 1: HTML Comment Directive (works everywhere)

```markdown
<!-- UIAO-DIAGRAM: DIAG_010 form_factor=full -->
```

This works in `.md` files (Option A injects the image reference) and `.qmd` files (Option B resolves at render time).

### Method 2: Quarto Shortcode (`.qmd` only)

```markdown
{{< uiao-diagram DIAG_010 >}}
{{< uiao-diagram DIAG_010 form_factor=nano >}}
{{< uiao-diagram DIAG_010 form_factor=full caption="Platform Overview" >}}
```

This uses Quarto's native shortcode system — better IDE support, cleaner syntax.

### Method 3: Direct Image Reference

```markdown
![DIAG_010: Platform Overview](../diagrams/rendered/full/DIAG_010.svg)
```

Direct references work but bypass the pipeline — you lose auto-resolution, form-factor selection, and placeholder fallback.

## Directive Parameters

| Parameter | Values | Default | Description |
|---|---|---|---|
| `form_factor` | `full`, `nano`, `auto` | `full` | Which rendered form factor to embed |
| `caption` | Any string (quoted) | Diagram title from registry | Override the figure caption |

## How It Works

```
                    ┌──────────────────┐
                    │  .mmd source     │
                    │  (SSOT)          │
                    └────────┬─────────┘
                             │ render.py / CI
                    ┌────────▼─────────┐
                    │  rendered/       │
                    │  ├── full/*.svg  │
                    │  └── nano/*.svg  │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───────┐  ┌──▼──────────┐  ┌▼──────────────┐
     │ Option A        │  │ Option B     │  │ Direct ref    │
     │ inject.py       │  │ Lua filter   │  │ ![](path)     │
     │ (pre-commit/CI) │  │ (Quarto)     │  │ (manual)      │
     └────────┬────────┘  └──┬──────────┘  └┬──────────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                    ┌────────▼─────────┐
                    │  Published doc   │
                    │  with diagram    │
                    └──────────────────┘
```

## Pre-Render Pipeline

When Quarto renders the site, `pre-render.py` runs automatically:

1. **Validates** all `.mmd` sources (frontmatter, registry, categories)
2. **Renders** any stale diagrams (source newer than SVG)
3. **Injects** image references into docs (Option A)
4. Quarto then renders with the Lua filter (Option B)

This means both pipelines execute during a full site build — belt and suspenders.

## Adding a Diagram to a Document

1. Choose your diagram ID from the [registry](../../diagrams/registry/diagram-registry.yaml)
2. Add the directive where you want the diagram to appear:
   ```markdown
   <!-- UIAO-DIAGRAM: DIAG_010 form_factor=full -->
   ```
3. Commit and push — CI handles the rest

For local preview:
```bash
python diagrams/scripts/render.py          # Generate SVGs
python diagrams/scripts/inject.py --scope docs/  # Inject into docs
cd docs && quarto preview                  # Live preview
```
