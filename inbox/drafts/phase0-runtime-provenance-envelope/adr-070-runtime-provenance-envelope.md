---
adr_id: adr-070
title: "Runtime Provenance Envelope — Typed Contract, Inline-at-Emit Validation"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-05-15
next_review: 2026-11-01
review_trigger: Adapter authors complain about emit() latency; FedRAMP 20x machine-readable evidence assessor feedback; any change to the §3 envelope schema in 15_ProvenanceProfile.qmd
impact: Promotes `15_ProvenanceProfile.qmd` §3 from prose to typed contract; unblocks Phase 1 (continuous event-time evidence capture) and Phase 2 (runtime drift for semantic / authz / identity); modifies the adapter conformance test plan to require envelope emission
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-070: Runtime Provenance Envelope — Typed Contract, Inline-at-Emit Validation

## Status

**PROPOSED** — 2026-05-15

## Context

The [Governance OS whitepaper](../../../docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd) §3 lists two **TARGET / DESIGN-ONLY** substrate rows:

| Surface | Defined in | Status today |
|---|---|---|
| Runtime drift (semantic / authz / identity) | `16_DriftDetectionStandard.qmd` | TARGET / DESIGN-ONLY |
| Continuous event-time evidence capture | `15_ProvenanceProfile.qmd` | TARGET |

Both rows reuse the same construct: the **provenance envelope** defined in `15_ProvenanceProfile.qmd` §3. Today that envelope exists only as a YAML
example in canon prose. Adapter code has no way to construct, validate, or
hash-chain an envelope, and the telemetry sink has no `uiao.provenance.*`
event shape to emit. The substrate cannot ship either TARGET row until the
envelope becomes a typed contract.

Three structural decisions must be made together:

1. **Where the envelope lives in the substrate.** Schema-only? Pydantic
   model? Both?
2. **When validation runs.** At adapter emit time (inline), or as a periodic
   scan over emitted claims?
3. **What rejection means.** Does an invalid envelope **block** the claim
   emission, or **flag** it for after-the-fact review?

These three decisions are entangled. A periodic scan can only flag — it
cannot block — because the claim has already been emitted by the time the
scan runs. An inline check can block, but only if the envelope exists as a
type the adapter must construct before the emission path will accept the
claim. The substrate cannot have it both ways: either the envelope is a
runtime contract (and the substrate refuses non-conforming emissions) or it
is documentation (and conformance is a goodwill protocol).

The whitepaper's framing — "deterministic governance replaces attestation-
based compliance" — requires the contract option. Attestation is the
goodwill protocol; the substrate exists to replace it.

## Decision

**The provenance envelope is a first-class typed contract — JSON Schema
plus pydantic model — and is validated inline at adapter emit. An adapter
that calls `emit(claim)` without a valid envelope receives a P1
DRIFT-PROVENANCE rejection, not a warning.**

Three sub-decisions land with this:

### 1. Two-form contract — schema AND model

The envelope ships as **both**:

- `src/uiao/schemas/provenance/envelope.schema.json` — JSON Schema 2020-12,
  the wire-format source of truth, validated by `schema-validation.yml`.
- `src/uiao/models/provenance.py` — pydantic v2 `Envelope` model with
  `seal()`, `lineage_hash`, `verify_chain()`, and `to_telemetry_event()`
  methods.

The model is generated against the schema; the schema is the canon. Two
forms because consumers split: adapter code constructs via the pydantic
model (ergonomics), assessors and external systems consume via the JSON
schema (interop with FedRAMP 20x machine-readable evidence).

### 2. Validation is inline at `BaseAdapter.emit()`

Every modernization adapter inherits from a shared `BaseAdapter`. The
`emit(claim, envelope)` method validates the envelope **before** the claim
reaches the telemetry sink, the OSCAL pipeline, or any downstream
consumer. Rejection happens at the adapter boundary, not after the fact.

Three classes of check run inline:

| Check | Drift class on failure | Severity | Sync/async |
|---|---|---|---|
| Envelope structure (schema) | `DRIFT-PROVENANCE` | P1 | sync |
| Signature (mTLS thumbprint resolves to a trusted issuer) | `DRIFT-PROVENANCE` | P1 | sync |
| Issuer identity resolves against the identity plane | `DRIFT-IDENTITY` | P1 | sync |
| Lineage hash matches source record (full chain) | `DRIFT-PROVENANCE` | P2 | **async** |
| Consent envelope alignment with claim destination | `DRIFT-AUTHZ` | P1 | sync |

The sync/async split exists for one reason: full-chain hash verification
can be O(N) in chain depth for derived/synthesized claims, and a high-
volume adapter cannot afford that on every emission. The sync set is
sufficient to refuse a malformed or unsigned envelope; the async set
catches chain breaks at telemetry-emit time and writes a `DRIFT-PROVENANCE
P2` finding without blocking the originating call.

### 3. Reuse the canonical drift taxonomy verbatim

ADR-012 declares the five drift classes. ADR-070 reuses them — it does
**not** introduce `RUNTIME-DRIFT-*` parallels. The substrate walker
(`src/uiao/substrate/walker.py`) already emits `DRIFT-AUTHZ`,
`DRIFT-IDENTITY`, `DRIFT-SCHEMA`, and `DRIFT-PROVENANCE` at canon-hygiene
level. The inline-at-emit checks add a second emission surface for the
same class codes, distinguished only by the `subkind` field on
`DriftFinding`:

- `subkind="hygiene"` — emitted by the substrate walker against canon
  registries.
- `subkind="runtime"` — emitted inline at `BaseAdapter.emit()`.

Both surfaces feed the same remediation contract shape declared in
`16_DriftDetectionStandard.qmd` §4. An assessor consuming the substrate's
findings does not see two parallel taxonomies; they see one taxonomy with
two emission paths.

## Consequences

### Positive

- **Substrate can refuse non-conforming emissions.** The contract is
  enforceable, not aspirational. Adapter authors cannot accidentally ship
  a claim without provenance.
- **Phase 1 and Phase 2 unblock together.** Continuous evidence capture
  (Phase 1) and runtime drift (Phase 2) both bind to the envelope; with
  Phase 0 in place, the two follow-on phases can ship in parallel.
- **OSCAL pipeline gains an event-time mode.** Bundles can be reconstructed
  from the envelope event log under `evidence/provenance/<adapter>/`,
  extending ADR-006 determinism from snapshot-at-time to full-history view.
- **FedRAMP 20x alignment improves.** The envelope schema is the machine-
  readable evidence contract FedRAMP 20x asks for; today the substrate
  ships bundles without a per-claim provenance envelope.
- **Federated provenance becomes a follow-on, not a blocker.** The local-
  substrate version of this ADR is the foundation for cross-agency
  envelope verification; that's a separate ADR once Phase 1 + 2 ship.

### Negative

- **Adapter authors must construct an envelope before `emit()` accepts a
  claim.** This is a real ergonomic cost; mitigated by the pydantic model
  carrying defaults for every field except `claim_id`, `issuer_identity`,
  `source_system`, and `extraction_timestamp`.
- **Sync validation adds latency at emit.** Worst-case ~5–10 ms per
  emission for schema + signature + identity resolution. High-volume
  adapters may need batched emission (`emit_batch`); deferred to Phase 1.
- **Existing adapters must be retrofitted.** Active Directory survey
  adapter, GCC boundary probe, and the OrgTree Phase 2–5 adapters all
  emit claims without envelopes today. Migration plan ships with Phase 1;
  retrofit is one adapter per PR, gated by a feature flag.
- **Async chain verification adds a new failure mode.** A claim can be
  accepted at emit but later flagged as a chain break. The remediation
  contract handles this (the `remediation_action` field), but assessors
  reading the event log must understand that an `accept` event can be
  followed by a `chain_break` event for the same claim_id.

### Neutral

- The envelope schema is **versioned** (`schema_version: "1.0"` in the
  prose; carried through into the JSON schema). Future changes go through
  the canon-change ADR process; no in-place schema mutation.
- The decision does not commit to a specific identity-plane resolver. The
  default is Entra ID (`issuer_identity` as Entra object ID), but the
  resolver is pluggable via the adapter manifest. Federal-only deployments
  can substitute a non-Microsoft identity plane without touching this ADR.

## Alternatives considered

### Alternative A — Periodic scan over emitted claims

Run a scheduled job over the telemetry plane's claim stream; emit
DRIFT-PROVENANCE findings after the fact. **Rejected** because:

- The substrate cannot refuse a non-conforming emission — by the time the
  scan runs, the claim is already in the consumer's hands.
- It is operationally the attestation model the whitepaper rejects (point-
  in-time snapshot, drift invisible between scans).
- It still requires the typed envelope as a check target — so it
  duplicates Phase 0 work without removing any of it.

### Alternative B — Schema-only, no pydantic model

Ship the JSON schema; let adapter authors construct envelopes as raw
dicts and validate against the schema. **Rejected** because:

- Adapter ergonomics are bad. Every adapter re-implements the same
  defaults, the same hash computation, and the same telemetry emission.
- Lineage hash computation is non-trivial (canonical JSON serialization
  + SHA-256 over a defined field set). Keeping it out of the substrate
  means it gets re-implemented inconsistently per adapter.
- A pydantic model is the right place to attach `seal()` and
  `verify_chain()` semantics — those are not declarative properties.

### Alternative C — Wire the envelope into `BaseAdapter` in this PR

Bundle the schema, the model, AND the `BaseAdapter.emit()` hook into one
PR. **Rejected** because:

- The PR becomes large (adapter retrofits) and the design call gets
  conflated with the engineering. Reviewers focus on the migration
  mechanics and the ADR-level decision gets less scrutiny.
- The schema and model can be reviewed independently and landed first
  with no risk to running adapters; the `emit()` hook is a real behavior
  change and deserves its own review surface.

## Mechanical interface (informative)

The adapter author's view of the contract:

```python
from uiao.models.provenance import Envelope

envelope = Envelope.for_claim(
    claim_id="urn:uiao:claim:hr:beneficiary:abc-123",
    issuer_identity="entra-object-id-of-issuing-service-principal",
    source_system="ssa-titan:v2.4.1",
    source_classification="authoritative",
    extraction_method="api",
)
envelope.seal(source_record=raw_ssa_payload)  # computes lineage_hash + signs
adapter.emit(claim, envelope)                  # inline validation; may raise
```

`Envelope.for_claim()` populates every field that has a default; `seal()`
computes the SHA-256 lineage hash and attaches the mTLS thumbprint;
`adapter.emit()` runs the sync validation suite and, on success, hands
the claim to the telemetry sink and queues the async chain check.

## Cross-references

- [`docs/docs/15_ProvenanceProfile.qmd`](../../../docs/docs/15_ProvenanceProfile.qmd) — envelope §3 (prose source of truth promoted by this ADR)
- [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) — drift classes and remediation contract §4
- [`src/uiao/canon/adr/adr-005-canonical-claim-schema.md`](../../../src/uiao/canon/adr/adr-005-canonical-claim-schema.md) — canonical claim schema the envelope wraps
- [`src/uiao/canon/adr/adr-006-evidence-determinism.md`](../../../src/uiao/canon/adr/adr-006-evidence-determinism.md) — determinism guarantees extended to event-time bundles
- [`src/uiao/canon/adr/adr-009-drift-ledger-immutability.md`](../../../src/uiao/canon/adr/adr-009-drift-ledger-immutability.md) — immutability inherited by the envelope event log
- [`src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md`](../../../src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md) — taxonomy reused verbatim
- [`src/uiao/substrate/walker.py`](../../../src/uiao/substrate/walker.py) — canon-hygiene DRIFT-* emission this ADR reuses (`subkind="hygiene"` vs `subkind="runtime"`)

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-05-15 | UIAO Architecture | Initial PROPOSED draft — Phase 0 of the whitepaper TARGET → SHIPPED plan |
