---
document_id: UIAO_142
title: "UIAO Customer KYC Onboarding & Reciprocity Runbook"
version: "1.0"
status: Draft
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-05-05"
updated_at: "2026-05-05"
boundary: "GCC-Moderate"
---

# UIAO Customer KYC Onboarding & Reciprocity Runbook

> **Inbox draft.** Held in `inbox/KYC/proposed-canon-additions/`. Promote on
> canon-merge per repo invariant I5.

## 1. Overview

This runbook is the operational counterpart to UIAO_141 (Customer Identity
Model). It defines the canonical sequences for:

1. **Inbound KYC** — agency receives a customer claim and verifies it
   against the authority of record.
2. **Outbound KYC** — agency receives a peer's attribute request and
   serves it under reciprocal-consumption entitlement.
3. **Reciprocity provisioning** — establishing a new
   reciprocal-consumption entitlement between an authority of record and
   a consumer.
4. **Drift detection and remediation** — applying the five drift classes
   to KYC flows.

The runbook is used by agency operators following the Operator track of
UIAO_125, by KYC-protocol implementers integrating an authority-of-record
adapter, and by governance reviewers auditing reciprocal-consumption
entitlements.

The reference instance for this runbook is the federal civilian customer
ICAM landscape — SSA / IRS / USCIS / GSA SAM.gov / state DMVs / Login.gov /
ID.me / e-Verify / OFAC / DCSA / VA — but the model is generic to any
authority-of-record / consumer pair under documented entitlement.

## 2. Preconditions

Before any KYC operation begins, the following must be in place:

1. **Canon available.** `$UIAO_WORKSPACE_ROOT` resolves; `uiao substrate
   walk` exits clean with no DRIFT-SCHEMA or DRIFT-PROVENANCE findings;
   UIAO_141 and UIAO_142 are both loaded.
2. **Authority Plane reachable.** Each authority-of-record adapter declared
   in the engagement scope (e.g., `ssa-attribute-service`,
   `irs-tin-attribute-service`) responds to health checks. Their adapter
   conformance status is green per UIAO_121.
3. **Reciprocal-consumption registry loaded.** The
   `src/uiao/canon/reciprocal-consumption-registry.yaml` registry is loaded
   and JSON-Schema-validated. Every entitlement has a `legal_basis` field
   resolving to a Privacy Act SORN, CMPPA agreement, statute, or customer
   consent reference.
4. **Federation operator configured.** If the inbound flow uses a federated
   IdP (Login.gov, ID.me, agency SAML), the federation operator is
   registered and its FAL is canonized.
5. **Privacy Act / CMPPA review complete.** For inter-agency flows, the
   System of Records Notice routine uses or CMPPA matching agreement is
   documented and current. Out-of-band; this runbook validates the
   citation, not the agreement itself.

## 3. State sequence — inbound KYC

The inbound flow drives a Customer Identity Record from `Proposed` to
`Active` (UIAO_141 §4). Each step ends with a state-change event signed
into the evidence graph; the next step is gated on the prior event's
cryptographic verification.

### 3.1 Proposed

A consuming agency receives a customer claim — directly via a portal
submission, via a federated IdP assertion, or via a peer's hand-off.

Inputs: canonical identifier (claimed), customer-asserted attributes,
declared FAL of the assertion (if federated), session metadata.

Gate: claim well-formedness validator (per attribute, per
authority-of-record adapter contract).

Output: `proposed` event in evidence graph.

### 3.2 Proofed

The consuming agency proofs the claim at the IAL required by the
downstream use case. Proofing is performed by:

- An in-person proofing event (IAL-3 baseline)
- A federated IdP at the declared FAL (Login.gov IAL-2, ID.me IAL-2, etc.)
- A direct call to the authority of record (SSA Consent-Based SSN
  Verification, IRS Income Verification Express Service, USCIS SAVE,
  e-Verify, etc.)

Gate: proofing-event signature matches a registered proofing-service
adapter; IAL declared in the event matches or exceeds the use-case
requirement.

Output: `proofed` event with the signed proofing artifact attached.

### 3.3 Active

The Customer Identity Record is bound to its authority of record. The
consuming agency caches the verified attribute set under the contractual
freshness window declared in the reciprocal-consumption entitlement.

Gate: first 100 events tagged with the CIR's canonical identifier arrive
correctly grouped (no DRIFT-PROVENANCE findings).

Output: `active` event.

### 3.4 Reciprocally-Provisioned (conditional)

Entered when one or more peers register a reciprocal-consumption
entitlement against this CIR's authority of record. The `Active` and
`Reciprocally-Provisioned` states overlap — a CIR can be Active for the
issuing agency while simultaneously being Reciprocally-Provisioned to N
peers.

Gate: each new entitlement validated against
`reciprocal-consumption-registry.yaml`; legal_basis citation resolves;
authority of record signs an entitlement-acknowledgment event.

Output: `reciprocity-attribute-record` event per peer.

### 3.5 Quarantined (conditional)

Entered on drift finding P2 or higher, or on explicit operator quarantine
(e.g., suspected identity theft). Outbound attribute requests return
`quarantined` until investigation closes; inbound verification falls back
to higher-IAL re-proofing.

Gate: quarantine envelope verified (peer notifications sent within the
contractual window); investigation ticket opened.

Output: `quarantined` event with drift-finding ID.

### 3.6 Retired

Authority of record marks the CIR retired (deceased, dissolved, expunged).
Cached copies in consumer caches must be invalidated within the contractual
freshness window. Evidence graph retains the full state history per
Privacy Act and Federal Records Act retention schedules.

Gate: all reciprocal consumers acknowledge retirement; cached copies
purged; no orphan bindings detectable via `uiao substrate drift`.

Output: `retired` event; evidence retained.

## 4. State sequence — outbound KYC

The outbound flow serves a peer's attribute request against an authority
of record's CIR.

### 4.1 Request received

A peer submits a signed attribute request. Required fields: requestor
identity (PIV-bound for federal employee, service-principal-bound for
service-to-service), entitlement reference, attribute scope, freshness
requirements.

Gate: request signature valid; requestor identity resolves; well-formed
per the authority-of-record adapter contract.

Output: `kyc-outbound-request-received` event.

### 4.2 Entitlement validated

Authority of record validates the cited entitlement:

- Entitlement exists in the reciprocal-consumption registry
- Entitlement is active (within `effective_date` / `expiry_date`)
- Requestor matches the `consumer_principal` field
- Requested scope is a subset of the entitled `scope`
- Freshness requirement is achievable

Gate: all five validation checks pass.

Output: `kyc-outbound-entitlement-validated` event, OR a typed rejection
event with `DRIFT-AUTHZ` finding ID if any check fails.

### 4.3 Attribute returned

Authority of record returns the attribute under the agreed format (signed
response, audit-trail metadata, freshness timestamp).

Gate: response signature valid; response logged to evidence graph with
the requestor as a co-grouped event participant.

Output: `kyc-outbound-disclosure` event.

### 4.4 Consumer acknowledgment (optional)

For high-stakes attributes (security clearance, sanctions screening),
the entitlement may require the consumer to emit an
`acknowledgment-received` event closing the loop. Failure to acknowledge
within the contractual window emits a `DRIFT-PROVENANCE` finding.

## 5. Reciprocity provisioning

Establishing a new reciprocal-consumption entitlement is a governance
action, not a runtime action. The flow:

1. **Proposal.** Consumer (or authority of record) drafts an entitlement
   record citing the legal basis (Privacy Act SORN routine use, CMPPA
   agreement, statute, customer consent).
2. **Legal review.** Privacy officer or general counsel of the authority
   of record validates the citation. Out-of-band; this runbook accepts
   the signed approval as canon input.
3. **Registry PR.** Entitlement YAML is added to
   `src/uiao/canon/reciprocal-consumption-registry.yaml` via PR; CI
   validates against the JSON Schema.
4. **Activation.** On merge, the authority-of-record adapter loads the
   entitlement at next health-check cycle; outbound KYC requests citing
   that entitlement begin succeeding.
5. **Audit.** Quarterly review of entitlement usage; expired or unused
   entitlements are retired via the same PR flow.

## 6. Operator commands

```bash
uiao kyc verify --identifier ssa.ssn --claim <claim-payload>
uiao kyc fetch --identifier irs.tin --consumer agency-X --entitlement <entitlement-id>
uiao kyc reciprocity propose --attribute ssa.ssn --consumer agency-Y --legal-basis sorn-routine-use-12
uiao kyc reciprocity list --authority ssa-attribute-service
uiao kyc cir status --identifier ssa.ssn-XXX-XX-XXXX
uiao kyc cir quarantine --identifier ssa.ssn-XXX-XX-XXXX --finding DRIFT-IDENTITY-P1-NN
uiao kyc cir retire --identifier ssa.ssn-XXX-XX-XXXX --confirm
```

Each command returns exit 0 on success and a non-zero drift-class code on
failure; codes map to the five drift classes in UIAO_141 §7.

## 7. Failure modes and handling

| Failure | Detection | Remediation |
|---|---|---|
| Authority-of-record adapter unreachable during inbound verification | adapter health check fails | Hold CIR in `Proposed` state; retry per contractual SLA; if persistently unavailable, escalate to authority-of-record incident response |
| Proofing event signature invalid | DRIFT-IDENTITY on first verification attempt | Reject claim; require re-proofing at higher IAL |
| Reciprocity entitlement expired during outbound request | DRIFT-AUTHZ at validation step | Reject request; notify consumer; route to entitlement-renewal flow |
| Cached consumer copy older than freshness window | DRIFT-SEMANTIC on next event tagged with the CIR | Invalidate cache; re-fetch from authority of record |
| Outbound disclosure not acknowledged within window | DRIFT-PROVENANCE on the consumer side | Open investigation; consumer's reciprocity entitlement may be suspended pending review |
| Customer-asserted identifier doesn't match authority-of-record value | DRIFT-IDENTITY P1 | Quarantine CIR; refer to identity-theft investigation per agency policy |
| Entitlement legal_basis citation no longer valid (SORN retired, statute repealed) | DRIFT-AUTHZ on next outbound request | Suspend entitlement; require legal review for re-establishment |

## 8. Evidence outputs

Each KYC operation produces:

1. Signed events in the evidence graph for each state transition (CIR
   lifecycle) and each request/response (inbound and outbound).
2. A per-CIR OSCAL-native evidence bundle referenced from UIAO_113, usable
   in agency Privacy Act audit responses.
3. A reciprocity-attribute-record event per active entitlement, tying the
   authority of record to each consumer.
4. A drift-scan baseline that subsequent runs compare against; drift
   between the authority-of-record value and consumer-cached values is
   first-class evidence.
5. A provenance record naming the operator (where applicable), the
   entitlement reference, and the exact timestamps of every state change
   and disclosure.

## 9. Rollback

Each provisioned step has a defined rollback that emits a compensating
event. Rollback is invoked on:

- Authority-of-record adapter returning `unavailable` during inbound
  verification (rollback to `Proposed`)
- Drift scan returning P1 finding post-`Active` (rollback to
  `Quarantined`)
- Operator abort during a KYC session
- Customer revocation of consent (where consent was the legal basis)

Rollback never deletes evidence-graph events — it emits compensating
events so the ledger remains append-only, consistent with the rest of UIAO.

## 10. Cross-References

- UIAO_003 — Adapter Segmentation Overview
- UIAO_110 — Drift Engine Specification
- UIAO_113 — Evidence Graph Model (event schema; minor amendment required)
- UIAO_120 — Zero-Trust Integration Layer (consumer; amendment required)
- UIAO_121 — Adapter Conformance Test Plan — Template
- UIAO_124 — Adapter Operations Runbook (parent operational context)
- UIAO_125 — Training Program (Operator track curriculum)
- UIAO_140 — Single-ATO Reciprocity Model (authorization-level reciprocity)
- UIAO_141 — Customer Identity Model (declarative spec)
- UIAO_200 — Substrate Manifest
- ADR-055 — Customer Identity Canon Block (authorizes this runbook)
- `src/uiao/canon/reciprocal-consumption-registry.yaml` — entitlement registry (introduced by ADR-055)
- NIST SP 800-63-3 / -4 (draft) — IAL/AAL/FAL definitions
- Privacy Act of 1974 (5 U.S.C. §552a)
- Computer Matching and Privacy Protection Act of 1988
- OMB M-19-17 (federal customer ICAM)
