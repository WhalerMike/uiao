---
adr_id: adr-072
title: "Runtime Drift Validators — Semantic, Authz, Identity Checks Inline at Emit"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-05-15
next_review: 2026-11-01
review_trigger: Identity-plane resolver swap (e.g., non-Microsoft federal deployment); FedRAMP 20x assessor feedback on runtime drift coverage; first adapter retrofit hitting validator latency budget
impact: Replaces Phase 1's three stub validators in `src/uiao/telemetry/provenance.py` with real validators; introduces typed `ConsentEnvelope` model + `IdentityPlaneResolver` ABC; refines the sink's accept rule from "any finding rejects" to "any P1 finding rejects"; flips the whitepaper TARGET row "Runtime drift (semantic / authz / identity)" to SHIPPED
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
depends_on: adr-070, adr-071
---

# ADR-072: Runtime Drift Validators — Semantic, Authz, Identity Checks Inline at Emit

## Status

**PROPOSED** — 2026-05-15

## Context

ADR-070 ships the typed provenance envelope. ADR-071 wires it into the
three adapter surfaces via a shared sink, with three sync validators
stubbed to return `True`. The stubs let Phase 1 ship the contract
shape without coupling the adapter retrofit to validator implementation
risk. Phase 2 is the validator implementation.

Four design questions must be answered before the stubs can be replaced:

1. **What does "signature resolves" actually check?** ADR-070 §2 lists
   it as DRIFT-PROVENANCE P1 sync, but the substrate walker today
   validates `trust-anchor:` declarations at canon-hygiene level — the
   runtime check is the *live* version of that hygiene check. The line
   between "signature matches a registered trust anchor" (DRIFT-PROVENANCE)
   and "issuer principal exists in the identity plane" (DRIFT-IDENTITY)
   has to be drawn explicitly.

2. **How does identity-plane resolution stay pluggable?** The default
   identity plane is Entra ID. Federal-only deployments need to be able
   to substitute Login.gov, PIV/CAC, or a non-Microsoft federal IdP
   *without* touching the sink code. The strategy memo from Phase 0
   commits to pluggability; this ADR has to pick the plug-point.

3. **Should DRIFT-SEMANTIC block emission?** ADR-070 §2 lists semantic
   as a runtime check but doesn't pin the severity. `16_DriftDetectionStandard.qmd`
   §3 puts P2 at "Schema or semantic drift in a live claim" — high but
   not halt-and-alert. The substrate's other drift surfaces (walker,
   scheduler freshness evaluator) treat P2 as "log + auto-remediate if
   deterministic, do not halt." The sink's Phase 1 code rejects on
   *any* finding; Phase 2 has to align with the rest of the substrate.

4. **What types the consent envelope?** `17_ConsentEnvelope.qmd` §3
   defines a 15-field YAML schema (envelope_id, claim_id, legal_authority,
   purpose_code, consent_expiry, permitted_uses, prohibited_uses,
   cross_boundary_flag, ...). The AUTHZ validator can't operate on raw
   dicts at runtime — it needs a typed model the same way ADR-070
   defines a typed `Envelope`.

## Decision

**Phase 2 replaces the three Phase 1 stub validators with four real
validators, refines the sink's accept rule to gate on P1 only, types
the consent envelope, and introduces a pluggable identity-plane
resolver.**

Six sub-decisions land with this:

### 1. Four validators, three blocking + one non-blocking

| Validator | Drift class | Severity | Blocks emission? |
|---|---|---|---|
| `signature_validator` | DRIFT-PROVENANCE | P1 | yes |
| `identity_validator` | DRIFT-IDENTITY | P1 | yes |
| `authz_validator` | DRIFT-AUTHZ | P1 | yes |
| `semantic_validator` | DRIFT-SEMANTIC | P2 | **no** |

A claim's emission is accepted iff none of the validators emits a P1
finding. P2/P3 findings are written to the event log alongside the
`accept` event and are visible to the OSCAL pipeline and the
substrate-status dashboard, but they do not stop the claim from
flowing downstream. This matches the substrate walker's pattern
(`blocking = any P1`) and matches `16_DriftDetectionStandard.qmd` §3
which already declares P2 as "auto-remediate if deterministic, 1 hour
SLA" — that doesn't fit halt-and-alert semantics.

### 2. Signature vs identity — a clean split

The two checks are sequential and observe different failure modes:

- **`signature_validator`** answers: "is `envelope.signature` a thumbprint
  the adapter's `trust-anchor:` block recognizes?" This is a registry
  lookup against the adapter manifest's declared trust anchors. Failure
  means an envelope was signed by a key the adapter doesn't trust —
  DRIFT-PROVENANCE because it's an envelope-integrity failure, not an
  identity failure.
- **`identity_validator`** answers: "does `envelope.issuer_identity`
  resolve to a live principal in the identity plane right now?" This
  requires an out-of-process lookup against Entra ID (or the
  configured resolver). Failure means the envelope is well-signed but
  the principal that signed it no longer exists (or never did) —
  DRIFT-IDENTITY.

Both checks are P1 sync. The order is fixed: signature first
(cheap, registry-only); identity second (expensive, network-bound).
The sink short-circuits on the first failure.

### 3. Pluggable `IdentityPlaneResolver` via adapter manifest

The identity resolver is an ABC:

```python
class IdentityPlaneResolver(abc.ABC):
    @abc.abstractmethod
    def resolve(self, issuer_identity: str) -> ResolutionResult: ...
```

Default implementation is `EntraIDResolver`. Concrete adapters declare
a resolver in their manifest:

```yaml
# active-directory/adapter-manifest.json
identity_resolver: "uiao.identity.resolver:EntraIDResolver"

# login-gov/adapter-manifest.json (future)
identity_resolver: "uiao.identity.resolver:LoginGovResolver"

# piv-usaccess/adapter-manifest.json (future)
identity_resolver: "uiao.identity.resolver:PIVResolver"
```

The plug-point is the manifest, not the sink — so the sink stays
identity-plane-agnostic, and a federal-only deployment can swap in a
non-Microsoft resolver without touching shared code. Each resolver is
responsible for its own caching strategy; the default `EntraIDResolver`
uses a 5-minute LRU cache to keep emit latency bounded.

### 4. Typed `ConsentEnvelope` model

`17_ConsentEnvelope.qmd` §3 is promoted to a pydantic model the same
way ADR-070 promoted the provenance envelope §3. The model lives at
`src/uiao/models/consent.py` and ships with:

- 15 typed fields matching the §3 schema exactly
- An `is_active(now)` method that checks `consent_expiry` against the
  current time (`"SESSION"` always returns True)
- A `permits(use_code)` method that checks `permitted_uses` and
  `prohibited_uses`
- A `requires_canon_steward_countersignature` property derived from
  `cross_boundary_flag` per §5

The `authz_validator` calls these methods rather than re-implementing
the §3 enforcement rules. The validator's job is to wire the consent
envelope into the emission decision; the model owns the §3 semantics.

### 5. `semantic_validator` wraps `freshness/drift_semantic.py`

`src/uiao/freshness/drift_semantic.py` already implements
`resolve_policy()` (per-adapter freshness window) and the staleness
classification (`fresh | stale-soon | stale | missing-timestamp`). The
inline `semantic_validator` is a thin shim:

1. Resolve the adapter's freshness window from the canon registries
   (cached at sink-init time)
2. Compute `age_hours = now - envelope.extraction_timestamp`
3. Classify via the same `_classify()` and `_severity_for_status()`
   functions in `drift_semantic.py`
4. Emit the runtime `DriftFinding` with the resolved status

No new freshness logic. The shim is ~20 LOC; the heavy lifting is
already done. This is deliberate — keeping the SEMANTIC evaluation in
one module means the scheduler-time evaluator and the inline emit-time
validator can never drift apart.

### 6. Sink accept rule: P1-only

Phase 1's `accepted = not findings` is replaced with:

```python
accepted = not any(f.severity == "P1" for f in findings)
```

A P2 DRIFT-SEMANTIC finding (stale claim) gets logged but doesn't
block. A P1 DRIFT-AUTHZ finding (expired consent) blocks. This matches
both `16_DriftDetectionStandard.qmd` §3 (only P1 is "halt") and the
substrate walker's `blocking` property. The change is one line; the
behavior change is material.

## Consequences

### Positive

- **Closes the second whitepaper TARGET row.** Once Phase 2 ships, both
  TARGET rows from §3 of the Governance OS whitepaper are SHIPPED.
- **One taxonomy, two emission paths.** Runtime findings reuse the
  ADR-012 drift classes with `subkind="runtime"`. The substrate walker
  emits `subkind="hygiene"` against the same classes. An assessor sees
  one taxonomy with two surfaces, not two parallel taxonomies.
- **Identity plane is swappable per adapter.** Federal-only deployments
  on Login.gov / PIV / non-Microsoft IdPs don't need a substrate fork
  to get runtime identity drift detection. The plug-point is the
  manifest, not the sink.
- **SEMANTIC stays observability, not refusal.** A stale claim is
  *information* for the dashboard, not a rejection. This is what the
  whitepaper's "drift as continuous signal" framing means concretely.
- **No new freshness logic.** The inline SEMANTIC validator is a 20-LOC
  shim over the existing `drift_semantic.py` module. The runtime and
  scheduler-time evaluators share one implementation; they cannot drift.
- **Single PR.** Unlike Phase 1's four sub-PRs, Phase 2 is one PR
  because there is no per-adapter rollout — every adapter already on
  Phase 1's emit hook gets the validators for free.

### Negative

- **Identity resolution latency is network-bound.** A cold `EntraIDResolver`
  lookup is ~50–150 ms depending on cache state and network conditions.
  At 100 emissions/sec per adapter, that's a meaningful budget. The
  5-minute LRU cache keeps warm-path latency low (~µs), but the first
  hit per principal pays the full cost. Mitigated by per-resolver
  caching; not eliminated.
- **Resolver pluggability adds a new manifest field.** Adapter authors
  who don't declare `identity_resolver:` get the Entra ID default. A
  future canon-hygiene check might want to flag adapters without an
  explicit declaration as a P3 advisory, but Phase 2 does not add that
  scan — defaults are valid.
- **Consent envelope model adds a hard dependency on `17_ConsentEnvelope.qmd`
  staying at v1.0.** A v1.1 schema change requires a model bump and
  potentially a validator update. The canon-change ADR process governs
  this; the dependency is documented.
- **P2-non-blocking is a behavior change from Phase 1.** Any adapter
  that today depends on the sink rejecting emissions on *any* finding
  will see a behavior shift. Phase 1 is in feature-flag territory so
  the blast radius is small, but the change must be called out in
  PR-2's release notes.

### Neutral

- The validators live in a new module `src/uiao/telemetry/validators.py`,
  imported by `src/uiao/telemetry/provenance.py`. Separation lets the
  validators be unit-tested independently of the sink's persistence
  side-effects.
- ADR-072 does not commit to a specific OSCAL-pipeline integration of
  the runtime findings — that's Phase 3. Today they only land in the
  event log; Phase 3 makes them visible to the bundle generator.

## Alternatives considered

### Alternative A — SEMANTIC blocks emission

Make `semantic_validator` P1 and reject stale-emission. **Rejected**
because:

- Inconsistent with the rest of the substrate (walker and scheduler
  freshness evaluator both treat staleness as observability, not gate).
- A stale extraction timestamp is rarely the adapter's choice — it
  reflects upstream system latency or a delayed scheduler run.
  Rejecting the emission punishes the adapter for an upstream problem.
- `16_DriftDetectionStandard.qmd` §3 already pins P2 as "auto-remediate
  if deterministic, 1 hour SLA" — that explicitly is not halt-and-alert.

### Alternative B — Identity resolver as a sink-level config

Configure the resolver globally in the sink, not per adapter. **Rejected**
because:

- Federal deployments with mixed identity planes (some adapters on
  Entra ID, some on Login.gov, some on PIV) cannot express that with
  a global config.
- Per-adapter manifest is already the established pattern for
  trust anchors, scope, freshness windows, and consent envelope refs.
  Adding a global config alongside the manifest splits the canon.

### Alternative C — Inline `freshness/drift_semantic.py` directly in the sink

Skip the `validators.py` module; call `drift_semantic.evaluate_*` from
inside the sink. **Rejected** because:

- The four validators have different shapes (some are pure functions,
  some hold cached state from the manifest). A single module with one
  pattern per validator is cleaner than four call-sites in the sink.
- The validators module is the natural place for the
  `IdentityPlaneResolver` registry to live; co-locating it with the
  resolver is more discoverable than scattering it through the sink.

## Mechanical interface (informative)

```python
# src/uiao/telemetry/validators.py (Phase 2 lands)

class Validator(Protocol):
    drift_class: str
    severity: str
    def check(self, envelope: Envelope, *, claim: dict, adapter_id: str) -> Optional[DriftFinding]: ...

# Concrete instances:
signature_validator: Validator  # DRIFT-PROVENANCE P1
identity_validator: Validator   # DRIFT-IDENTITY    P1
authz_validator: Validator      # DRIFT-AUTHZ       P1
semantic_validator: Validator   # DRIFT-SEMANTIC    P2 (non-blocking)

VALIDATOR_PIPELINE: list[Validator] = [
    signature_validator,   # cheap; fail fast
    identity_validator,    # network; cached
    authz_validator,       # registry + envelope.consent_envelope
    semantic_validator,    # in-process; always runs last
]
```

The sink's emit path becomes:

```python
def emit(envelope: Envelope, *, claim: dict, adapter_id: str) -> EmitOutcome:
    findings = [
        f for v in VALIDATOR_PIPELINE
        if (f := v.check(envelope, claim=claim, adapter_id=adapter_id)) is not None
    ]
    accepted = not any(f.severity == "P1" for f in findings)
    event_type = "accept" if accepted else "reject"
    log_path = _write_event(envelope, claim=claim, adapter_id=adapter_id,
                            event_type=event_type, findings=findings)
    if accepted:
        _enqueue_chain_check(envelope, claim=claim, adapter_id=adapter_id)
    return EmitOutcome(accepted=accepted, envelope=envelope,
                       findings=findings, log_path=log_path)
```

## Cross-references

- [`inbox/drafts/phase0-runtime-provenance-envelope/adr-070-runtime-provenance-envelope.md`](../phase0-runtime-provenance-envelope/adr-070-runtime-provenance-envelope.md) — envelope this phase validates
- [`inbox/drafts/phase1-emit-hook-and-evidence-capture/adr-071-adapter-emit-hook-and-event-log.md`](../phase1-emit-hook-and-evidence-capture/adr-071-adapter-emit-hook-and-event-log.md) — sink + stubs this phase replaces
- [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) — taxonomy + severity model + §4 remediation contract (Phase 3 extends findings to carry it)
- [`docs/docs/17_ConsentEnvelope.qmd`](../../../docs/docs/17_ConsentEnvelope.qmd) — §3 schema promoted to typed model in this phase
- [`src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md`](../../../src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md) — taxonomy reused verbatim with `subkind="runtime"`
- [`src/uiao/canon/adr/adr-051-saml-trust-anchor.md`](../../../src/uiao/canon/adr/adr-051-saml-trust-anchor.md) — trust anchor canon the signature validator reads from
- [`src/uiao/freshness/drift_semantic.py`](../../../src/uiao/freshness/drift_semantic.py) — SEMANTIC evaluator wrapped by `semantic_validator`
- [`src/uiao/substrate/walker.py`](../../../src/uiao/substrate/walker.py) — canon-hygiene `_scan_consent_envelope` + `_scan_issuer_chain` this phase complements

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-05-15 | UIAO Architecture | Initial PROPOSED draft — Phase 2 of the whitepaper TARGET → SHIPPED plan; replaces Phase 1's three stub validators with four real validators (sync × 3 + non-blocking semantic), refines accept rule to P1-only, types the consent envelope, introduces pluggable identity-plane resolver |
