---
adr_id: adr-132
title: "OrgLink — Fourth Org-Family Pillar: The External Interaction Plane"
status: PROPOSED
decided: 2026-07-25
deciders: Michael Stratton
updated: 2026-07-25
next_review: 2027-01-25
review_trigger: The first OrgLink narrative section or Link-class canon spec is authored (revisit the charter against realized content); a HIPAA or other boundary-attached regime vertical adapter pack is registered under the ADR-129 mechanics (verify the D3 regime-pack boundary held); the Link object is proposed as a runtime schema or registry surface (requires its own ADR); OrgComp is proposed to absorb interconnection governance; a fifth Org-family pillar is proposed
impact: "Establishes OrgLink as the fourth Org-family pillar, alongside OrgPath (Governance), OrgComp (Compliance), and OrgMod (Modernization): the external interaction plane, where every interconnection between the governed org and an outside party — agency, business partner, customer, or the public — is a first-class governed Link carrying its interface contract, its agreement artifact (ISA / MOU / BAA / DUA), and its regime overlay. Protagonist-named per ADR-089 D2 doctrine: the Link is the binding invariant, mapping onto the agreement object every regime already requires (NIST 800-53 CA-3 information exchange, HIPAA business-associate agreements, CJIS management control agreements, IRS 1075 safeguard agreements). Boundary-attached compliance regimes (HIPAA and successors) ship as vertical adapter packs per ADR-085/ADR-129 — the pillar tells the external-boundary story; it does not become a second compliance home. Doctrine only: no runtime, schema, or registry change. Fires the review triggers of ADR-089 (fourth pillar proposed) and ADR-131 (new operational expression joins the Org family)."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-132-orglink-external-interaction-pillar.html
---

# ADR-132: OrgLink — Fourth Org-Family Pillar: The External Interaction Plane

## Status

**PROPOSED** — 2026-07-25.

This ADR is doctrine. It extends the Org-family pillar set fixed by
[ADR-089](adr-089-program-narrative-pillars.md) and re-anchored by
[ADR-131](adr-131-academy-org-family-umbrella.md). It changes no runtime
behavior, no schema, and no registry entry.

## Context

The Org family tells the UIAO program's story through three pillars —
**OrgPath** (Governance), **OrgComp** (Compliance), **OrgMod**
(Modernization) — established as narrative pillars by
[ADR-089](adr-089-program-narrative-pillars.md) and treated as the
program's operational expressions by
[ADR-131](adr-131-academy-org-family-umbrella.md). ADR-089's own review
trigger anticipated this ADR: *"A fourth program narrative pillar is
proposed."*

All three existing pillars face **inward**. OrgPath governs the org's own
objects; OrgMod modernizes the org's own estate; OrgComp proves the org
itself to its authorizing official. Each has external *aspects* — OrgComp
literally exists to satisfy an outside authority — but none makes the
external party the protagonist. Nothing in the family owns the **outward**
surface:

- **Inter-agency data exchange** — system interconnections, information
  exchange agreements, reciprocity across authorization boundaries.
- **Business-partner and guest identity** — B2B federation, external
  collaborator lifecycle, non-employee trust.
- **Public-facing services** — citizen/customer-facing interfaces and the
  obligations that attach to them.
- **Boundary-attached compliance regimes** — obligations that arise
  *because* data crosses to an outside party: HIPAA business-associate
  flows, CJIS, IRS 1075, StateRAMP reciprocity, and successors.

Two constraints shape how that gap may be filled:

1. **Compliance regimes already have a doctrinal home.**
   [ADR-085](adr-085-universal-enterprise-positioning.md) fixes that the
   core is vertical-agnostic and regimes ship as vertical adapter packs;
   [ADR-129](adr-129-non-federal-vertical-registration.md) proved it by
   registering the SOC 2 pack under the `commercial-general` boundary. A
   pillar chartered as "more compliance regimes" would collide with both
   that doctrine and with OrgComp.
2. **The naming doctrine of ADR-089 D2.** A pillar is protagonist-named
   when the name describes its binding invariant (OrgPath: every governed
   object carries an OrgPath), domain-named otherwise, and never named so
   that a part's word collides with a whole's word.

The ethos motivating the pillar — the external party comes first — must
therefore be elevated *structurally*, not as a slogan: the relationship
with the outside party becomes a governed object in its own right.

## Decision

### D1 — OrgLink is the fourth Org-family pillar: the external interaction plane

The Org family gains a fourth pillar, **OrgLink**. Its charter: **every
interconnection between the governed org and an outside party — agency,
business partner, customer, or the public — is a first-class governed
Link**, carrying its interface contract, its agreement artifact, and its
regime overlay, provenance-anchored like every other substrate object.

This extends ADR-089 D1's pillar table without superseding it: ADR-089's
naming doctrine (D2), Explanation-not-duplication rule (D3), and
layered-refinement pattern apply to OrgLink unchanged.

### D2 — Protagonist naming: the Link is the binding invariant

OrgLink is **protagonist-named** per ADR-089 D2. The pillar's first-class
object is *the Link* — interface + agreement + regime overlay, one per
external relationship. The name is not a metaphor; it maps onto the
agreement object every regime already requires:

| Regime | The Link's agreement artifact |
|---|---|
| NIST SP 800-53 CA-3 (Information Exchange) | Interconnection security agreement / MOU / information exchange agreement |
| HIPAA | Business Associate Agreement (BAA) |
| CJIS Security Policy | Management control agreement |
| IRS Publication 1075 | Safeguard agreement |
| Data-sharing generally | Data use agreement (DUA) |

One governed Link class, multiple regime skins. Every external interaction
carries a Link the way every internal object carries an OrgPath.

### D3 — Boundary with OrgComp; regimes remain vertical adapter packs

**OrgComp keeps sole ownership of proving the org itself to its
authorizing official** — the boundary model, FedRAMP, and SCuBA regime.
**OrgLink owns the interconnection story** — what crosses the boundary to
an outside party, under what agreement, with what regime overlay.

Boundary-attached compliance regimes (HIPAA, CJIS, IRS 1075, and
successors) ship as **vertical adapter packs** under the
[ADR-085](adr-085-universal-enterprise-positioning.md) /
[ADR-129](adr-129-non-federal-vertical-registration.md) mechanics — never
as pillar-owned parallel compliance content. OrgLink is the Explanation
layer and doctrine home for the external boundary; the packs are the
conformance machinery underneath it. This mirrors ADR-131 D2's rule for
curricula: owned where they live, sequenced by the pillar.

### D4 — HIPAA is the first OrgLink-motivated regime pack; follow-on work

The first vertical adapter pack motivated by this pillar is **HIPAA**
(Security Rule, mapped via NIST SP 800-66 to the same substrate surface
slots the federal and SOC 2 packs bind). It follows the ADR-129 precedent
exactly: authored as a pack under `src/uiao/adapters/`, registered in
`adapter-registry.yaml` under a non-federal boundary, promoted to `active`
only when an operational conformance surface exists. Whether it registers
under the existing `commercial-general` boundary or a new value is decided
by that pack's own authorizing ADR, in lockstep with the schema per ADR-085
D3. **This ADR authorizes none of that** — it fixes only that HIPAA's home
is a regime pack under the OrgLink story, not a pillar charter.

### D5 — Incremental establishment; doctrine only

OrgLink is established the way ADR-089 D5 established the second and third
pillars: incrementally, with no existing section moved or renamed. The
canonical reading order extends to **Modernize → Govern → Comply → Link**
— first the journey, then the substrate, then proving the org, then
extending outward. Follow-on work, each landing under its own review:

- The OrgLink narrative section under `/customer-documents/`, when its
  first book is authored.
- The Academy's OrgLink path per ADR-131 D1/D2, when there is published
  material to sequence — the Academy routes; it authors no parallel
  curriculum.
- A Link-class canon spec (UIAO_NNN) and any runtime schema or registry
  surface, each requiring its own ADR.

Until then, OrgLink exists as doctrine: a named pillar with a fixed
charter and boundary, awaiting content.

## Consequences

- The Org family becomes four pillars; the external party is elevated to
  protagonist structurally rather than rhetorically.
- The review triggers of [ADR-089](adr-089-program-narrative-pillars.md)
  ("a fourth program narrative pillar is proposed") and
  [ADR-131](adr-131-academy-org-family-umbrella.md) ("a new operational
  expression joins the Org family") fire; this ADR is their resolution.
  Neither is superseded.
- OrgComp's charter is sharpened, not shrunk: proving the org itself.
  Interconnection governance has an unambiguous home, ending the
  alternative of inflating OrgComp with external-party scope.
- A HIPAA pack gains a sanctioned path (D4) that cannot drift into a
  second compliance pillar.
- Costs: a fourth narrative section and Academy path must eventually be
  authored; the Link-class spec is net-new canon work; until content
  ships, OrgLink is a doctrine-only pillar and site surfaces must not
  imply otherwise.

## Alternatives considered

- **Name it OrgCust ("Organizational Customer").** Rejected: "customer"
  already means *UIAO's* customers in the published-site vocabulary
  (`docs/customer-documents/`); overloading it to mean the governed org's
  external parties is exactly the part-vs-whole word collision ADR-089 D2
  exists to prevent.
- **Name it OrgPublic.** Rejected as underscoped: agency-to-agency and
  business-partner exchange is not "public," and public-facing services
  are one slice of the charter, not its spine.
- **Name it OrgExt ("External").** Rejected: negative-space naming — it
  says which direction the pillar faces, not what it governs, and yields
  no first-class noun. "Every exchange carries a Link" works; "every
  exchange carries an Ext" does not.
- **Charter the pillar as compliance-regime expansion (HIPAA et al.).**
  Rejected: collides with OrgComp and with the ADR-085/129 vertical-pack
  doctrine; regimes are packs, not pillars.
- **Fold external interaction into OrgComp.** Rejected: different
  protagonist (the outside party vs. the authorizing official) and it
  re-creates the over-claiming, part-carries-whole problem ADR-089
  resolved for OrgPath.
- **No pillar — adapter packs only.** Rejected: leaves the external-
  boundary story with no Explanation-layer home, forcing it into the
  inward-facing pillars or leaving it untold — the same gap ADR-089 D1
  closed for modernization and compliance.

## References

- [ADR-089](adr-089-program-narrative-pillars.md) — the pillar structure
  and naming doctrine this ADR extends; its review trigger anticipated
  this proposal.
- [ADR-131](adr-131-academy-org-family-umbrella.md) — the Org-family
  umbrella; its Academy gains an OrgLink path when content ships.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — vertical-
  agnostic core; regimes as vertical adapter packs.
- [ADR-129](adr-129-non-federal-vertical-registration.md) — the
  non-federal vertical registration precedent the HIPAA pack follows.
- [ADR-083](adr-083-docs-architecture-reorganization.md) — the Divio
  Explanation quadrant the pillars inhabit.

## Date

2026-07-25
