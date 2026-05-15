---
title: "Phase 2 — Runtime Drift Validators (semantic / authz / identity)"
status: DRAFT
date: 2026-05-15
owner: Michael Stratton
depends_on: Phase 0 (ADR-070 ACCEPTED), Phase 1 (ADR-071 ACCEPTED + provenance_sink in place)
related_strategy: "Whitepaper TARGET → SHIPPED plan (governance-os whitepaper §3)"
---

# Phase 2 — Runtime Drift Validators

This is the smallest of the four phases. Phase 1 ships the sink with
three stub validators that return `True`. Phase 2 replaces the stubs
with real validators tied to existing canon. The hook contract is
unchanged; the substrate gains inline runtime checks for the three
drift classes the whitepaper still lists as TARGET.

When this phase ships, the whitepaper row **"Runtime drift (semantic /
authz / identity)"** moves from TARGET to SHIPPED.

## What Phase 2 actually does

Replace three lines of `return True` with real validators:

| Stub today (Phase 1) | Real validator (Phase 2) | Canon binding | Drift class | Severity |
|---|---|---|---|---|
| `_check_signature_resolves` (Phase 1 already wires trust-anchor) | `signature_validator.check()` | `trust-anchor:` in adapter/modernization registries (already validated at canon-hygiene level) | DRIFT-PROVENANCE | P1 (blocks) |
| `_check_identity_resolves` | `identity_validator.check()` via pluggable `IdentityPlaneResolver` | `issuer_identity` field; default resolver is Entra ID | DRIFT-IDENTITY | P1 (blocks) |
| `_check_consent_envelope` | `authz_validator.check()` against typed `ConsentEnvelope` | [`17_ConsentEnvelope.qmd`](../../../docs/docs/17_ConsentEnvelope.qmd) §3 schema | DRIFT-AUTHZ | P1 (blocks) |
| (new) | `semantic_validator.check()` wrapping `freshness/drift_semantic.py` | per-adapter `freshness-window-hours:` in adapter registries | DRIFT-SEMANTIC | **P2 (non-blocking)** |

Two material refinements ride with this:

1. **The sink's accept rule changes.** Phase 1 wrote
   `accepted = not findings`. That is too strict — P2/P3/P4 findings
   should be observed and logged but should not block emission, matching
   the substrate-walker pattern (`blocking` = any P1). Phase 2 changes
   the rule to `accepted = not any(f.severity == "P1" for f in findings)`.
2. **SEMANTIC fires non-blocking.** A claim with a stale extraction
   timestamp gets emitted, but a P2 DRIFT-SEMANTIC finding is appended
   to the event log alongside the `accept` event. This is the runtime
   surface that matches the whitepaper's "drift as continuous signal"
   framing — staleness is information, not refusal.

## What Phase 2 does NOT do

- It does **not** introduce the remediation contract on findings (that's
  Phase 3 — promotes `DriftFinding` to carry §4 of
  `16_DriftDetectionStandard.qmd`).
- It does **not** wire runtime findings into the OSCAL pipeline (that's
  Phase 3 too; today they only land in the event log).
- It does **not** replace the substrate walker's canon-hygiene
  DRIFT-AUTHZ / DRIFT-IDENTITY scans. Those run at PR time on registry
  declarations; Phase 2's runtime versions run at emit time on live
  envelopes. Same drift class, two `subkind`s (`hygiene` vs `runtime`).
- It does **not** redesign `freshness/drift_semantic.py`. Phase 2 calls
  the existing module inline; the module is already production-ready as
  a scheduler-artifact evaluator.

## What's in this folder

| File | Purpose | Lands at |
|---|---|---|
| [adr-072-runtime-drift-validators.md](adr-072-runtime-drift-validators.md) | Records the four validator design, the P1-only blocking rule, and identity-plane pluggability | `src/uiao/canon/adr/` |
| [consent.py](consent.py) | Pydantic model for `17_ConsentEnvelope.qmd` §3; typed wire-format the AUTHZ validator consumes | `src/uiao/models/consent.py` |
| [identity_resolver.py](identity_resolver.py) | `IdentityPlaneResolver` ABC + `EntraIDResolver` default; pluggable per adapter manifest | `src/uiao/identity/resolver.py` |
| [validators.py](validators.py) | Four inline validators (signature, identity, authz, semantic) wired into the sink | `src/uiao/telemetry/validators.py` |
| [provenance_sink_phase2.diff.md](provenance_sink_phase2.diff.md) | Diff sketch replacing the Phase 1 stubs in `provenance_sink.py`, plus the accept-rule fix | Inline in `src/uiao/telemetry/provenance.py` |

## Promotion plan

Phase 2 is a single PR. There is no per-adapter rollout (every adapter
that's already retrofitted to Phase 1 inherits the validators
automatically). Promotion order:

1. Promote the consent model and identity resolver to canon paths.
2. Promote `validators.py` to `src/uiao/telemetry/validators.py`.
3. Apply the `provenance_sink_phase2.diff.md` changes to
   `src/uiao/telemetry/provenance.py` (built from Phase 1).
4. Update the substrate-status dashboard to surface the new
   `subkind="runtime"` findings alongside the existing hygiene findings.
5. Flip the whitepaper row to **SHIPPED**.

## Exit criteria

Phase 2 is complete when:

1. ADR-072 ACCEPTED.
2. The four validators are in `src/uiao/telemetry/validators.py` with
   the stubs removed.
3. CI tests pass:
   - A claim with a missing `issuer_identity` → P1 DRIFT-IDENTITY, rejected.
   - A claim with an expired `consent_envelope` → P1 DRIFT-AUTHZ, rejected.
   - A claim with an `extraction_timestamp` older than the adapter's
     freshness window → P2 DRIFT-SEMANTIC, **accepted** + logged.
   - A claim with an `mTLS thumbprint` outside the adapter's
     `trust-anchor:` declaration → P1 DRIFT-PROVENANCE, rejected.
4. The whitepaper row "Runtime drift (semantic / authz / identity)"
   flips to SHIPPED in `uiao-governance-os-whitepaper.qmd` §3.

## Cross-references

- [`inbox/drafts/phase0-runtime-provenance-envelope/`](../phase0-runtime-provenance-envelope/) — typed envelope this phase validates
- [`inbox/drafts/phase1-emit-hook-and-evidence-capture/`](../phase1-emit-hook-and-evidence-capture/) — sink the validators bind into
- [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) — taxonomy reused verbatim
- [`docs/docs/17_ConsentEnvelope.qmd`](../../../docs/docs/17_ConsentEnvelope.qmd) — consent envelope §3 schema the AUTHZ validator types
- [`src/uiao/freshness/drift_semantic.py`](../../../src/uiao/freshness/drift_semantic.py) — production-ready SEMANTIC evaluator the inline validator wraps
- [`src/uiao/substrate/walker.py`](../../../src/uiao/substrate/walker.py) — canon-hygiene DRIFT-AUTHZ / DRIFT-IDENTITY scans this phase complements
