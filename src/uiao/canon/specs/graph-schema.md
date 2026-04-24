---
document_id: UIAO_113
title: "UIAO Evidence Graph Model"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
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

---

## Edge Types

| Edge | From | To | Relationship |
|------|------|----|-------------|
| implements | Control | IR Object | A control is implemented by an IR object |
| validated-by | IR Object | Evidence | An IR object is validated by evidence |
| provenance-of | Evidence | Provenance | Evidence has a provenance record |
| violated-by | Control | Finding | A control is violated by a finding |
| remediated-by | Finding | POA&M | A finding is remediated by a POA&M entry |

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
