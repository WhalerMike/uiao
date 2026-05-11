# KYC Customer Protocol — Scoping & Findings

> **Status:** DRAFT — `inbox/` content, not canon. Proposed canon additions
> live in [`proposed-canon-additions/`](proposed-canon-additions/).
>
> **Created:** 2026-05-05
>
> **Companion to:** [HRIT-IAM-Findings](../HRIT%20Modernization/HRIT-IAM-Findings.md)
> (workforce-identity surface). KYC closes the customer-identity surface.
>
> **User intent (verbatim):** *"KYC implemented as an important Customer
> protocol both as a Federal Agencie's support for external customers, as
> well as for Agencies to be a SSOT for things like SSA # and other info
> to other agencies, States, Employers, and etc. Agencies are both Vendors
> and Customers of each other."*

---

## 1. Executive summary

UIAO has substantial canon for the **workforce-identity surface** —
applications, devices, service principals, and federal employees authenticated
through PIV / Entra (UIAO_129, UIAO_130, the Spec2-D3.x HR-driven IAM stack).
It has **no canon** for the **customer-identity surface** — the citizens,
businesses, applicants, and beneficiaries that federal agencies actually serve
mission-side, and the cross-agency / agency↔state / agency↔employer attribute
exchange that powers federal mission delivery.

This document scopes that gap and proposes a four-artifact canon block to
close it:

| Artifact | Role | Parallel to |
|---|---|---|
| **UIAO_141 — Customer Identity Model** | Declarative spec | UIAO_129 (Application Identity Model) |
| **UIAO_142 — Customer KYC Onboarding & Reciprocity Runbook** | Operational runbook | UIAO_130 (Application Identity Onboarding Runbook) |
| **ADR-055 — Customer Identity Canon Block** | Doctrinal ADR | ADR-051..054 (HRIT IAM block) |
| **Adapter slots** | Authority adapters per attribute (SSN, TIN, UEI, citizenship status, e-Verify, etc.) | `entra-id`, `piv-usaccess`, `opm-azure-apim` |

The doctrine: **agencies are simultaneously vendors and customers of each
other**. Each high-value identity attribute has exactly one **authority of
record** (SSA owns SSN, IRS owns TIN, USCIS owns immigration status, Treasury
owns UEI/SAM.gov, etc.). Every other consumer — peer agency, state, employer,
or external party — runs a KYC protocol *against* the authority of record
under documented reciprocal-consumption entitlements.

---

## 2. The two coupled scopes

### 2.1 Scope A — Agency-to-external-customer

When a citizen or business interacts with a federal agency, the agency runs
a KYC protocol against that external party. Examples:

| Agency | External customer | KYC purpose |
|---|---|---|
| SSA | Beneficiary applying for retirement / disability benefits | Establish identity, eligibility, payment routing |
| IRS | Taxpayer filing a return | Match TIN, prevent identity-theft refund fraud |
| USCIS | Immigration petitioner | Verify identity of petitioner and beneficiary |
| USAJobs (OPM) | Federal job applicant | Verify identity ahead of background check |
| GSA SAM.gov | Vendor registering for federal contracts | Verify business identity, ownership, financial standing |
| VA | Veteran applying for healthcare/benefits | Verify service record and dependent status |
| FEMA | Disaster-relief applicant | Verify identity and eligibility for assistance |
| HHS / CMS | Medicare/Medicaid enrollee | Verify identity and benefit eligibility |
| Department of Education | Student loan borrower | Verify identity for FAFSA / repayment |

These are **inbound** KYC flows — the agency is the *customer* of the
external party's identity claim, but is also acting as a *vendor* to its
own peers when it accepts that claim and writes evidence for downstream
consumers.

### 2.2 Scope B — Inter-agency / agency↔state / agency↔employer attribute SSOT

Agencies act as the **authority of record** for high-value attributes that
other agencies, states, employers, and external parties consume. Examples
of authority-of-record assignments:

| Attribute | Authority of record | Common consumers |
|---|---|---|
| **SSN** | Social Security Administration (SSA) | IRS, USCIS, state DMVs, employers (W-2/W-4), DoD/military, banks (CIP), state benefits agencies, e-Verify |
| **TIN / EIN** | Internal Revenue Service (IRS) | All federal agencies, banks, state revenue departments, SAM.gov |
| **UEI** | GSA SAM.gov | All federal agencies issuing contracts/grants, state procurement |
| **Immigration / citizenship status** | USCIS | DoS, e-Verify, employers, state DMVs, state benefits agencies, federal benefits |
| **Federal employee record** | OPM (per-agency NFC EmpowHR / DCPDS / Treasury HR Connect) | Other agencies for transfers, security clearance, federal benefits, retirement |
| **Security clearance** | DCSA (DoD), state-dept-IBN, agency self-issued | Cleared facilities, contracting officers, federal employers |
| **Veteran status** | VA / DoD | Federal hiring (5 USC §2108), state benefits, employers (USERRA), preference points |
| **Vital records** (birth, marriage, death) | State vital-records bureaus | Federal agencies, courts, employers, insurers |
| **Driver licenses / state IDs** | State DMVs (REAL-ID) | TSA, state agencies, employers |
| **e-Verify employment authorization** | DHS USCIS + SSA composite | All employers, federal/state agencies hiring |
| **OFAC sanctions screening** | Treasury OFAC | Banks, federal agencies issuing payments, exporters |
| **Federal court records** | DOJ / Federal Judiciary | Federal hiring, security clearance, immigration |
| **Federal tax compliance** | IRS | All federal contracting, security clearance, federal hiring |
| **Federal benefits eligibility** (Medicare/SNAP/SSI) | HHS, USDA, SSA | State agencies cross-checking eligibility, DoD for dependents |

These are **outbound** KYC flows — the agency is the *vendor* providing
attribute attestations to other consumers. The same agency that runs Scope A
inbound KYC also operates Scope B outbound KYC against its peers.

### 2.3 The unifying doctrine

A single agency operates in **both** modes simultaneously: it accepts
inbound customer identity claims (Scope A) and answers outbound peer
attribute requests (Scope B). UIAO must model this symmetry — there is
no asymmetric "vendor" or "customer" axis; every agency is both.

The same Customer Identity Record can be:
- **Authored** by the authority of record agency
- **Verified** by a consuming agency on inbound KYC
- **Provided** to the next consumer on outbound KYC

…all under signed, certificate-anchored evidence in the UIAO evidence graph.

---

## 3. What's in canon today

| Canon | Touches customer identity? | Notes |
|---|---|---|
| UIAO_129 — Application Identity Model | No | Application primitives (workload identity, mTLS/OIDC/SAML trust anchors) |
| UIAO_130 — Application Identity Onboarding | No | Operational runbook for app provisioning |
| Spec2-D3.x — HR-driven IAM | No | Federal employee provisioning from HR system to Entra |
| ADR-052 — PIV/USAccess adapter | Partially | PIV credential covers federal employees and contractors, **not** external customers |
| `b-02-identity-anchoring.md` Truth Fabric | Partially | `identity_type` enum (person/device/service/organization) is the closest existing taxonomy — but no protocol for inter-agency attribute exchange |
| `b-03-multi-cloud-identity-matrix.md` | No | Cloud-platform identity types only (AAD, AWS IAM, GCP) |
| UIAO_120 — Zero-Trust Integration Layer | No | Zero-Trust posture for the workforce surface; doesn't cover citizen-facing flows |

**The gap is total.** No canon entity describes:
- The customer as an identity primitive
- The authority-of-record concept for federal attributes
- The reciprocal-consumption entitlement model
- The KYC protocol itself (inbound or outbound)
- IAL/AAL/FAL applied to customer flows (only workforce flows referenced)
- Cross-agency attribute exchange contracts

---

## 4. Proposed canon block

### 4.1 UIAO_141 — Customer Identity Model (declarative)

Companion to UIAO_129. Defines the **Customer Identity** primitive with the
following required bindings:

| Binding | Authority | Example |
|---|---|---|
| Canonical identifier | Authority of record (per attribute) | SSN owned by SSA; TIN owned by IRS; UEI owned by GSA |
| Identity assurance level (NIST SP 800-63 IAL-1/2/3) | Verifying agency | IAL-2 for benefits enrollment; IAL-3 for security-clearance flows |
| Authentication assurance level (AAL-1/2/3) | Verifying agency | AAL-2 (MFA) baseline for federal customer portals; AAL-3 for high-stakes |
| Federation assurance level (FAL-1/2/3) | Federation operator (e.g., Login.gov) | FAL-2 for cross-agency federation |
| Authority of record | The agency that owns the attribute | SSA for SSN, IRS for TIN, etc. |
| Reciprocal-consumption entitlement | Authority of record | Documented list of consumers entitled to fetch the attribute |

Unlike UIAO_129's six application bindings (which all live within one
substrate), Customer Identity bindings frequently **cross agency
boundaries**. The reciprocal-consumption binding is the load-bearing
addition: it formalizes inter-agency attribute exchange as a first-class
canon concept.

### 4.2 UIAO_142 — Customer KYC Onboarding & Reciprocity Runbook (operational)

Companion to UIAO_130. Defines the operational sequences for:

1. **Inbound KYC** — agency receives a customer claim, runs verification
   against the authority of record, produces a Customer Identity Record
   in the evidence graph.
2. **Outbound KYC** — agency receives a peer's attribute request, validates
   reciprocal-consumption entitlement, returns the attribute with signed
   audit trail.
3. **Reciprocity-record provisioning** — the documented entitlement that
   permits a consumer to fetch attributes from an authority of record
   (analogous to UIAO_140's ATO-reciprocity model, but at the attribute
   level rather than the authorization-decision level).
4. **Drift detection** — five drift classes applied to customer identity:
   - `DRIFT-IDENTITY` — claimed identifier doesn't match authority-of-record
   - `DRIFT-AUTHZ` — consumer fetched an attribute without entitlement
   - `DRIFT-PROVENANCE` — attribute returned without signed audit trail
   - `DRIFT-SCHEMA` — Customer Identity Record missing a required binding
   - `DRIFT-SEMANTIC` — authority-of-record value differs from cached consumer copy

### 4.3 ADR-055 — Customer Identity Canon Block

Establishes the doctrine, allocates UIAO_141 and UIAO_142, registers the
adapter slots in §4.4 below, and amends UIAO_120 (Zero-Trust Integration
Layer) to recognize the customer-identity surface as a peer to the
workforce-identity surface.

### 4.4 Adapter slots — the federal authorities of record

Reserved adapter slots, one per major attribute authority. Each is
`status: reserved` until per-adapter activation ADRs land:

| Adapter ID | Authority | Mission-class | Class | Attribute(s) |
|---|---|---|---|---|
| `ssa-attribute-service` | Social Security Administration | identity | conformance | SSN, earnings record, benefit eligibility |
| `irs-tin-attribute-service` | Internal Revenue Service | identity | conformance | TIN, EIN, federal tax compliance |
| `gsa-sam-attribute-service` | GSA SAM.gov | identity | conformance | UEI, business registration, exclusion list |
| `uscis-immigration-attribute-service` | USCIS | identity | conformance | Immigration / citizenship status |
| `dhs-everify-attribute-service` | DHS USCIS + SSA composite | identity | conformance | Employment authorization |
| `treasury-ofac-attribute-service` | Treasury OFAC | policy | conformance | Sanctions screening |
| `state-dmv-realid-attribute-service` | State DMVs (REAL-ID) | identity | conformance | Driver license / state ID verification |
| `dcsa-clearance-attribute-service` | DCSA | identity | conformance | Federal security clearance |
| `va-veteran-attribute-service` | VA / DoD | identity | conformance | Veteran status, service record |
| `vitals-attribute-service` | State vital-records bureaus | identity | conformance | Birth / marriage / death records |
| `loginGov-federation-service` | GSA Login.gov | identity | modernization | FAL-2 federated authentication for citizen portals |
| `idMe-federation-service` | ID.me (commercial; federal-authorized) | identity | modernization | IAL-2/AAL-2 verification for citizen portals |

Some are pure conformance (read-only attribute observation); some are
modernization (federated authentication that issues claims agencies
consume). All operate under the symmetric vendor/customer doctrine.

---

## 5. Tie-ins to existing canon

| Existing canon | KYC tie-in |
|---|---|
| UIAO_129 §2 binding #4 (Trust anchor) — now includes SAML 2.0 (ADR-051) | KYC reuses SAML for citizen-portal federation; FAL-2 IdPs (Login.gov, ID.me) federate via SAML to consuming agencies |
| ADR-052 — PIV/USAccess | Federal employees authenticate via PIV; **external customers** authenticate via Login.gov / ID.me / agency portals — different trust anchors, same trust-anchor binding model |
| UIAO_140 — Single-ATO Reciprocity | UIAO_140 reciprocity is *authorization-level* (one ATO covers many tenants); UIAO_142 reciprocity is *attribute-level* (one authority of record serves many consumers). Same doctrine, different scope. |
| ADR-053 — OPM Azure APIM | Pattern for inter-agency API gateway; KYC peer-to-peer attribute exchange will likely use similar gateways operated by each authority of record |
| UIAO_113 — Evidence Graph | Customer Identity Records and reciprocity events emit to the same graph as workforce events |
| UIAO_120 — Zero-Trust Integration Layer | Zero Trust applies to *both* workforce and customer surfaces; UIAO_120 will need amendment to recognize the customer surface explicitly |
| Truth Fabric `b-02-identity-anchoring.md` | The `identity_type` enum stays (person/device/service/organization); KYC adds a parallel concept of **authority of record** as a property of person and organization records |
| Spec2-D3.x — HR-driven IAM | HR-driven IAM is *workforce* customer onboarding; KYC is *external* customer onboarding. Distinct flows, parallel architecture. |

---

## 6. NIST and federal frame references

The canon block aligns with these standards (citation, not customization):

| Reference | Role |
|---|---|
| **NIST SP 800-63-3 / -4 (draft)** | IAL/AAL/FAL definitions; the customer-identity-assurance vocabulary |
| **OMB M-19-17** | Enabling Mission Delivery through Improved Identity, Credential, and Access Management — the policy mandate for federal customer ICAM |
| **OMB M-22-09** | Federal Zero Trust Strategy (already referenced for HRIT) — applies to customer surfaces too |
| **HSPD-12 / FIPS 201-3** | PIV — workforce only, but FIPS 201-3 §6 derived-PIV applies to certain customer scenarios |
| **5 U.S.C. §552a (Privacy Act of 1974)** | The legal floor for inter-agency attribute exchange — every reciprocal-consumption entitlement must be Privacy-Act-compliant |
| **Computer Matching and Privacy Protection Act of 1988 (CMPPA)** | Specific governance for inter-agency matching programs — directly applicable to KYC reciprocity |
| **REAL ID Act of 2005** | State-DMV identity assurance baseline |
| **18 U.S.C. §1028 / Identity Theft and Assumption Deterrence Act** | The threat model the customer-identity surface must defend against |
| **Bank Secrecy Act / FinCEN CIP rule** | Customer Identification Program — financial-sector parallel that several federal agencies coordinate with |
| **NIST SP 800-66 (HIPAA Security Rule)** | Customer-identity for HHS/CMS contexts |

---

## 7. Out-of-scope for this draft

These belong in follow-up ADRs / specs once the foundational block lands:

- **PII minimization architecture** — selective disclosure, attribute-based
  credentials (ABCs), zero-knowledge proofs for "is over 18" / "is US citizen"
  without revealing the underlying value. Worth a dedicated UIAO_NNN spec.
- **Login.gov-specific integration runbook** — a Spec3-D6.x candidate
  paralleling Spec2-D3.x for federated citizen authentication.
- **State-level reciprocity governance** — federal-state attribute exchange
  has its own legal frame (state-level Privacy Acts vary). Worth a separate
  spec once federal-side canon is stable.
- **Employer-facing reciprocity** — e-Verify, W-2 reporting, work-authorization
  flows. Tied to NFC/SSA but with employer-specific compliance constraints.
- **Continuous-evaluation / continuous-vetting** — the security-clearance
  modernization layer that consumes inter-agency attributes on an ongoing
  basis. Distinct from one-shot KYC.

---

## 8. Recommended path forward

1. **Land this draft in inbox** — done by this PR session.
2. **Review the four-artifact bundle** — UIAO_141 / UIAO_142 / ADR-055 +
   adapter slots — held in [`proposed-canon-additions/`](proposed-canon-additions/).
3. **Promote to canon** when ready, following the same pattern as the HRIT
   IAM bundle (PR #312):
   - Allocate UIAO_141, UIAO_142, ADR-055 (next sequential numbers at
     promotion time).
   - Land as one PR or four (one per artifact); recommend one PR since the
     four are tightly coupled.
4. **Per-adapter activation ADRs** — each authority-of-record adapter
   (SSA, IRS, GSA, USCIS, etc.) gets its own activation ADR modeled on
   ADR-035 when an agency engagement requires it.
5. **Implementation work** — OSCAL emitter for `customer-identity-record`
   and `reciprocity-attribute-record` lands in a separate PR after canon
   is stable.

---

*End of scoping document. The four ADR/spec drafts in
[`proposed-canon-additions/`](proposed-canon-additions/) are the actionable
output, ready for review and canon promotion.*
