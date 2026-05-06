---
title: "FedRAMP 20x Moderate Pilot active — boundary and telemetry framework movement"
finding_id: "FINDING-002"
status: Awaiting-External-Remediation
severity: P2
created_at: "2026-04-27"
updated_at: "2026-04-27"
owner: "Michael Stratton"
related_canon: ["UIAO_003", "UIAO_020", "UIAO_022", "UIAO_023", "UIAO_109", "UIAO_110", "UIAO_113", "UIAO_131", "UIAO_132", "UIAO_133"]
related_adrs: ["ADR-047"]
supersedes: []
superseded_by: []
---

# FedRAMP 20x Moderate Pilot active — boundary and telemetry framework movement

## 1. Constraint

FedRAMP has moved its authorization framework forward in two ways
that materially change the policy environment UIAO operates in,
without yet changing the operational telemetry surface inside
GCC-Moderate:

1. **Minimum Assessment Scope Standard (RFC-0005, comment period
   closed 2025-05-25).** Replaces the prior "authorization
   boundary" construct with a two-pronged inclusion test: an
   information resource is in scope if it (1) handles federal
   information, and/or (2) likely impacts confidentiality,
   integrity, or availability of federal information. Information
   resources and **most metadata** that do not meet either prong
   are explicitly outside the Minimum Assessment Scope. The
   standard rescinds and replaces all previous boundary guidance,
   including the in-flight RFC-0004 boundary policy draft.
2. **20x Phase Two Moderate Pilot active.** Phase Two formally
   began November 2025 and concludes by end of Q1 2026, with a
   public Moderate path arriving in Q2 2026. Phase Two introduces
   ~61 Key Security Indicators (KSIs) at the Moderate baseline,
   organized into themes including KSI-CNA (cloud-native
   architecture), KSI-SVC (service configuration), KSI-IAM
   (identity and access), KSI-MLA (monitoring, logging, audit),
   KSI-CMT (change management / continuous monitoring), and
   KSI-AFR (FedRAMP-specific reporting). KSIs sit above NIST
   SP 800-53 — each KSI maps to a control family, but the artifact
   produced is a machine-readable, continuously-validated evidence
   payload, not an SSP narrative.

The constraint UIAO names is **the gap between framework
movement and operational reality.** 20x changes how FedRAMP
assesses; it does not by itself ship telemetry features into
sovereign clouds. Until Microsoft (or any other CSP whose
government offering is referenced by UIAO) files a 20x-aligned
package for its GCC-Moderate offering, the telemetry signals
documented in [FINDING-001](./fedramp-gcc-moderate-informed-network-routing.md)
and the broader gap inventory remain operationally unchanged.

## 2. Evidence

### Primary sources (FedRAMP)

- **[FedRAMP 20x Overview](https://www.fedramp.gov/20x/)** —
  Accessed 2026-04-27. Program scope, automation-first model,
  KSI framing, Phase One / Phase Two structure.
- **[FedRAMP 20x Documentation index](https://www.fedramp.gov/docs/20x/)** —
  Accessed 2026-04-27. Standards published under 20x including
  Minimum Assessment Scope and Key Security Indicators.
- **[Key Security Indicators — 20x docs](https://www.fedramp.gov/docs/20x/key-security-indicators/)** —
  Accessed 2026-04-27. KSI taxonomy and machine-readable
  definitions.
- **[FedRAMP 20x Phase One](https://www.fedramp.gov/20x/phase-one/)** —
  Accessed 2026-04-27. Phase One scope, Low-baseline KSI count
  (~56), pilot authorization references.
- **[RFC-0005 Minimum Assessment Scope Standard](https://www.fedramp.gov/rfcs/0005/)** —
  Accessed 2026-04-27. Standard replacing prior boundary policy.
  Comment period 2025-04-24 to 2025-05-25, closed.
- **[RFC-0005 Community Discussion (closed)](https://github.com/FedRAMP/community/discussions/2)** —
  Accessed 2026-04-27. Verbatim standard language, commenter
  exchange. Direct quote of inclusion test:
  > "The Minimum Assessment Scope includes all information
  > resources managed by a cloud service provider and their cloud
  > service offering that: 1. Handle federal information; and/or
  > 2. Likely impact confidentiality, integrity, or availability
  > of federal information."

  Direct quote of exclusion language:
  > "Information resources and metadata that do not meet condition
  > (1) or (2) are outside the Minimum Assessment Scope."
- **[RFC-0006 20x Phase One Key Security Indicators](https://www.fedramp.gov/rfcs/0006/)** —
  Accessed 2026-04-27. Phase One KSI catalog.
- **[RFC-0014 Phase Two Key Security Indicators](https://www.fedramp.gov/rfcs/0014/)** —
  Accessed 2026-04-27. Phase Two KSI additions for Moderate.
- **[RFC-0024 Rev5 Machine-Readable Packages](https://www.fedramp.gov/rfcs/0024/)** —
  Accessed 2026-04-27. OSCAL-aligned machine-readable package
  format that 20x KSI evidence rides on.
- **[FedRAMP — Realizing the FedRAMP Authorization Act (Jan 2026)](https://www.fedramp.gov/2026-01-13-realizing-the-fedramp-authorization-act/)** —
  Accessed 2026-04-27. Statutory grounding for the 20x direction.

### Supporting sources

- **[FedRAMP RFCs index](https://www.fedramp.gov/rfcs/)** —
  Open and closed RFCs, including the companion RFC-0010
  best-practices guidance referenced (but not yet published) at
  RFC-0005 closure.
- **[Initial Outcome from RFC-0024 Rev5 Machine-Readable Packages](https://www.fedramp.gov/notices/0009/)** —
  FedRAMP's published outcome for the machine-readable package
  RFC.
- **[FedRAMP Changelog](https://www.fedramp.gov/changelog/)** —
  Authoritative timeline for FedRAMP 20x publications.

### Provenance note

Numbers cited in this finding (KSI counts, baseline counts,
phase dates) are snapshot facts current as of the access date
above. They must be re-verified against the FedRAMP.gov primary
sources at any time the finding is acted on, since 20x is in
active rollout.

## 3. Capability gap

### What UIAO can newly express because of this framework movement

1. **Native KSI emission language.** Phase 2 substrate output
   ([Phase 2 — Governance OS Deployment](../customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd))
   — drift findings, evidence-graph nodes, provenance entries —
   can now be expressed in the KSI vocabulary directly, rather
   than translated into bespoke SSP narrative. Strongest fit
   with KSI-MLA (monitoring/logging/audit) and KSI-CMT (change
   management / continuous monitoring) themes.
2. **Continuous ATO crosswalk.** Phase 3 cATO alignment
   ([Phase 3 — Optimization & Continuous ATO Alignment](../customer-documents/modernization/uiao-modernization-program/04-phase3-optimization-cato.qmd))
   gains a federally-ratified evidence path. Generic cATO
   references in Phase 3 can be retargeted as
   "KSI machine-readable payload → agency authorization sponsor
   → continuous-validation cadence."

### What UIAO still cannot do, because the framework movement has
not landed in product

1. **Consume Microsoft commercial-cloud telemetry signals in a
   GCC-Moderate deployment.** The FINDING-001 INR constraint
   stands. Identity Protection ML risk scoring, Continuous
   Access Evaluation real-time signaling, sensitivity-label and
   DLP behavioral analytics, Adoption Score, and Endpoint
   Analytics Advanced remain unavailable until Microsoft acts on
   the new framework with product changes. RFC-0005 makes those
   product changes architecturally easier to authorize but does
   not by itself cause them.
2. **Treat 20x as a substitute for substrate-side compensating
   analytics today.** Agencies operating in GCC-Moderate today
   continue to need agency-built local analytics for the gaps
   FINDING-001 and adjacent assessments document. UIAO's drift
   engine and evidence graph remain the substrate-level response
   while the framework-to-product gap closes.

### What this does NOT affect

- UIAO canon. No canon document changes its declared behavior on
  RFC-0005 / 20x publication. Canon adds emission-side mappings;
  it does not redefine what the substrate does.
- The Microsoft INR finding (FINDING-001). RFC-0005 names the
  framework lever, not the product fix; FINDING-001 stays
  Awaiting-External-Remediation independently.
- OSCAL evidence generation. UIAO's existing OSCAL pathway is
  compatible with RFC-0024 machine-readable packages by design;
  no architectural change required.

## 4. Proposed remedy

### Internal remedy (inside UIAO scope)

1. **KSI Emission Surface section in Phase 2
   ([UIAO_022 — Phase 2 Governance OS Deployment](../customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd)).**
   Enumerate each substrate output (drift class, evidence-graph
   node type, provenance entry kind) against the KSI it
   satisfies. Land as §13.3 KSI Emission Surface, sitting beside
   §13.1 cATO Framework and §13.2 OSCAL Artifact Generation
   Pipeline.
2. **20x cATO Crosswalk in Phase 3
   ([UIAO_023 — Phase 3 Optimization & cATO](../customer-documents/modernization/uiao-modernization-program/04-phase3-optimization-cato.qmd)).**
   Add a 20x KSI crosswalk subsection under §4.1 cATO Framework
   Alignment that maps each existing cATO-NNN row to the
   corresponding KSI theme(s), retargeting the cATO acceptance
   path against KSI machine-readable payload → agency
   authorization sponsor → continuous-validation cadence.
3. **Forward-looking note in Phase 0 strategic master plan
   ([UIAO_020 — Phase 0 Modernization Master Plan](../customer-documents/modernization/uiao-modernization-program/01-phase0-master-plan.qmd)).**
   Goal #2 ("restore network and telemetry visibility by
   eliminating signal gaps that result from authorization
   boundary constraints") gains an explicit pointer to RFC-0005
   and 20x as the federal mechanism the goal now operates against,
   appended to the §1 Executive Summary's "FedRAMP Boundary Gap"
   paragraph.
4. **Cross-reference from FINDING-001.** Add a §6 Related entry
   pointing to this finding so readers traversing FINDING-001's
   external-remedy path see RFC-0005 / 20x as the active
   framework movement.
5. **Promote substrate-side decision and operational mechanics
   to canon.** Land [ADR-047 — FedRAMP 20x Integration](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-047-fedramp-20x-integration.md)
   (decision, status PROPOSED) and
   [UIAO_133 — FedRAMP 20x Integration spec](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/fedramp-20x-integration.md)
   (operational mechanics: KSI emission tagging, MAS classification
   rubric, KSI-staleness drift class, dual pathway posture).
6. **Findings registry.** Land
   [docs/findings/registry.yaml](./registry.yaml) enumerating
   FINDING-001 and FINDING-002 with their cross-references, per
   the README "Registry" section's "lands with the first concrete
   finding" plan.

These internal actions do not depend on Microsoft or FedRAMP
landing further milestones; they reframe the substrate's existing
emissions in the new federal vocabulary. Items 1–4 landed in
commit `be8907b`. Items 5–6 land in the same series of commits as
this finding update.

### External remedy (outside UIAO scope)

1. **FedRAMP publishes RFC-0010 best-practices guidance** with
   explicit metadata-vs-telemetry definitions. The
   metadata-exclusion language in RFC-0005 is the lever for
   recovering deterministic / machine-generated telemetry from
   sovereign-cloud constraints; without companion guidance,
   3PAO interpretation will drift.
2. **Microsoft files a 20x-aligned package for GCC-Moderate**
   covering the telemetry-bearing services UIAO depends on
   (Microsoft 365 service plane, Microsoft Entra ID, Microsoft
   Intune). This is the action that converts framework movement
   into operational telemetry recovery for GCC-Moderate
   tenants.
3. **3PAO consensus on the "likely impact" inclusion test.**
   Until 3PAOs converge on a shared reading of prong (2),
   identical signals will be scoped differently across CSPs and
   agencies, blocking inheritance.

The external remedy is not a prerequisite for UIAO to deliver
value; the internal remedy proceeds independently.

## 5. Ownership trail

- **2026-04-27** — Constraint identified during review of the
  FedRAMP 20x documentation index following the Moderate Pilot
  status announcement at <https://www.fedramp.gov/docs/20x/>.
  RFC-0005 standard text and KSI taxonomy verified against the
  FedRAMP RFCs index and the closed RFC-0005 community discussion.
- **2026-04-27** — Companion external-use assessment published
  at `out/FedRAMP_20x_Moderate_Pilot_Impact_Assessment.docx`
  capturing the same evidence base for non-UIAO audiences.
- **2026-04-27** — Finding lands under `docs/findings/` with
  status **Awaiting-External-Remediation**. Michael Stratton
  owns the finding. Internal remedies §4 are in scope for UIAO
  and proceed on the substrate roadmap; external remedies stay
  tracked here until FedRAMP publishes RFC-0010 companion
  guidance and CSPs file 20x-aligned packages for sovereign-cloud
  offerings.

## 6. Related

- [FINDING-001 — FedRAMP GCC-Moderate Informed Network Routing
  unavailable](./fedramp-gcc-moderate-informed-network-routing.md)
  — names "FedRAMP authorization package adjustment" as an
  external remedy. RFC-0005 / 20x is the formal lever that
  external remedy now operates against. FINDING-001 stays
  independently open until product action follows.
- [ADR-030 §5.2](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md)
  — established the governance-findings artifact class this
  document instantiates.
- [UIAO_022 — Phase 2 Governance OS Deployment](../customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd)
  — Phase 2 chapter that gains the KSI Emission Surface section
  (§13.3) per §4.1 above.
- [UIAO_023 — Phase 3 Optimization & cATO](../customer-documents/modernization/uiao-modernization-program/04-phase3-optimization-cato.qmd)
  — Phase 3 chapter that gains the 20x KSI Crosswalk subsection
  under §4.1 per §4.2 above.
- [UIAO_132 — FedRAMP RFC-0026 CA-7 Pathway Integration](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/fedramp-rfc-0026-ca7-integration.md)
  — sibling FedRAMP-RFC integration spec; UIAO_133 (this
  finding's §4 item 5) follows the same pattern.
- [ADR-047 — FedRAMP 20x Integration decision](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-047-fedramp-20x-integration.md)
  — substrate-level decision (status PROPOSED) committing UIAO to
  KSI emission tagging, MAS classification, and KSI-staleness
  drift class. Ratification gate: RFC-0010 publication + stable
  Moderate KSI catalog + clean dry-run + steward signoff.
- [UIAO_133 — FedRAMP 20x Integration spec](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/fedramp-20x-integration.md)
  — operational companion to ADR-047. KSI emission tagging
  contract (§2), MAS classification rubric (§3), KSI-staleness
  drift class (§4), dual pathway posture (§5).
- [docs/findings/registry.yaml](./registry.yaml) — cross-finding
  index enumerating FINDING-001 and FINDING-002.
- [Phase 0 — Modernization Master Plan](../customer-documents/modernization/uiao-modernization-program/01-phase0-master-plan.qmd)
  — strategic framing whose Goal #2 gains a pointer to this
  finding in §4.3.
- External-use companion assessment:
  `out/FedRAMP_20x_Moderate_Pilot_Impact_Assessment.docx`.

## Status tracking

| Date | Status | Note |
|---|---|---|
| 2026-04-27 | Awaiting-External-Remediation | Initial landing |

This table is append-only. Closure of the finding (Resolved or
Withdrawn) moves the status and adds a row; the prior rows
remain for audit.
