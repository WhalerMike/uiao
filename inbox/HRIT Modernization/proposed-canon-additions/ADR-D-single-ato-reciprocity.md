---
id: ADR-D-DRAFT
title: "Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary"
status: draft
date: 2026-05-04
deciders:
  - governance-steward
  - oscal-engineer
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-A-DRAFT  # SAML trust anchor
  - ADR-B-DRAFT  # PIV / USAccess
  - ADR-C-DRAFT  # OPM Azure APIM
  - ADR-043      # FedRAMP RFC-0026 pathway alignment (related, not superseded)
canon_refs:
  - UIAO_112  # Multi-Tenant Isolation
  - UIAO_120  # Zero-Trust Integration Layer
  - VISION.md # FedRAMP / OSCAL framing
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26) — single ATO covers all agencies"
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107) — OPM ATO process"
  - "Q&A #43 — ATO reciprocity"
  - "Q&A #44 — SSP draft within 30 days, final within 45 days of award"
  - "Q&A #47-48 — single code line, configuration-only differentiation"
---

# ADR-D (DRAFT): Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary

> **Draft status.** Held in `inbox/HRIT Modernization/proposed-canon-additions/`.
> Promote on canon-merge per repo invariant I5. This ADR introduces a new
> canon spec (UIAO_NNN to be allocated) that formalizes the multi-tenant
> ATO reciprocity model.

## Status

Draft — pending governance review.

## Context

UIAO's value proposition centers on **OSCAL-native compliance pipelines**
that produce continuous evidence against FedRAMP Moderate and the broader
federal control set ([VISION.md](../../docs/governance/VISION.md)). The
canon assumes a **per-system** ATO model implicitly — every authorized
system has its own SSP, POA&M, and authorization decision.

The HRIT Modernization Solicitation 24322626R0007 (Amd 4) imposes a
materially different model:

- **PWS §5.1.1 #5** (p. 26): *"OPM's ATO covers any agency's use of the
  platform. The ATO will be required before any work can be done in
  Production."*
- **Q&A #43**: *"The OPM ATO will cover all agency use, as stated in
  section 5.1.1, 'OPM's ATO covers any agency's use of the platform.'"*
- **Q&A #44**: SSP draft due within 30 days of award, final within 45 days;
  *"This solution will have a single authoritative ATO covering all customers."*
- **Q&A #47-48**: single code line; agency differences via configuration,
  no per-agency forks.
- **Clause 1752.239-74** (p. 107): OPM CIO is the final authority on
  compliance; FedRAMP packages may be leveraged but are not a substitute
  for an explicit OPM ATO decision.

This is a **single-tenant-of-record / multi-tenant-of-consumption** model:
**one** SSP, **one** authorizing official decision, **N** agency consumers
under reciprocity. UIAO has no canon document that formalizes this pattern,
even though it is precisely the pattern UIAO's deterministic OSCAL pipeline
is best positioned to operate.

Without explicit canon, HRIT-bound deployments would:

1. Force every agency to file its own SSP — directly contradicting the
   solicitation.
2. Mis-classify the trust boundary — the boundary is at OPM CIO / OPM
   Authorizing Officials, not at each agency's CIO.
3. Produce drift findings against an artifact (per-agency SSP) that the
   contractor is contractually forbidden from generating.

## Decision

1. Create a new canon spec under `src/uiao/canon/specs/` (UIAO_NNN to be
   allocated by the registry steward at merge time):
   `single-ato-reciprocity-model.md`. The spec defines:

   - **One System Security Plan (SSP)** authored by the system operator
     (e.g., the HRIT prime contractor), submitted to and approved by the
     federal authorizing official (e.g., OPM CIO).
   - **One Authority to Operate (ATO)** decision, issued by the federal
     authorizing official, that **covers all consuming agencies**.
   - **Reciprocity acceptance** by each consuming agency via documented
     acknowledgment of the controlling SSP and ATO; no separate ATO
     decision per agency.
   - **Configuration-only differentiation** — agencies are
     consumption-tenants of the single platform; no per-tenant SSP or POA&M
     forks. Drift between platform-canon and per-tenant configuration is a
     `DRIFT-AUTHZ` or `DRIFT-SCHEMA` finding.
   - **Continuous monitoring** is operated against the single SSP; per-tenant
     evidence is *additional* (tenant-scoped views), not *primary*.
   - **Evidence graph** (UIAO_113) records both the controlling ATO event
     and each tenant's reciprocity acknowledgment, preserving chain of
     custody for audit.

2. Amend UIAO_112 (Multi-Tenant Isolation) §1 Overview to reference the
   single-ATO reciprocity spec as the controlling-authority pattern, not
   per-tenant ATOs.

3. The OSCAL pipeline gains a new artifact class — `reciprocity-record` —
   emitted per consuming agency when they accept the controlling ATO. The
   record is signed, timestamped, and linked into the evidence graph.

4. The pipeline does **not** generate per-agency SSPs by default. A future
   ADR can introduce that capability for non-HRIT deployments where each
   agency does run its own ATO.

## Consequences

**Positive**

- HRIT-bound deployments produce the contractually-mandated artifact set
  (one SSP, one ATO, per-agency reciprocity acknowledgments) without
  requiring contortions in the OSCAL pipeline.
- The model maps directly to the OPM-as-CISP-of-record pattern that is
  already established in CISA SCuBA / FedRAMP authorization shared-service
  patterns.
- Scales: when DoD, DHS, or Treasury follow a similar shared-service
  authorization pattern, the same canon applies — only the federal
  authorizing official changes.
- Single source of evidence for cross-agency oversight: OPM (and any
  consuming agency) can see the same ATO state through the evidence graph.

**Negative**

- The single-ATO model concentrates risk: if the controlling ATO lapses,
  every consuming agency is affected simultaneously. The spec must mandate
  **continuous monitoring SLA** and **30-day reauthorization window**
  consistent with the FedRAMP cadence.
- Drift detection complexity: per-tenant configuration drift must be
  evaluated against the single SSP's approved configuration baseline,
  which means the SSP must enumerate per-tenant configuration latitude
  explicitly (i.e., what is in scope for tenant variation vs. what is fixed).

**Neutral**

- For non-HRIT deployments where each agency does run its own ATO, this
  model is opt-in via a flag in the substrate manifest — existing
  per-system ATO behavior remains the default.

## Alternatives considered

1. **Treat HRIT as an exception, no canon change.** Rejected — exceptions
   accumulate as silent drift. The HRIT pattern is general (any
   shared-service federal platform), not HRIT-specific.
2. **Force per-agency SSPs anyway, ignoring the solicitation.** Rejected
   on contractual grounds.
3. **Defer until a second federal customer arrives.** Rejected — HRIT
   covers ~24 CFO-Act agencies, ~2 million federal civilian employees.
   It is a sufficient population to warrant canon now.

## Implementation footprint (post-merge)

| File | Change |
|---|---|
| `src/uiao/canon/specs/single-ato-reciprocity-model.md` | New spec (UIAO_NNN allocation required) |
| `src/uiao/canon/document-registry.yaml` | New UIAO_NNN entry |
| `src/uiao/canon/specs/application-identity-model.md` | UIAO_112 cross-reference update |
| `src/uiao/oscal/` | New `reciprocity_record.py` emitter (separate PR) |
| `src/uiao/canon/adr/adr-NNN-single-ato-reciprocity.md` | This document, renamed and ID-allocated |
| `tests/oscal/test_reciprocity_record.py` | Happy-path + lapsed-ATO failure case |

## Spec outline — proposed structure

The new spec at `src/uiao/canon/specs/single-ato-reciprocity-model.md`
should follow the UIAO_129 / UIAO_130 pattern:

1. **§1 Overview** — Purpose, applicability, relationship to FedRAMP
2. **§2 Roles** — System Operator, Authorizing Official, Consuming Agency
3. **§3 Artifacts** — SSP, ATO, Reciprocity Record, POA&M, Continuous Monitoring evidence
4. **§4 Lifecycle** — Authorization, Reciprocity, Continuous Monitoring,
   Reauthorization, Termination
5. **§5 Drift Classes** — How drift between SSP-declared and tenant-actual
   configuration maps to the existing five drift classes
6. **§6 Evidence Graph Mapping** — Event types and grouping keys
7. **§7 OSCAL Output Profile** — Which OSCAL artifacts are emitted by
   default vs. per-tenant request
8. **§8 Cross-References** — UIAO_112, UIAO_113, UIAO_120, ADR-043

## References

- Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26)
- Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107)
- Q&A #43, #44, #47, #48 — reciprocity, SSP timelines, single code line
- `inbox/HRIT Modernization/HRIT-IAM-Findings.md` §7
- UIAO_112 — Multi-Tenant Isolation (to be amended)
- UIAO_120 — Zero-Trust Integration Layer
- VISION.md — Pillar 1 (Deterministic FedRAMP Moderate Rev 5 Automation)
- ADR-043 — FedRAMP RFC-0026 pathway alignment (related; defines the BIR pathway under which this ATO model operates)
