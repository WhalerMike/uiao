# UIAO Core — Generation Engine & Adapter Framework

**Repository:** `uiao-core`
**Role:** Machine-readable tooling — OSCAL generation, adapter framework, Python engine, schemas
**Classification:** CUI/FOUO

---

## What This Repository Is

`uiao-core` is the **generation engine and adapter framework** for the Unified Identity-Addressing-Overlay Architecture (UIAO). It contains:

- **Python generation engine** (`src/`) — transforms YAML canon into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM
- **Adapter framework** — standardized interfaces connecting vendor systems to the UIAO schema
- **JSON schemas** (`schemas/`) — validation schemas for KSI mappings, OSCAL profiles, drift detection
- **Scripts** (`scripts/`) — crosswalk validation, drift checks, pre-commit hooks, directory enforcement
- **Tests** (`tests/`) — unit and integration tests for the generation pipeline

## What This Repository Is NOT

This repository does not contain the documentation canon. The canonical `.qmd` source files, YAML data schemas, rendered HTML site, and Quarto pipeline live in **[uiao-docs](https://github.com/WhalerMike/uiao-docs)**.

| What | Where |
|------|-------|
| 20+ canonical documents (`.qmd`) | [uiao-docs](https://github.com/WhalerMike/uiao-docs) |
| YAML data schemas (30 files) | [uiao-docs/data/](https://github.com/WhalerMike/uiao-docs/tree/main/data) |
| Rendered HTML site | [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html) |
| OSCAL generation engine | **This repo** (`src/`) |
| Adapter framework | **This repo** (`src/adapters/`) |
| JSON validation schemas | **This repo** (`schemas/`) |
| Operational wiki | [uiao-docs wiki](https://github.com/WhalerMike/uiao-docs/wiki) |

See the [Repository Ownership & SSOT Policy](https://github.com/WhalerMike/uiao-docs/wiki/Repository-Ownership-and-SSOT-Policy) for the full ownership table.

---

## Repository Structure

```
uiao-core/
├── src/                    # Python generation engine
│   ├── adapters/           # Vendor adapter implementations
│   ├── generators/         # OSCAL, Markdown, DOCX, PPTX generators
│   └── validators/         # Schema and drift validators
├── schemas/                # JSON schemas (KSI, OSCAL, drift)
├── scripts/                # Utility scripts (crosswalk, validation, hooks)
├── tests/                  # Unit and integration tests
├── generation-inputs/      # Machine-readable generation inputs (YAML definitions)
├── visuals/                # Visual asset sources
├── docs/                   # Non-document assets only (images, pitch deck)
│   └── README.md           # Points to uiao-docs for all documentation
├── machine/                # Machine-readable artifact definitions
├── templates/              # Jinja2 templates for document generation
└── compliance/             # FedRAMP reference data
```

---

## Intentional Exceptions

Two items in this repo may look like documentation artifacts but are intentionally retained:

| Item | Why It's Here |
|------|---------------|
| `_quarto.yml` | Simplified stub kept for local generation script testing. The canonical Quarto pipeline lives in [uiao-docs](https://github.com/WhalerMike/uiao-docs). |
| `generation-inputs/` | Machine-readable YAML definitions (diagram specs, visual manifest, pitch deck data, project plan data) that drive the Python generation engine in `src/`. These are inputs to code, not human-readable documentation. |

---

## UIAO Overview

UIAO (Unified Identity-Addressing-Overlay Architecture) is a federal network modernization program that replaces legacy infrastructure silos with a unified, identity-driven, cloud-optimized architecture.

It provides deterministic identity correlation and cross-service telemetry across six control planes: **Identity**, **Addressing**, **Overlay**, **Telemetry**, **Management**, and **Governance**. UIAO enables agencies to safely extract authoritative claims from legacy systems while maintaining provenance, drift detection, and continuous compliance.

The architecture is specified across a 20-document modernization canon maintained in [uiao-docs](https://github.com/WhalerMike/uiao-docs), aligned with Zero Trust, TIC 3.0, NIST 800-63, and FedRAMP 20x.

---

## Eight Core Concepts

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
