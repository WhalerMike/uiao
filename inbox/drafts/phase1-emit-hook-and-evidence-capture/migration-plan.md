---
title: "Phase 1 — Adapter retrofit migration plan"
status: DRAFT
date: 2026-05-15
depends_on: ADR-070 (ACCEPTED), ADR-071 (ACCEPTED)
---

# Phase 1 — Adapter retrofit migration plan

Phase 1 binds the runtime provenance envelope (ADR-070) to three adapter
surfaces. This document is the **per-adapter migration order** that
governs the rollout. Each entry below corresponds to one PR; each PR is
gated by the relevant feature flag and lands independently.

## Feature flag inventory

Three flags govern the Phase 1 rollout. Each is declared in
[`src/uiao/canon/feature-flags.yaml`](../../../src/uiao/canon/feature-flags.yaml)
with a documented `spec_ref` and `expires_at` per UIAO_119 v2:

| Flag | Surface | spec_ref | Default | Expires |
|---|---|---|---|---|
| `uiao.envelope.collectors` | `BaseCollector._emit_envelope()` | ADR-071 §1 | off | 2026-12-31 |
| `uiao.envelope.modernization` | `ModernizationAdapter.emit()` | ADR-071 §1 | off | 2026-12-31 |
| `uiao.envelope.enforcement` | `EnforcementAdapter.enforce()` envelope field | ADR-071 §1 | off | 2027-03-31 |

A flag flips to `on` once all adapters on that surface have completed at
least Pattern A migration. The `expires_at` removes the flag entirely
once Pattern B is complete for that surface.

## Surface 1 — Collectors (Phase 1a)

Order: lowest-risk first; flag flips between PR-1a.5 and PR-1a.6.

| # | Collector | Path | Pattern | Risk | Notes |
|---|---|---|---|---|---|
| 1a.1 | Foundation: projection classmethods | `collectors/base_collector.py` | n/a | low | No collectors changed; just adds `from_envelope`/`to_envelope` |
| 1a.2 | Test fixture collectors | `tests/fixtures/collectors/` | A | low | Smoke test for auto-promotion path |
| 1a.3 | KSI Evidence Collector | `collectors/ksi/` | B | medium | Highest-value content; full retrofit (Pattern B) up front |
| 1a.4 | AD Survey Collector | `adapters/modernization/active_directory/collector.py` | A | low | Pattern A; promoted to B in Phase 1b alongside the AD modernization adapter retrofit |
| 1a.5 | GCC Boundary Probe Collector | `adapters/modernization/gcc_boundary_probe/collector.py` | A | low | Pattern A; promoted to B in Phase 1b |
| 1a.6 | **Flag flip:** `uiao.envelope.collectors = on` | — | — | low | All four collectors at Pattern A or better |
| 1a.7 | Pattern A → B promotion for AD + GCC collectors | (folded into Phase 1b) | B | medium | Done as part of the modernization adapter retrofit so the adapter and its collector share an envelope construction site |

## Surface 2 — Modernization adapters (Phase 1b)

Order: AD survey adapter as canary; then GCC boundary probe; then the
rest. Each PR ships the new `ModernizationAdapter` ABC subclass for the
named adapter plus the existing adapter's emit-site retrofit.

| # | Adapter | Manifest path | Risk | Notes |
|---|---|---|---|---|
| 1b.1 | Foundation: `ModernizationAdapter` ABC + manifest loader | `src/uiao/adapters/base.py` | low | No adapters changed; just the new ABC |
| 1b.2 | AD Survey adapter (canary) | `adapters/modernization/active_directory/` | medium | First production adapter on the new ABC; observe event-log volume + latency |
| 1b.3 | GCC Boundary Probe adapter | `adapters/modernization/gcc_boundary_probe/` | medium | Second production adapter; validates boundary-aware sink routing |
| 1b.4 | HR-IT adapter | `adapters/modernization/hrit/` | medium | Carries citizen-PII claims; first adapter to exercise the consent_envelope field |
| 1b.5 | PKI adapter | `adapters/modernization/pki/` | low | Small claim volume |
| 1b.6 | **Flag flip:** `uiao.envelope.modernization = on` | — | — | After 4 adapters retrofitted |
| 1b.7+ | Remaining adapters (SCuBA family, Infoblox, BlueCat, future Login.gov/PIV) | — | — | One PR per adapter as they come online; no flag flip needed |

## Surface 3 — Enforcement adapters (Phase 1c)

Smallest surface in scope — currently `NoOpAdapter` plus a small handful
of EPL policy enforcement adapters. Retrofit is straightforward: extend
`AdapterResult` with the `envelope` field, retrofit each enforcement
adapter to construct one.

| # | Adapter | Path | Risk | Notes |
|---|---|---|---|---|
| 1c.1 | `AdapterResult.envelope` field | `enforcement/runtime.py` | low | Optional[Envelope] in v1; defaults None |
| 1c.2 | `NoOpAdapter` retrofit | `enforcement/runtime.py` | low | Synthesizes a degenerate envelope to validate the path |
| 1c.3 | Each concrete enforcement adapter | per-adapter | medium | One PR per adapter; policy-enforcement evidence is the highest-value content for ATO packages |
| 1c.4 | **Flag flip:** `uiao.envelope.enforcement = on` | — | — | After all enforcement adapters retrofitted |
| 1c.5 | `AdapterResult.envelope` becomes required (v2) | `enforcement/runtime.py` | medium | Flag removal; degenerate envelopes no longer accepted |

## Shared infrastructure (Phase 1d)

Ships **before** any of the surface retrofits — provides the sink that
all three surfaces emit to.

| # | Component | Path | Risk | Notes |
|---|---|---|---|---|
| 1d.1 | Provenance sink module | `src/uiao/telemetry/provenance.py` | low | Sync validators stubbed True for Phase 1; Phase 2 populates |
| 1d.2 | Event-log writer + sidecar `.idx` | (in 1d.1) | low | Append-only; atomic per-line write |
| 1d.3 | OSCAL `--source event-log` mode | `src/uiao/generators/oscal.py` | medium | New mode; default unchanged |
| 1d.4 | Substrate walker post-hoc mutation check | `src/uiao/substrate/walker.py` | low | New `_scan_provenance_log` that compares each line hash to the sidecar `.idx` |
| 1d.5 | Reproducibility test | `tests/test_oscal_event_log_replay.py` | low | snapshot-mode and event-log-mode produce byte-identical bundle hash for the same accepted-envelope set |

## Sequencing

```
Phase 0 (ACCEPTED) ── ADR-070 + Envelope model + schema
        │
        ▼
Phase 1d.1–1d.4 ── shared infra (sink + event log + walker check)
        │
        ├──────────────────┬──────────────────┐
        ▼                  ▼                  ▼
Phase 1a (collectors)   Phase 1b (mod.)   Phase 1c (enforcement)
        │                  │                  │
        ▼                  ▼                  ▼
   Flag flip 1a.6   Flag flip 1b.6     Flag flip 1c.4
        │                  │                  │
        └──────────────────┴──────────────────┘
                           │
                           ▼
            Phase 1d.5 reproducibility test green
                           │
                           ▼
        Whitepaper row "Continuous event-time evidence capture" → SHIPPED
                           │
                           ▼
                  Phase 2 (runtime drift)
```

## Exit criteria for Phase 1

The "Continuous event-time evidence capture" row flips to SHIPPED when
**all** of the following hold:

1. ADR-070 and ADR-071 both ACCEPTED in `src/uiao/canon/adr/`.
2. All three feature flags (`uiao.envelope.*`) flipped on.
3. Reproducibility test (1d.5) passing in CI.
4. Substrate walker emits zero P1 findings related to provenance event
   log mutation across a 30-day window.
5. At least one production adapter on each surface has been emitting
   envelopes for 7 consecutive days without rejected emissions
   indicating broken envelope construction.

Phase 2 (runtime drift) can begin as soon as Phase 1d.1 lands — the sink
exists; Phase 2 just replaces the stub validators with real ones.
