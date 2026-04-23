# UIAO Diagram Pipeline

**Boundary:** GCC-Moderate · **Status:** DRAFT · **Version:** 2.0

## Overview

This directory contains the complete UIAO **universal** dual-form-factor diagram system. Every canonical diagram exists as a single **Mermaid SSOT source** (`.mmd`) and is rendered into two output form factors:

| Form Factor | Codename | Use Case |
|---|---|---|
| **Full** | Banana | Documentation, appendices, deep reference — complete detail |
| **Compact** | NanoBanana | Dashboards, slides, inline embedding — high information density |

The pipeline covers **all 9 UIAO document categories** — Training, Architecture, Testing, Planning, Governance, Identity, Operations, Enforcement, and Data/Evidence — with reserved ID ranges and category-specific subdirectories.

## Directory Structure

```
diagrams/
├── README.md                                     ← You are here
├── governance/
│   ├── DIAGRAM-GOVERNANCE.md                     ← Governance rules (v2.0)
│   └── diagram-metadata-schema.yaml              ← YAML schema with category ranges
├── specs/
│   ├── NANOBANANA-SPEC.md                        ← Dual-output specification
│   └── AUTO-SELECTION-LOGIC.md                   ← Form factor auto-selection rules
├── sources/
│   ├── _template.mmd                             ← Starter template (category-aware)
│   ├── training/                                 ← DIAG_001–009
│   │   ├── DIAG_001_Training_Pipeline.mmd
│   │   ├── DIAG_002_UIAO_Education_Program_Flow.mmd
│   │   └── DIAG_003_UIAO_Adapter_Developer_Training_Path.mmd
│   ├── architecture/                             ← DIAG_010–019
│   │   ├── DIAG_010_UIAO_Platform_Overview.mmd
│   │   ├── DIAG_011_UIAO_Platform_Services_Layer.mmd
│   │   └── DIAG_012_UIAO_Adapter_Segmentation_Model.mmd
│   ├── testing/                                  ← DIAG_020–029
│   │   ├── DIAG_020_UIAO_Three-Tier_Test_Strategy.mmd
│   │   └── DIAG_021_UIAO_Adapter_Conformance_Test_Flow.mmd
│   ├── planning/                                 ← DIAG_030–039
│   │   ├── DIAG_030_UIAO_Project_Plans_Program.mmd
│   │   └── DIAG_031_UIAO_Release_Engineering_Pipeline.mmd
│   ├── governance/                               ← DIAG_040–049
│   │   └── DIAG_040_UIAO_Canon_Governance_Flow.mmd
│   ├── identity/                                 ← DIAG_050–059
│   │   └── DIAG_050_UIAO_Application_Identity_Model.mmd
│   ├── operations/                               ← DIAG_060–069
│   │   ├── DIAG_060_UIAO_Adapter_Operations_Runbook_Flow.mmd
│   │   └── DIAG_061_UIAO_Recovery_Layer.mmd
│   ├── enforcement/                              ← DIAG_070–079
│   │   └── DIAG_070_UIAO_Enforcement_Runtime_Pipeline.mmd
│   └── data/                                     ← DIAG_080–089
│       ├── DIAG_080_UIAO_Drift_Detection_Pipeline.mmd
│       └── DIAG_081_UIAO_Evidence_Graph_and_Data_Lake_Model.mmd
├── rendered/
│   ├── full/                                     ← Full-size (Banana) rendered outputs
│   └── nano/                                     ← Compact (NanoBanana) rendered outputs
├── registry/
│   └── diagram-registry.yaml                     ← Master registry (17 diagrams)
├── scripts/
│   ├── render.py                                 ← Dual-form-factor rendering pipeline (v2.0)
│   └── validate.py                               ← Governance validation pipeline (v2.0)
└── .github/
    └── workflows/
        └── diagrams-ci.yaml                      ← CI: validate on PR, render on merge
```

## Category ID Ranges

| Category | ID Range | Diagrams | Canon Coverage |
|---|---|---|---|
| **Training** | DIAG_001–009 | 3 | UIAO_122, UIAO_125, UIAO_128 |
| **Architecture** | DIAG_010–019 | 3 | UIAO_100–102, UIAO_003 |
| **Testing** | DIAG_020–029 | 2 | UIAO_121, UIAO_123, UIAO_126, UIAO_131 |
| **Planning** | DIAG_030–039 | 2 | UIAO_118, UIAO_127 |
| **Governance** | DIAG_040–049 | 1 | UIAO_001, UIAO_200, UIAO_201 |
| **Identity** | DIAG_050–059 | 1 | UIAO_129, UIAO_130 |
| **Operations** | DIAG_060–069 | 2 | UIAO_114, UIAO_117, UIAO_124 |
| **Enforcement** | DIAG_070–079 | 1 | UIAO_111, UIAO_116, UIAO_120 |
| **Data** | DIAG_080–089 | 2 | UIAO_108–110, UIAO_113 |

## Quick Start

### Create a New Diagram

1. Copy `sources/_template.mmd` to `sources/{category}/DIAG_NNN_Your_Title.mmd`.
2. Choose the correct category subdirectory and ID range.
3. Fill in the YAML frontmatter (diagram_id, title, document_category, owner, etc.).
4. Write your Mermaid diagram definition.
5. Configure `nano_config` to specify which subgraphs collapse in compact mode.
6. Add an entry to `registry/diagram-registry.yaml`.
7. Run validation: `python scripts/validate.py`
8. Render locally: `python scripts/render.py --source DIAG_NNN_Your_Title.mmd --format png`

### Validate All Diagrams

```bash
# All categories
python scripts/validate.py

# Single category
python scripts/validate.py --category testing

# Strict mode (warnings = errors)
python scripts/validate.py --strict
```

Checks performed (all CI-blocking):
- Valid YAML frontmatter on every `.mmd` source
- Schema compliance against `diagram-metadata-schema.yaml`
- `document_category` matches source subdirectory
- `diagram_id` falls within reserved range for its category
- Registry presence in `diagram-registry.yaml`
- No orphaned renders without matching sources
- Both full and nano renders exist for active diagrams
- No prohibited FOUO markings

### Render Diagrams

```bash
# Render all active diagrams in both form factors
python scripts/render.py --all --format png

# Render a specific diagram
python scripts/render.py --source DIAG_040_UIAO_Canon_Governance_Flow.mmd --format svg

# Render only one category
python scripts/render.py --category testing --format png

# Render only the nano form factor
python scripts/render.py --all --format png --form-factor nano

# Dry run (validate without rendering)
python scripts/render.py --all --dry-run
```

**Prerequisites:** Node.js with `@mermaid-js/mermaid-cli` (`npm install -g @mermaid-js/mermaid-cli`) and Python with PyYAML (`pip install pyyaml`).

## Governance

All diagrams are governed by [DIAGRAM-GOVERNANCE.md](governance/DIAGRAM-GOVERNANCE.md) (UIAO_DG_001 v2.0), which enforces:

- **Canon Supremacy** — `.mmd` sources are the single source of truth
- **Dual-Form-Factor Requirement** — every diagram produces both Full and Nano outputs
- **Category Structure** — 9 categories with reserved ID ranges and matching subdirectories
- **Metadata Schema Compliance** — all frontmatter validates against the schema
- **Registry Requirement** — every diagram must be registered
- **Cross-Reference Traceability** — diagrams link to their parent UIAO_NNN documents
- **Deprecation Protocol** — never delete; set status to DEPRECATED with `superseded_by`

## Key Specifications

| Document | ID | Description |
|---|---|---|
| [Governance Rules](governance/DIAGRAM-GOVERNANCE.md) | UIAO_DG_001 | Lifecycle, rendering, CI, category, and provenance rules |
| [NanoBanana Spec](specs/NANOBANANA-SPEC.md) | UIAO_DG_002 | Dual-output rendering specification |
| [Auto-Selection Logic](specs/AUTO-SELECTION-LOGIC.md) | UIAO_DG_003 | Context-based form factor selection |
| [Metadata Schema](governance/diagram-metadata-schema.yaml) | — | YAML validation schema with category ID ranges |

## CI Integration

The GitHub Actions workflow (`.github/workflows/diagrams-ci.yaml`) runs on every push and PR that touches `diagrams/`:

1. **Validate** — runs `scripts/validate.py --strict` (all 8 checks)
2. **Render** — runs `scripts/render.py --all --format png` (on merge to main)
3. **Commit** — auto-commits rendered outputs back to the repository

## Form Factor Auto-Selection

Consuming systems (docs sites, dashboards, slide generators) use the [Auto-Selection Logic](specs/AUTO-SELECTION-LOGIC.md) to choose between Full and Nano outputs based on rendering context:

- Container ≥ 800px → **Full**
- Container < 800px → **Nano**
- Email / notification → **Nano** (always)
- Explicit override via `<!-- UIAO-DIAGRAM: DIAG_001 form_factor=full -->` → respected

When Nano is displayed, a discoverable link to the Full version is always provided.
