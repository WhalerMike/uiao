---
adr_id: adr-076
title: "Evidence Fabric → OSCAL Assessment Results Projection — Canonical Mapping and Byte-Stable Emission Contract"
status: PROPOSED
decided: TBD
deciders: Michael Stratton
updated: 2026-05-19
next_review: TBD
review_trigger: OSCAL spec version uplift (1.1.2 → next); FedRAMP 20x submission contract change; Evidence Fabric record schema change
impact: Closes the implicit OSCAL projection gap left by ADR-006/016/043/047/061; precondition for ADR-077 (detached signatures)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: false
publication_style: include
published_at: TBD
---

# ADR-076: Evidence Fabric → OSCAL Assessment Results Projection

## Status

**PROPOSED** — May 19, 2026

## Context

UIAO's Evidence Fabric ([ADR-006](../../src/uiao/canon/adr/adr-006-evidence-determinism.md)) and Evidence Bundle lifecycle ([ADR-016](../../src/uiao/canon/adr/adr-016-evidence-bundle-lifecycle.md)) establish the substrate-internal shape of governance evidence: deterministic, write-once, hash-chained, idempotently keyed. [ADR-043](../../src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md) (FedRAMP RFC-0026 CA-7), [ADR-047](../../src/uiao/canon/adr/adr-047-fedramp-20x-integration.md) (FedRAMP 20x), and [ADR-061](../../src/uiao/canon/adr/adr-061-fedramp-cr26-catalog-vendoring.md) (CR26 catalog vendoring) establish that the substrate emits its output to the FedRAMP submission pathway, which is OSCAL-native.

What no ADR locks today is the **projection**: the field-level mapping from a SEALED Evidence Bundle to an OSCAL Assessment Results (AR) document. Without a locked projection:

1. Every adapter or assembly path could emit a different shape. The substrate-level determinism of ADR-006 does not survive translation to the compliance edge.
2. AR documents cannot be byte-diffable across runs of the same bundle. Diffability is the property that lets an auditor see "zero compliance drift between this week and last week" by `diff`-ing two AR JSONs.
3. The companion signing layer ([ADR-077](./adr-077-detached-signatures-evidence-bundles-and-ar.md)) cannot be built — detached signatures require byte-stable input, which requires a canonical projection.

The projection has been implicit in the substrate since ADR-043 was accepted. This ADR makes it explicit.

## Decision

**Five canonical positions, in operational sequence:**

### 1. Canonical field-level projection mapping

| UIAO Evidence Fabric field | OSCAL Assessment Results location |
|---|---|
| `record.event_id` | `observation.uuid` (stable across re-runs per ADR-006 §5) |
| `record.recorded_at` | `observation.collected` |
| `record.content_hash` | `back-matter.resources[].rlinks[].hashes` (algorithm: SHA-256 minimum, SHA-384 preferred) |
| `record.subject` | `observation.subjects[]` with `subject-uuid` + `type` |
| `record.adapter.name` + `record.adapter.version` | `observation.origins[].actors[]` with `type: tool`, `actor-uuid` encoding adapter identity |
| `record.correction_of` (per ADR-006 §2) | New `observation` with `types: [historic]` + back-reference via `related-observations` |
| `bundle.uuid` | `result.uuid` |
| `bundle.state == SEALED` transition timestamp | `result.end` |
| `bundle.state == SUBMITTED` transition timestamp | `result.attestations[].timestamp` |
| `bundle.records[]` (in sequence order) | `result.observations[]` (preserving sequence) |
| `bundle.hash_chain_head` | `back-matter.resources[].props[name=uiao-hash-chain-head]` |
| `bundle.scope.controls[]` | `result.reviewed-controls.control-selections[].include-controls[]` |
| `bundle.findings_summary[]` | `result.findings[]` with `target.status.state ∈ {satisfied, not-satisfied, other}` |

### 2. OSCAL spec version pinning

- Target version: **OSCAL 1.1.2** (NIST). Spec version is recorded in `assessment-results.metadata.oscal-version` and additionally in a `result.props[name=uiao-oscal-spec-version]` for redundancy.
- OSCAL version upgrade requires a follow-on ADR documenting the migration and re-projection guarantees.

### 3. JCS canonicalization for byte stability

- All emitted OSCAL JSON MUST be canonicalized per **RFC 8785 (JSON Canonicalization Scheme)** before being persisted, hashed, or signed.
- JCS is what makes signing meaningful (ADR-077 companion) and what makes inter-run `diff` semantically faithful.

### 4. Re-emission idempotency

- Re-projecting the same SEALED bundle MUST yield byte-identical output.
- This is the projection-layer analogue of ADR-006 §5 (idempotent writes) and is the substrate's compliance-edge promise to auditors: "we can re-derive this AR from the same bundle at any time, byte-for-byte."

### 5. Reference projector library is canonical implementation

- The projection contract is enforced by a single reference implementation (`src/uiao/oscal/projector.py` or equivalent module path).
- Adapters do not roll their own projection. They emit Evidence Fabric records; the projector reads sealed bundles and emits AR.
- Golden tests assert byte-stability over a frozen corpus of test bundles.

## Rationale

1. **Determinism only survives translation if the translator is itself deterministic.** ADR-006's record-level guarantees are wasted if the OSCAL projection introduces nondeterminism (e.g., field ordering, timestamp formatting, optional-field inclusion).
2. **Diffability proves zero compliance drift.** Two AR JSONs produced from successive runs of the same control set should differ only in timestamps and observation UUIDs. A byte-stable projection makes that semantic claim mechanically checkable.
3. **JCS is the canonicalization the rest of the OSCAL ecosystem is converging on.** Choosing a non-standard canonicalization would block interoperability with NIST tooling, FedRAMP validators, and `compliance-trestle`.
4. **Locking the projection in one library prevents per-adapter drift.** Adapter teams write evidence emitters; they do not write OSCAL emitters. This separation of concerns mirrors ADR-013 (adapter failure isolation) and ADR-015 (adapter extensibility).
5. **External auditor re-projection is the trust closure.** An auditor with the sealed bundle, the projection contract, and a clean-room projector implementation MUST be able to independently re-derive the AR. This is what makes the projection auditable rather than UIAO-internal magic.

## Implementation Plan

| Phase | Deliverable | Owner |
|---|---|---|
| **A** | UIAO_xxx primitive spec document codifying the field-level mapping above | Compliance team |
| **A** | Reference projector library + JCS canonicalization + golden test corpus | Compliance team |
| **A** | Projection contract version stamp + OSCAL spec version pinning | Compliance team |
| **B** | Adapter framework integration — every adapter that emits Evidence Fabric records inherits AR projection for free | Adapter team |
| **B** | NIST OSCAL metaschema validation in CI for every emitted AR | Compliance team |
| **B** | Re-emission diff CLI (`uiao oscal diff <bundle-A> <bundle-B>` shows control-level differences) | Tools team |
| **C** | Continuous AR emission feed from sealed bundles → FedRAMP submission pathway (consumes ADR-043 CA-7 surface) | Compliance + Submission teams |
| **C** | External-auditor re-projection harness (clean-room reference implementation usable for independent verification) | Compliance team |

## Consequences

**Positive:**
- AR documents are byte-stable across re-runs of the same bundle — compliance drift is mechanically diffable.
- OSCAL conformance is enforced at the substrate boundary, not delegated to downstream tooling.
- FedRAMP 20x and RFC-0026 CA-7 submission pathways become substrate-native rather than bespoke per engagement.
- External auditors can independently re-project from sealed bundles — closes the trust loop.

**Negative:**
- Hard contract: any change to the Evidence Fabric record schema now requires a coordinated projector update + golden-test refresh.
- OSCAL spec version upgrades require a follow-on ADR + migration plan; the projection cannot silently track spec changes.
- JCS canonicalization adds per-emission CPU cost (negligible at single-bundle scale; non-trivial at continuous-monitoring scale).

**Operationally accepted:** the projection contract is a load-bearing dependency for the compliance edge. Changes to it carry the same governance weight as changes to ADR-006 (record determinism) or ADR-016 (bundle lifecycle). Casual schema changes that "should be transparent to OSCAL" are not — they go through the full ADR review.

## References

- [ADR-006](../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — Evidence Determinism (record-level guarantees this projection rests on)
- [ADR-016](../../src/uiao/canon/adr/adr-016-evidence-bundle-lifecycle.md) — Evidence Bundle Lifecycle (SEALED is the projection input state)
- [ADR-043](../../src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md) — FedRAMP RFC-0026 CA-7 Integration (continuous monitoring consumer)
- [ADR-047](../../src/uiao/canon/adr/adr-047-fedramp-20x-integration.md) — FedRAMP 20x Integration (submission pathway)
- [ADR-061](../../src/uiao/canon/adr/adr-061-fedramp-cr26-catalog-vendoring.md) — FedRAMP CR26 Catalog Vendoring (source of control IDs referenced in projection)
- [ADR-077](./adr-077-detached-signatures-evidence-bundles-and-ar.md) — companion: detached signatures over bundles and AR
- NIST OSCAL 1.1.2 specification — https://pages.nist.gov/OSCAL/
- RFC 8785 — JSON Canonicalization Scheme (JCS)
- FedRAMP PMO GitHub — https://github.com/fedramp (successor to retired `GSA/fedramp-automation`)
