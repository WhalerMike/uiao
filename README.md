# UIAO Core — Generation Engine & Adapter Framework

[![CI](https://github.com/WhalerMike/uiao-core/actions/workflows/ci.yml/badge.svg)](https://github.com/WhalerMike/uiao-core/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![FedRAMP Moderate](https://img.shields.io/badge/FedRAMP-Moderate%20Rev%205-orange.svg)](#control-library-status)
[![Controls](https://img.shields.io/badge/controls-247%20(163%20base%20%2B%2084%20enhancements)-blueviolet.svg)](#control-library-status)

**Repository:** `uiao-core`
**Role:** Machine-readable tooling — OSCAL generation, adapter framework, Python engine, schemas
**Classification:** CUI/FOUO

---

## What This Repository Is

`uiao-core` is the **generation engine and adapter framework** for the Unified Identity-Addressing-Overlay Architecture (UIAO) — a federal network modernization program targeting FedRAMP Moderate Rev 5 compliance. It transforms YAML definitions into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM artifacts.

- **Python generation engine** (`src/`) — transforms YAML canon into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM
- **Control library** (`data/control-library/`) — 247 granular NIST controls covering the full FedRAMP Moderate baseline
- **Adapter framework** — standardized interfaces connecting vendor systems (Entra, Infoblox, CyberArk, ServiceNow, Palo Alto, Cisco, SD-WAN) to the UIAO schema
- **JSON schemas** (`schemas/`) — validation schemas for KSI mappings, OSCAL profiles, drift detection
- **Scripts** (`scripts/`) — crosswalk validation, drift checks, pre-commit hooks, directory enforcement
- **Tests** (`tests/`) — unit and integration tests for the generation pipeline

---

## Documentation Canon — Separation Notice

> **This repository is the engine, not the documentation source.**

The canonical `.qmd` source files, YAML data schemas, rendered HTML site, and Quarto pipeline live in **[uiao-docs](https://github.com/WhalerMike/uiao-docs)**.

| What | Where |
|------|-------|
| 20+ canonical documents (`.qmd`) | [uiao-docs](https://github.com/WhalerMike/uiao-docs) |
| YAML data schemas (30 files) | [uiao-docs/data/](https://github.com/WhalerMike/uiao-docs/tree/main/data) |
| Rendered HTML site | [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html) |
| OSCAL generation engine | **This repo** (`src/`) |
| Control library (247 controls) | **This repo** (`data/control-library/`) |
| Adapter framework | **This repo** (`src/adapters/`) |
| JSON validation schemas | **This repo** (`schemas/`) |
| Operational wiki | [uiao-docs wiki](https://github.com/WhalerMike/uiao-docs/wiki) |

See the [Repository Ownership & SSOT Policy](https://github.com/WhalerMike/uiao-docs/wiki/Repository-Ownership-and-SSOT-Policy) for the full ownership table.

---

## Control Library Status

The control library covers the **full FedRAMP Moderate Rev 5 baseline** with 247 granular control files.

| Metric | Value |
|--------|-------|
| Total controls | **247** (163 base + 84 enhancements) |
| Parameter coverage | **86.7%** |
| KSI rules coverage | **163 rules — schema + index complete, enrichment in progress** |
| Implementation statements | **27.4%** |

Each control is a standalone YAML file in `data/control-library/` following the naming convention `<family>-<number>.yml` (e.g., `AC-2.yml`) with enhancements as `<family>-<number>(<enhancement>).yml` (e.g., `AC-2(3).yml`).

---

## Architecture

### Two-Repo Model

```
┌──────────────────────────────────┐      ┌──────────────────────────────────┐
│          uiao-core               │      │          uiao-docs               │
│  (this repo)                     │      │  (documentation canon)           │
│                                  │      │                                  │
│  Python engine + adapters        │      │  .qmd source files               │
│  OSCAL generation pipeline       │─────>│  Quarto pipeline                 │
│  Control library (247 controls)  │      │  Rendered HTML site              │
│  JSON schemas + validators       │      │  YAML data schemas               │
└──────────────────────────────────┘      └──────────────────────────────────┘
```

### Generation Pipeline

```
YAML definitions (generation-inputs/)
        │
        ▼
Python generation engine (src/uiao_core/generators/)
        │
        ├──> OSCAL JSON (SSP, POA&M, profiles)
        ├──> Markdown / DOCX / PPTX
        ├──> CycloneDX SBOM
        └──> Mermaid diagrams → PNG
```

### Diagram Pipeline

`generation-inputs/diagrams.yaml` is SSOT for all Mermaid diagrams:

```
diagrams.yaml → generate_diagrams_from_canon() → visuals/*.mermaid → render_mermaid_file() → assets/images/mermaid/*.png
```

<!-- TODO: Add architecture diagram (Mermaid or PNG) -->

### Source Layout

```
uiao-core/
├── src/uiao_core/
│   ├── cli/                # Typer CLI app and subcommands
│   ├── generators/         # OSCAL, SSP, POA&M, DOCX, PPTX, SBOM, diagram generators
│   ├── adapters/           # Vendor system interfaces (Big 7)
│   ├── collectors/         # Data collectors for vendor systems
│   ├── evidence/           # Bundler, collector, linker for compliance evidence
│   ├── validators/         # Schema and drift validators
│   ├── models/             # Pydantic models
│   ├── monitoring/         # Telemetry and health checks
│   ├── onboarding/         # JML (Joiner/Mover/Leaver) scenarios
│   ├── abstractions/       # Provider interface contracts
│   ├── dashboard/          # Dashboard components
│   └── utils/              # Shared utilities
├── data/
│   ├── control-library/    # 247 NIST control YAML files (FedRAMP Moderate)
│   └── vendor-overlays/    # Big 7 vendor integration specs
├── schemas/                # JSON validation schemas (KSI, UDC, UIAO API)
├── templates/              # Jinja2 templates for DOCX/PPTX rendering
├── generation-inputs/      # YAML definitions driving the generation engine
├── scripts/                # Utility scripts (crosswalk, validation, hooks)
├── tests/                  # Unit and integration tests
└── .github/workflows/      # 23 GitHub Actions workflows
```

---

## How Adapters Work

The UIAO adapter framework is intentionally **lightweight and sits outside the main data path**.
Its only job is to **create alignments** — exactly like a DNS resolver.

It does **not** perform the actual conversions into OSCAL JSON, SSPs, POA&Ms, or SBOMs.
Those happen downstream in the `generators/` layer.
The adapters simply "tell the engine how to get there."

### DNS Analogy

| DNS Concept              | UIAO Adapter Equivalent                          | What It Does |
|--------------------------|--------------------------------------------------|--------------|
| Domain name              | YAML canon (Single Source of Truth)              | The one authoritative address |
| DNS resolver             | Adapter (ServiceNow, Entra, Palo Alto, etc.)     | "Tells you how to get there" |
| IP address returned      | Vendor-overlay + claim alignment                 | Pointer + mapping + evidence hash |
| Recursive lookup         | Collector → normalize → overlay                  | Fast, repeatable, no data duplication |
| TTL / cache invalidation | Drift detection                                  | Continuous validation against canon |

### What an Adapter Actually Does (Step-by-Step)

1. **Collector** reaches out to the vendor system (API, SDK, database, etc.) using secure credentials.
2. **Adapter** normalizes the raw data into UIAO schema concepts (identity as root namespace).
3. **Adapter** builds a vendor-specific **overlay** (stored in `data/vendor-overlays/`) and lightweight claims with evidence links.
4. **Engine** merges the alignment into the canon and hands it to the generators for full artifact creation.

This keeps SSOT pure, makes adapters swappable, and lets you add a new Big 7 vendor in hours instead of weeks.

Result: No more manual spreadsheets, no more copy-paste into FedRAMP artifacts, and real-time drift detection from the systems you already own.

---

## Quick Start

```bash
# Install in development mode
pip install -e ".[dev]"

# Run CI test subset
pytest tests/test_models.py tests/test_cli.py tests/test_workflow_serialization.py -v --tb=short

# Lint
ruff check --fix src/

# Type check
mypy src/uiao_core/
```

## CLI

The `uiao` CLI (typer-based) is the primary interface:

```bash
uiao --version
uiao generate-ssp --canon <path> --data-dir data/ --output exports/
uiao generate-diagrams        # Renders Mermaid → PNG
uiao generate-docs             # Full doc generation
uiao generate-sbom --output sbom.cyclonedx.json
uiao validate <path>
uiao canon-check --dir <path>
```

---

## Roadmap

### Completed

- [x] Full FedRAMP Moderate baseline — 247 controls (163 base + 84 enhancements)
- [x] 86.7% parameter coverage across control library
- [x] OSCAL SSP and POA&M generation pipeline
- [x] Big 7 vendor adapter framework (Entra, Infoblox, CyberArk, ServiceNow, Palo Alto, Cisco, SD-WAN)
- [x] CycloneDX SBOM generation
- [x] Mermaid diagram pipeline from YAML SSOT
- [x] 23 GitHub Actions CI/CD workflows
- [x] ServiceNow adapter — first real Big 7 implementation (alignment-only, DNS pattern)

### In Progress

- [ ] Implementation statements — expand from 27.4% to full coverage
- [ ] Parameter coverage — close remaining 13.3% gap

### Next Major Tasks

- [x] **KSI rules** — 163 indicators in 7 categories, schema + master index live
- [ ] Evidence linker integration with OSCAL back-matter
- [ ] GPG-signed commit hard gate (currently advisory)
- [ ] FedRAMP 20x alignment updates
- [ ] Entra adapter — Big 7 #2 (identity is the root namespace)
- [ ] `data/vendor-overlays/servicenow.yaml` — overlay spec for ServiceNow control mappings
- [ ] CLI command: `uiao adapter run servicenow`

---

## UIAO Overview

UIAO (Unified Identity-Addressing-Overlay Architecture) is a federal network modernization program that replaces legacy infrastructure silos with a unified, identity-driven, cloud-optimized architecture.

It provides deterministic identity correlation and cross-service telemetry across six control planes: **Identity**, **Addressing**, **Overlay**, **Telemetry**, **Management**, and **Governance**. UIAO enables agencies to safely extract authoritative claims from legacy systems while maintaining provenance, drift detection, and continuous compliance.

The architecture is specified across a 20-document modernization canon maintained in [uiao-docs](https://github.com/WhalerMike/uiao-docs), aligned with Zero Trust, TIC 3.0, NIST 800-63, and FedRAMP 20x.

### Eight Core Concepts

1. **Single Source of Truth (SSOT)** — Every claim has one authoritative origin. All other representations are pointers, not copies.
2. **Conversation as the atomic unit** — Every interaction binds identity, certificates, addressing, path, QoS, and telemetry.
3. **Identity as the root namespace** — Every IP, certificate, subnet, policy, and telemetry event derives from identity.
4. **Deterministic addressing** — Addressing is identity-derived and policy-driven.
5. **Certificate-anchored overlay** — mTLS anchors tunnels, services, and trust relationships.
6. **Telemetry as control** — Telemetry is a real-time control input, not passive reporting.
7. **Embedded governance and automation** — Governance is executed through orchestrated workflows.
8. **Public service first** — Citizen experience, accessibility, and privacy are top-level design constraints.

---

## License

[Apache License 2.0](LICENSE)
