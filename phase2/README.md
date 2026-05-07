# `phase2/` — Phase 2 architecture artifacts

This directory holds the architecture-artifact layer for the
**Phase 2 — Governance OS Deployment** chapter of the customer-facing
modernization program (see
[`docs/customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd`](../docs/customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd)).

## Generation pipeline

```
canon/phase2/UIAO_Phase2_TSA.psd1     ← source model (PowerShell data file)
            ↓
tools/Write-Phase2TSA.ps1              ← generator
            ↓
phase2/UIAO_P2_TSA_Overview.md         ← generated overview
phase2/_legacy/UIAO_P2_DOM_*.md        ← prior generator output
phase2/{domains,lifecycles,...}/*.md   ← newer scaffolds (most are TBD)
```

The source-of-truth is the `.psd1` model. Markdown files here are
**derived**, not authored — regenerate by running
`tools/Write-Phase2TSA.ps1` against the model.

## Naming

This subtree uses the `UIAO_P2_NNN` namespace (e.g., `UIAO_P2_201`,
`UIAO_P2_TSA_001`). It is **distinct from** the canonical `UIAO_NNN`
allocation in
[`src/uiao/canon/document-registry.yaml`](../src/uiao/canon/document-registry.yaml).
Phase 2 artifacts are not registered there.

## Layout

| Path | Contents |
|---|---|
| [`UIAO_Phase2_Index.md`](UIAO_Phase2_Index.md) | Master index of all `UIAO_P2_NNN` docs and their diagram references |
| `_legacy/` | Prior generator output (`UIAO_P2_DOM_DOM_*`, `UIAO_P2_TSA_Overview.md`) — kept for reference |
| `apps/` `baselines/` `domains/` `governance/` `lifecycles/` `network/` `registry/` `transformations/` `workloads/` | Newer per-topic scaffolds — most files are placeholder TBDs pending design sessions |
| `diagrams/` | PlantUML sources for Phase 2 domain diagrams (e.g., `domains/identity/ID-201-A01.puml`) |

## Status

Most domain/lifecycle/transformation files contain only the placeholder
text "To be defined in Phase 2 design sessions." The generator emits
the scaffold; design content is filled in later. Do not expect prose
content here until Phase 2 design sessions land.

## Relationship to canon

Nothing in this directory is canon. Canon authority is at
[`src/uiao/canon/`](../src/uiao/canon/). When Phase 2 design output
matures, individual artifacts may be promoted into canon via the
standard `UIAO_NNN` allocation process documented in
[`AGENTS.md`](../AGENTS.md) and [`CONTRIBUTING.md`](../CONTRIBUTING.md).
