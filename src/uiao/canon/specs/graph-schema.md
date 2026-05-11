---
document_id: UIAO_113
title: "UIAO Evidence Graph Model"
version: "1.2"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-05-06"
boundary: "GCC-Moderate"
---

# UIAO Evidence Graph Model

UIAO represents compliance as a graph of interconnected nodes.

---

## Node Types

### 1. Control
- id: "AC-2"
- type: "control"
- properties:
  - family
  - baseline
  - priority

### 2. IR Object
- id: "IR-ACCT-MFA-001"
- type: "ir-object"
- properties:
  - description
  - mapping

### 3. Evidence
- id: "EV-0001"
- type: "evidence"
- properties:
  - source
  - field
  - value
  - hash
  - timestamp

### 4. Provenance
- id: "prov-scuba-20260407-01"
- type: "provenance"
- properties:
  - hash
  - timestamp
  - environment

### 5. Finding
- id: "FIND-0001"
- type: "finding"
- properties:
  - severity
  - description

### 6. POA&M Entry
- id: "POAM-0001"
- type: "poam"
- properties:
  - status
  - milestones

### 7. Customer Identity Record (CIR)
- id: "CIR-ssa.ssn-XXX-XX-XXXX"
- type: "customer-identity-record"
- properties:
  - canonical_identifier
  - identity_assurance_level
  - authentication_assurance_level
  - federation_assurance_level
  - authority_of_record
  - lifecycle_state

> Established by ADR-055 / UIAO_141. The CIR is the customer-side
> identity primitive paralleling the workforce-side primitives
> declared by UIAO_129. KYC-related events (sub-types below) group
> by `canonical_identifier`.

### 8. CIR State Transition
- id: "CIR-STATE-0001"
- type: "cir-state-transition"
- properties:
  - cir_id
  - from_state
  - to_state
  - timestamp
  - drift_finding_id (optional, when transitioning to Quarantined)

### 9. KYC Inbound Verification
- id: "KYC-IN-0001"
- type: "kyc-inbound-verification"
- properties:
  - cir_id
  - verifying_agency
  - authority_of_record
  - entitlement_id
  - ial_at_proofing
  - timestamp

### 10. KYC Outbound Disclosure
- id: "KYC-OUT-0001"
- type: "kyc-outbound-disclosure"
- properties:
  - cir_id
  - authority_of_record
  - consumer_principal
  - entitlement_id
  - scope
  - timestamp

### 11. Reciprocity Attribute Record
- id: "RECIP-ATTR-0001"
- type: "reciprocity-attribute-record"
- properties:
  - entitlement_id
  - attribute_id
  - authority_of_record
  - consumer_principal
  - effective_date
  - signed_by

> Node types 7-11 added by UIAO_113 v1.1 (ADR-055 / UIAO_141 §8).
> They map to the events and records described in UIAO_141 §8 and
> UIAO_142 §3-§5.

### 12. ATO Decision
- id: "ATO-OPM-HRIT-2026-001"
- type: "ato-decision"
- properties:
  - controlling_ato_id (string, key)
  - authorizing_official (string)
  - decision_date (date-time)
  - expires_at (date-time)
  - ssp_ref (string — OSCAL SSP UUID reference)
  - provenance (block — conforms to metadata provenance schema)

### 13. Reciprocity Record
- id: "RECIP-OPM-HRIT-2026-001/TREAS"
- type: "reciprocity-record"
- properties:
  - record_id (string, key — typically `{controlling_ato_id}/{consuming_agency_code}`)
  - controlling_ato_id (string, foreign key → ato-decision)
  - consuming_agency_code (string)
  - effective_at (date-time)
  - expires_at (date-time)
  - legal_basis (string, enum from reciprocal-consumption schema)
  - record_hash (string — sha256 hex of stable content fields)
  - signature_ref (string — HMAC signature reference)

> Node types 12-13 added by UIAO_113 v1.2 (ADR-058 / UIAO_140 §6).
> They implement the `ato-decision → reciprocity-record` hierarchy
> described in UIAO_140 §6 lines 102–108. Node type 12 is the singular
> root of authority under the Single-ATO Reciprocity Model; continuous-
> monitoring evidence attaches to the controlling `ato-decision`, not to
> individual reciprocity records. Node type 13 scopes one consuming
> agency's entitlement under that controlling ATO.

---

## Edge Types

| Edge | From | To | Relationship |
|------|------|----|-------------|
| implements | Control | IR Object | A control is implemented by an IR object |
| validated-by | IR Object | Evidence | An IR object is validated by evidence |
| provenance-of | Evidence | Provenance | Evidence has a provenance record |
| violated-by | Control | Finding | A control is violated by a finding |
| remediated-by | Finding | POA&M | A finding is remediated by a POA&M entry |
| state-of | CIR State Transition | Customer Identity Record | A state transition belongs to a CIR (UIAO_113 v1.1) |
| verified-by | Customer Identity Record | KYC Inbound Verification | A CIR was verified inbound by a KYC verification event (UIAO_113 v1.1) |
| disclosed-by | Customer Identity Record | KYC Outbound Disclosure | A CIR attribute was disclosed outbound to a peer (UIAO_113 v1.1) |
| entitled-by | KYC Outbound Disclosure | Reciprocity Attribute Record | An outbound disclosure is authorized by a reciprocity entitlement (UIAO_113 v1.1) |
| authorizes-reciprocity | ATO Decision | Reciprocity Record | A controlling ATO authorizes a per-agency reciprocity record (UIAO_113 v1.2) |
| scopes-to-agency | Reciprocity Record | Consuming Agency | A reciprocity record scopes the entitlement to a specific consuming agency (UIAO_113 v1.2) |
| derives-from-ssp | Reciprocity Record | SSP | A reciprocity record is derived from the controlling ATO's System Security Plan (UIAO_113 v1.2) |

---

## Example Graph Path

```
AC-21
  → IR-SHARE-EXT-006 (implements)
    → EV-0006 (validated-by)
      → prov-scuba-20260407-01 (provenance-of)
  → FIND-0001 (violated-by)
    → POAM-0001 (remediated-by)
```

---

## Graph DB Implementation Notes

- Recommended: Neo4j, Amazon Neptune, or any property graph DB
- Each node has a unique ID and type label
- Edges are directed and typed
- All nodes include a timestamp and source system reference
- The graph supports traversal queries for compliance traceability:
  - "Show all evidence for control AC-21"
  - "Show all open findings and their associated POA&M entries"
  - "Trace control IA-2 from SCuBA field to OSCAL output"
  - "Show all reciprocity records authorized by a controlling ATO"
  - "Identify consuming agencies scoped by a given reciprocity record"

---

## Provenance Log

### Provenance entry — v1.1 → v1.2

- **Amended by:** ADR-058 (HRIT Single-ATO Productization as v0.6.0 Mission Theme)
- **Authority:** UIAO_140 §6 lines 102–108 — defines the `ato-decision → reciprocity-record`
  hierarchy as the evidence graph anchor for the Single-ATO Reciprocity Model
- **Date:** 2026-05-06
- **Changes:**
  - Added Node Type 12: `ato-decision` — the singular root of authority under the
    Single-ATO Reciprocity Model; continuous-monitoring evidence attaches here
  - Added Node Type 13: `reciprocity-record` — scopes one consuming agency's entitlement
    under a controlling ATO; keyed by `{controlling_ato_id}/{consuming_agency_code}`
  - Added edge type `authorizes-reciprocity` (ATO Decision → Reciprocity Record)
  - Added edge type `scopes-to-agency` (Reciprocity Record → Consuming Agency)
  - Added edge type `derives-from-ssp` (Reciprocity Record → SSP)
- **Rationale:** ADR-054 §Implementation explicitly deferred these node and edge types to
  a follow-on PR. ADR-058 ratifies HRIT Single-ATO Productization as the v0.6.0 mission
  theme and mandates this amendment as acceptance condition 3 of that release.
- **Canon references:** ADR-058 §Consequences; UIAO_140 §6; ADR-054 §Implementation table
