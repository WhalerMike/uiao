---
title: "Whitepaper Roadmap — How the 22 Papers Relate, and What to Read First"
status: DRAFT
date: 2026-08-03
depends_on: inbox/whitepaper-structure-assessment-2026-08-03.md
scope: docs/customer-documents/whitepapers/ (22 papers, excludes index.qmd)
---

# Whitepaper Roadmap

`docs/customer-documents/whitepapers/index.qmd` lists all 22 papers as a
flat table (slug, topic, status, canon anchor) — good for lookup, silent
on how the papers relate to each other or which order to read them in.
Nobody arriving cold can tell that `modernization-journey.qmd` and
`federal-application-aware-networking-architecture.qmd` cover the same
forty-year arc from two different angles, or that
`zero-trust-governance-principles.qmd` supersedes the scope of
`zero-trust-governance-whitepaper.qmd` without replacing it. **None of
the 22 papers cross-reference each other along these lines today** — this
document makes those relationships explicit for the first time and
proposes a set of reading paths. It is a draft companion to the index,
not a replacement; nothing here has been published to the site.

## The corpus at a glance

Two genres (established in the 2026-08-03 structure assessment):

- **Policy/architecture papers** — Executive Summary → numbered sections
  → Honest Limits → Conclusion. These state UIAO's governance doctrine
  and map it onto a compliance framework (ZTMM, BOD-25-01, FedRAMP).
- **Narrative papers** — "In this whitepaper" → Act/Part structure →
  canon-mapping table → Provenance. These tell an operational or
  historical story and derive the doctrine from it rather than stating it
  up front.

Three papers (`ad-to-entraid-migration-problem`,
`aodim-executive-whitepaper`, `uiao-vs-native-tools`) predate both
genres — they're docx imports from before the canon-anchoring convention
existed. They carry real content (the original business case for the
whole program) but the 2026-07-26 content memo already flags them for
reconciliation; treat them as historically important but structurally
behind the rest of the corpus.

## Six tracks

Papers are grouped by the question they answer, not by filename. Several
papers earn a place in more than one track — that's cross-listed, not a
mistake.

### Track 1 — Governance Foundations (start here for "what is UIAO")

| Slug | Status | Role |
|---|---|---|
| `uiao-governance-os-whitepaper` | Active | **Flagship.** Defines the substrate, the three operating principles, the evidence chain. Everything downstream assumes this. |
| `zero-trust-governance-whitepaper` | Active | Maps the substrate onto CISA's five ZTMM pillars, pillar by pillar. |
| `zero-trust-governance-principles` | Active | Broader and newer than the paper above — whole-agency (Network+CSP+VMware) scope, cross-cutting capabilities, the "why programs stall below Advanced" argument. Read *after* `zero-trust-governance-whitepaper`, not instead of it: the whitepaper is the substrate-to-pillar mapping, the principles paper is the maturity-model argument for why pillar tools alone don't clear Advanced. |
| `modernization-governance-whitepaper` | Active | Governance framing specifically for the AD→Entra ID migration — the bridge into Track 2. |

### Track 2 — Identity & Directory Modernization (the AD → Entra ID arc)

| Slug | Status | Role |
|---|---|---|
| `ad-to-entraid-migration-problem` | Active *(pre-canon import)* | Original statement of the structural migration problem. Read for the business case; content is due for a canon-reconciliation pass. |
| `aodim-executive-whitepaper` | Active *(pre-canon import)* | The attribute-oriented directory/identity model — oldest architectural core of the program. Also flagged for reconciliation (retired Model B OrgPath examples). |
| `modernization-journey` | Draft | The canon-anchored version of the mainframe→cloud arc (ADR-092/066/068/007), reconciled and cross-linked to Vol I Book 05. **UIAO-branded** — see the AAN note below for how this differs from Track 4's narrative. |
| `hybrid-join-without-governance` | Draft | One concrete operation *inside* the `modernization-journey` arc — flipping devices to hybrid join, governed vs. ungoverned. Read after `modernization-journey`; it assumes that arc's control-plane/data-plane framing. |
| `federal-ssot-alignment` | Active | Same identity-modernization event, read through the data-governance/SSOT-mandate lens instead of the architecture lens. |
| `uiao-vs-native-tools` | Active *(pre-canon import)* | AD assessment methodology and gap analysis against Microsoft-native tooling — also anchors Track 6. |

### Track 3 — Zero Trust Assessment & Compliance Closure (BOD-25-01 / SCuBA)

| Slug | Status | Role |
|---|---|---|
| `bod-25-01-close-before-assess` | Active | The sequencing argument — remediate before you assess — that the other three papers in this track assume. Read first in this track. |
| `scubagear-integration-whitepaper` | Active | How CISA's ScubaGear assessor output feeds UIAO's evidence pipeline. |
| `zta-scuba-relationship` | Active | Disambiguates Microsoft's Zero Trust Assessment from CISA SCuBA — read when a stakeholder asks "aren't these the same tool?" |
| `ticket-to-machine-not-ticket-to-human` | Draft | Closure-evidence argument across Azure/AWS/VMware + ServiceNow/SailPoint — the "how do we know a finding is actually closed" question this whole track is building toward. |

### Track 4 — Network & Infrastructure Modernization

| Slug | Status | Role |
|---|---|---|
| `federal-application-aware-networking-architecture` (AAN) | Draft | **Flagship of this track.** Same forty-year mainframe-to-Zero-Trust arc as `modernization-journey`, told **vendor-neutral, product-neutral, and explicitly not reconciled to any UIAO ADR** (see frontmatter `derived-from`) — written to hand to an audience that isn't ready for a UIAO-branded pitch. Has the corpus's only labeled Call to Action. |
| `tic3-sdwan-vs-dia` | Draft | The transport-and-policy layer underneath AAN's Act 4 — SD-WAN vs. DIA under TIC 3.0. Read after AAN's Act 4 or standalone for a network-engineering audience. |
| `infoblox-hybrid-dns-unified-ddi` | Draft | The DNS layer underneath the same Act 4 architecture — split-brain DNS, Universal DDI, Cisco SD-WAN interception. Sibling to `tic3-sdwan-vs-dia`, not sequential to it — both sit under AAN's Act 4 independently. |
| `git-server-interfaces-whitepaper` | Draft | Platform deployment surface (Windows Server 2025) — narrower scope, useful once an agency has committed to a UIAO deployment rather than during the architecture-decision phase the rest of this track addresses. |

**AAN vs. `modernization-journey` — read one, not both, unless your
audience needs both angles.** They are siblings, not a sequence: AAN is
the external, vendor-neutral pitch (hand it to an audience wary of a
platform commitment); `modernization-journey` is the internal,
canon-anchored version (hand it to a team that has already adopted UIAO
and needs the ADR trail). Picking the wrong one for the audience is the
single most common mis-sequencing risk in this corpus.

### Track 5 — Federal Program-Specific Alignment

| Slug | Status | Role |
|---|---|---|
| `federal-hrit-productization` | Active | Inbound HR provisioning into Entra ID under Spec 2 — a specific integration domain, not a general-purpose entry point. |
| `federal-ai-governance-submission-readiness` | Active | AI-system governance under M-25-21 — narrowest scope in the corpus; read only if AI-system inventory/ATO submission is the live question. |
| `federal-ssot-alignment` | Active | Cross-listed from Track 2 — also belongs here as a data-governance-mandate alignment paper. |

### Track 6 — Positioning, Comparison & Vendor Reads

| Slug | Status | Role |
|---|---|---|
| `uiao-vs-native-tools` | Active *(pre-canon import)* | Cross-listed from Track 2 — the build-vs-buy / gap-analysis anchor for this track. |
| `orgpath-composability-matrix` | Active | "Choose your partners" — which OrgPath capability packs and identity/storage targets combine, à la carte. Read before either comparison paper below if the reader needs the composability model first. |
| `snowflake-keypair-vs-uiao-orgpath` | Draft | Illustrative-only architecture comparison (explicitly not an authorization to build) — read as a worked example of how OrgPath *would* apply to a platform UIAO doesn't govern today. |

## Recommended reading paths

Pick the path that matches why the reader opened the site, not the
alphabetical file list.

**A federal CIO/CISO with 30 minutes (first exposure)**
1. `uiao-governance-os-whitepaper` — what the substrate is and why "operating system," not "framework."
2. `federal-application-aware-networking-architecture` — the compliance-deadline argument (FedRAMP 20x) and the Call to Action. This is the one paper in the corpus written to be handed off without modification.

**An assessor validating BOD-25-01 / ZTMM claims**
1. `bod-25-01-close-before-assess` — the sequencing argument.
2. `scubagear-integration-whitepaper` → `zta-scuba-relationship` — how the evidence is produced and how it differs from Microsoft's own assessment.
3. `zero-trust-governance-principles` — the maturity-model context for what "closed" is being measured against.
4. `ticket-to-machine-not-ticket-to-human` — how closure evidence is distinguished from a changed setting.

**A network/infrastructure architect**
1. `federal-application-aware-networking-architecture` — the full arc and the physics argument.
2. `tic3-sdwan-vs-dia` and `infoblox-hybrid-dns-unified-ddi` — read in either order; both sit under AAN's Act 4 independently.
3. `git-server-interfaces-whitepaper` — once a UIAO deployment is actually being planned.

**An identity/directory team running an AD → Entra ID modernization**
1. `ad-to-entraid-migration-problem` — the original problem statement.
2. `modernization-governance-whitepaper` → `modernization-journey` — governance framing, then the canon-anchored arc.
3. `hybrid-join-without-governance` — the first concrete operation to execute inside that arc.
4. `federal-ssot-alignment` — the data-governance-mandate framing of the same event.

**Someone evaluating UIAO against Microsoft-native tools or a build-vs-buy decision**
1. `uiao-vs-native-tools` — the gap analysis.
2. `orgpath-composability-matrix` — what's actually à la carte, so "build vs. buy" isn't a false binary.
3. `snowflake-keypair-vs-uiao-orgpath` — a worked example on a platform outside today's boundary, useful for gauging how far the model generalizes.

**Reading the whole corpus, start to finish**

Track 1 (all four) → Track 2 (all six) → Track 3 (all four) → Track 4
(all four) → Track 5 (`federal-hrit-productization`,
`federal-ai-governance-submission-readiness`; `federal-ssot-alignment`
already read in Track 2) → Track 6
(`orgpath-composability-matrix`, `snowflake-keypair-vs-uiao-orgpath`;
`uiao-vs-native-tools` already read in Track 2). This order front-loads
the doctrine (Track 1) before any domain paper assumes it, and reads
AAN and `modernization-journey` back-to-back so the vendor-neutral vs.
canon-anchored contrast is visible rather than discovered by accident
months apart.

## Open items this roadmap surfaces

- No paper currently states these track relationships in its own
  frontmatter or a "Related"/"Companion series" section — `AAN` and
  `modernization-journey` in particular should probably cross-link to
  each other given how easy it is to hand the wrong one to an audience.
- The Track-4 CTA drafts (`inbox/drafts/narrative-whitepaper-ctas-2026-08-03.md`)
  cover `modernization-journey`, `hybrid-join-without-governance`,
  `infoblox-hybrid-dns-unified-ddi`, and `tic3-sdwan-vs-dia` — i.e. most
  of Track 4 plus one Track 2 paper. `git-server-interfaces-whitepaper`
  (Track 4) has no CTA draft yet.
- If this roadmap is adopted, the natural home is a new
  `docs/customer-documents/whitepapers/reading-guide.qmd`, linked from
  `index.qmd`, rather than leaving it in `inbox/`.
