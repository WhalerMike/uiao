---
document_id: UIAO_113
title: "UIAO Evidence Graph Model"
version: "1.1"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-05-05"
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
