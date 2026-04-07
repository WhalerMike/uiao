# UIAO Documentation Site

Welcome to the Unified Integration Architecture Operations (UIAO) documentation portal.

!!! tip "Start Here -- Canon Overview"
    New to UIAO? Start with the **[Canon Overview](canon/index.md)** -- the authoritative entry point
    for the entire governance corpus. It explains the structure, authority model, and how everything connects.

## Quick Start

| Resource | Description |
|----------|-------------|
| [Canon Overview](canon/index.md) | **Start here** -- governance structure and authority model |
| [Corpus Status Dashboard](canon/corpus-status-dashboard.md) | Document maturity and governance health at a glance |
| [Document Library](documents/index.md) | Browse all UIAO documents with status badges |
| [ADR Index](adr/index.md) | Architecture decisions by theme and lifecycle state |
| [Contributor Guide](contributing.md) | How to add or update documentation |
| [Request Export](request-export.md) | Request PDF or Word exports of any document |

## Operating Environment

This site is built with MkDocs Material and deployed via GitHub Pages from the
[uiao-docs repository](https://github.com/WhalerMike/uiao-docs).

## Site Conventions

- **Document Identifiers** follow the `UIAO_<AppendixLetter>_<NN>` pattern (e.g., `UIAO_A_01`)
- **Status Badges** indicate document maturity: Current, Draft, Needs Replacing, Needs Creating, Deprecated
- **ADR lifecycle:** PROPOSED -> ACCEPTED -> SUPERSEDED | DEPRECATED
- **Dark Mode** is available via the toggle in the header
- **Search** covers all content including ADRs, appendices, and canon documents

## Governance Canon

The Canon is organized into five appendices plus the canonical rules, glossary, and ADR corpus:

| Appendix | Domain | Key Topics |
|----------|--------|------------|
| [A -- Adapter Plane](appendix/a-adapter-plane/index.md) | Integration adapters | Lifecycle, sandbox, hot-swap, health |
| [B -- Truth Fabric](appendix/b-truth-fabric/index.md) | Canonical state | Claim schema, identity anchoring, multi-cloud |
| [C -- Drift Fabric](appendix/c-drift-fabric/index.md) | Drift detection | Detection algorithm, taxonomy, containment |
| [D -- Evidence Fabric](appendix/d-evidence-fabric/index.md) | Audit and compliance | Determinism, lifecycle, signing, correlation |
| [E -- Governance Plane](appendix/e-governance-plane/index.md) | Governance process | ARB, mission corridors, cross-fabric consistency |
