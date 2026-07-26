---
adr_id: adr-134
title: "OrgLink Pillar Elevation — The Fourth Org-Family Pillar Goes Live"
status: PROPOSED
decided: 2026-07-25
deciders: Michael Stratton
updated: 2026-07-25
next_review: 2027-01-25
review_trigger: The OrgLink narrative shelf gains its second published work (build the Academy OrgLink path per D3 — the routing threshold); the OrgLink navbar/portal presentation is proposed (D3 follow-on); the link-gap scanner reaches zero and flips to --strict (retire the D4 residual-debt note); the HIPAA pack ADR lands (second regime pack on the elevated pillar); ADR-089 or ADR-131 is next reviewed (confirm their four-pillar re-anchoring stayed consistent)
impact: "Elevates OrgLink from candidate to the fourth Org-family pillar, alongside OrgPath (Governance), OrgComp (Compliance), and OrgMod (Modernization). All three ADR-132 D3 elevation conditions hold: the Link object class and registry are operational (UIAO_145, Phase 1-2 complete: schema-validated registry, walker scan, evidence rendering, graph/CQL/dashboard surfaces, link-gap scanner); the GovRAMP reciprocity pack is registered active under the state-local boundary (ADR-133); and the first narrative work publishes in this ADR's landing PR on the decider's explicit instruction — the whitepaper moves from inbox/drafts to the published OrgLink narrative section. The ADR-132 D6 publication posture flips with it, all together per that decision: ADR-132, ADR-133, and UIAO_145 become publish_to_site: true with wrappers/index rows; the link-registry schema gains its developer-reference page and its publication-gap exclusion is removed. Resolves the anticipated review triggers of ADR-089 (fourth pillar) and ADR-131 (new operational expression joins the Org family): the family is four pillars. The Academy OrgLink path and navbar/portal presentation are phased follow-ons (D3) — the Academy routes over published material and a one-work shelf is not yet a sequence. Doctrine + publication only; no runtime, schema-content, or registry-semantics change."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-134-orglink-pillar-elevation.html
---

# ADR-134: OrgLink Pillar Elevation — The Fourth Org-Family Pillar Goes Live

## Status

**PROPOSED** — 2026-07-25.

This is the short elevation ADR that [ADR-132](adr-132-orglink-link-object-class.md)
D3 anticipated. It elevates a candidate pillar whose conditions are met and
flips the publication posture that ADR-132 D6 deliberately held back — and
does nothing else.

## Context

ADR-132 established OrgLink as the **candidate** fourth Org-family pillar,
with elevation earned by a future short ADR when three conditions hold. As
of this ADR's date, they do:

1. **Link spec + registry operational.** UIAO_145 is canon; the link
   registry is schema-validated in CI, scanned by the substrate walker,
   and surfaced through evidence rendering (`uiao evidence links`), the
   Evidence Graph (node type 14), CQL (`SHOW LINKS`), the ConMon
   dashboard's external-interconnections panel, and the link-gap scanner.
2. **One active boundary-attached regime pack.**
   [ADR-133](adr-133-govramp-reciprocity-vertical-pack.md) authorized the
   GovRAMP reciprocity pack; it is registered `active` under the
   `state-local` boundary with a CI-covered operational surface, and the
   `govramp` overlay resolves in the link-gap engine.
3. **First narrative work published.** The external-interconnection
   whitepaper ("Governed Links") was authored to `inbox/drafts/` per the
   ADR-132 D6 posture. The decider has explicitly instructed its
   publication; it publishes **in this ADR's landing PR** as the seed of
   the OrgLink narrative shelf, with its statistics verified against the
   cited GAO sources at publication.

ADR-132 D6 requires the site surfaces to land "all together, none
earlier" — publication of the narrative *is* the elevation event, so the
publication flips ship here.

## Decision

### D1 — OrgLink is the fourth Org-family pillar

The Org family is **four pillars**: OrgPath (Governance), OrgComp
(Compliance), OrgMod (Modernization), **OrgLink (External
Interconnection)**. The canonical reading order fixed by ADR-132 D5
stands: **Modernize → Govern → Comply → Link**. This resolves the
anticipated review triggers of
[ADR-089](adr-089-program-narrative-pillars.md) ("a fourth program
narrative pillar is proposed") and
[ADR-131](adr-131-academy-org-family-umbrella.md) ("a new operational
expression joins the Org family"); neither is superseded — ADR-089's
naming and Explanation-quadrant doctrine and ADR-131's
Academy-routes-it-doesn't-author rule now simply apply to four pillars.

### D2 — The publication posture flips, all together

In this ADR's landing PR:

- The **whitepaper publishes** as
  `docs/customer-documents/orglink-narrative/governed-links-external-interconnection.qmd`,
  the first work on the OrgLink shelf, with a sidebar pane for the
  pillar. The inbox draft becomes a pointer stub.
- **ADR-132 and ADR-133** flip to `publish_to_site: true` with the
  standard publication set (generated wrappers, adr-index rows, sidebar,
  sitemap).
- **UIAO_145** flips to `publish_to_site: true`; its published surface is
  the narrative page (which cites and links the spec) per the
  link-back convention, with the spec source linked from the shelf.
- The **link-registry schema** gains its developer-reference page under
  `docs/reference/schemas/`, and the ADR-132-era exclusion in the
  publication-gap scanner is removed — the OrgLink surface is no longer
  a special case anywhere in the publication tooling.
- This ADR itself publishes (`publish_to_site: true`).

### D3 — Academy path and portal presentation are phased follow-ons

Per ADR-131 D2, the Academy **routes over published material and authors
no parallel curriculum**. A shelf with one work is not yet a sequence to
route: the Academy's OrgLink path, and any navbar/portal re-presentation
of the four-pillar family, land as follow-on phases when the shelf has at
least a second work (this ADR's review trigger). Elevation is real today
— the pillar, its canon, and its first work are live — without
manufacturing an empty curriculum to look bigger than it is.

### D4 — Residual debt stays visible, not blocking

Elevation does not launder the known migration debt: the link-gap
scanner's remaining findings (unrecorded/unanchored agreement artifacts
and the CA-3 diagram-evidence residue) stay advisory and visible on the
ConMon panel until the real agreement artifacts are brought into the
substrate, at which point the scanner flips `--strict` (UIAO_145 §7).
Publishing the pillar with its debt on display is the substrate's
honesty posture applied to itself.

## Consequences

- The Org family presents as four pillars; the fourth spoke proposed in
  the ADR-132 deliberation is fully realized: doctrine → object class →
  registry → visibility surfaces → regime pack → published narrative.
- The site gains one new section (OrgLink narrative) and the canon
  publication set for ADR-132/133/UIAO_145 + the link-registry schema;
  nothing else on the site moves (D3).
- ADR-089's and ADR-131's review triggers are resolved by reference;
  their next scheduled reviews confirm consistency (this ADR's own
  trigger).
- Costs: the Academy path and portal presentation remain owed when the
  shelf grows; the whitepaper's GAO statistics carry a re-verification
  duty at review cadence.

## Alternatives Considered

- **Publish the whitepaper without elevating.** Rejected: ADR-132 D6
  binds the site surfaces together precisely so the pillar cannot dribble
  out half-lit; publication of the first narrative *is* the D3 completion
  event.
- **Elevate with the full Academy path now.** Rejected: one published
  work is not a routable sequence; building a path over it would violate
  ADR-131 D2's no-parallel-curriculum rule in spirit.
- **Hold elevation until the gap baseline is zero.** Rejected: the
  remaining gaps require agreement artifacts only the org can source;
  they are tracked, visible, and advisory by design (D4). Holding the
  pillar hostage to them adds no integrity — the scanner already tells
  the truth.

## References

- [ADR-132](adr-132-orglink-link-object-class.md) — the candidate-pillar
  doctrine, D3 conditions, and D6 publication posture this ADR executes.
- [ADR-133](adr-133-govramp-reciprocity-vertical-pack.md) — the active
  regime pack satisfying condition 2.
- [ADR-089](adr-089-program-narrative-pillars.md),
  [ADR-131](adr-131-academy-org-family-umbrella.md) — the pillar and
  Academy doctrine whose triggers resolve here.
- UIAO_145 (`src/uiao/canon/specs/UIAO_145_link-object-class.md`) — the
  Link object class.
- The published narrative:
  `docs/customer-documents/orglink-narrative/governed-links-external-interconnection.qmd`.

## Date

2026-07-25
