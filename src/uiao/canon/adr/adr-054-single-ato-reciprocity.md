---
id: ADR-054
title: "Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary"
status: accepted
date: 2026-05-04
deciders:
  - governance-steward
  - oscal-engineer
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-051  # SAML trust anchor
  - ADR-052  # PIV / USAccess
  - ADR-053  # OPM Azure APIM
  - ADR-043  # FedRAMP RFC-0026 pathway alignment
canon_refs:
  - UIAO_112  # Multi-Tenant Isolation — amended by this ADR
  - UIAO_120  # Zero-Trust Integration Layer
  - UIAO_140  # Single-ATO Reciprocity Model — new spec introduced by this ADR
  - VISION.md
hrit_traceability:
  - "Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26) — single ATO covers all agencies"
  - "Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107) — OPM ATO process"
  - "Q&A #43 — ATO reciprocity"
  - "Q&A #44 — SSP draft within 30 days, final within 45 days of award"
  - "Q&A #47-48 — single code line, configuration-only differentiation"
---

# ADR-054: Single-ATO Reciprocity Model — Multi-Tenant Authorization Boundary

## Status

Accepted.

## Context

UIAO's value proposition centers on **OSCAL-native compliance pipelines** that
produce continuous evidence against FedRAMP Moderate and the broader federal
control set (`docs/governance/VISION.md`). The canon assumes a **per-system**
ATO model implicitly — every authorized system has its own SSP, POA&M, and
authorization decision.

The HRIT Modernization Solicitation 24322626R0007 (Amd 4) imposes a materially
different model:

- **PWS §5.1.1 #5** (p. 26): *"OPM's ATO covers any agency's use of the
  platform. The ATO will be required before any work can be done in
  Production."*
- **Q&A #43**: *"The OPM ATO will cover all agency use, as stated in section
  5.1.1, 'OPM's ATO covers any agency's use of the platform.'"*
- **Q&A #44**: SSP draft due within 30 days of award, final within 45 days;
  *"This solution will have a single authoritative ATO covering all
  customers."*
- **Q&A #47-48**: single code line; agency differences via configuration,
  no per-agency forks.
- **Clause 1752.239-74** (p. 107): OPM CIO is the final authority on
  compliance; FedRAMP packages may be leveraged but are not a substitute for
  an explicit OPM ATO decision.

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

1. Create a new canon spec `src/uiao/canon/specs/single-ato-reciprocity-model.md`
   allocated as **UIAO_140**. The spec defines:

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

2. Amend UIAO_112 (Multi-Tenant Isolation) to reference UIAO_140 as the
   controlling-authority pattern when a single authorizing official issues a
   reciprocal ATO across consuming tenants.

3. The OSCAL pipeline gains a new artifact class — `reciprocity-record` —
   emitted per consuming agency when they accept the controlling ATO. The
   record is signed, timestamped, and linked into the evidence graph. The
   pipeline implementation lands in a separate PR; canon establishes the
   contract here.

4. The pipeline does **not** generate per-agency SSPs by default. A future
   ADR can introduce that capability for non-HRIT deployments where each
   agency does run its own ATO.

## Consequences

**Positive**

- HRIT-bound deployments produce the contractually-mandated artifact set
  (one SSP, one ATO, per-agency reciprocity acknowledgments) without
  requiring contortions in the OSCAL pipeline.
- The model maps directly to the OPM-as-CSP-of-record pattern that is already
  established in CISA SCuBA / FedRAMP authorization shared-service patterns.
- Scales: when DHS, Treasury, or other agencies follow a similar
  shared-service authorization pattern, the same canon applies — only the
  federal authorizing official changes.
- Single source of evidence for cross-agency oversight: OPM (and any
  consuming agency) can see the same ATO state through the evidence graph.

**Negative**

- The single-ATO model concentrates risk: if the controlling ATO lapses,
  every consuming agency is affected simultaneously. The spec mandates
  **continuous monitoring SLA** and **30-day reauthorization window**
  consistent with the FedRAMP cadence.
- Drift detection complexity: per-tenant configuration drift must be
  evaluated against the single SSP's approved configuration baseline, which
  means the SSP must enumerate per-tenant configuration latitude explicitly
  (i.e., what is in scope for tenant variation vs. what is fixed).

**Neutral**

- For non-HRIT deployments where each agency does run its own ATO, the
  single-ATO model is opt-in via a flag in the substrate manifest — existing
  per-system ATO behavior remains the default.

## Alternatives considered

1. **Treat HRIT as an exception, no canon change.** Rejected — exceptions
   accumulate as silent drift. The HRIT pattern is general (any
   shared-service federal platform), not HRIT-specific.
2. **Force per-agency SSPs anyway, ignoring the solicitation.** Rejected on
   contractual grounds.
3. **Defer until a second federal customer arrives.** Rejected — HRIT
   covers ~24 CFO-Act agencies, ~2 million federal civilian employees. It
   is a sufficient population to warrant canon now.

## Implementation

| File | Change | Status |
|---|---|---|
| `src/uiao/canon/specs/single-ato-reciprocity-model.md` | New spec (UIAO_140) | done in same PR |
| `src/uiao/canon/document-registry.yaml` | UIAO_140 entry added | done in same PR |
| `src/uiao/canon/specs/governance.md` | UIAO_112 amended with UIAO_140 cross-reference; version bumped to 1.1 | done in same PR |
| `uiao.oscal.reciprocity_record` | New artifact emitter (separate PR) | deferred |
| `tests/oscal/test_reciprocity_record.py` | Happy-path + lapsed-ATO failure case (separate PR) | deferred |

## References

- Solicitation 24322626R0007 Amd 4, PWS §5.1.1 #5 (p. 26)
- Solicitation 24322626R0007 Amd 4, Clause 1752.239-74 (p. 107)
- Q&A #43, #44, #47, #48 — reciprocity, SSP timelines, single code line
- UIAO_112 — Multi-Tenant Isolation (amended)
- UIAO_120 — Zero-Trust Integration Layer
- UIAO_140 — Single-ATO Reciprocity Model (new)
- ADR-051, ADR-052, ADR-053 — companion HRIT IAM canon additions
- ADR-043 — FedRAMP RFC-0026 pathway alignment (related; defines the BIR pathway under which this ATO model operates)
- VISION.md — Pillar 1 (Deterministic FedRAMP Moderate Rev 5 Automation)
- `inbox/HRIT Modernization/HRIT-IAM-Findings.md` §7
