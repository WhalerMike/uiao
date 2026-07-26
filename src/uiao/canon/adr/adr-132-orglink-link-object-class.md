---
adr_id: adr-132
title: "OrgLink — Link Object Class for External Interconnection Governance; Candidate Fourth Org-Family Pillar"
status: ACCEPTED
decided: 2026-07-25
deciders: Michael Stratton
updated: 2026-07-25
next_review: 2027-01-25
review_trigger: The Link-class canon spec (UIAO_NNN) is authored (verify the D1 object model held); the link registry becomes operational in the substrate walker (D6 Phase 1 complete — assess Phase 2 readiness); a HIPAA or GovRAMP regime-pack ADR is proposed (verify the D5 boundaries); the D3 elevation conditions are met (author the elevation ADR); the external-interconnection whitepaper is proposed for site publication (re-assess this ADR's publish_to_site posture per D6); OrgComp is proposed to absorb interconnection governance; a counterparty class or SSOT stance not expressible in the D1 model is encountered
impact: "Establishes the Link — interface + agreement artifact + regime overlay, one per external relationship — as a first-class governed substrate object class for every interconnection between the governed org and an outside party: federal agency, branch of government, state, local, tribal, regulated-commercial (banks, hospitals), general-commercial, consortium, or the public. Follows the LocPath (ADR-102) and non-human SSOT registry (ADR-130) overlay pattern: new object class + registry + drift integration, surfaced through the existing pillars, no new pillar today. Reserves the OrgLink name as the candidate fourth Org-family pillar, with elevation earned via explicit conditions rather than declared (the ADR-129 proposed-to-active pattern applied to pillar status). Motivated by a concrete SSOT violation: CA-3 (Information Exchange) evidence today consists of DOCX/PDF pointers into SharePoint folders — unmanaged, undrifted, provenance-free — in a substrate whose thesis is provenance-anchored evidence. Organizes the existing but scattered external-interconnection surface (CHARTER-003 FILE 4 inter-agency source-of-authority doctrine; the Federal HRIT Integration Runbook and UIAO_144; UIAO_140 reciprocity; UIAO_141/142/143 customer identity; ADR-003/053 inbound, ADR-128 outbound, ADR-059 non-employee; ADR-074 SSOT contention) under one object model. The statutory precedent is the Computer Matching and Privacy Protection Act's written-agreement regime. Boundary-attached compliance regimes (HIPAA via NIST SP 800-66, GovRAMP formerly StateRAMP) ship as vertical adapter packs per ADR-085/ADR-129, each under its own future ADR. Doctrine only: no runtime, schema, or registry change in this ADR. Not published to the site until the OrgLink surface is developed (publish_to_site: false)."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-132-orglink-link-object-class.html
---

# ADR-132: OrgLink — Link Object Class for External Interconnection Governance; Candidate Fourth Org-Family Pillar

## Status

**ACCEPTED** — 2026-07-25.

This ADR is doctrine. It establishes a substrate object class and reserves a
candidate pillar name; it changes no runtime behavior, no schema, and no
registry entry. Per the publication decision in D6, it is deliberately **not
published to the site** until the OrgLink surface it charters is developed.

## Context

### The Org family faces inward; the outward surface is real but scattered

The Org family tells the program's story through three pillars — **OrgPath**
(Governance), **OrgComp** (Compliance), **OrgMod** (Modernization) — fixed by
[ADR-089](adr-089-program-narrative-pillars.md) and re-anchored by
[ADR-131](adr-131-academy-org-family-umbrella.md). All three face inward:
govern the org's own objects, modernize its own estate, prove the org itself
to its authorizing official.

The **outward** surface — interconnections with outside parties — already
exists in the repo, but as scattered point solutions with no unifying object
model:

| Concern | Where it lives today | Layer |
|---|---|---|
| Inter-agency source-of-authority doctrine | CHARTER-003 FILE 4 ("Source of Authority: Location, Inter-Jurisdictional, Inter-Agency"; addressable as CHARTER-005-SOA) | Charter |
| Federal HRIT integration | Spec2-D6.1 Federal HRIT Integration Runbook; UIAO_144 (HRIT Productization) | Spec |
| Whose-SSOT-wins mechanics | [ADR-074](adr-074-drift-ssot-contention.md) `DRIFT-SSOT-CONTENTION`; [ADR-088](adr-088-hr-as-orgtree-truth-source.md) | Drift engine |
| Cross-boundary reciprocity | UIAO_140 (Single-ATO Reciprocity Model) | Spec |
| External-party identity exchange | [ADR-055](adr-055-customer-identity-canon-block.md) + UIAO_141/142 (customer identity, KYC, reciprocal attribute exchange); UIAO_143 (SCIM pin); [ADR-059](adr-059-sailpoint-adapter-family.md) (non-employee lifecycle) | Spec + adapters |
| Live federal interconnections | [ADR-003](adr-003-api-driven-inbound-provisioning.md) / [ADR-053](adr-053-opm-azure-apim-adapter.md) (inbound); [ADR-128](adr-128-reporting-egress-actuator.md) (gated outbound evidence egress) | Adapters |
| The compliance control | CA-3 (Information Exchange) in the control library | Control library |

Charter doctrine at the top, adapters at the bottom, and nothing in the
middle: no object model that makes an interconnection a queryable,
drift-detected, provenance-anchored thing.

### The motivating finding: CA-3 evidence violates the substrate's own thesis

The control library's CA-3 entry declares its evidence as **DOCX/PDF
documents in SharePoint folders** (Interconnection Security Agreements,
MOUs, boundary and data-flow diagrams). In a substrate whose entire thesis
is provenance-anchored, drift-detected, SSOT evidence, the interconnection
agreements are the one evidence class still living as unmanaged Office
documents: no registry, no schema, no review-date drift, no provenance
chain. CA-3's own "reviewed annually" parameter is unenforceable as
declared.

### The external precedent: the Link pattern is proven and statutorily mandated

This is not an invented shape. Federal law and practice already run on it:

- The **Computer Matching and Privacy Protection Act of 1988** requires a
  *written matching agreement* for every eligibility-matching exchange
  between agencies, a cost-benefit analysis, a Data Integrity Board in each
  participating agency, and public notice — a legally mandated link
  registry, administered today as PDFs and Federal Register notices
  ([CRS R47325](https://www.congress.gov/crs-product/R47325);
  [DOJ CMA inventory](https://www.justice.gov/opcl/computer-matching-agreements-and-notices)).
- The federal identity-verification mesh is a working system of
  attribute-scoped SSOTs exposing verification links: SSA's
  [data exchange services](https://www.ssa.gov/dataexchange/) (SVES/SOLQ,
  SSOLV, CBSV), DHS SAVE and E-Verify, NAPHSIS
  [EVVE](https://www.naphsis.org/evve/) for vital events, and AAMVA's
  [State-to-State service](https://www.aamva.org/technology/systems/driver-licensing-systems/s2s-frequently-asked-questions)
  which deduplicates driver identity across jurisdictions — the mechanism
  [REAL ID](https://www.ecfr.gov/current/title-6/chapter-I/part-37)
  issuance chains onto.

Every entry in that mesh is a Link in this ADR's sense: two parties, a
declared authority relationship, an agreement artifact, a regime overlay.
The gap is that no governance substrate treats those links as first-class,
drift-detected objects. A fuller treatment of the mesh and its
eligibility-integrity implications is deferred to a whitepaper (D6); this
ADR takes from it only the object model and the statutory precedent.

### Constraints from existing doctrine

1. **Regimes are packs, not pillars.**
   [ADR-085](adr-085-universal-enterprise-positioning.md) fixes the core as
   vertical-agnostic; [ADR-129](adr-129-non-federal-vertical-registration.md)
   proved it by registering the SOC 2 pack at `commercial-general`. HIPAA
   and GovRAMP follow that road.
2. **Pillars have been organizations of existing gravity.** OrgPath was
   named after eighteen books existed; OrgMod and OrgComp organized existing
   corpora. Declaring a content-less pillar would be the family's first
   empty shelf, and would churn the just-completed ADR-131 Academy rebuild.
3. **Naming doctrine** ([ADR-089](adr-089-program-narrative-pillars.md) D2):
   protagonist names are earned by a binding invariant; part-names must not
   collide with whole-words.
4. **Precedent for overlay-shaped growth**: LocPath
   ([ADR-102](adr-102-locpath-location-addressing.md)) and the non-human
   SSOT registry ([ADR-130](adr-130-nonhuman-ssot-registry.md)) added
   object classes with registries and drift taxonomies — no new pillar.

## Decision

### D1 — The Link is a first-class governed substrate object class

A **Link** is the governed record of one interconnection between the org
and one outside party. Its object model:

| Facet | Content |
|---|---|
| **Counterparty class** | `federal-agency`, `federal-branch`, `state`, `local`, `tribal`, `regulated-commercial` (banks, hospitals, insurers), `general-commercial`, `consortium` (e.g. AAMVA-shaped bodies), `public` |
| **Direction** | `inbound` (e.g. OPM HR feed), `outbound` (e.g. ConMon evidence egress), `bidirectional` (e.g. reciprocal attribute exchange) |
| **SSOT stance** | `we-are-source`, `they-are-source`, `contended` — wired to [ADR-074](adr-074-drift-ssot-contention.md): a counterparty asserting authority over data the org stewards is a detected `DRIFT-SSOT-CONTENTION` event, not a silent overwrite |
| **Interface contract** | Transport, protocol, and identity binding (WIF per [ADR-004](adr-004-workload-identity-federation-default.md) where applicable) |
| **Agreement artifact** | The ISA / MOU / CMA / BAA / DUA — provenance-anchored in the substrate, with review-cadence drift (making CA-3's annual-review parameter enforceable) |
| **Regime overlay** | Which boundary-attached regimes attach to this link (HIPAA, CJIS, IRS 1075, GLBA, GovRAMP reciprocity, …), each satisfied by a vertical adapter pack per D5 |

**Explicit boundaries of the class.** The Link registry governs
*agreements, flows, and authority stances*. It is **not** an
entity-resolution or master-data engine — it does not deduplicate or match
records across parties, and it holds **metadata about exchanges, never the
exchanged payload data**. Any proposal that would put person-level payload
attributes into the registry is out of scope for this class and requires
its own ADR.

### D2 — The name OrgLink is reserved; protagonist naming applies

The surface this class anchors is named **OrgLink**, protagonist-named per
ADR-089 D2: the Link is the binding invariant — every external interaction
carries a Link the way every governed object carries an OrgPath. The name
maps onto the agreement object every regime already requires (CA-3
information-exchange agreement, HIPAA BAA, CJIS management control
agreement, IRS 1075 safeguard agreement, CMPPA computer matching
agreement). Alternatives rejected in the naming deliberation are recorded
under Alternatives Considered.

### D3 — OrgLink is a candidate pillar; elevation is earned, not declared

OrgLink is **not** established as the fourth Org-family pillar by this ADR.
It is the **candidate** fourth pillar, and elevation happens by a short
future ADR when all three conditions hold:

1. The Link-class canon spec (UIAO_NNN) is authored and the link registry
   is operational in the substrate walker (D6 Phase 1 complete);
2. At least one boundary-attached regime pack (D5) is registered `active`
   under the ADR-129 mechanics;
3. The first OrgLink narrative work (the whitepaper or first book) is
   published.

This applies the ADR-129 proposed-to-active promotion pattern to pillar
status, using the repo's existing `review_trigger` machinery rather than
inventing a candidacy apparatus. Until elevation: no navbar entry, no
Academy path, no site section, and the three-pillar presentation of
[ADR-131](adr-131-academy-org-family-umbrella.md) stands unchanged.

### D4 — OrgComp remains the sole assessor-facing flow; Links supply it

**OrgComp keeps sole ownership of proving the org to its authorizing
official — including its interconnections.** CA-3 and its siblings (CA-9,
SA-9, AC-20) are controls in the org's own authorization package; the
assessor conversation stays in OrgComp. The Link registry is the
**evidence source** those controls render from: SSP narratives, agreement
inventories, and review-status attestations are generated from registry
state instead of pointing at SharePoint folders. Link objects serve every
pillar — OrgComp renders evidence from them, OrgPath governs them, OrgMod
migrates the legacy interconnection estate onto them.

### D5 — Boundary-attached regimes ship as vertical adapter packs

Compliance regimes that attach because data crosses to an outside party
ship as **vertical adapter packs** under
[ADR-085](adr-085-universal-enterprise-positioning.md) /
[ADR-129](adr-129-non-federal-vertical-registration.md) mechanics — never
as pillar-owned parallel compliance content. The first two, each requiring
its own authorizing ADR:

- **HIPAA** — Security Rule mapped via
  [NIST SP 800-66r2](https://csrc.nist.gov/pubs/sp/800/66/r2/final) to the
  same substrate surface slots the federal and SOC 2 packs bind; the BAA is
  the link-level agreement artifact.
- **GovRAMP (formerly StateRAMP)** — state/local eligibility via
  reciprocity from existing federal artifacts, riding UIAO_140's
  single-ATO reciprocity model; the pack is a crosswalk, not a new stack.

Whether each pack registers at `commercial-general` or under a new boundary
enum value is decided by its own ADR in lockstep with the schema, per
ADR-085 D3.

### D6 — Phased roadmap: repo and website scope

The scope this ADR adds to the program roadmap, in order. Each phase lands
under its own PR(s) and review; no phase is authorized to skip ahead of its
predecessor's completion.

**Repo roadmap:**

- **Phase 0 (this ADR)** — doctrine: the Link class, the candidate-pillar
  posture, the boundaries.
- **Phase 1 — Link spec + registry.** A Link-class canon spec under a new
  UIAO_NNN allocation; `link-registry.yaml` under `src/uiao/canon/` with a
  JSON Schema under `src/uiao/schemas/`; substrate-walker integration.
  Backfill the worked examples that already exist as the first registry
  entries: the OPM APIM interconnection (ADR-053), the inbound HR feed
  (ADR-003), the Federal HRIT integration (Spec2-D6.1 / UIAO_144), the
  reporting-egress destination (ADR-128), and the NERM non-employee
  exchange (ADR-059).
- **Phase 2 — Evidence and visibility.** CA-3 / CA-9 / SA-9 / AC-20
  evidence rendered from registry state into SSP/OSCAL output, retiring
  the SharePoint-pointer pattern; Link nodes in the Evidence Graph
  (UIAO_113); CQL (UIAO_108) queryability; a ConMon dashboard panel; and a
  **link-gap scanner** in the family of the publication-gap and
  lifecycle-consistency scanners — flagging counterparties with missing or
  expired agreements, links with undeclared SSOT stance, regime overlays
  with no active pack, and controls whose narratives claim agreements the
  registry cannot produce.
- **Phase 3 — Regime packs.** The HIPAA and GovRAMP packs per D5, each
  under its own ADR.
- **Phase 4 — Elevation.** The short elevation ADR when D3's conditions
  hold.

**Website roadmap (deferred by design):**

- **Nothing publishes until developed.** This ADR carries
  `publish_to_site: false`; no wrapper, index row, sidebar, or sitemap
  entry ships with it. The posture is re-assessed (per this ADR's review
  trigger) when the OrgLink surface has real content.
- **The whitepaper** — the external-interconnection / eligibility-integrity
  narrative (the identity-verification mesh, the CMPPA precedent, SSOT
  with due-process framing) — is authored to `inbox/` first and published
  only when fully developed; it is the natural seed of the OrgLink shelf.
- **At elevation (Phase 4)** — the OrgLink narrative section under
  `/customer-documents/`, the Academy path per ADR-131 D1/D2 (routing over
  published material, authoring no parallel curriculum), navbar and portal
  entries, and this ADR's own publication flip — all together, none
  earlier.

## Consequences

- The scattered external-interconnection surface gains one object model
  under CHARTER-003 FILE 4's authority, and the CA-3 SharePoint-pointer
  SSOT violation gets a named, phased fix.
- The registry is a **gap-detection engine** by construction: regulatory
  gaps (counterparty × regime matrix, expired agreements), control gaps
  (registry entries with no CA-3/SA-9/AC-20 mapping and vice versa), KSI
  gaps (link-scoped KSIs with no registry evidence behind them), and SSOT
  gaps (undeclared stances surfacing latent contention) all become
  computable findings rather than audit surprises.
- The Org family's three-pillar presentation stands unchanged today; the
  ADR-089 and ADR-131 review triggers fire at **elevation** (Phase 4), not
  now. No Academy or navbar churn ships with this ADR.
- The OrgLink name, charter, and rejected-alternatives record are fixed in
  canon and cannot be lost to session memory.
- Costs: the Phase 1 spec/registry/schema work is net-new; the whitepaper
  is net-new authorship; until Phase 2, CA-3 evidence remains
  SharePoint-shaped (the finding is named here but fixed there); carrying
  an unpublished PROPOSED ADR means the site's ADR index will not reflect
  ADR-132 until the publication flip.

## Alternatives Considered

- **Establish the fourth pillar now** (this ADR's own first draft).
  Rejected: it would be the first pillar named before its content existed;
  the pillar boundary leaks by construction (CA-3 evidence belongs to the
  org's own authorization, splitting one assessor conversation across two
  pillars); and ratifying it fixes nothing found — the ISAs stay in
  SharePoint the day after. The empty shelf also re-churns the
  just-completed ADR-131 Academy rebuild.
- **Overlay only, no candidate pillar.** Rejected: leaves the
  external-boundary narrative with no future Explanation-layer home,
  forcing eventual GovRAMP/HIPAA storytelling into inward-facing pillars —
  the inflation ADR-089 was written to stop — and loses the naming
  deliberation to session memory.
- **Do nothing; ship regime packs ad hoc.** Rejected: leaves a known,
  named SSOT violation standing and the point solutions unorganized.
- **Charter the class as national-scale identity governance.** Rejected as
  canon over-claim (the ADR-085 positioning discipline): the
  identity-verification mesh is motivating context and whitepaper
  material; the substrate's charter stays at org altitude — govern *this
  org's* links, not the nation's.
- **Naming: OrgCust** ("Organizational Customer"). Rejected: "customer"
  already means UIAO's own customers in the site vocabulary
  (`customer-documents`) — the part-vs-whole collision ADR-089 D2 forbids.
- **Naming: OrgPublic.** Rejected: underscoped — agency-to-agency and
  business-partner exchange is not "public."
- **Naming: OrgExt.** Rejected: negative-space naming with no first-class
  noun; "every exchange carries a Link" works, "carries an Ext" does not.

## References

- [ADR-089](adr-089-program-narrative-pillars.md) — pillar structure and
  naming doctrine; its review trigger fires at elevation, not now.
- [ADR-131](adr-131-academy-org-family-umbrella.md) — Org-family umbrella;
  unchanged until elevation.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — vertical-
  agnostic core; the positioning discipline D6 applies to publication.
- [ADR-129](adr-129-non-federal-vertical-registration.md) — the
  registration + promotion pattern D3 borrows and D5 rides.
- [ADR-102](adr-102-locpath-location-addressing.md),
  [ADR-130](adr-130-nonhuman-ssot-registry.md) — the object-class overlay
  precedents.
- [ADR-074](adr-074-drift-ssot-contention.md) — the contention drift class
  the SSOT stance wires into.
- CHARTER-003 FILE 4 / CHARTER-005-SOA — inter-agency source-of-authority
  doctrine this class operationalizes.
- External: [CRS R47325 on the CMPPA](https://www.congress.gov/crs-product/R47325);
  [DOJ computer matching agreements](https://www.justice.gov/opcl/computer-matching-agreements-and-notices);
  [SSA data exchange](https://www.ssa.gov/dataexchange/);
  [NAPHSIS EVVE](https://www.naphsis.org/evve/);
  [AAMVA S2S FAQ](https://www.aamva.org/technology/systems/driver-licensing-systems/s2s-frequently-asked-questions);
  [6 CFR Part 37 (REAL ID)](https://www.ecfr.gov/current/title-6/chapter-I/part-37);
  [NIST SP 800-66r2](https://csrc.nist.gov/pubs/sp/800/66/r2/final).

## Date

2026-07-25
