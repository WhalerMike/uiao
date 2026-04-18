---
title: "Adapter-Responsibilities-Diagram-Set"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Adapter Responsibilities Diagram Set
**UIAO Adapter Suite — Document 2 of 4**
**Version 1.0.0 — Canonical, Frozen**

This document provides the **complete diagram suite** for the UIAO Adapter Layer.
Each diagram is accompanied by a **text-box image description** to ensure accessibility and canonical clarity.

The diagrams illustrate:

- The adapter's position in the UIAO ecosystem
- The 10 responsibility domains
- The adapter lifecycle
- Provenance and drift flows
- Publication and boundary rules
- Governance relationships

These diagrams are **normative** and MUST be used in all adapter documentation, training, and certification materials.

---

# 1. Adapter in the UIAO Architecture

### **Figure 1 — Adapter Position in UIAO Architecture**
*(Text-box image description: A three-box horizontal diagram. Left: Source System. Middle: Adapter inside boundary. Right: UIAO Truth Fabric outside boundary. Arrows show raw data flowing left→middle and canonical claims flowing middle→right.)*

```text
+-----------------------+        +-----------------------+        +-----------------------+
|    Source System      |        |     UIAO Adapter      |        |   UIAO Truth Fabric   |
| (Vendor-native APIs,  | -----> | (Normalize, Drift,    | -----> | (Merge, Reconcile,    |
|  DBs, Logs, Events)   | Raw    |  Provenance, Publish) | Claims |  Federate, Govern)    |
+-----------------------+        +-----------------------+        +-----------------------+

Boundary: Adapter runs INSIDE the source system's security perimeter.
```

---

# 2. The 10 Responsibility Domains (Diagram Set)

Each responsibility domain is illustrated with a canonical diagram.

---

## Domain 1 — API Structure

### **Figure 2 — Adapter API Structure**
*(Text-box image description: A vertical list of API methods with arrows showing the flow from discover → pull_state → normalize → publish → health.)*

```text
+------------------+
| discover()       |
+------------------+
         |
         v
+------------------+
| pull_state()     |
+------------------+
         |
         v
+------------------+
| pull_changes()   |
+------------------+
         |
         v
+------------------+
| normalize()      |
+------------------+
         |
         v
+------------------+
| publish()        |
+------------------+
         |
         v
+------------------+
| health()         |
+------------------+
```

---

## Domain 2 — Identity Requirements

### **Figure 3 — Identity Mapping Flow**
*(Text-box image description: Raw identity object enters a mapping engine, producing uiao_id + local_id + canonical identity object.)*

```text
+--------------------+     +-----------------------+     +---------------------------+
| Raw Identity Data  | --> | Identity Mapping      | --> | Canonical Identity Object |
| (Vendor-native)    |     | (Deterministic Rules) |     | (uiao_id, local_id, etc.) |
+--------------------+     +-----------------------+     +---------------------------+
```

---

## Domain 3 — Certs and Tokens

### **Figure 4 — Credential Flow**
*(Text-box image description: Adapter authenticates to source system using secure credentials and to UIAO using mTLS/tokens.)*

```text
+------------------+     +------------------+     +------------------------+
| Source System    | <-- | Adapter          | --> | UIAO Truth Fabric      |
| (Auth Required)  | mTLS| (Secure Storage) | mTLS| (Auth Required)        |
+------------------+     +------------------+     +------------------------+
```

---

## Domain 4 — Provenance Encoding

### **Figure 5 — Provenance Envelope Injection**
*(Text-box image description: Canonical object enters a provenance injector, producing a canonical object with provenance.)*

```text
+---------------------------+
| Canonical Object (Raw)    |
+-------------+-------------+
              |
              v
+---------------------------+
| Provenance Injector       |
| (source_system, adapter,  |
|  collected_at, pointer)   |
+-------------+-------------+
              |
              v
+---------------------------+
| Canonical Object +        |
| Provenance Envelope       |
+---------------------------+
```

---

## Domain 5 — Normalization & Canonicalization

### **Figure 6 — Normalization Pipeline**
*(Text-box image description: Raw vendor data flows through mapping, enum translation, schema validation, and emerges as canonical object.)*

```text
+------------------+
| Raw Vendor Data  |
+---------+--------+
          |
          v
+------------------+
| Field Mapping    |
+---------+--------+
          |
          v
+------------------+
| Enum Translation |
+---------+--------+
          |
          v
+------------------+
| Schema Validation|
+---------+--------+
          |
          v
+---------------------------+
| Canonical UIAO Object     |
+---------------------------+
```

---

## Domain 6 — Drift Detection

### **Figure 7 — Drift Comparator**
*(Text-box image description: Previous value and new value enter a comparator, producing a drift envelope.)*

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

### **Figure 8 — Confidence Aggregation**
*(Text-box image description: Evidence quality, source reliability, and mapping certainty feed into a scoring engine.)*

```text
+------------------+     +------------------+
| Evidence Quality | --->|                  |
+------------------+     |                  |
                         | Confidence Engine| ---> confidence: 0.0–1.0
+------------------+     |                  |
| Source Reliability| --->|                  |
+------------------+     +------------------+

+------------------+
| Mapping Certainty|
+------------------+
```

---

## Domain 8 — Error Semantics & Recovery

### **Figure 9 — Error Handling Flow**
*(Text-box image description: Errors classified into transient/permanent/data, each with different handling paths.)*

```text
+------------------+
| Error Occurs     |
+---------+--------+
          |
          v
+------------------+     +------------------+     +------------------+
| Transient Error  | --> | Retry w/Backoff  | --> | Continue         |
+------------------+     +------------------+     +------------------+

+------------------+     +------------------+     +------------------+
| Permanent Error  | --> | Fail Fast        | --> | Report via health|
+------------------+     +------------------+     +------------------+

+------------------+     +------------------+     +------------------+
| Data Error       | --> | Quarantine       | --> | Continue         |
+------------------+     +------------------+     +------------------+
```

---

## Domain 9 — Publication Rules

### **Figure 10 — Claim Publication Flow**
*(Text-box image description: Canonical object enters a publisher, which sends claims to the truth fabric with ordering and idempotency guarantees.)*

```text
+---------------------------+
| Canonical Object +        |
| Provenance + Drift        |
+-------------+-------------+
              |
              v
+---------------------------+
| Claim Publisher           |
| (Idempotent, Ordered)     |
+-------------+-------------+
              |
              v
+---------------------------+
| UIAO Truth Fabric         |
+---------------------------+
```

---

## Domain 10 — Security Controls

### **Figure 11 — Boundary Enforcement**
*(Text-box image description: Adapter inside boundary, truth fabric outside boundary, with strict outbound-only canonical claim flow.)*

```text
Inside Boundary                            Outside Boundary
+------------------+                       +----------------------+
| Source System    |                       | UIAO Truth Fabric    |
| (Raw Data)       |                       | (Canonical Claims)   |
+--------+---------+                       +----------+-----------+
         | Raw Data                                    ^
         v                                            |
+------------------+                                  |
| UIAO Adapter     |----------------------------------+
| (Normalize Only) |  Canonical Claims Only (No Raw Data)
+------------------+
```

---

# 3. Adapter Lifecycle (Full Diagram)

### **Figure 12 — Full Adapter Lifecycle**
*(Text-box image description: A vertical flowchart showing the nine lifecycle stages from discover to repeat.)*

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
| 3. pull_changes  |
+------------------+
          |
          v
+------------------+
| 4. normalize     |
+------------------+
          |
          v
+------------------+
| 5. drift detect  |
+------------------+
          |
          v
+------------------+
| 6. provenance    |
+------------------+
          |
          v
+------------------+
| 7. publish       |
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

# 4. Adapter–Governance Relationship

### **Figure 13 — Governance Oversight of Adapters**
*(Text-box image description: Adapter at bottom, Adapter Steward above it, Federated Council and Privacy Board above that.)*

```text
+------------------------+
| Federated Council      |
+-----------+------------+
            |
            v
+------------------------+
| Privacy Board          |
+-----------+------------+
            |
            v
+------------------------+
| Adapter Steward        |
+-----------+------------+
            |
            v
+------------------------+
| UIAO Adapter           |
+------------------------+
```

---

# 5. Summary

This diagram suite is the **canonical visual reference** for all UIAO Adapter documentation.
It MUST be used in:

- Adapter authoring
- Certification
- Governance review
- Training
- Sector onboarding
- Vendor integration

This document is **frozen** and forms part of the UIAO Adapter Suite.
