---
document_id: UIAO_DG_001
title: Diagram Pipeline Governance Rules
version: "2.0"
status: DRAFT
classification: Controlled
owner: Michael Stratton
created_at: 2026-04-18
updated_at: 2026-04-18
boundary: GCC-Moderate
artifact_type: OPERATIONAL
---

# Diagram Pipeline Governance Rules

## 1. Purpose

This document defines the governance rules for all diagrams within the UIAO canonical corpus. It ensures every diagram has a single source of truth (SSOT), machine-trackable metadata, deterministic rendering, and dual-form-factor publishing via the NanoBanana specification.

The diagram pipeline is **universal** — it covers every document category in the UIAO canon: Training, Architecture, Testing, Planning, Governance, Identity, Operations, Enforcement, and Data/Evidence.

## 2. Core Principles

### 2.1 Canon Supremacy for Diagrams

- Every diagram **must** have exactly one Mermaid source file (`.mmd`) in `diagrams/sources/{category}/`.
- The `.mmd` file is the **single source of truth**. All rendered outputs are DERIVED artifacts.
- No rendered image (PNG, SVG, PDF) may exist without a corresponding `.mmd` source.
- Orphaned renders (no matching source) are **CI-blocking**.

### 2.2 Dual-Form-Factor Requirement

Every diagram source **must** produce two rendered outputs:

| Form Factor | Directory | Purpose |
|---|---|---|
| **Full** | `diagrams/rendered/full/` | Complete detail for documentation, appendices, and deep reference |
| **Nano** | `diagrams/rendered/nano/` | Compact, high-density summary for dashboards, slides, and inline embedding |

### 2.3 Metadata Schema Compliance

Every `.mmd` source file **must** include a YAML frontmatter header that validates against `diagrams/governance/diagram-metadata-schema.yaml`. Required fields:

- `diagram_id` — unique identifier (format: `DIAG_NNN`)
- `title` — human-readable title
- `version` — `Major.Minor`
- `status` — `DRAFT | ACTIVE | DEPRECATED`
- `owner` — responsible individual
- `document_category` — one of the 9 canonical categories
- `form_factors` — array, must include `full` and `nano`
- `source_format` — must be `mermaid`
- `created_at` / `updated_at` — ISO 8601 dates
- `boundary` — must be `GCC-Moderate`

### 2.4 Category Structure

Diagrams are organized by document category with reserved DIAG_ID ranges:

| Category | ID Range | Directory | Canon Coverage |
|---|---|---|---|
| **Training** | DIAG_001–DIAG_009 | `sources/training/` | UIAO_122, UIAO_125, UIAO_128 |
| **Architecture** | DIAG_010–DIAG_019 | `sources/architecture/` | UIAO_100–UIAO_102 |
| **Testing** | DIAG_020–DIAG_029 | `sources/testing/` | UIAO_121, UIAO_123, UIAO_126, UIAO_131 |
| **Planning** | DIAG_030–DIAG_039 | `sources/planning/` | UIAO_127, UIAO_118 |
| **Governance** | DIAG_040–DIAG_049 | `sources/governance/` | UIAO_001, UIAO_200, UIAO_201 |
| **Identity** | DIAG_050–DIAG_059 | `sources/identity/` | UIAO_129, UIAO_130 |
| **Operations** | DIAG_060–DIAG_069 | `sources/operations/` | UIAO_124, UIAO_117, UIAO_114 |
| **Enforcement** | DIAG_070–DIAG_079 | `sources/enforcement/` | UIAO_111, UIAO_116, UIAO_120 |
| **Data** | DIAG_080–DIAG_089 | `sources/data/` | UIAO_108–UIAO_110, UIAO_113 |

### 2.5 Registry Requirement

Every diagram **must** be registered in `diagrams/registry/diagram-registry.yaml`. Unregistered diagrams are CI-blocking.

## 3. Lifecycle Rules

### 3.1 Creation

1. Author creates `.mmd` source in `diagrams/sources/{category}/` using `_template.mmd`.
2. Diagram ID must fall within the reserved range for its category.
3. Author adds entry to `diagrams/registry/diagram-registry.yaml`.
4. CI validates metadata schema, registry presence, category-ID alignment, and renders both form factors.

### 3.2 Modification

1. Edit only the `.mmd` source file.
2. Increment the `version` field in frontmatter.
3. Update `updated_at`.
4. CI re-renders both form factors automatically.

### 3.3 Deprecation

1. Set `status: DEPRECATED` in the `.mmd` frontmatter.
2. Add `superseded_by: DIAG_NNN` pointer.
3. **Never delete** a source file — deprecation protocol only.
4. Deprecated diagrams are excluded from publishing but retained in the repository.

## 4. Rendering Rules

### 4.1 Deterministic Output

- Rendering **must** be deterministic: same source → same output, every time.
- Rendering scripts live in `diagrams/scripts/` and are the only authorized renderers.
- Manual rendering or ad-hoc tool usage is prohibited for canonical outputs.

### 4.2 Output Naming Convention

Rendered files follow the pattern:

```
{diagram_id}_{short_title}_{form_factor}.{ext}
```

Examples:
- `DIAG_001_Training_Pipeline_full.png`
- `DIAG_040_Canon_Governance_Flow_nano.svg`

### 4.3 Supported Output Formats

| Format | Use Case |
|---|---|
| PNG | Default rendered output for documentation and embedding |
| SVG | Scalable output for web and interactive dashboards |
| PDF | Print-ready output for formal deliverables |

## 5. CI Integration

### 5.1 Validation Checks (CI-Blocking)

- [ ] Every `.mmd` file has valid YAML frontmatter
- [ ] Frontmatter validates against `diagram-metadata-schema.yaml`
- [ ] `document_category` matches the source subdirectory
- [ ] `diagram_id` falls within the reserved range for its category
- [ ] Every `.mmd` file is registered in `diagram-registry.yaml`
- [ ] No orphaned renders exist without a matching source
- [ ] Both `full` and `nano` renders exist for every active source
- [ ] No `FOUO` markings present in any diagram or metadata

### 5.2 Automated Rendering

On merge to `main`:
1. Validate all sources.
2. Render both form factors for any changed `.mmd` files.
3. Commit rendered outputs to `diagrams/rendered/`.

## 6. Provenance

All rendered outputs are DERIVED artifacts. Their provenance chain is:

```
Source: diagrams/sources/{category}/{diagram_id}.mmd
  → Renderer: diagrams/scripts/render.py
    → Output: diagrams/rendered/{full|nano}/{filename}.{ext}
```

Provenance is embedded in rendered file metadata (EXIF/SVG comments) by the rendering script.

## 7. Cross-Reference Rules

Every diagram **should** declare `related_documents` in its frontmatter, linking to the UIAO_NNN canon documents it visualizes. This enables:

- Bidirectional traceability between canon documents and their diagrams
- CI detection of diagrams orphaned from their parent documents
- Automatic diagram embedding in documentation site builds
