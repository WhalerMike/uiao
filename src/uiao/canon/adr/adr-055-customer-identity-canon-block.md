---
id: ADR-055
title: "Customer Identity Canon Block — KYC Protocol & Reciprocal Attribute Exchange"
status: accepted
date: 2026-05-05
deciders:
  - governance-steward
  - identity-engineer
  - privacy-officer
supersedes: []
related_adrs:
  - ADR-051  # SAML trust anchor — federation context for FAL bindings
  - ADR-052  # PIV / USAccess — workforce-side parallel
  - ADR-053  # OPM Azure APIM — gateway pattern reused at attribute-exchange boundary
  - ADR-054  # Single-ATO Reciprocity — authorization-level reciprocity (companion concept to UIAO_141 attribute-level reciprocity)
canon_refs:
  - UIAO_113  # Evidence Graph — minor amendment required
  - UIAO_120  # Zero-Trust Integration Layer — amendment required
  - UIAO_141  # Customer Identity Model — new spec introduced by this ADR
  - UIAO_142  # Customer KYC Onboarding & Reciprocity Runbook — new spec introduced by this ADR
  - VISION.md
mandate_traceability:
  - "User-stated architectural intent (2026-05-04): KYC as customer protocol, agency-as-vendor / agency-as-customer doctrine"
  - "OMB M-19-17 — Enabling Mission Delivery through Improved ICAM"
  - "OMB M-22-09 — Federal Zero Trust Strategy"
  - "Privacy Act of 1974 (5 U.S.C. §552a)"
  - "Computer Matching and Privacy Protection Act of 1988"
  - "NIST SP 800-63-3 / -4 (draft) — IAL/AAL/FAL"
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-055-customer-identity-canon-block.html
---

# ADR-055: Customer Identity Canon Block — KYC Protocol & Reciprocal Attribute Exchange

## Status

Accepted.

## Context

UIAO has substantial canon for the **workforce-identity surface**:
applications and devices (UIAO_129 / UIAO_130), federal employees and
contractors authenticated via PIV (ADR-052) and federated via SAML/OIDC
(ADR-051), HR-driven IAM provisioning (Spec2-D3.x), and the central API
gateway pattern (ADR-053). The recently merged HRIT IAM block (ADR-051..054
+ UIAO_140) closes the federal-HRIT contractual gap end-to-end.

UIAO has **no canon** for the **customer-identity surface**:

1. The citizens, businesses, applicants, and beneficiaries that federal
   agencies actually serve mission-side. Examples: SSA beneficiaries, IRS
   taxpayers, USCIS petitioners, USAJobs applicants, GSA SAM.gov vendors,
   VA veterans, FEMA disaster-relief applicants, HHS/CMS enrollees.
2. The cross-agency, agency↔state, agency↔employer attribute exchange that
   powers federal mission delivery — the "agencies are both vendors and
   customers of each other" doctrine. Examples: SSA owns SSN consumed by
   IRS / employers / state DMVs; IRS owns TIN consumed by every federal
   agency; GSA owns UEI consumed by every contracting agency; USCIS owns
   immigration status consumed by employers via e-Verify.

Without canon for this surface, UIAO covers the system-and-workforce
identity story but is silent on the **mission delivery** story. The
existing Truth Fabric appendix B-02 declares an `identity_type` enum
(`person | device | service | organization`) that *touches* the customer
concept, but defines no protocol, no authority-of-record doctrine, no
reciprocal-consumption entitlement model, and no operational lifecycle.

This is a structural gap, not an oversight — the workforce surface was
the right first deliverable. With that surface stable, the customer
surface is the natural next canon block.

## Decision

This ADR establishes the **Customer Identity Canon Block** as a four-part
addition to canon, paralleling the workforce-identity block (UIAO_129 +
UIAO_130 + the supporting adapters):

1. **UIAO_141 — Customer Identity Model** (new spec at
   `src/uiao/canon/specs/customer-identity-model.md`). Declarative spec
   defining the Customer Identity Record (CIR) primitive with six required
   bindings: canonical identifier, IAL, AAL, FAL, authority of record,
   reciprocal-consumption entitlement.

2. **UIAO_142 — Customer KYC Onboarding & Reciprocity Runbook** (new spec
   at `src/uiao/canon/specs/customer-kyc-runbook.md`). Operational
   counterpart defining inbound KYC, outbound KYC, reciprocity provisioning,
   and drift detection lifecycles.

3. **Reciprocal-consumption registry** (new canon registry at
   `src/uiao/canon/reciprocal-consumption-registry.yaml`, with JSON Schema
   at `src/uiao/schemas/reciprocal-consumption/registry.schema.json`).
   Stores attribute-level entitlements: `attribute_id`, `authority_of_record`,
   `consumer_principal`, `legal_basis`, `scope`, `freshness_window`,
   `effective_date`, `expiry_date`, `signed_by`. Every entitlement requires
   a `legal_basis` citation (Privacy Act SORN routine use, CMPPA agreement,
   statute, or customer consent reference); CI rejects entitlements without
   one.

4. **Authority-of-record adapter slots.** Reserved adapter entries in
   `adapter-registry.yaml` (conformance) and `modernization-registry.yaml`
   (federation-issuer) for the canonical federal authorities of record.
   Initial allocation:

   | Adapter ID | Class | Mission-class | Authority |
   |---|---|---|---|
   | `ssa-attribute-service` | conformance | identity | SSA — SSN, earnings record, benefits eligibility |
   | `irs-tin-attribute-service` | conformance | identity | IRS — TIN/EIN, federal tax compliance |
   | `gsa-sam-attribute-service` | conformance | identity | GSA SAM.gov — UEI, business registration, exclusion list |
   | `uscis-immigration-attribute-service` | conformance | identity | USCIS — immigration / citizenship status |
   | `dhs-everify-attribute-service` | conformance | identity | DHS USCIS + SSA — employment authorization |
   | `treasury-ofac-attribute-service` | conformance | policy | Treasury OFAC — sanctions screening |
   | `state-dmv-realid-attribute-service` | conformance | identity | State DMVs (REAL-ID) — driver license / state ID |
   | `dcsa-clearance-attribute-service` | conformance | identity | DCSA — federal security clearance |
   | `va-veteran-attribute-service` | conformance | identity | VA / DoD — veteran status, service record |
   | `vitals-attribute-service` | conformance | identity | State vital-records bureaus — birth/marriage/death |
   | `login-gov-federation-service` | modernization | integration | GSA Login.gov — FAL-2 federated authentication for citizen portals |
   | `id-me-federation-service` | modernization | integration | ID.me — IAL-2/AAL-2 verification (commercial; federal-authorized) |

   All slots are `status: reserved`. Activation requires a per-adapter ADR
   modeled on ADR-035, naming the legal basis, the integration approach,
   the conformance evidence pathway (UIAO_131), and the operating tenancy.

5. **UIAO_113 (Evidence Graph) amendment.** Enumerate the new event types
   introduced by UIAO_141 §8: `customer-identity-record`,
   `cir-state-transition`, `kyc-inbound-verification`,
   `kyc-outbound-disclosure`, `reciprocity-attribute-record`. Bump
   UIAO_113 to v1.1.

6. **UIAO_120 (Zero-Trust Integration Layer) amendment.** Recognize the
   customer-identity surface as a peer to the workforce-identity surface
   in Zero Trust posture. The CIR's IAL/AAL/FAL fields are first-class
   inputs to Zero-Trust evaluation envelopes alongside workforce-identity
   inputs. Bump UIAO_120 to v1.1.

## Consequences

**Positive**

- UIAO models the customer-identity surface contractually for the first
  time; mission-delivery flows become canon-legible.
- The agency-as-vendor / agency-as-customer doctrine becomes a first-class
  invariant — every authority of record and every consumer registers
  symmetrically.
- Reciprocal-consumption entitlements get a canonical home with mandatory
  legal-basis citations; Privacy Act / CMPPA compliance becomes a CI gate
  rather than an out-of-band review artifact.
- IAL/AAL/FAL move from VISION.md prose to first-class CIR bindings,
  enabling drift detection on customer-identity assurance levels.
- The pattern scales to state-level reciprocity, employer reciprocity, and
  international reciprocity (e.g., e-Passport / ICAO 9303) once the federal
  block is stable.

**Negative**

- Substantial new canon surface — two specs, one new registry, one new
  schema, twelve adapter slots, two amendments. Larger than the HRIT IAM
  block.
- Privacy review burden — every reciprocal-consumption entitlement requires
  Privacy Officer or General Counsel sign-off on the legal-basis citation.
  This is a feature (governance discipline) but adds latency to entitlement
  provisioning.
- Dependency on per-adapter activation ADRs for every authority of record
  before any concrete KYC flow operates. Initial activation will likely
  focus on Login.gov (federation-issuer) and one or two attribute services
  (SSA Consent-Based SSN Verification or IRS Income Verification Express
  Service); the remaining slots stay reserved until customer engagements
  warrant.

**Neutral**

- The workforce-identity canon block (UIAO_129 / UIAO_130 / ADR-051..054 /
  UIAO_140) is unaffected. Both surfaces coexist; some adapters
  (`entra-id`, `piv-usaccess`) participate in workforce flows only, others
  (`login-gov-federation-service`, `ssa-attribute-service`) participate in
  customer flows only, and the substrate manifest can scope to one or both.
- The Truth Fabric `identity_type` enum (`person | device | service |
  organization`) is unchanged; KYC operates on `person` and `organization`
  records as a refinement layer, not a replacement.

## Alternatives considered

1. **Extend UIAO_129 to cover customer identity.** Rejected — UIAO_129's
   six-binding model is built around application primitives that all live
   inside one substrate (DNS, address, workload identity, trust anchor,
   segmentation label, location). The customer model has fundamentally
   different bindings (canonical identifier, IAL, AAL, FAL, authority of
   record, reciprocal-consumption entitlement) and operates *across*
   substrate boundaries. Conflating the two produces an unwieldy spec with
   branching scope.

2. **Defer KYC to per-engagement specs.** Rejected — the doctrine
   (agencies as vendors and customers of each other; authority of record;
   reciprocal entitlement; legal-basis citation) is general, not
   engagement-specific. A foundational canon block enables every future
   engagement to land cleanly; deferring forces every engagement to
   re-derive the doctrine.

3. **Subsume KYC under existing Privacy / CMPPA tooling outside UIAO.**
   Rejected — UIAO's evidence graph, drift engine, OSCAL pipeline, and
   adapter conformance framework are precisely what KYC needs. Splitting
   the customer-identity surface to an adjacent system fragments the
   evidence story and forces dual maintenance.

4. **Wait for NIST SP 800-63-4 final.** Considered — the draft is stable
   enough to cite (we reference -3 and -4-draft); waiting for final
   publication delays the canon block by months for a vocabulary refinement
   that won't materially change the architecture. Proceeding now and
   updating cross-references when -4 finalizes is the better path.

## Implementation footprint (post-merge)

| File | Change |
|---|---|
| `src/uiao/canon/specs/customer-identity-model.md` | New spec (UIAO_141 allocation) |
| `src/uiao/canon/specs/customer-kyc-runbook.md` | New spec (UIAO_142 allocation) |
| `src/uiao/canon/document-registry.yaml` | UIAO_141 + UIAO_142 entries |
| `src/uiao/canon/reciprocal-consumption-registry.yaml` | New registry (initially empty); schema-validated |
| `src/uiao/schemas/reciprocal-consumption/registry.schema.json` | New JSON Schema for entitlements |
| `src/uiao/canon/adapter-registry.yaml` | +10 reserved conformance slots (SSA, IRS, GSA, USCIS, e-Verify, OFAC, DMV, DCSA, VA, vitals) |
| `src/uiao/canon/modernization-registry.yaml` | +2 reserved modernization slots (Login.gov, ID.me) |
| `src/uiao/canon/specs/graph-schema.md` | UIAO_113 v1.1 — new event-type enumeration |
| `src/uiao/canon/specs/<UIAO_120 path>` | UIAO_120 v1.1 — customer-surface amendment |
| `src/uiao/canon/adr/adr-055-customer-identity-canon-block.md` | This document |

This is approximately 14 file touches — significantly larger than the
HRIT IAM bundle (11 files). Recommend splitting into 2–3 commits at
promotion time:

- **Commit 1**: UIAO_141 + UIAO_142 + ADR-055 + document-registry
- **Commit 2**: reciprocal-consumption-registry + schema
- **Commit 3**: adapter-registry + modernization-registry slot additions
- **Commit 4** (optional): UIAO_113 + UIAO_120 amendments

Or one PR with all four commits, mirroring the HRIT IAM PR shape.

## References

- `inbox/KYC/KYC-Customer-Protocol-Findings.md` — full scoping document
- UIAO_141, UIAO_142 — companion drafts in this directory
- ADR-051..054 — workforce-identity canon block (precedent pattern)
- NIST SP 800-63-3 / -4 (draft) — IAL/AAL/FAL definitions
- Privacy Act of 1974 (5 U.S.C. §552a)
- Computer Matching and Privacy Protection Act of 1988
- OMB M-19-17 — Enabling Mission Delivery through Improved ICAM
- OMB M-22-09 — Federal Zero Trust Strategy
- VISION.md — Pillar 6 (Zero Trust / TIC 3.0 Modernization), Pillar 7 (Future-Proof Governance Platform)
- ADR-035 — pattern for per-adapter activation ADRs
