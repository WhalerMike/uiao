---
adr_id: adr-089
title: "UIAO Program Narrative Pillars — Three Domain Reading-Sequences (OrgPath, Modernization, Compliance)"
status: ACCEPTED
decided: 2026-06-01
deciders: Michael Stratton
updated: 2026-06-01
next_review: 2026-12-01
review_trigger: A fourth program narrative pillar is proposed; the Divio Explanation-quadrant mapping in ADR-083 is revised; UIAO Modernization or UIAO Compliance is proposed to subsume the Reference-Architecture (ADR-083) or compliance reference docs rather than sit alongside them as Explanation; the "UIAO OrgPath" pillar is proposed to be renamed "UIAO Governance"
impact: 'Establishes that the UIAO program tells its story through three domain-scoped narrative pillars in the Divio Explanation quadrant (ADR-083): UIAO OrgPath (the governance substrate), UIAO Modernization (the Active Directory to Entra ID journey), and UIAO Compliance (the GCC-Moderate boundary and FedRAMP / SCuBA regime). Fixes that UIAO is the program and OrgPath is one part of it, so the governance-substrate narrative is named for its protagonist (UIAO OrgPath) rather than "UIAO Governance" — which would collide with the program-level term "UIAO Governance OS." The pillars are Explanation-layer narratives that do not duplicate the Reference (reference-architecture canon) or How-to (operational-guides) content of their domains. Doctrine only: no runtime, schema, or registry change. UIAO OrgPath is realized today (the orgpath-narrative section, renamed from "OrgPath Narrative" in PR #733); UIAO Modernization and UIAO Compliance are established incrementally as new narrative sections. Interim home for new governance-substrate product books (InfoBlox DDI, Identity Governance, PKI) is UIAO OrgPath.'
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-089-program-narrative-pillars.html
---

# ADR-089: UIAO Program Narrative Pillars — Three Domain Reading-Sequences

## Status

**ACCEPTED** — 2026-06-01.

This ADR is doctrine. It fixes how the UIAO program is told as narrative — the
naming, scope, and relationship of its domain reading-sequences. It does not
change any runtime behavior, schema, registry entry, or URL. It extends
[ADR-083](adr-083-docs-architecture-reorganization.md) (the Divio documentation
architecture) by formalizing the structure of the **Explanation** quadrant.

## Context

[ADR-083](adr-083-docs-architecture-reorganization.md) reorganized the site into
a single `/customer-documents/` umbrella with Divio-aligned quadrants. It mapped
the **Explanation** quadrant (understanding-oriented; the "why") to "UIAO OrgPath,
executive briefs, whitepapers," and named the meta-pattern behind the program's
recurring "are these duplicates?" reviews: *what looks like duplication is
layered refinement* — a canon spec (Reference) plus an operational guide (How-to)
plus a narrative explainer (Explanation) for the same topic.

Since then the **UIAO OrgPath** narrative (renamed from "OrgPath Narrative" in
PR #733) has matured into the program's only developed Explanation-voice reading
sequence — eighteen book-level documents (Books 01–16, the 07a Azure-SSOT
supplement, and the 11a Identity-Governance supplement). It is excellent at what
it does: it explains the OrgTree/OrgPath governance substrate and its projection
onto every Microsoft and third-party surface.

But **UIAO is the whole program, and OrgPath is one part of it** — the governance
substrate. Two other large bodies of program work have no narrative home:

1. **The Active Directory → Entra ID modernization journey** — the phase model,
   modernization mechanics, and decommissioning sequence. This material exists as
   specification (the Reference-Architecture canon, e.g. the ADR-081 phase model)
   and as drafts (`inbox/Modernization/` — Phase 0–5 documents), but it has never
   been told as a continuous-voice reading sequence.
2. **The boundary and compliance regime** — the GCC-Moderate boundary model,
   FedRAMP 20x, and SCuBA. This material exists as reference and how-to content
   (`/customer-documents/compliance/`) and as analyses (`inbox/` FedRAMP work),
   but, again, not as a narrative.

Three symptoms follow from having one program narrative carry program-wide scope:

- **Over-claim.** Book 15 is titled "UIAO Governance OS — The Complete Narrative,"
  but its own subtitle scopes it to "a synthesis of the OrgPath / OrgTree
  substrate." A *part's* narrative is wearing the *program's* name.
- **No home for new narrative.** When the modernization or compliance story needs
  telling as a reading sequence, there is nowhere for it to go, so it is either
  forced into UIAO OrgPath (inflating it) or left only as spec/how-to.
- **A naming hazard.** "Governance" is already the program-level word — the
  program is informally called the "UIAO Governance OS." Naming the
  governance-substrate narrative "UIAO Governance" would re-create the exact
  whole-vs-part confusion this ADR resolves.

## Decision

### D1. Three program narrative pillars

The UIAO program tells its story through **three domain-scoped narrative pillars**
in the Divio **Explanation** quadrant ([ADR-083](adr-083-docs-architecture-reorganization.md)).
Each is a multi-book reading sequence in the continuous narrative voice, prefixed
`UIAO`:

| Pillar | Domain | Status |
|---|---|---|
| **UIAO OrgPath** | The governance substrate — OrgTree/OrgPath and its projection onto every Microsoft and third-party surface | **Realized** (the `orgpath-narrative` section) |
| **UIAO Modernization** | The Active Directory → Entra ID journey — phase model, modernization mechanics, decommissioning | To be established |
| **UIAO Compliance** | The boundary and compliance regime — GCC-Moderate boundary, FedRAMP 20x, SCuBA | To be established |

### D2. Naming doctrine — protagonist for OrgPath, domain for the others

The pillar names are program-scoped (`UIAO …`). The governance-substrate pillar
retains its **protagonist** name, **UIAO OrgPath**, rather than "UIAO Governance."
"Governance" is the program-level term (the "UIAO Governance OS"); naming a part
"Governance" would collide with the whole. OrgPath is also the binding invariant
of that pillar — every governed object carries OrgPath in a native field — so the
name describes the spine, not merely one product among many. The Modernization and
Compliance pillars are **domain-named** because no such collision exists for them.

### D3. Pillars are Explanation, not duplication

The pillars are **Explanation**-quadrant narratives. They *explain*; they do not
duplicate the **Reference** (the reference-architecture canon specifications) or
**How-to** (the operational guides) content of their domain. Each domain may
therefore carry up to three layers — canon spec + operational guide + program
narrative — which is the layered-refinement pattern [ADR-083](adr-083-docs-architecture-reorganization.md)
named, applied deliberately rather than discovered as accidental duplication.

### D4. Reading order — Modernize → Govern → Comply

The canonical program reading order is **UIAO Modernization → UIAO OrgPath → UIAO
Compliance**: first the journey from the legacy estate, then the governance
substrate that the journey stands up, then the boundary and compliance regime that
proves it to authorizing officials. Cross-links between pillars follow this spine.

### D5. Incremental establishment; no existing section is moved

UIAO OrgPath is live. **UIAO Modernization** and **UIAO Compliance** are stood up
as new narrative sections under `/customer-documents/`, seeded from the existing
modernization drafts (`inbox/Modernization/`) and the compliance corpus
respectively, authored to the established OrgPath book recipe (subagent-drafted
chapters from an exemplar + deterministic fact-check + white-background fig-alt
diagrams). **This ADR fixes the structure and naming only.** It does not rename or
move the `reference-architecture/` or `compliance/` sections; the new pillars sit
*alongside* them as the Explanation layer of their domains. The books are
follow-on work.

### D6. Interim home for governance-substrate product books

Until the other pillars mature, new governance-substrate product books — the
InfoBlox DDI reframe (Book 14), the Identity Governance Plane (Book 11a), the
forthcoming PKI / network-access / PAM work tracked in
`inbox/drafts/ad-governance-to-products-mapping.md` — belong under **UIAO
OrgPath**, because they are governance-substrate content. This ratifies the
current practice; it is not a new constraint.

## Consequences

**Positive.** Every program domain gets a narrative home of the right altitude.
UIAO OrgPath stops being asked to carry program-wide scope. The naming is
unambiguous, and there is a defined reading spine for a reader who wants the whole
program rather than one part.

**Costs / follow-ups (not done by this ADR).**

- Two new narrative sections must be authored over time.
- Book 15's title ("UIAO Governance OS — The Complete Narrative") should be
  re-scoped to the OrgPath substrate; it currently over-claims at the program
  level. Tracked as follow-up, not changed here (ADR immutability and content
  review apply to the book, not this ADR).
- The `UIAO Modernization` and `UIAO Compliance` section landings, sidebar nav,
  and the customer-documents portal index will be added when each pillar's first
  book lands.

**Boundary.** GCC-Moderate. Doctrine only — no runtime, schema, or registry
change, consistent with [ADR-088](adr-088-hr-as-orgtree-truth-source.md).

## Alternatives considered

- **Keep one program narrative (status quo).** Rejected: it conflates the part
  (OrgPath) with the whole (UIAO) and forces over-claiming titles like Book 15's.
- **Domain-name all three, including "UIAO Governance."** Rejected: collides with
  the program-level "UIAO Governance OS," re-introducing the whole-vs-part
  ambiguity this ADR removes.
- **Tell modernization and compliance only as Reference / How-to (no narrative).**
  Rejected: it discards the Explanation-voice reading sequence that UIAO OrgPath
  has demonstrated is the most accessible way into a complex substrate — the
  precise value the narrative form provides.

## References

- [ADR-083](adr-083-docs-architecture-reorganization.md) — Divio documentation
  architecture; the Explanation quadrant this ADR structures.
- [ADR-072](adr-072-canon-publication-policy.md) — canon publication policy and
  the publication-gap scanner.
- [ADR-076](adr-076-tier-conformance-model.md) — lifecycle/tier semantics for
  canon vs customer-doc surfaces.
- [ADR-085](adr-085-universal-enterprise-positioning.md) — universal-enterprise
  positioning of the UIAO core engine (program scope).
- PR #733 — the "OrgPath Narrative" → "UIAO OrgPath" rename that realized the
  first pillar.
- `inbox/drafts/ad-governance-to-products-mapping.md` — the governance-substrate
  product buildout that lands under UIAO OrgPath (D6).
