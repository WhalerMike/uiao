---
document_id: UIAO_141
title: "UIAO Customer Identity Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-05"
updated_at: "2026-05-05"
boundary: "GCC-Moderate"
---

# UIAO Customer Identity Model

## 1. Overview

The Customer Identity Model is the canon counterpart to UIAO_129
(Application Identity Model). Where UIAO_129 treats applications as
first-class identity primitives within the substrate, UIAO_141 treats
**customers** — citizens, businesses, beneficiaries, applicants, and
peer-agency attribute consumers — as first-class identity primitives
**across substrate boundaries**.

This spec defines the customer primitive, its authoritative bindings, the
authority-of-record / reciprocal-consumption doctrine, the lifecycle of a
Customer Identity Record (CIR), and the drift classes that apply when any
binding diverges from canon.

It is consumed by UIAO_120 (Zero-Trust Integration Layer), UIAO_113
(Evidence Graph), UIAO_140 (Single-ATO Reciprocity — *authorization*-level
reciprocity; UIAO_141 introduces *attribute*-level reciprocity), and the
Truth Fabric appendix B-02 (Identity Anchoring). Its operational counterpart
is UIAO_142 (Customer KYC Onboarding & Reciprocity Runbook).

**Doctrine.** *Agencies are simultaneously vendors and customers of each
other.* Each high-value identity attribute has exactly one authority of
record. Every other consumer — peer agency, state, employer, or external
party — runs a KYC protocol against the authority of record under
documented reciprocal-consumption entitlements.

## 2. The Customer Identity Primitive

A Customer Identity Record (CIR) is a canonical object with six required
bindings:

| Binding | Authority | Example |
|---|---|---|
| Canonical identifier | Authority of record (per attribute) | SSN owned by SSA; TIN/EIN owned by IRS; UEI owned by GSA SAM.gov |
| Identity assurance level (IAL) | Verifying agency | NIST SP 800-63 IAL-1 / IAL-2 / IAL-3 |
| Authentication assurance level (AAL) | Verifying agency | AAL-1 / AAL-2 (MFA baseline) / AAL-3 (hardware-bound) |
| Federation assurance level (FAL) | Federation operator | FAL-1 / FAL-2 / FAL-3 (per Login.gov / ID.me / agency portal) |
| Authority of record | The agency that owns the attribute | SSA for SSN; IRS for TIN; USCIS for immigration status |
| Reciprocal-consumption entitlement | Authority of record | Documented list of consumers entitled to fetch the attribute, with legal basis (Privacy Act SORN, CMPPA agreement, statute) |

All six are required. A Customer Identity Record missing any binding is a
DRIFT-IDENTITY finding (see §7).

The `identity_type` field from Truth Fabric appendix B-02 (`person`,
`device`, `service`, `organization`) remains valid; KYC operates primarily
on `person` and `organization`. Customer Identity Records are a refinement
of those types, not a replacement.

## 3. Authoritative Bindings

Each binding has exactly one authority. Authorities are declared in
`src/uiao/canon/adapter-registry.yaml` (conformance: read-only attribute
observers) and `src/uiao/canon/modernization-registry.yaml` (modernization:
federated-identity issuers like Login.gov). Overlays and consumers read
the binding — they do not define it.

- **Canonical identifier binding** — the SSN, TIN, UEI, or other globally
  unique identifier issued by exactly one federal authority. The authority's
  attribute service is the SSOT; consumer copies are caches with explicit
  freshness windows.
- **IAL binding** — the strength of the customer's identity-proofing event.
  Set at proofing time by the verifying agency or its delegated proofing
  service (Login.gov, ID.me, agency in-person).
- **AAL binding** — the strength of the authentication mechanism in use at
  any given session. Re-evaluated per session.
- **FAL binding** — the strength of the federation assertion that delivered
  the identity claim. Set by the federation operator.
- **Authority-of-record binding** — the immutable assignment of "who owns
  this attribute." SSA owns SSN by statute (42 U.S.C. §405); IRS owns TIN
  by 26 U.S.C. §6109; etc. Authority-of-record changes require an act of
  Congress, not an ADR.
- **Reciprocal-consumption binding** — the contractual / statutory
  authorization for a consumer to fetch the attribute. Examples:
  - Privacy Act System of Records Notice (SORN) routine uses
  - Computer Matching and Privacy Protection Act (CMPPA) matching agreements
  - Treasury Do Not Pay program statutory authorities
  - Direct statutory authorization (e.g., e-Verify per IIRIRA §403)
  - Customer consent (NIST SP 800-63A §5.5)

## 4. Lifecycle

Six states, all transitions logged to the evidence graph (UIAO_113):

1. **Proposed** — customer claim received by a consuming agency or
   authority-of-record agency. No verification yet performed.
2. **Proofed** — identity proofed at the declared IAL. The verifying
   agency emits a signed proofing event.
3. **Active** — Customer Identity Record bound to an authority of record;
   the customer can authenticate at the declared AAL via the declared FAL.
4. **Reciprocally-Provisioned** — one or more consumers have registered
   reciprocal-consumption entitlements; outbound KYC requests can be
   served. Multiple reciprocity bindings may be active simultaneously.
5. **Quarantined** — drift finding (any class) has moved the CIR out of
   the production path; forensic evidence retained; outbound attribute
   requests return `quarantined` until investigation closes.
6. **Retired** — customer deceased / business dissolved / record
   expunged. Authority-of-record marks the CIR retired; consumers receive
   a `retired` response on subsequent fetches; cached copies must be
   invalidated within the contractual freshness window.

Each transition requires a signed state-change event in the evidence graph.
Quarantine transitions are tied to a drift finding ID. Retired transitions
preserve historical evidence per the Privacy Act and Federal Records Act
retention schedules.

## 5. KYC Protocol

The KYC protocol operates in two directions, simultaneously, against every
Customer Identity Record:

### 5.1 Inbound KYC (agency-as-customer)

The agency receives a customer claim and verifies it against the authority
of record:

1. Customer presents claim (SSN, name, DOB, etc.) to the consuming agency.
2. Consuming agency identifies the authority of record per the canonical
   identifier (SSA for SSN, IRS for TIN, etc.).
3. Consuming agency verifies its **reciprocal-consumption entitlement** for
   that attribute and consumer pair. If no entitlement exists, the request
   is rejected as `DRIFT-AUTHZ`.
4. Consuming agency issues a signed attribute-request to the authority of
   record, carrying the entitlement reference and the requestor identity
   (federal employee with PIV, or service principal under
   reciprocal-attribute-service entitlement).
5. Authority of record validates the entitlement, returns the attribute
   value with a signed response, logs the disclosure to the evidence graph.
6. Consuming agency writes the verified Customer Identity Record to the
   evidence graph with provenance pointing to the authority-of-record
   response.

### 5.2 Outbound KYC (agency-as-vendor)

The agency receives a peer's attribute request and serves it:

1. Peer (consuming agency / state / employer / external party) submits a
   signed attribute request, citing its reciprocal-consumption entitlement.
2. Authority of record validates the requestor identity, the entitlement
   reference, the requested attribute scope, and the freshness requirements.
3. If valid, authority of record returns the attribute under the agreed
   format (e.g., e-Verify attestation, Income Verification Express Service
   transcript, etc.) with signed response and audit-trail metadata.
4. If invalid, authority of record returns a typed rejection (entitlement
   expired, scope mismatch, requestor identity unverified, etc.) and logs
   a `DRIFT-AUTHZ` finding referencing the rejected request.

Both inbound and outbound KYC events emit to the evidence graph; cross-
references are bidirectional.

## 6. Reciprocal-Consumption Entitlements

A reciprocal-consumption entitlement is a signed canon record with the
following required fields:

| Field | Description |
|---|---|
| `attribute_id` | Canonical attribute (e.g., `ssa.ssn`, `irs.tin`, `gsa.uei`) |
| `authority_of_record` | Adapter ID (e.g., `ssa-attribute-service`) |
| `consumer_principal` | The agency / state / employer authorized to consume |
| `legal_basis` | Privacy Act SORN routine use citation, CMPPA agreement ID, statute, or customer consent reference |
| `scope` | Attribute fields permitted (full SSN vs. last-four; tax-year subset; etc.) |
| `freshness_window` | Maximum cache age before the consumer must re-fetch |
| `effective_date` / `expiry_date` | Entitlement validity window |
| `signed_by` | Authority-of-record signing identity |

Entitlements are stored in a new canon registry
`src/uiao/canon/reciprocal-consumption-registry.yaml` (introduced by
ADR-055, drafted alongside this spec). The registry is JSON-Schema-
constrained; CI rejects entitlements without a documented `legal_basis`.

This is the **attribute-level reciprocity** that pairs with UIAO_140's
**authorization-level reciprocity** (single-ATO covering many tenants).
Same doctrinal pattern, different scope.

## 7. Drift Classes

| Class | Trigger | Severity |
|---|---|---|
| `DRIFT-SCHEMA` | Customer Identity Record missing a required binding | P2 |
| `DRIFT-IDENTITY` | Claimed canonical identifier doesn't match authority-of-record verification | P1 |
| `DRIFT-AUTHZ` | Consumer fetched an attribute without a valid reciprocal-consumption entitlement | P1 |
| `DRIFT-PROVENANCE` | Attribute returned without signed audit trail or evidence-graph event | P2 |
| `DRIFT-SEMANTIC` | Authority-of-record value differs from cached consumer copy beyond the contractual freshness window | P2 |

Detection runs continuously in the drift engine (UIAO_110). KYC drift
findings are first-class peers to existing workforce-identity drift findings
in the evidence graph; the same classifier covers both surfaces.

## 8. Evidence Graph Mapping

Every KYC event — inbound verification, outbound disclosure, reciprocity
provisioning, lifecycle transition — emits a structured event to the
evidence graph (UIAO_113) with the Customer Identity Record's canonical
identifier as the grouping key. Events emitted without that grouping key
are incomplete and logged as `DRIFT-PROVENANCE` findings.

The evidence-graph node types introduced by this spec:

- `customer-identity-record` — the CIR itself
- `cir-state-transition` — lifecycle events
- `kyc-inbound-verification` — agency verifying a customer claim
- `kyc-outbound-disclosure` — authority of record serving a peer request
- `reciprocity-attribute-record` — entitlement provisioning event

UIAO_113 (Evidence Graph) requires a minor amendment to enumerate these
node types in its schema. That amendment lands with ADR-055.

## 9. Cross-References

- UIAO_003 — Adapter Segmentation Overview (taxonomy parent)
- UIAO_110 — Drift Engine (detection runtime)
- UIAO_112 — Multi-Tenant Isolation (authorization boundary)
- UIAO_113 — Evidence Graph (event schema; minor amendment required)
- UIAO_120 — Zero-Trust Integration Layer (consumer; amendment required)
- UIAO_129 — Application Identity Model (workforce-side parallel)
- UIAO_130 — Application Identity Onboarding Runbook (workforce-side parallel)
- UIAO_140 — Single-ATO Reciprocity Model (authorization-level reciprocity; companion concept)
- UIAO_142 — Customer KYC Onboarding & Reciprocity Runbook (operational counterpart)
- ADR-051 — SAML trust anchor (federation context for FAL bindings)
- ADR-052 — PIV / USAccess (federal-employee credential; informational)
- ADR-055 — Customer Identity Canon Block (the ADR that authorizes this spec)
- Truth Fabric appendix B-02 — Identity Anchoring (`identity_type` enum carries forward)
- NIST SP 800-63-3 / -4 (draft) — IAL/AAL/FAL definitions
- Privacy Act of 1974 (5 U.S.C. §552a)
- Computer Matching and Privacy Protection Act of 1988
- OMB M-19-17 (federal customer ICAM)
- OMB M-22-09 (Zero Trust Strategy)
