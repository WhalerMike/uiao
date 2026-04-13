# UIAO Documentation — Modernization Atlas

**Repository:** `uiao-docs`
**Role:** Canonical documentation source — Quarto pipeline, YAML schemas, rendered site
**Live site:** [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html)
**License:** [MIT](LICENSE)

---

## What This Repository Is

`uiao-docs` is the **single source of truth** for all human-readable UIAO documentation. It contains:

- **124 Quarto `.qmd` source files** (`docs/`) — the 20-document modernization canon plus Phase 5 operations, deep dives, adapters, ADRs, and governance
- **30 YAML data schemas** (`data/`) — program metadata, control planes, compliance matrices, style guide
- **Quarto rendering pipeline** (`_quarto.yml`) — produces HTML, DOCX, and PPTX from a single source
- **CI/CD workflows** (`.github/workflows/`) — auto-build, deploy to GitHub Pages, link validation, changelog generation
- **Styled reference templates** (`data/docx-reference.docx`, `data/pptx-reference.pptx`) — Microsoft Learn aesthetic

The rendered site auto-deploys on every push to `main`.

## Repository Ownership

| What | Where |
|------|-------|
| Documentation canon (`.qmd`) | **This repo** |
| YAML data schemas | **This repo** (`data/`) |
| Rendered HTML site | [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html) (build artifact) |
| OSCAL generation engine | [uiao-core](https://github.com/WhalerMike/uiao-core) |
| Adapter framework | [uiao-core](https://github.com/WhalerMike/uiao-core) |
| Operational wiki | [Wiki](https://github.com/WhalerMike/uiao-docs/wiki) |

See the [SSOT Policy](https://github.com/WhalerMike/uiao-docs/wiki/Repository-Ownership-and-SSOT-Policy) for the full ownership table and duplication rules.

---

## Quick Start

```bash
# Clone
git clone https://github.com/WhalerMike/uiao-docs.git
cd uiao-docs

# Render HTML locally
quarto render --to html

# Preview with live reload
quarto preview
```

Requires [Quarto 1.4+](https://quarto.org/docs/get-started/). See the [Getting Started](https://github.com/WhalerMike/uiao-docs/wiki/Getting-Started) wiki page for full setup.

---

## Canon Structure

The 20 numbered canon documents are organized into six phases:

| Phase | Documents | Focus |
|-------|-----------|-------|
| 1 — Foundational Architecture | 00–02 | Control planes, unified architecture, canon specification |
| 2 — Compliance & Governance | 03–05 | FedRAMP crosswalk, Phase 2 summary, management stack |
| 3 — Program & Leadership | 06–08 | Program vision, leadership briefing, modernization timeline |
| 4 — Index & Cross-Reference | 09–11 | Crosswalk index, directory structure, glossary |
| 4.5 — Extended Reference | 12–14 | AI security, FIMF adapter registry, TIC 3.0 roadmap |
| 5 — Data Governance Substrate | 15–20 | Provenance, drift detection, consent, claims, reconciliation, adapter contract |

Plus 100+ additional documents: Phase 5 operations, deep dives, v1.0 specifications, adapters, ADRs, and governance artifacts.

---

## Navigation

The site uses a structured sidebar with 11 sections. See `_quarto.yml` for the full navigation tree, or browse the [live site](https://whalermike.github.io/uiao-docs/docs/index.html).

---

## UIAO Overview

UIAO (Unified Identity-Addressing-Overlay Architecture) is a federal network modernization program replacing legacy infrastructure silos with a unified, identity-driven, cloud-optimized architecture. It provides deterministic identity correlation and cross-service telemetry across six control planes, aligned with Zero Trust, TIC 3.0, NIST 800-63, and FedRAMP 20x.

### Eight Core Concepts

1. **Single Source of Truth** — Every claim has one authoritative origin.
2. **Conversation as the atomic unit** — Every interaction binds identity, certificates, addressing, path, QoS, and telemetry.
3. **Identity as the root namespace** — Every IP, certificate, subnet, policy, and telemetry event derives from identity.
4. **Deterministic addressing** — Addressing is identity-derived and policy-driven.
5. **Certificate-anchored overlay** — mTLS anchors tunnels, services, and trust relationships.
6. **Telemetry as control** — Telemetry is a real-time control input, not passive reporting.
7. **Embedded governance and automation** — Governance executes through orchestrated workflows.
8. **Public service first** — Citizen experience, accessibility, and privacy are top-level constraints.

---

## Contributing

- See the [Contributing Guidelines](https://github.com/WhalerMike/uiao-docs/wiki/Contributing-Guidelines) wiki page
- Canon documents (00–20) require Canon Steward review for changes
- All contributions must follow the [Style Guide](https://whalermike.github.io/uiao-docs/docs/STYLE-GUIDE.html) and [Format Canon](https://whalermike.github.io/uiao-docs/docs/FORMAT-CANON.html)
- Diagrams use PlantUML (server-rendered PNG) or Gemini AI images — PlantUML is deprecated

---

## CI/CD

5 active workflows run on every push to `main`:

| Workflow | Purpose |
|----------|---------|
| `build-docs.yml` | Renders `.qmd` → HTML, deploys to GitHub Pages |
| `pr-preview.yml` | Renders preview for pull requests |
| `changelog.yml` | Auto-generates CHANGELOG.md |
| `repo-hygiene.yml` | Validates internal links and directory structure |
| `verify-signatures.yml` | Checks commit signature integrity |

16 additional workflows are disabled pending dependency setup.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
