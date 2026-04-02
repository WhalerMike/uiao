---
title: "Canonical-Definition-Of-A-Uiao-Adapter"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# Canonical Definition of a UIAO Adapter
**UIAO Adapter Suite — Document 1 of 4**
**Version 1.0.0 — Canonical, Frozen**

---

# 1. Introduction

A **UIAO Adapter** is the bridge between a source system's native truth and the **UIAO Canonical Truth Fabric**.
It is the only component in the UIAO ecosystem that:

- touches raw source data
- interprets vendor-specific semantics
- normalizes truth into canonical schemas
- attaches provenance
- detects drift
- computes confidence
- publishes canonical claims

UIAO adapters are **not** pipelines, collectors, or ETL jobs.
They are **semantic translators** that convert local truth into federated truth.

This document defines the **canonical, long-form definition** of a UIAO Adapter, including:

- The 10 responsibility domains
- The adapter lifecycle
- The adapter's relationship to the truth fabric
- The adapter's relationship to governance
- Embedded diagrams (ASCII + text-box image descriptions)

This document is **normative** and MUST be followed by all adapter authors.

---

# 2. What a UIAO Adapter *Is*

A UIAO Adapter is:

- A **deterministic translator** from vendor-native truth → canonical truth
- A **boundary-resident component** that runs *inside* the source system's security perimeter
- A **provenance-first agent** that produces evidence-backed claims
- A **drift-aware observer** that detects changes over time
- A **publisher** of canonical claims into the UIAO truth fabric
- A **participant in governance**, subject to certification and oversight

---

# 3. What a UIAO Adapter *Is Not*

A UIAO Adapter is **not**:

- A data pipeline
- A log collector
- A SIEM agent
- A telemetry exporter
- A database replicator
- A policy engine
- A runtime component of the truth fabric

Adapters do **not**:

- store raw telemetry
- export raw logs
- perform analytics
- enforce policy
- make governance decisions

Adapters are **semantic**, not operational.

---

# 4. The Adapter's Position in the UIAO Architecture

Below is the canonical placement of an adapter in the UIAO ecosystem.

---

### **Figure 1 — Adapter Position in UIAO Architecture**
*(Text-box image description: A diagram showing a source system on the left, the adapter in the middle inside the boundary, and the UIAO truth fabric on the right outside the boundary. Arrows show raw data flowing into the adapter and canonical claims flowing out.)*

```text
+-----------------------+        +-----------------------+        +-----------------------+
|    Source System      |        |     UIAO Adapter      |        |   UIAO Truth Fabric   |
| (Entra, Cisco, DB,    | -----> | (Normalize, Drift,    | -----> | (Merge, Reconcile,    |
|  EHR, Finance, etc.)  | Raw    |  Provenance, Publish) | Claims |  Federate, Govern)    |
+-----------------------+        +-----------------------+        +-----------------------+

Boundary: Adapter runs INSIDE the source system's security perimeter.
```

---

# 5. The 10 Responsibility Domains of a UIAO Adapter

A UIAO Adapter MUST implement all ten responsibility domains.
These domains are canonical and frozen.

---

## Domain 1 — API Structure

The adapter MUST implement the canonical API:

- `discover()`
- `pull_state(scope)`
- `pull_changes(since)`
- `normalize(raw)`
- `publish(claims)`
- `health()`

These operations define the adapter's lifecycle.

### **Figure 2 — Adapter API Lifecycle**
*(Text-box image description: A circular diagram showing discover → pull_state → normalize → publish → health → back to discover.)*

```text
+-----------+
| discover  |
+-----+-----+
      |
      v
+-----------+
| pull_state|
+-----+-----+
      |
      v
+-----------+
| normalize |
+-----+-----+
      |
      v
+-----------+
| publish   |
+-----+-----+
      |
      v
+-----------+
| health    |
+-----------+
```

---

## Domain 2 — Identity Requirements

Adapters MUST:

- Produce deterministic `uiao_id` values
- Preserve `local_id` values
- Map subjects to canonical identity/device/network schemas
- Maintain stable identity across runs

Identity mapping MUST be documented and deterministic.

---

## Domain 3 — Certs and Tokens

Adapters MUST:

- Authenticate to source systems using secure credentials
- Authenticate to UIAO truth fabric using mTLS or signed tokens
- Store credentials securely
- Rotate credentials according to policy

No plaintext credentials may appear in logs or claims.

---

## Domain 4 — Provenance Encoding

Adapters MUST attach provenance envelopes conforming to:
`/schemas/provenance.schema.json`

Provenance MUST include:

- `source_system`
- `source_adapter`
- `collected_at`
- `observed_at`
- `method`
- `evidence_pointer`

Provenance is mandatory for every canonical object.

---

## Domain 5 — Normalization & Canonicalization

Adapters MUST:

- Convert raw source data → canonical schemas
- Use declarative mapping rules where possible
- Validate canonical objects against JSON Schemas
- Enforce minimization (no raw logs, no unnecessary PII)

Normalization is the core semantic responsibility of the adapter.

---

## Domain 6 — Drift Detection

Adapters MUST detect:

- State transitions
- Value changes
- Conflicts with previous values
- Missing or withdrawn truth

Drift MUST be encoded using:
`/schemas/drift.schema.json`

Drift MUST include:

- `changed`
- `changed_at`
- `previous_value`
- `change_type`
- `severity`

### **Figure 3 — Drift Detection Flow**
*(Text-box image description: A diagram showing previous value and new value entering a comparator, producing a drift envelope.)*

```text
+------------------+     +------------------+     +----------------------+
| Previous Value   | --> | Drift Comparator | --> | Drift Envelope       |
+------------------+     +------------------+     | changed=true/false   |
                                                   | previous_value=...   |
+------------------+     +------------------+     | changed_at=timestamp |
| New Value        | --> | Drift Comparator |     +----------------------+
+------------------+     +------------------+
```

---

## Domain 7 — Confidence Scoring

Adapters SHOULD compute confidence scores when:

- Truth is inferred
- Evidence is partial
- Source system is degraded
- Identity mapping is uncertain

Confidence is a float between `0.0` and `1.0`.

---

## Domain 8 — Error Semantics & Recovery

Adapters MUST:

- Distinguish transient vs. permanent errors
- Retry transient errors with backoff
- Fail fast on permanent errors
- Quarantine malformed records
- Never publish invalid canonical objects

Errors MUST be surfaced via `health()`.

---

## Domain 9 — Publication Rules

Adapters MUST:

- Publish canonical claims
- Ensure idempotency
- Preserve ordering per entity
- Support batch or streaming modes
- Include provenance and drift

Publication MUST follow the canonical contract.

---

## Domain 10 — Security Controls

Adapters MUST:

- Run inside the source boundary
- Enforce minimization
- Restrict outbound connectivity
- Log security events
- Protect credentials
- Never export raw telemetry

Security is non-negotiable.

---

# 6. Adapter Lifecycle

The adapter lifecycle is deterministic:

1. Discover
2. Pull state
3. Normalize
4. Detect drift
5. Attach provenance
6. Publish claims
7. Emit telemetry
8. Report health
9. Repeat

### **Figure 4 — Adapter Lifecycle (Full)**
*(Text-box image description: A vertical flowchart showing each lifecycle stage from discover to repeat.)*

```text
+------------------+
| 1. discover      |
+------------------+
          |
          v
+------------------+
| 2. pull_state    |
+------------------+
          |
          v
+------------------+
| 3. normalize     |
+------------------+
          |
          v
+------------------+
| 4. drift detect  |
+------------------+
          |
          v
+------------------+
| 5. provenance    |
+------------------+
          |
          v
+------------------+
| 6. publish       |
+------------------+
          |
          v
+------------------+
| 7. telemetry     |
+------------------+
          |
          v
+------------------+
| 8. health        |
+------------------+
          |
          v
+------------------+
| 9. repeat        |
+------------------+
```

---

# 7. Adapter Governance

Adapters are subject to:

- Certification
- Recertification
- Drift audits
- Provenance audits
- Security audits
- Sector compliance

The Adapter Steward oversees certification.

---

# 8. Summary

A UIAO Adapter is:

- **Canonical**
- **Deterministic**
- **Provenance-first**
- **Drift-aware**
- **Boundary-safe**
- **Governance-aligned**

It is the semantic foundation of the UIAO truth fabric.

This document defines the canonical, frozen definition of what a UIAO Adapter is and MUST remain stable across all future versions of UIAO-Core.
