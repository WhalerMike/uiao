---
title: "Phase 0 — Runtime Provenance Envelope (draft package)"
status: DRAFT
date: 2026-05-15
owner: Michael Stratton
related_strategy: "Whitepaper TARGET → SHIPPED plan (governance-os whitepaper §3)"
---

# Phase 0 — Runtime Provenance Envelope

This draft folder is the foundation PR for closing the two TARGET rows in the
[Governance OS whitepaper](../../../docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd):

| Whitepaper row | Closed by phases |
|---|---|
| Runtime drift (semantic / authz / identity) — `16_DriftDetectionStandard.qmd` | Phase 2 |
| Continuous event-time evidence capture — `15_ProvenanceProfile.qmd` | Phase 1 |

Both phases sit on top of Phase 0. Phase 0 turns the provenance envelope from
documentation prose (15_ProvenanceProfile §3) into a typed contract that
adapter code can produce, validate, hash-chain, and emit to the telemetry
plane. Until that contract exists as a model + schema, every downstream PR
would be re-defining the same envelope ad-hoc.

## What's in this folder

| File | Purpose |
|---|---|
| [adr-070-runtime-provenance-envelope.md](adr-070-runtime-provenance-envelope.md) | The load-bearing ADR — records the inline-at-emit design choice and the sync/async validation split |
| [envelope.schema.json](envelope.schema.json) | Draft JSON Schema (2020-12) for the envelope; lands at `src/uiao/schemas/provenance/envelope.schema.json` |
| [provenance.py](provenance.py) | Pydantic v2 model skeleton; lands at `src/uiao/models/provenance.py` |

## What this draft is NOT

- It is **not** the `emit()` hook on `BaseAdapter` — that's Phase 1.
- It is **not** the telemetry sink for `uiao.provenance.*` events — that's Phase 1.
- It is **not** the three inline runtime drift checks — that's Phase 2.

Phase 0 ships the envelope and the design call; everything else binds to it.

## Promotion plan

When this draft is reviewed and approved:

1. Move `adr-070-*.md` → `src/uiao/canon/adr/`
2. Move `envelope.schema.json` → `src/uiao/schemas/provenance/envelope.schema.json`
3. Move `provenance.py` → `src/uiao/models/provenance.py`
4. Add an `adr-070` row to `src/uiao/canon/adr/adr-index.md`
5. Add the new schema path to `schema-validation.yml` (CI gate)
6. Open the PR titled `phase 0 — runtime provenance envelope as typed contract (ADR-070)`

The PR is intentionally narrow — no adapter code is changed, only canon
(ADR + schema) and an unwired model. Phase 1 then wires the model into
`BaseAdapter.emit()` and the telemetry sink in a follow-on PR.

## Cross-references

- [docs/docs/15_ProvenanceProfile.qmd](../../../docs/docs/15_ProvenanceProfile.qmd) — envelope §3 (prose source of truth)
- [docs/docs/16_DriftDetectionStandard.qmd](../../../docs/docs/16_DriftDetectionStandard.qmd) — drift classes that the envelope feeds
- [src/uiao/canon/adr/adr-006-evidence-determinism.md](../../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — determinism guarantees ADR-070 reuses
- [src/uiao/canon/adr/adr-009-drift-ledger-immutability.md](../../../src/uiao/canon/adr/adr-009-drift-ledger-immutability.md) — immutability the envelope inherits
- [src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md](../../../src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md) — drift classes the envelope cannot re-define
- [src/uiao/substrate/walker.py](../../../src/uiao/substrate/walker.py) — canon-hygiene DRIFT-* detection that ADR-070's inline checks must reuse (not duplicate)
