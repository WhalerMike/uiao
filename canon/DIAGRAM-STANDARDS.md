# UIAO-Core Diagram Standards

> **Canon Document** | Version 1.0 | April 2026
> **Owner:** UIAO Architecture Team
> **Status:** Active

---

## 1. Purpose

This document defines the authoritative standard for diagram generation, rendering, and insertion across the UIAO-Core repository. It eliminates ambiguity between the two diagram pipelines (Gemini Imagen and Mermaid CLI) by establishing explicit routing rules, ownership boundaries, and insertion conventions.

## 2. Pipeline Architecture

UIAO-Core uses a **Structured Hybrid** diagram pipeline:

| Pipeline | Renderer | Scope | Output Path | Trigger |
|---|---|---|---|---|
| **Gemini Imagen 4.0** | AI-generated (Imagen API) | Architecture diagrams in `src/templates/` | `assets/generated_diagrams/` | `deploy.yml` |
| **Mermaid CLI** | Deterministic (mmdc) | All other diagrams repo-wide | `assets/images/mermaid/` | `render-and-insert-diagrams.yml` |

### 2.1 Execution Order

1. `render-and-insert-diagrams.yml` runs first (Mermaid CLI)
2. `deploy.yml` runs second (Gemini Imagen), gated by `needs: render-and-insert`
3. No file is ever processed by both pipelines

## 3. Routing Rules

### 3.1 Owner Tag (Authoritative Gate)

Any Markdown file may declare its diagram owner via YAML frontmatter:

```yaml
---
diagram-owner: gemini   # or: mermaid (default)
---
```

- Files tagged `diagram-owner: gemini` are **skipped** by the Mermaid CLI workflow
- Files tagged `diagram-owner: mermaid` (or untagged) are **skipped** by the Gemini pipeline
- The owner tag is the authoritative routing gate

### 3.2 Folder-Based Routing (Fallback)

When no owner tag is present, routing follows folder conventions:

| Folder | Default Owner | Rationale |
|---|---|---|
| `src/templates/` | Gemini | Architecture docs for ATO/FedRAMP packages |
| `docs/` | Mermaid CLI | Operational and reference documentation |
| `canon/` | Mermaid CLI | Canonical compliance specifications |
| `templates/` | Mermaid CLI | Jinja2 template sources |
| `visuals/` | Mermaid CLI | Standalone `.mermaid` source files |

### 3.3 YAML Catalog Routing

Diagrams defined in YAML catalogs are always owned by Mermaid CLI:

- `data/diagrams.yml` -- Mermaid CLI renders all entries
- `canon/diagrams.yaml` -- Mermaid CLI renders all entries

## 4. Diagram Types and Ownership

### 4.1 Decision Matrix

| Diagram Type | Owner | Rationale |
|---|---|---|
| System architecture (UIAO overlay, data flow) | Gemini | High-fidelity FedRAMP blueprint aesthetic |
| Authorization boundary | Gemini | ATO package requirement, must be polished |
| Control plane architecture | Gemini | Leadership briefing quality |
| Flowcharts (operational, incident, lifecycle) | Mermaid CLI | Deterministic, auditable, source-preserved |
| Sequence diagrams (API, auth, integration) | Mermaid CLI | Precision matters more than aesthetics |
| Gantt charts (roadmaps, timelines) | Mermaid CLI | Native Mermaid type |
| State diagrams (identity lifecycle, trust) | Mermaid CLI | Deterministic rendering required |
| Compliance control mappings | Mermaid CLI | Must match YAML catalog exactly |

## 5. Insertion Conventions

### 5.1 Mermaid Code Blocks (in Markdown)

Mermaid CLI replaces fenced mermaid blocks with:
1. A PNG image reference
2. A collapsible `<details>` block preserving the source

### 5.2 YAML Catalog Keys

Use HTML comments in Markdown to reference catalog diagrams:

```markdown
<!-- diagram:enforcement_pipeline -->
```

The Mermaid CLI workflow replaces these with rendered PNGs.

### 5.3 Visual File References

Reference standalone visual files from `visuals/`:

```markdown
![Identity Trust Lifecycle](../visuals/identity_trust_lifecycle.png)
```

### 5.4 Gemini-Generated Diagrams

Gemini writes processed Markdown to `build/templates/` (not in-place). Source files in `src/templates/` are never modified. Pandoc compiles from the build directory.

## 6. Style Standards

### 6.1 Gemini Imagen Style Guide

- White background (mandatory)
- No shadows, gradients, or 3D effects
- Clean black lines, sans-serif labeling
- Blueprint aesthetic suitable for FedRAMP specifications
- Centered, balanced composition with clear whitespace

### 6.2 Mermaid CLI Style

- Transparent background (default)
- Resolution: 2048x1536 minimum
- Standard Mermaid theme (no custom CSS overrides)

## 7. Output Paths

| Pipeline | Output Directory | Naming Convention |
|---|---|---|
| Gemini Imagen | `assets/generated_diagrams/` | `diagram_{uuid8}.png` |
| Mermaid CLI (standalone) | `assets/images/mermaid/` | `{source_stem}.png` |
| Mermaid CLI (YAML catalog) | `assets/images/mermaid/` | `{yaml_key}.png` |

## 8. Conflict Prevention

1. **No dual processing**: The owner tag and folder routing ensure no file is touched by both pipelines
2. **Serialized execution**: `deploy.yml` depends on `render-and-insert-diagrams.yml`
3. **Separate output paths**: Gemini and Mermaid never write to the same directory
4. **Source preservation**: Gemini writes to `build/`, Mermaid preserves source in `<details>` blocks

## 9. Migration Notes

- `src/templates/` does not yet exist; create it when architecture documents are ready for Gemini rendering
- Existing `.mermaid` files in `visuals/` are exclusively Mermaid CLI owned
- Existing Gemini-generated PNGs in `visuals/` (e.g., `cyberark_identity_vault.png`) are static assets, not pipeline outputs

---

**Changelog:**
- v1.0 (April 2026): Initial standard establishing structured hybrid pipeline
