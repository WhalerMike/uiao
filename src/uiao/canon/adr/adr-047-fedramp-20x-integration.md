---
id: ADR-047
title: "FedRAMP 20x Integration — KSI emission and Minimum Assessment Scope adoption"
status: PROPOSED
date: 2026-04-27
deciders:
  - canon-steward
  - governance-steward
  - Michael Stratton
extends:
  - ADR-043
supersedes: []
tags:
  - fedramp
  - rfc-0005
  - rfc-0006
  - rfc-0014
  - rfc-0024
  - 20x
  - ksi
  - minimum-assessment-scope
  - oscal
  - cato
canon_refs:
  - UIAO_022
  - UIAO_023
  - UIAO_132
  - UIAO_133
related_findings:
  - FINDING-001
  - FINDING-002
related_discussions:
  - https://www.fedramp.gov/20x/
  - https://www.fedramp.gov/docs/20x/
  - https://www.fedramp.gov/rfcs/0005/
  - https://www.fedramp.gov/rfcs/0006/
  - https://www.fedramp.gov/rfcs/0014/
  - https://www.fedramp.gov/rfcs/0024/
  - https://github.com/FedRAMP/community/discussions/2
---

# ADR-047: FedRAMP 20x Integration — KSI emission and Minimum Assessment Scope adoption

## Status

**PROPOSED — 2026-04-27.** Tracks an actively-rolling-out FedRAMP
program (20x Phase Two Moderate Pilot active November 2025; public
Moderate path Q2 2026). This ADR captures UIAO's intent to align the
substrate's evidence emissions with the FedRAMP 20x KSI catalog and to
apply the Minimum Assessment Scope test to substrate components.
Ratification to ACCEPTED is gated on (a) RFC-0010 best-practices
guidance landing, (b) the Moderate KSI catalog reaching a stable
release at 20x Phase Two close, and (c) substrate evidence emissions
passing a dry-run KSI completeness check against a representative
agency Moderate baseline. Until then, treat every commitment below as
**intent, not obligation**.

## Context

### The framework movement

Two FedRAMP standards introduced under the 20x program materially
change UIAO's authorization-framework environment:

1. **RFC-0005 — Minimum Assessment Scope Standard.** Comment period
   closed 2025-05-25. Replaces traditional FedRAMP boundary policy
   with a two-pronged inclusion test: an information resource is in
   scope if it (a) handles federal information, and/or (b) likely
   impacts confidentiality, integrity, or availability of federal
   information. Information resources and **most metadata** that do
   not meet either prong are explicitly outside the Minimum Assessment
   Scope. The standard rescinds and replaces all previous FedRAMP
   boundary guidance, including the in-flight RFC-0004 boundary policy
   draft.
2. **RFC-0006 / RFC-0014 — Key Security Indicators.** Phase One KSIs
   (RFC-0006) define the Low-baseline catalog (~56 KSIs); Phase Two
   KSIs (RFC-0014) define the Moderate-baseline catalog (~61 KSIs).
   KSIs are organized into themes — KSI-CNA (cloud-native
   architecture), KSI-SVC (service configuration), KSI-IAM (identity
   and access), KSI-MLA (monitoring, logging, audit), KSI-CMT (change
   management / continuous monitoring), KSI-AFR (FedRAMP-specific
   reporting) — and sit above NIST SP 800-53 controls. Each KSI maps
   to a control family, but the artifact a CSP produces is a
   machine-readable, continuously-validated evidence payload, not an
   SSP narrative.

These two standards are coupled with **RFC-0024 — Rev5 Machine-Readable
Packages** (OSCAL-aligned package format that 20x KSI evidence rides
on; mandatory for new submissions after 2026-09-30) and the broader
**OMB M-24-15** reconstitution of FedRAMP under the FedRAMP
Authorization Act.

### Why this is an ADR and not just a finding

[FINDING-002](../../../../docs/findings/fedramp-20x-moderate-pilot.md)
records the framework movement as an environmental constraint. This
ADR records the substrate-level *decision* about how UIAO responds:
the substrate emits KSI-tagged OSCAL evidence, applies the Minimum
Assessment Scope inclusion test to substrate components, and treats
KSI freshness as a first-class drift class. The decision is
substrate-internal and proceeds independently of CSP product timelines
and FedRAMP companion-guidance publication.

### Why this is paired with ADR-043 (RFC-0026 CA-7)

ADR-043 / UIAO_132 commit the substrate to dual-track Continuous
Monitoring pathways (Pathway 1 modernized, Pathway 2 traditional) for
RFC-0026. The 20x program is the umbrella under which that
modernization rides — KSI-tagged OSCAL evidence is the artifact format
the modernized pathway produces. ADR-047 / UIAO_133 are therefore the
*program-level* sibling of ADR-043's *requirement-level* commitment,
and the two documents share the OSCAL machinery defined in Phase 2
§13.2 / UIAO_022.

## Decision

### D1. KSI emission as a tagging discipline, not a re-emission

UIAO does **not** create a new evidence pipeline for KSIs. The
substrate's existing OSCAL artifact pipeline (Phase 2 §13.2,
UIAO_022) — `component-definition`, `assessment-results`, `poam-item`,
`assessment-plan`, aggregated `system-security-plan` — gets a
**KSI-theme tag** at generation time. Each emission carries
`fedramp:ksi-themes: [...]` machine-readable metadata identifying the
KSI(s) the artifact backs, plus a freshness timestamp and a reference
to the Phase 2 TBL-P2-011 row that authorizes the mapping.

**Rationale.** Re-emitting evidence in a parallel KSI-shaped pipeline
would double the substrate's emission surface, halve its provenance
guarantees (two pipelines to keep in sync), and is unnecessary because
KSIs explicitly sit above NIST 800-53 controls — the same evidence
satisfies both layers.

### D2. Minimum Assessment Scope test applied at canon-component granularity

Every canon component (canonical baselines, drift engines, remediation
workflows, provenance layer, adapters, connectors, OSCAL artifact
generators, dashboards) carries a `mas-scope` frontmatter field with
one of three values:

- `in-scope` — the component handles federal information and/or
  likely impacts CIA of federal information; full FedRAMP assessment
  applies.
- `metadata-out-of-scope` — the component handles only metadata
  about substrate operations and does not handle federal information
  itself; explicitly excluded under RFC-0005's metadata exclusion.
- `agency-side-out-of-scope` — the component is installed, managed,
  and operated on agency information systems (per RFC-0005 §D);
  explicitly excluded.

Every component classification carries a brief justification and is
re-evaluated at every canon-version increment. Disagreements among
reviewers escalate to canon-steward for resolution.

**Rationale.** Without per-component classification, the substrate
inherits the prior boundary's "all in" default. RFC-0005 explicitly
permits a narrower in-scope surface; capturing the classification in
canon makes the choice auditable and re-litigatable rather than
implicit.

### D3. KSI staleness is a drift class

A KSI claimed by a substrate component but not backed by a
freshly-generated OSCAL artifact within the cadence specified in Phase
2 TBL-P2-011 is itself a `DRIFT-EVIDENCE-STALE` class drift event.
The drift engine emits the event with severity matching the underlying
KSI's importance (KSI-AFR aggregate failures = P1; per-component KSI
staleness = P2). Remediation workflow is the standard substrate
pattern — open POA&M, route to the responsible adapter owner, close on
fresh emission.

**Rationale.** KSIs are continuous-validation artifacts. A stale KSI
is not "less complete" — it is a control failure under 20x's
continuous-validation premise. Treating it as drift makes the
substrate's response automatic rather than discretionary.

### D4. Pathway posture mirrors ADR-043

UIAO runs the **traditional pathway** at the start of any agency's
20x adoption (existing OSCAL artifacts, manual assessment-style
review of KSI completeness) and **pre-wires** the modernized pathway
(automated KSI completeness certification, agency-authorization-sponsor
direct consumption of the KSI feed) as a gated migration. The gate
fires on the same triggers as ADR-043 — companion-guidance publication
(RFC-0010 for 20x), agency authorization sponsor readiness, and a
clean dry-run.

**Rationale.** Same as ADR-043 D1: dual-track posture protects against
the framework moving in a way the modernized adapter cannot
accommodate, while keeping the modernized path non-deferrable.

### D5. CSP-side filings are out of substrate scope

The substrate's KSI emission surface is well-defined and stable
regardless of whether any specific CSP (Microsoft, AWS, Google) has
filed a 20x-aligned package for its sovereign-cloud offering. CSP
filings are tracked as external-remedy items in
[FINDING-002](../../../../docs/findings/fedramp-20x-moderate-pilot.md)
and propagate to UIAO only as inherited control evidence becomes
available; they do not block substrate-side readiness.

**Rationale.** Coupling substrate readiness to CSP timelines would
make UIAO's 20x posture indeterminate. Decoupling lets the substrate
reach modernized-pathway readiness on its own clock and inherit CSP
KSI evidence opportunistically.

## Consequences

### Positive

1. **Vocabulary parity with FedRAMP 20x.** Substrate emissions speak
   the federal-side framework natively. SSP-narrative translation
   becomes optional rather than mandatory.
2. **Smaller in-scope surface.** Components classified
   `metadata-out-of-scope` or `agency-side-out-of-scope` exit the
   substrate's FedRAMP assessment burden, consistent with RFC-0005's
   metadata exclusion.
3. **KSI freshness as a drift class** raises the quality bar on
   telemetry ingestion: stale telemetry now produces a substrate-level
   alert rather than a silent compliance gap.
4. **Continuity with ADR-043.** The modernized pathway adapters under
   ADR-043 (`vdr-bir`, `ccm-bir`) compose cleanly with KSI emission;
   no architectural conflict.

### Negative / risks

1. **`mas-scope` classification drift.** Per-component classification
   adds a maintenance surface. Mitigation: classification review is
   bundled into canon-version increment review (existing process).
2. **3PAO interpretation risk.** RFC-0005's "likely impact" prong is
   intentionally broad. A 3PAO could re-classify a substrate
   component the canon-steward marked `metadata-out-of-scope`.
   Mitigation: every classification carries a written justification
   citing the specific data the component touches, so the disagreement
   is structured and adjudicable.
3. **KSI catalog churn.** Phase Two KSI count is approximate (~61 at
   Moderate); the final published catalog at Phase Two close may
   re-number or merge themes. Mitigation: TBL-P2-011 mapping uses KSI
   *themes* (KSI-CNA, KSI-MLA, etc.) not individual KSI IDs, so
   theme-level mappings are stable across catalog churn.
4. **Companion-guidance dependency.** Promotion to ACCEPTED depends on
   RFC-0010 best-practices guidance, which has been promised but not
   yet published. Mitigation: PROPOSED status is honest; substrate
   emission tagging proceeds under the published RFC-0005 / 0006 /
   0014 / 0024 surfaces.

### Neutral / informational

- ADR-047 does not change substrate code or emission contracts. It
  changes *labels* on existing emissions and adds a frontmatter field
  to canon components. The drift engine, evidence graph, provenance
  chain, OSCAL pipeline, and all adapters are unchanged.
- ADR-047 does not assert that any specific CSP has filed a
  20x-aligned sovereign-cloud package. CSP filings are tracked
  externally in FINDING-002.

## Ratification gate

This ADR moves from PROPOSED to ACCEPTED when **all** of the following
conditions are met:

1. FedRAMP RFC-0010 (best practices guidance) is published and the
   substrate's MAS classification rubric (D2) is re-validated against
   it.
2. The Moderate KSI catalog reaches a stable release at FedRAMP 20x
   Phase Two close (Q2 2026 or later as the program slips).
3. A dry-run KSI completeness check is executed against a
   representative agency Moderate baseline and produces zero
   KSI-staleness drift events with P0 or P1 severity.
4. Canon-steward and governance-steward sign off on the dry-run
   results.

Until all four conditions are met, this ADR remains PROPOSED.

## Operational mechanics

Operational mechanics — which adapter emits which KSI, which workflow
fans out which staleness alert, which canon artifact answers which
KSI theme — are recorded in **UIAO_133** at
`src/uiao/canon/specs/fedramp-20x-integration.md`. UIAO_133 is the
operational companion to this ADR.

## Related

- [ADR-043 — FedRAMP RFC-0026 CA-7 Integration](./adr-043-fedramp-rfc-0026-ca7-integration.md)
- UIAO_132 — FedRAMP RFC-0026 CA-7 Pathway Integration spec
- UIAO_133 — FedRAMP 20x Integration spec (operational mechanics)
- [FINDING-001 — FedRAMP GCC-Moderate INR unavailability](../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md)
- [FINDING-002 — FedRAMP 20x Moderate Pilot active](../../../../docs/findings/fedramp-20x-moderate-pilot.md)
- Phase 0 §1 — Master Plan, FedRAMP Boundary Gap paragraph (forward-looking note)
- Phase 2 §13.3 — KSI Emission Surface (TBL-P2-011)
- Phase 3 §4.1.1 — FedRAMP 20x KSI Crosswalk (P3-T-001a)
