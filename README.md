# UIAO Core — Generation Engine & Adapter Framework

[![CI](https://github.com/WhalerMike/uiao-core/actions/workflows/ci.yml/badge.svg)](https://github.com/WhalerMike/uiao-core/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)
[![FedRAMP Moderate](https://img.shields.io/badge/FedRAMP-Moderate%20Rev%205-orange.svg)](#control-library-status)
[![Controls](https://img.shields.io/badge/controls-247%20(163%20base%20%2B%2084%20enhancements)-blueviolet.svg)](#control-library-status)

## Mission

> UIAO is a federal compliance and network modernization platform that eliminates
> manual, error-prone compliance machinery and replaces it with a single
> deterministic engine — one strict YAML SSOT that continuously generates every
> required artifact, enforces every required control, and contains drift in
> under 120 seconds.

**What this platform is designed to accomplish:**

- **FedRAMP Moderate Rev 5** — Full 247-control baseline, OSCAL-native SSP/POA&M generation, continuous ATO evidence. Authorization packages are a pipeline output.
- **CISA SCuBA / BOD 25-01** — Live bidirectional governance envelope across covered M365 and cloud platforms. Policy drift is detected, attributed, and evidence-backed automatically.
- **KSI Compliance Engine** — 163 Key Security Indicators across 7 categories, continuously evaluated and embedded in OSCAL back-matter as cryptographically linked evidence.
- **Immutable Evidence Fabric** — Every compliance claim is backed by a tamper-evident bundle (raw output → normalized overlay → KSI result → GPG-signed commit hash). Auditors get a verifiable chain, not a screenshot.
- **Drift Detection in < 120 s** — Every commit and scheduled run validates live state against the YAML canon. Drift is never silently tolerated — always measured, attributed, and actionable.
- **Zero Trust / TIC 3.0** — Identity is the root namespace. Six control planes (Identity, Addressing, Overlay, Telemetry, Management, Governance) implement NIST SP 800-207 and TIC 3.0 as architectural properties, not checkboxes.
- **Future-proof governance** — The adapter framework and KSI schema extend to any new CISA directive, OMB memo, or cloud platform without touching the generation engine.

→ **[Full mission scope, mandate alignment, and architectural invariants: VISION.md](./VISION.md)**

---

**Repository:** `uiao-core`
**Role:** Machine-readable tooling — OSCAL generation, adapter framework, Python engine, schemas
**Classification:** CUI/FOUO

---

## What This Repository Is

`uiao-core` is the **generation engine and adapter framework** for the Unified Identity-Addressing-Overlay Architecture (UIAO) — a federal network modernization program targeting FedRAMP Moderate Rev 5 compliance. It transforms YAML definitions into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM artifacts.

- **Python generation engine** (`src/`) — transforms YAML canon into OSCAL JSON, Markdown, DOCX, PPTX, and CycloneDX SBOM
- - **Control library** (`data/control-library/`) — 247 granular NIST controls covering the full FedRAMP Moderate baseline
  - - **Adapter framework** — standardized interfaces connecting vendor systems (Entra, Infoblox, CyberArk, ServiceNow, Palo Alto, Cisco, SD-WAN) to the UIAO schema
    - - **JSON schemas** (`schemas/`) — validation schemas for KSI mappings, OSCAL profiles, drift detection
      - - **Scripts** (`scripts/`) — crosswalk validation, drift checks, pre-commit hooks, directory enforcement
        - - **Tests** (`tests/`) — unit and integration tests for the generation pipeline
         
          - ---

          ## Documentation Canon — Separation Notice

          > **This repository is the engine, not the documentation source.** The canonical `.qmd` source files, YAML data schemas, rendered HTML site, and Quarto pipeline live in **[uiao-docs](https://github.com/WhalerMike/uiao-docs)**.
          >
          > | What | Where |
          > |------|-------|
          > | 20+ canonical documents (`.qmd`) | [uiao-docs](https://github.com/WhalerMike/uiao-docs) |
          > | YAML data schemas (30 files) | [uiao-docs/data/](https://github.com/WhalerMike/uiao-docs/tree/main/data) |
          > | Rendered HTML site | [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs/docs/index.html) |
          > | OSCAL generation engine | **This repo** (`src/`) |
          > | Control library (247 controls) | **This repo** (`data/control-library/`) |
