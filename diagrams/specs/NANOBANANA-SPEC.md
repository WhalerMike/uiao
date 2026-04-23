---
document_id: UIAO_DG_002
title: "NanoBanana Dual-Output Specification"
version: "1.0"
status: DRAFT
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
artifact_type: OPERATIONAL
---

# NanoBanana Dual-Output Specification

## 1. Overview

NanoBanana is the UIAO dual-form-factor rendering specification for diagrams. Every canonical diagram produces two outputs from a single Mermaid SSOT source:

| Form Factor | Codename | Target | Characteristics |
|---|---|---|---|
| Full | **Banana** | Documentation, appendices, deep reference | Complete detail, all nodes, full labels, annotations |
| Compact | **NanoBanana** | Dashboards, slides, inline embedding | Collapsed subgraphs, abbreviated labels, high information density |

## 2. Design Principles

### 2.1 Single Source, Dual Output

- **One `.mmd` file** is the canonical source.
- The rendering pipeline reads `nano_config` from frontmatter to produce the compact variant.
- Authors never maintain two separate diagram files for the same concept.

### 2.2 Information Preservation

The NanoBanana (compact) form factor **must** preserve:
- All top-level process flows and decision points
- Critical dependency relationships
- Entry and exit points

The NanoBanana form factor **may** collapse or omit:
- Internal subgraph detail (collapsed to a single labeled node)
- Annotation notes and comments
- Secondary/optional paths
- Detailed attribute lists on nodes

### 2.3 Visual Consistency

Both form factors share:
- Identical color palette and theming
- Consistent node shape semantics (rectangles = processes, diamonds = decisions, etc.)
- Same directional flow (typically top-down or left-right)

## 3. Nano Configuration Schema

The `nano_config` block in diagram frontmatter controls compact rendering:

```yaml
nano_config:
  max_nodes: 12
  collapse_groups:
    - subgraph_validation
    - subgraph_error_handling
  label_mode: abbreviated
  edge_simplification: true
  hide_annotations: true
```

### 3.1 Configuration Fields

| Field | Type | Default | Description |
|---|---|---|---|
| `max_nodes` | integer | 15 | Target maximum visible nodes in nano output |
| `collapse_groups` | string[] | [] | Subgraph IDs to collapse into single summary nodes |
| `label_mode` | enum | `abbreviated` | `full`, `abbreviated`, or `icon_only` |
| `edge_simplification` | boolean | true | Merge parallel edges into single weighted edges |
| `hide_annotations` | boolean | true | Remove note nodes and comment annotations |

### 3.2 Collapse Behavior

When a subgraph is listed in `collapse_groups`:

1. All internal nodes are removed from the nano render.
2. A single summary node replaces the subgraph, labeled with the subgraph title.
3. All edges entering/leaving the subgraph are rerouted to the summary node.
4. The summary node uses a **double-bordered** style to indicate collapsed detail.

```
Full (Banana):                    Nano (NanoBanana):
┌─────────────────┐              ┌═══════════════════┐
│  Validation      │              ║  Validation (5)   ║
│  ┌───┐  ┌───┐   │      →       ╚═══════════════════╝
│  │ A │→ │ B │   │
│  └───┘  └───┘   │
│     ↓            │
│  ┌───┐  ┌───┐   │
│  │ C │→ │ D │   │
│  └───┘  └───┘   │
└─────────────────┘
```

## 4. Rendering Pipeline

### 4.1 Full (Banana) Rendering

1. Parse `.mmd` source file.
2. Apply standard Mermaid theme configuration.
3. Render to target format(s) (PNG, SVG, PDF).
4. Embed provenance metadata.
5. Output to `diagrams/rendered/full/`.

### 4.2 Compact (NanoBanana) Rendering

1. Parse `.mmd` source file.
2. Read `nano_config` from frontmatter.
3. Apply collapse transformations:
   a. Collapse listed subgraphs to summary nodes.
   b. Reroute edges.
   c. Apply label abbreviation rules.
4. Apply edge simplification if enabled.
5. Remove annotation nodes if `hide_annotations` is true.
6. Validate node count against `max_nodes` threshold.
7. Render to target format(s).
8. Embed provenance metadata (including `form_factor: nano`).
9. Output to `diagrams/rendered/nano/`.

### 4.3 Label Abbreviation Rules

When `label_mode: abbreviated`:

| Full Label | Abbreviated |
|---|---|
| "Metadata Schema Validation" | "Schema Valid." |
| "Governance Compliance Check" | "Gov. Check" |
| "Artifact Classification Engine" | "Classify" |

Rules:
- Drop articles and prepositions.
- Truncate to first significant word + abbreviation.
- Maximum 15 characters for nano labels.
- Abbreviation map can be customized per-diagram via `label_overrides` in `nano_config`.

## 5. Quality Gates

### 5.1 Nano Output Validation

- Node count must not exceed `max_nodes` (warning at 80%, error at 100%).
- All top-level flows must be preserved (no disconnected components).
- Every collapsed subgraph summary node must retain at least one inbound and one outbound edge.

### 5.2 Visual Regression

- Both form factors are rendered on every CI run.
- Pixel-diff comparison against previous renders detects unintended visual changes.
- Threshold: >5% pixel diff triggers manual review.

## 6. Extensibility

### 6.1 Custom Form Factors

The pipeline is designed for dual output but can extend to additional form factors:
- **Micro** — icon-only, for status indicators
- **Print** — high-DPI, full annotations, page-break aware

Additional form factors require a governance amendment to `DIAGRAM-GOVERNANCE.md` and schema extension.

### 6.2 Format Support

While Mermaid is the current SSOT format, the pipeline architecture supports adding PlantUML or D2 sources in the future. Each format would require:
- A dedicated parser module in `diagrams/scripts/`.
- Schema extension for `source_format` enum.
- Governance amendment.
