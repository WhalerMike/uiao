---
adr: ADR-066
title: "Application-Aware Networking and Token-Bound Transport Plane"
status: Proposed
date: 2026-05-05
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-008  # Zero-Trust Identity Anchoring (foundational)
  - ADR-018  # Mission Channel Enforcement
  - ADR-034  # Three-Plane Device Model
  - ADR-038  # Device-Plane OrgPath
  - ADR-039  # Policy Targeting
  - ADR-040  # Drift Engine
  - ADR-043  # FedRAMP RFC-0026 CA-7 Pathway Integration
  - ADR-051  # SAML Trust Anchor (federation answer to "who issued the token")
  - ADR-052  # PIV / USAccess Adapter (cardholder identity binding)
  - ADR-054  # Single-ATO Reciprocity Model (downstream consumer of bundle integrity)
  - ADR-056  # Login.gov Federation Service Activation (Stage 2)
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-066-application-aware-networking-and-token-bound-transport.html
---

# ADR-066: Application-Aware Networking and Token-Bound Transport Plane

> **Renumber history:** This ADR was originally drafted as ADR-047 on a
> stale branch base, then renumbered to ADR-057 (next free slot above the
> ADR-051..056 federal-federation block). ADR-057 subsequently collided
> with `adr-057-thousandeyes-networks-pillar-scope.md` (drafted
> 2026-04-27, an earlier occupant of that slot). Renumbered again to
> ADR-066 on 2026-05-12 to resolve the collision; ADR-057 is now
> canonically `adr-057-thousandeyes-networks-pillar-scope.md`. The
> doctrinal content is unchanged. Several premises this ADR raised
> ("who issues the token", "what does federation look like across
> agencies") are now partly answered by ADR-051 / ADR-052 / ADR-054 /
> ADR-056; the transport-plane / per-call-token argument itself
> remains open.

## Context

UIAO's substrate today governs five mission classes (Identity, Telemetry,
Policy, Enforcement, Integration) per UIAO_003. The transport plane — the
network path that carries every claim, evidence bundle, and adapter call —
is *implicit*: addressed at Layer 3/4 by the host environment, secured by
perimeter constructs (TIC 3.0, F5 LTM, NGFW choke-points), and authorized
by long-lived sessions. Three observations make that implicit posture
untenable for a FedRAMP-Moderate governance OS:

1. **The TIC3 / F5 model is being retired.** `docs/docs/14_TIC3_F5RetirementRoadmap.qmd`
   already names SD-WAN with local DIA breakout, SASE/ZTNA, and
   conditional-access traffic policy as the post-perimeter stack. The
   roadmap exists; the substrate machinery to govern it does not.

2. **Identity is the new boundary, but only halfway.** UIAO_001 (SSOT)
   and UIAO_003 (Identity-first adapter class) made identity the root of
   trust, and UIAO_006 (AODIM) made it the addressing model. But the
   transport that carries identity-derived claims is still session-based:
   a TLS connection establishes once, then rides for minutes-to-hours
   carrying intent the issuer can no longer attest to. Hijacking the
   session inherits its trust.

3. **EO 14028 and EO 14144 push toward per-call authorization.** Both
   EOs name zero-trust architecture and short-lived credentials. NIST
   SP 800-207 (Zero Trust Architecture) defines the policy
   decision/enforcement-point split that long-lived sessions cannot
   satisfy. UIAO already cites EO 14028, EO 14144, EO 14306, and the
   March 2026 *Cyber Strategy for America* in
   `canon/compliance/executive-orders.md` (UIAO_004); the canon does
   not yet operationalize the *per-call* part.

The pre-existing canon names the destination — application-aware overlay,
ZTNA, identity-bound traffic policy — but routes around it. The result is
that UIAO can govern *what* runs and *who* runs it, but not *how it gets
there*. That gap shows up as `DRIFT-AUTHZ` findings the substrate cannot
explain because the transport context is invisible.

## Decision

Promote the transport plane to a first-class governed concern with three
specific moves:

1. **Add `transport` as a sixth canonical mission class to UIAO_003.**
   Adapters that observe or shape the network path between two governed
   objects declare `mission-class: transport`. The class joins identity
   / telemetry / policy / enforcement / integration as a peer; it does
   not replace any of them.

2. **Adopt token-bound, per-call transport authorization as the
   canonical authorization unit.** A "session" — defined as any
   long-lived authorization context that survives a single authorized
   intent — is no longer a canonical concept in UIAO. Every adapter
   call, every evidence transfer, every overlay tunnel carries a
   short-lived, audience-scoped token (SPIFFE SVID, signed JWT/PASETO,
   or equivalent) bound to: caller identity, target application, device
   posture, and orgPath-derived location. Tokens are issued by a
   governed token-issuer adapter, validated at the enforcement point,
   and logged as evidence.

3. **Define the `OverlayTunnel` as a typed canonical object.**
   UIAO_001's "identity-derived, certificate-anchored tunnel
   abstraction" is promoted from concept to schema. An `OverlayTunnel`
   carries `{identity, application, posture, location, token, lease,
   certificate-chain}`. Tunnels are *leased* (not opened); the lease is
   bounded by token lifetime; the canonical record is
   provenance-anchored to SSOT.

The decision is **doctrinal, not implementation-prescriptive**: it does
not pick SPIFFE vs PASETO, does not pick a specific SD-WAN vendor, and
does not put UIAO in the data-plane business. UIAO observes, governs,
and emits evidence; the data plane stays with whatever fabric the agency
operates.

## Consequences

### Canon work required (downstream of this ADR)

This ADR is the doctrinal anchor. The following canon work items follow
and are **not in scope for this ADR** — each requires its own UIAO_NNN
allocation in `document-registry.yaml` and, where doctrinal, its own
ADR:

| Item | Type | Purpose |
|---|---|---|
| **UIAO_122** | Canon doc (`specs/`) | Token-Based Transport Authorization Specification — token format, lifetime, scope, rotation, revocation, replay defense |
| **UIAO_123** | Canon doc (`specs/`) | Application-Aware Overlay Fabric Model — `OverlayTunnel` object, lease semantics, drift class binding |
| **UIAO_124** | Canon doc (`specs/`) | Transport Plane Telemetry Contract — flow telemetry (NetFlow / IPFIX / eBPF) ingestion contract for `mission-class: transport` conformance adapters |
| **`overlay-fabric.schema.json`** | JSON Schema | Constrains overlay / SD-WAN / SASE adapter entries; required fields, token-issuer reference, posture-source reference |
| **UIAO_003 §4.8** | Canon doc edit | Add "Transport Adapter Class" section with role statement and ratification evidence |

### Drift taxonomy extension

Add **`DRIFT-TRANSPORT`** as a sixth drift class, joining `DRIFT-SCHEMA`,
`DRIFT-SEMANTIC`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, and `DRIFT-IDENTITY`.
Severity guidance:

- **P1** — Token lifetime exceeds canon-declared maximum, or token
  validated outside its declared audience scope.
- **P2** — `OverlayTunnel` observed without an issuing token, or with
  an expired lease.
- **P3** — Transport telemetry gap exceeds freshness window for a
  `mission-class: transport` adapter.
- **P4** — Path-policy variance between canonical orgPath / location
  binding and observed flow.

`docs/docs/16_DriftDetectionStandard.qmd` is the SSOT for the taxonomy
and is updated as part of UIAO_122/UIAO_123 work, not this ADR.

### Adapter registry implications

Reserve the following adapter slots (`status: reserved`,
`phase: phase-planning`) so the registry reflects the doctrinal commitment
without forcing an immediate vendor selection:

**Modernization (`mission-class: transport`):**

- `sdwan-fabric` — observes and reconciles SD-WAN policy intent against
  canon
- `service-mesh` — observes and reconciles service-mesh authorization
  (SPIFFE / Istio / Linkerd-style)
- `token-issuer` — issues short-lived transport tokens; emits issuance
  records as evidence
- `sase-egress` — reconciles SASE / ZTNA egress policy against canon

**Conformance (`mission-class: transport`):**

- `flow-telemetry` — ingests NetFlow / IPFIX / eBPF flow records as
  `DRIFT-TRANSPORT` evidence
- `posture-telemetry` — ingests device + application posture used as
  the `posture` axis of token issuance

### GCC-Moderate boundary impact

Token issuance for transport authorization will require a key-management
surface (HSM, AD CS, Entra Verified ID, or an in-boundary SPIFFE/SPIRE
deployment). Two paths:

- **Path A (in-boundary):** Issuer runs inside GCC-Moderate; no boundary
  exception required. **Preferred.**
- **Path B (declared exception):** Issuer runs outside GCC-Moderate;
  requires a second declared boundary exception alongside Amazon Connect
  in `canon/gcc-boundary-gap-registry.yaml`. **Discouraged.**

The follow-on UIAO_122 spec MUST select Path A or document a Path B
exception with the same rigor as the Amazon Connect entry.

### Lane discipline (what UIAO does NOT become)

UIAO is a **governance OS**, not an SD-WAN controller, service-mesh
control plane, or token-issuance service. Adapters under
`mission-class: transport`:

- **Observe** the live transport state (telemetry).
- **Reconcile** observed state against canonical intent (drift).
- **Emit** policy outcome records and evidence bundles.
- **Do NOT** terminate tunnels, route packets, modify routes, or hold
  a data-plane position.

A modernization-class transport adapter MAY make change-making API calls
into an SD-WAN / SASE / mesh controller (as `entra-id` does for identity)
— but it MUST NOT be the controller itself. Any PR that crosses that
line is rejected at review.

### Executive-order alignment

`canon/compliance/executive-orders.md` (UIAO_004) gains a new pillar row
in the per-pillar capability table:

| Pillar | UIAO artifact(s) |
|---|---|
| **Token-bound transport authorization** | Transport mission class (UIAO_003 §4.8), Token-Based Transport Authorization (UIAO_122), Overlay Fabric Model (UIAO_123) |

EO 14028 §3 (Zero Trust Architecture), EO 14144 (post-quantum readiness
— token agility supports algorithm rotation), and the March 2026 *Cyber
Strategy for America* (per-call authorization, network as a hostile
substrate) are the citation chain.

### CI consequences

- New schema requires a `schema-validation.yml` row.
- `substrate-drift.yml` extended to surface `DRIFT-TRANSPORT` findings
  at P1.
- New adapter conformance tests required for any reserved slot that
  promotes to active.

## Rejected alternatives

- **Extend `enforcement` mission class to cover transport.** Rejected —
  conflates *what is enforced* (policy outcomes, evidence) with *how
  the call gets there* (overlay path, token). Two different drift
  classes, two different audit conversations, two different vendor
  ecosystems. A peer class is cleaner.

- **Treat transport as a sub-concern of `integration`.** Rejected —
  integration adapters are change-makers against named external
  systems. Transport adapters observe and govern the *medium between*
  systems. Different role statement, different SSOT-mutation contract.

- **Wait for a FedRAMP RFC on transport.** Rejected — the doctrinal
  direction is already clear from EO 14028, NIST SP 800-207, and the
  TIC3 / F5 retirement roadmap. Waiting on a specific RFC ratification
  (cf. ADR-043's pathway-1 / pathway-2 model) would strand the
  substrate without a transport governance class through the entire
  FedRAMP 20x transition.

- **Token model only, no overlay model.** Rejected — tokens without an
  addressable, governed overlay object leave the transport observable
  but ungoverned. The two together close the loop.

- **Overlay model only, no token model.** Rejected — preserves
  session-based authorization, which is the antipattern this ADR
  exists to retire.

## Verification

Acceptance of this ADR is a doctrinal commitment; verification is the
existence and integrity of the downstream artifacts:

- [ ] UIAO_122 (Token-Based Transport Authorization Spec) drafted and
  registered in `document-registry.yaml`.
- [ ] UIAO_123 (Application-Aware Overlay Fabric Model) drafted and
  registered.
- [ ] UIAO_124 (Transport Plane Telemetry Contract) drafted and
  registered.
- [ ] UIAO_003 §4.8 (Transport Adapter Class) added with ratification
  evidence pointing to a first reserved slot.
- [ ] `overlay-fabric.schema.json` added under `src/uiao/schemas/`.
- [ ] `DRIFT-TRANSPORT` added to the drift taxonomy in
  `docs/docs/16_DriftDetectionStandard.qmd`.
- [ ] Six reserved adapter slots added (4 modernization, 2 conformance)
  with `status: reserved`.
- [ ] `canon/compliance/executive-orders.md` extended with the new
  pillar row.
- [ ] ADR index (`canon/adr/index.md`) updated to include ADR-032
  through ADR-047 (pre-existing housekeeping debt — the index has been
  stale since ADR-031).

---

This ADR ratifies the *direction*; each verification line above ratifies
the *implementation*.
