---
title: "Phase 1 — Adapter emit() Hook + Continuous Event-Time Evidence Capture (draft package)"
status: DRAFT
date: 2026-05-15
owner: Michael Stratton
depends_on: Phase 0 (ADR-070 ACCEPTED)
related_strategy: "Whitepaper TARGET → SHIPPED plan (governance-os whitepaper §3)"
---

# Phase 1 — Adapter emit() Hook + Continuous Event-Time Evidence Capture

This is the follow-on to Phase 0. Phase 0 ships the typed envelope; Phase 1
wires it into the adapter surfaces and persists envelopes to the event log
that OSCAL bundles read from. Together they close the whitepaper row
**"Continuous event-time evidence capture"** (currently TARGET).

## Finding that re-shapes the strategy

When the strategy was first written it assumed a single `BaseAdapter` with
one `emit()` method to wire. **That base class does not exist.** The
substrate has three independent adapter surfaces, each with its own
emission idiom:

| Surface | File | Today's emission idiom | Envelope today |
|---|---|---|---|
| Evidence collectors | [`src/uiao/collectors/base_collector.py`](../../../src/uiao/collectors/base_collector.py) | `collect(ksi_id) -> EvidenceObject` | 3-field `EvidenceProvenance` (collector_id, hash, timestamp) |
| Enforcement adapters | [`src/uiao/enforcement/runtime.py`](../../../src/uiao/enforcement/runtime.py) | `enforce(ir_object, policy, dry_run) -> AdapterResult` | None |
| Modernization adapters | [`src/uiao/adapters/modernization/*`](../../../src/uiao/adapters/modernization/) | Free-form per adapter (no shared base) | None |

Phase 1 ships the three-surface binding as one engineering stream but
separate sub-PRs:

- **Phase 1a — `BaseCollector` envelope upgrade.** Replace the 3-field
  `EvidenceProvenance` with the 10-field `Envelope` from ADR-070. This is
  the lowest-risk surface because there's already an envelope shape to
  upgrade (no greenfield).
- **Phase 1b — `ModernizationAdapter` base class.** Introduce a thin ABC
  with `emit(claim, envelope)`; retrofit existing modernization adapters
  one PR at a time behind a feature flag.
- **Phase 1c — `EnforcementAdapter` envelope on `enforce()`.** Extend
  the result type to carry an `Envelope`. Smallest surface (few enforcement
  adapters today), but most consequential — policy enforcement evidence
  is the highest-value content for an ATO package.
- **Phase 1d — Shared infrastructure.** JSONL provenance event log
  (`evidence/provenance/<adapter>/<yyyy-mm>/*.jsonl`) and the
  `uiao.telemetry.provenance` sink that all three surfaces emit to.

## What's in this folder

| File | Purpose | Lands at |
|---|---|---|
| [adr-071-adapter-emit-hook-and-event-log.md](adr-071-adapter-emit-hook-and-event-log.md) | Records the three-surface binding decision, the legacy `EvidenceProvenance` reconciliation, and the JSONL event-log shape | `src/uiao/canon/adr/` |
| [modernization_adapter.py](modernization_adapter.py) | New `ModernizationAdapter` ABC + `emit()` | `src/uiao/adapters/base.py` |
| [provenance_sink.py](provenance_sink.py) | JSONL provenance event log writer; reused by all three surfaces | `src/uiao/telemetry/provenance.py` |
| [base_collector_upgrade.diff.md](base_collector_upgrade.diff.md) | Diff sketch for the `BaseCollector` envelope upgrade (Phase 1a) | Inline in `src/uiao/collectors/base_collector.py` |
| [migration-plan.md](migration-plan.md) | Adapter-by-adapter retrofit order with feature-flag gate | `src/uiao/canon/specs/` (informative) |

## What this draft is NOT

- It is **not** the runtime drift checks (Phase 2). Phase 1 emits and
  persists the envelope; it does not yet validate `DRIFT-SEMANTIC` /
  `DRIFT-AUTHZ` / `DRIFT-IDENTITY` inline. The hook is in place, but the
  validators are stubs that return `True`.
- It is **not** a rewrite of the legacy `EvidenceProvenance`. The legacy
  3-field shape is preserved as a subset/projection of the new 10-field
  envelope (see ADR-071 §3); existing tests stay green.
- It is **not** the OSCAL pipeline rewrite. Phase 1d adds an event-log
  reader; the existing snapshot-based assembly path is untouched.

## Promotion plan

When this draft is reviewed and approved, Phase 1 ships as **four sub-PRs**
in order:

1. **PR-1d (foundation, lands first)** — `provenance_sink.py` + ADR-071
   ACCEPTED. No adapter code changes; just the shared sink. Allows the
   sink to be reviewed in isolation.
2. **PR-1a** — `BaseCollector` envelope upgrade + new `EvidenceProvenance →
   Envelope` projection. Retrofit the existing collectors (≈4 today).
3. **PR-1b** — `ModernizationAdapter` ABC + first adapter retrofit
   (Active Directory survey adapter as canary). Behind feature flag
   `uiao.envelope.modernization`.
4. **PR-1c** — `EnforcementAdapter.enforce()` envelope extension. Behind
   feature flag `uiao.envelope.enforcement`.

After all four ship, the whitepaper row "Continuous event-time evidence
capture" moves from TARGET to SHIPPED. Phase 2 (runtime drift) then has
a unified hook to bind to.

## Cross-references

- [inbox/drafts/phase0-runtime-provenance-envelope/](../phase0-runtime-provenance-envelope/) — the typed envelope this phase wires
- [src/uiao/collectors/base_collector.py](../../../src/uiao/collectors/base_collector.py) — existing 3-field provenance shape this phase reconciles
- [src/uiao/enforcement/runtime.py](../../../src/uiao/enforcement/runtime.py) — `EnforcementAdapter` to be extended
- [src/uiao/adapters/modernization/](../../../src/uiao/adapters/modernization/) — modernization adapter directory; targets for the `ModernizationAdapter` retrofit
- [src/uiao/canon/adr/adr-006-evidence-determinism.md](../../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — determinism guarantees extended to event-time log replay
- [src/uiao/canon/adr/adr-009-drift-ledger-immutability.md](../../../src/uiao/canon/adr/adr-009-drift-ledger-immutability.md) — immutability the JSONL log inherits
