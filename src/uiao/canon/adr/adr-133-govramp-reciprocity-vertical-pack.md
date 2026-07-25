---
adr_id: adr-133
title: "GovRAMP Reciprocity Vertical Pack — State/Local Eligibility as a Crosswalk, and the state-local Boundary"
status: ACCEPTED
decided: 2026-07-25
deciders: Michael Stratton
updated: 2026-07-25
next_review: 2027-01-25
review_trigger: The govramp_reciprocity_catalog pack is authored (verify the D1 crosswalk charter held); the pack's registration PR lands (verify the D2 state-local enum shipped in lockstep); the pack is promoted to active (D3 conditions — reassess the ADR-132 D3 elevation condition it satisfies); GovRAMP materially changes its reciprocity/Fast Track intake such that FedRAMP-derived artifacts no longer transfer; a second state/local program (e.g. a TX-RAMP-style state-run program) proposes a pack (verify the boundary value generalizes); the deferred verticals-registry.yaml work begins (ADR-129 D4 — this pack's entry migrates with it)
impact: "Authorizes the GovRAMP (formerly StateRAMP) vertical adapter pack — the substrate's second non-federal conformance pack and the first for the state/local vertical ADR-085 reserved. The pack is chartered as a CROSSWALK, not a new stack: GovRAMP assesses against the same NIST 800-53 Rev 5 baseline the substrate already generates evidence for, and its reciprocity intake accepts FedRAMP-derived authorization artifacts, so the pack maps existing evidence outputs and the UIAO_140 single-ATO reciprocity model onto GovRAMP submission surfaces. Decides the boundary treatment per the ADR-085 D3 lockstep rule: a new `state-local` value on the gcc-boundary enum (added in the pack's registration PR, not this ADR), because ADR-129's `commercial-general` is defined as commercial-sector and misdescribes a state/local government scope — the exact positioning-truthfulness rule that motivated ADR-129 itself. Registers nothing today: pack directory (src/uiao/adapters/govramp_reciprocity_catalog/), registry row (status proposed), enum value, and the `govramp` OVERLAY_PACK_MAP entry all land with the pack's own PR; promotion to active follows the ADR-129 D3 pattern. On promotion, the pack satisfies the ADR-132 D3 elevation condition requiring one active boundary-attached regime pack. Doctrine only; unpublished until OrgLink elevation (publish_to_site: false)."
supersedes: null
superseded_by: null
publish_to_site: false
publication_style: include
published_at: null
---

# ADR-133: GovRAMP Reciprocity Vertical Pack — State/Local Eligibility as a Crosswalk, and the state-local Boundary

## Status

**ACCEPTED** — 2026-07-25.

This ADR is doctrine: it authorizes a vertical adapter pack and fixes its
boundary treatment. It changes no runtime behavior, no schema, and no
registry entry — those land with the pack's own PR, in lockstep with this
ADR per ADR-085 D3.

## Context

### The seat was already reserved

[ADR-085](adr-085-universal-enterprise-positioning.md) fixed that the UIAO
core is vertical-agnostic and explicitly reserved a **state/local
government vertical (StateRAMP)** alongside commercial-regulated and
generic-enterprise packs. [ADR-129](adr-129-non-federal-vertical-registration.md)
then registered the first non-federal pack (SOC 2) and, in its own review
trigger, anticipated this moment: *"a second non-federal boundary value
beyond `commercial-general` is proposed."*
[ADR-132](adr-132-orglink-link-object-class.md) D5 named GovRAMP one of
the first two boundary-attached regime packs on the OrgLink roadmap, and
the link registry's `regime-overlays` field (UIAO_145) is the attachment
point waiting for it.

### What GovRAMP is

GovRAMP — [rebranded from StateRAMP in early 2025](https://govramp.org/)
— is a nonprofit program providing FedRAMP-modeled cloud security
verification for state, local, and education procurement. Two properties
make it the cheapest pack the substrate can ship:

1. **Same baseline.** GovRAMP assesses against NIST SP 800-53 Rev 5 —
   the control set the substrate's evidence pipeline, control library,
   KSI machinery, and OSCAL generators already speak.
2. **Reciprocity intake.** GovRAMP accepts FedRAMP-derived authorization
   artifacts through its expedited paths, so a provider holding FedRAMP
   Moderate evidence largely *maps* rather than *re-produces*. This is
   the same shape as the UIAO_140 single-ATO reciprocity model: one
   authoritative evidence base, N consuming acceptance regimes.

Adoption is state-by-state procurement policy, not a federal mandate,
and some states run their own programs (TX-RAMP-style); the pack
therefore represents *eligibility machinery*, and canon must not
overclaim it as a regulatory requirement.

### The boundary question

The adapter-registry schema requires `gcc-boundary` on every entry. The
current enum: `gcc-moderate`, three named commercial-product exceptions,
and ADR-129's `commercial-general` — which that ADR defines as the
boundary for a *"non-federal, **commercial-sector** vertical pack."* A
GovRAMP pack's evidence is scoped to **state/local government**
acceptance, not the commercial sector. Registering it as
`commercial-general` would misdescribe its governance scope — a milder
form of the exact positioning bug (asserting a boundary that isn't true)
that ADR-129 was written to prevent. ADR-085 D3 requires any enum
extension to ship in lockstep with an authorizing ADR; this is that ADR.

## Decision

### D1 — The pack is authorized, chartered as a crosswalk

The **GovRAMP reciprocity vertical pack** is authorized:

- **Location:** `src/uiao/adapters/govramp_reciprocity_catalog/`
  (future work; nothing ships with this ADR).
- **Class:** `conformance` × mission-class `policy`, mirroring the SOC 2
  pack's dual-axis declaration (UIAO_003).
- **Charter:** map the substrate's existing 800-53 Rev 5 evidence
  outputs and FedRAMP-derived artifacts onto GovRAMP's submission
  surfaces (security snapshot / progressing / authorized statuses and
  their document intakes), riding the UIAO_140 single-ATO reciprocity
  model for the one-evidence-base / N-acceptors shape. The pack binds
  the **same surface slots** the federal and SOC 2 packs bind; it
  introduces no new engine capability. A pack PR that starts producing
  novel control interpretations instead of crosswalking existing
  evidence has left this charter and needs its own ADR.

### D2 — Boundary: a new `state-local` enum value, shipped in lockstep

The pack registers with **`gcc-boundary: state-local`** — a new enum
value denoting a non-federal vertical pack whose evidence is scoped to
state/local/education government acceptance regimes. Rationale over
reusing `commercial-general`: ADR-129's own field description draws the
line at *commercial-sector*, and boundary values must describe the
governance scope truthfully (ADR-085 D1). The value is deliberately
**program-neutral** — `state-local`, not `state-local-govramp` — so a
future TX-RAMP-style pack shares the boundary while carrying its program
specifics in the pack itself, exactly as `gcc-moderate` serves multiple
federal packs.

The enum addition and its description update land **in the pack's
registration PR**, in lockstep with this ADR per ADR-085 D3 — not here.

### D3 — Registration at `proposed`; promotion per the ADR-129 pattern

The pack registers at `status: proposed` and advances to **`active`**
only when both hold, mirroring ADR-129 D3:

1. An operational conformance surface exists — the pack renders its
   declared crosswalk output (e.g. a GovRAMP submission-mapping
   artifact) and that renderer is exercised by the adapter-conformance
   CI suite; **and**
2. This ADR is ratified from PROPOSED to ACCEPTED.

`active` means operational and CI-covered, not "has a paying state/local
engagement" — an engagement deepens confidence in the crosswalk, it does
not change the status. On promotion, the pack satisfies the ADR-132 D3
elevation condition requiring at least one active boundary-attached
regime pack.

### D4 — The `govramp` regime overlay binds at the link

The link registry's `regime-overlays` vocabulary gains `govramp` as the
overlay name, and the link-gap scanner's `OVERLAY_PACK_MAP` gains
`govramp → govramp-reciprocity-catalog` **when the pack registers** (the
mapping is meaningless before there is a pack id to map to). From that
point, any link declaring a `govramp` overlay with the pack absent or
inactive is a computable `GAP-OVERLAY-NO-PACK` finding — the gap-engine
behavior UIAO_145 §7 defines.

### D5 — What this ADR does not do

- Ships no code, no schema change, no registry row (all lockstep with
  the pack PR).
- Does not create `verticals-registry.yaml` — still deferred per
  ADR-129 D4; this pack's entry migrates when that work happens.
- Does not claim GovRAMP status for any deployment, and does not
  represent GovRAMP as a regulatory mandate — it is procurement
  eligibility, adopted state-by-state.
- Does not alter the HIPAA pack plan (ADR-132 D5); HIPAA follows under
  its own ADR with the pattern proven here.

## Consequences

- The substrate gains its cheapest path to a second active non-federal
  vertical: a crosswalk over evidence it already produces, validating
  the ADR-085 vertical-agnosticism claim for a *government* non-federal
  scope (SOC 2 proved the commercial one).
- The boundary enum grows truthfully: federal (`gcc-moderate` +
  exceptions), commercial (`commercial-general`), state/local
  (`state-local`) — each value describing a real governance scope, none
  overloaded.
- The OrgLink elevation path (ADR-132 D3) gains its regime-pack
  condition candidate; with the whitepaper drafted, elevation then
  waits only on the pack going active and the narrative publishing.
- Costs: the crosswalk mapping (GovRAMP intake formats change on the
  program's schedule, so the pack carries a re-verification burden at
  its review cadence), and one more enum value whose vertical-neutral
  redesign travels with the deferred verticals-registry work.

## Alternatives Considered

**A1. Register under `commercial-general`.** Rejected: ADR-129 defines
that value as commercial-sector; a state/local pack registered there
misdescribes its scope — the positioning-truthfulness rule (ADR-085 D1)
that created the enum discipline in the first place.

**A2. Program-named value (`state-local-govramp`).** Rejected: boundary
values describe governance scope classes, not programs — `gcc-moderate`
is not `gcc-moderate-fedramp`. A TX-RAMP-style pack should share
`state-local` the way federal packs share `gcc-moderate`.

**A3. Build the HIPAA pack first.** Rejected for sequencing, not merit:
HIPAA requires the full SP 800-66 mapping onto the surface slots (a
genuine build), while GovRAMP is a crosswalk over existing evidence —
the shortest path to proving the regime-overlay machinery end to end
and to the ADR-132 elevation condition. HIPAA follows with the pattern
proven twice.

**A4. Wait for a state/local engagement before authorizing.** Rejected:
the ADR-129 precedent registers at `proposed` precisely so the registry
can be truthful before a customer exists; the promotion gate (D3)
already prevents overclaiming.

## References

- [ADR-085](adr-085-universal-enterprise-positioning.md) — the reserved
  state/local vertical; D1 truthful-boundary rule; D3 lockstep rule.
- [ADR-129](adr-129-non-federal-vertical-registration.md) — the
  non-federal registration + promotion pattern; the review trigger this
  ADR resolves.
- [ADR-132](adr-132-orglink-link-object-class.md) — D5 (GovRAMP named a
  first regime pack), D3 (the elevation condition this pack can satisfy).
- UIAO_140 (`src/uiao/canon/specs/single-ato-reciprocity-model.md`) —
  the one-evidence-base / N-acceptors model the crosswalk rides.
- UIAO_145 (`src/uiao/canon/specs/UIAO_145_link-object-class.md`) — the
  regime-overlay attachment point and gap semantics.
- External: [GovRAMP (formerly StateRAMP)](https://govramp.org/).

## Date

2026-07-25
