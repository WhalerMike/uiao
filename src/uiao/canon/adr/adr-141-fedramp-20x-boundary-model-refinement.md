---
id: ADR-141
title: "FedRAMP 20x Boundary Model — Per-Resource Categorisation, Metadata Inclusion, and the Shared-Responsibility Scope Test (refines ADR-106)"
status: PROPOSED
date: 2026-09-09
deciders:
  - governance-steward
  - conmon-steward
  - Michael Stratton
extends:
  - ADR-106
supersedes: []
tags:
  - fedramp
  - fedramp-20x
  - cr26
  - minimum-assessment-scope
  - boundary
  - scn
  - gcc
canon_refs:
  - UIAO_007
related_findings:
  - FINDING-PGM-005
related_discussions:
  - https://fedramp.gov/scope
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-141-fedramp-20x-boundary-model-refinement.html
---

# ADR-141: FedRAMP 20x Boundary Model — Per-Resource Categorisation, Metadata Inclusion, and the Shared-Responsibility Scope Test (refines ADR-106)

## Status

**PROPOSED — 2026-09-09.** ADR-106 (ACCEPTED 2026-06-25) adopted the Minimum
Assessment Scope test against **RFC-0005**, the pre-consolidation draft. The
Consolidated Rules for 2026 shipped on **2026-06-24** — one day before ADR-106
was accepted — and three MAS provisions differ from the draft it was written
against.

This ADR **refines** ADR-106; it supersedes nothing. Per **CR-003**, ADR-106 is
ACCEPTED and its Context, Decision and Date are immutable, so it is not edited.
This follows the partial-refinement pattern ADR-111 established for ADR-043.
The environmental facts are recorded in
[FINDING-PGM-005](../../../../docs/findings/fedramp-20x-replaces-the-authorization-boundary.qmd).

### Status history

| Date | Status | Note |
|---|---|---|
| 2026-09-09 | PROPOSED | Raised from a direct read of the vendored official CR26 ruleset (2026.06.24.01) while extending the Microsoft Docset Cross-Check of 2026-09-04. |

## Context

ADR-106 §Context characterises the MAS test from RFC-0005 and states that
"most metadata that do not meet either prong are explicitly outside the
Minimum Assessment Scope." Read against the shipped ruleset, three things need
saying that the draft did not support.

**There is no CSP authorization boundary at all.** "Authorization boundary"
occurs **zero** times in the official ruleset. The eight occurrences of
"boundary" are the *agency's* boundary containing the offering (3), a
classification tag on four rule families (4), and inherited SP 800-53 `SR-08`
guidance (1). FedRAMP tags exactly four families `boundary`: **MAS**, **UCM**,
**VDR** and **CDS**. The boundary is no longer a shape; it is those four
obligations.

**Metadata inclusion reversed between draft and rule.** `MAS-CSO-MDI` requires
providers to include metadata — explicitly including metadata *about* federal
customer data — in the Minimum Assessment Scope whenever `MAS-CSO-IIR` applies.
That is more inclusive than ADR-106's characterisation.

**Security category became per-resource.** `MAS-CSO-FLO` requires flows and
categories for all resources and its guidance states resources **"MAY vary by
security category."** Rev 5 carried one impact level across a whole boundary.
This is the provision with the largest consequence for how the substrate and
the customer corpus describe GCC.

## Decision

**D1 — Metadata is in scope with its resource.** The substrate treats metadata
as inheriting the scope determination of the resource it describes, per
`MAS-CSO-MDI`. Where ADR-106's Context implies metadata is presumptively out of
scope, **this decision governs.** ADR-106's decisions are unaffected; only its
characterisation of the draft rule is corrected.

**D2 — Security category is a per-resource property, not a system-wide label.**
Substrate scope determinations record a security category *per information
resource*, not one category for an offering or an environment. No emitted
artifact may assert a single impact level across a heterogeneous set of
resources on the strength of an environment name.

**D3 — The shared-responsibility test is a scope question, and must be asked
explicitly.** `MAS-CSO-IIR` guidance places software delivered for installation
on agency systems and **not operated in a shared-responsibility model** —
"agents, application clients, mobile applications" — entirely outside FedRAMP
under the Certification Act. Any substrate document that reasons about endpoint
software inside a federal scope claim (Intune agents, Defender sensors, the
Entra Connect Sync engine) MUST state whether that component is operated in a
shared-responsibility model, because the answer decides whether it is in scope
at all. Silence is not a neutral default; it reads as an unstated assumption
that it is in scope.

**D4 — Change classification follows SCN, and routine recurring is exempt.**
Substrate change-control language maps to the three `FRD` classes — routine
recurring (`FRD-RTR`, exempt from notification per `SCN-RTR-NNR`), adaptive
(`FRD-ADP`, notify within 10 business days after), transformative (`FRD-TRF`,
30/10 before and 5/5 after). Notifications are emitted human- and
machine-readable per `SCN-CSO-HRM`, which the evidence fabric already
satisfies.

**D5 — "Boundary" is used in this corpus only with a stated referent.** Because
the ruleset has three distinct senses, no substrate or customer document uses
"boundary" unqualified. It is either *the agency's authorization boundary*, or
*one of the four boundary-tagged rule families*, or an explicitly historical
Rev 5 reference. The GCC-Moderate terminology footnote at B.1 §0 stands and is
extended by this decision.

## Consequences

**Positive.** The scope question becomes one the substrate is already built to
answer: "which resources are likely to handle or impact federal customer data"
is a data-lineage query, not a network diagram. Per-resource categorisation
also removes the high-water-mark pressure that made a single environment label
attractive in the first place.

**Negative / accepted cost.** D2 invalidates the shorthand. A good deal of
corpus prose reaches for one label per environment, and replacing it means
naming resources and their categories — more words, and in places genuine work
that has not been done. D3 will surface questions the boundary documents
currently do not ask, and some will not have answers yet.

**Unresolved — partly closed 2026-09-09.** The ruleset carries no FedRAMP impact
level for any Microsoft offering, so this ADR does not settle the GCC question
from the framework side. The Marketplace does settle the Rev5 listing, and was
read: `MSO365MTA` is **Class D (High)**, **FedRAMP In Process**, zero
authorizations, having left FedRAMP Certified on 2026-07-01
([FINDING-PGM-006](../../../../docs/findings/gcc-marketplace-listing-class-d-in-process.qmd)).
That resolves the level as **High rather than Moderate**, and confirms this
ADR's expectation that the lookup would answer a Rev5 question: the listing is
Type Rev5, so it says nothing about how the offering will be scoped once D2's
per-resource categorisation applies.

One tension this creates and does not resolve: the listing's **vendor-supplied**
description says M365 GCC "leverages Azure Government as the IaaS/PaaS", while
the M365 docset (p.755) has GCC pairing with Azure Commercial. These are most
likely different layers — IaaS/PaaS hosting versus Entra ID tenant pairing — but
that is inference, and neither source is authoritative for the other's layer.
Documents should state the layer they mean rather than swapping one claim for
the other.

## Ratification gate

Promotion from PROPOSED to ACCEPTED requires:

1. A pass over the boundary documents applying **D2**, confirming no emitted
   artifact asserts one impact level across heterogeneous resources.
2. An explicit **D3** determination for the three named endpoint components,
   recorded wherever they appear inside a federal scope claim.
3. Confirmation of how the Rev5 and 20x paths coexist for offerings certified
   under Rev5 through at least 2028-12-31, since D2 and D5 describe the 20x
   model and Rev5 packages retain boundary vocabulary.
