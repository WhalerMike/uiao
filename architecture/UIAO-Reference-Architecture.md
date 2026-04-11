# UIAO Reference Architecture Layer

## Overview

The UIAO Reference Architecture Layer is the canonical, enduring, system-of-record description of how UIAO works as a platform, a control plane, and a compliance engine. This is the source of truth for engineering, auditors, integrators, and analysts.

---

## 1. The UIAO Four-Plane Architecture (Canonical Model)

UIAO is built on four deterministic planes, each transforming inputs into outputs with no ambiguity.

### Plane 1 — Evidence Ingestion Plane

**Purpose:** Collect raw configuration evidence.
**Inputs:** SCuBA, M365, Azure AD, Defender, SaaS APIs.
**Outputs:** Raw evidence snapshots.
**Properties:** Immutable, timestamped, source-tagged, stored in Raw Zone.

### Plane 2 — Normalization + KSI Evaluation Plane

**Purpose:** Convert raw evidence to IR to KSI results.
**Inputs:** Raw evidence.
**Outputs:** Normalized IR, KSI evaluation results, Drift deltas.
**Properties:** Deterministic, schema-validated, control-mapped.

### Plane 3 — Evidence Bundle Plane

**Purpose:** Convert KSI results to Evidence Bundle.
**Inputs:** {source}.ksi.json
**Outputs:** {source}.evidence.json
**Properties:** Pure function, provenance-ready, OSCAL-compatible.

### Plane 4 — OSCAL Output Plane

**Purpose:** Convert Evidence Bundles to OSCAL SSP/SAP/SAR/POA&M.
**Inputs:** Evidence bundles.
**Outputs:** ssp.json, sap.json, sar.json, poam.json
**Properties:** Auditor-ready, machine-verifiable, provenance-linked.

---

## 2. The UIAO Data Model (Canonical)

UIAO's data model is four-layered:

### 2.1 IR (Information Representation)
- Normalized configuration facts
- Source-agnostic
- Deterministic schema
- Basis for KSI evaluation

### 2.2 KSI Results
- Control-mapped evaluation results
- PASS / WARN / FAIL
- Severity
- Details

### 2.3 Evidence Bundle
- Evidence items
- Hashes
- Provenance
- Source metadata
- Bundle metadata

### 2.4 OSCAL Artifacts
- SSP, SAP, SAR, POA&M

Each layer is strictly derived from the previous one.

---

## 3. The UIAO Control Model

### 3.1 Control Packs
- NIST/FedRAMP, CIS, Zero-trust identity, SaaS posture
- Each pack contains: Control definitions, KSI rules, Evidence requirements, OSCAL fragments

### 3.2 Control Mapping
Evidence to IR to KSI to Control. This mapping is deterministic, versioned, and provenance-backed.

### 3.3 Control Evaluation
KSI rules evaluate IR objects to produce PASS, WARN, or FAIL. Results feed: Drift Engine, POA&M Generator, Enforcement Runtime, OSCAL SAR.

---

## 4. The UIAO Enforcement Model

### 4.1 Enforcement Policies (EPL)

Declarative policies defining condition, action, evidence requirement.

Example:
    when LegacyAuthEnabled == true
    enforce conditional_access.disable("legacy_auth")

### 4.2 Enforcement Adapters

Adapters for: Conditional Access, DLP, Defender, SaaS APIs.
Properties: Least-privilege, tenant-scoped, logged, reversible.

### 4.3 Enforcement Runtime

Executes: Evaluate EPL, Detect violation, Execute adapter, Collect post-enforcement evidence, Update POA&M, Update OSCAL SAR.

---

## 5. The UIAO Evidence Lifecycle (Cradle-to-Grave)

1. **Collection** — Raw evidence collected, timestamped, stored in Raw Zone
2. **Normalization** — Converted to IR, schema-validated
3. **Evaluation** — KSI rules applied, results stored
4. **Bundling** — Evidence bundle created, hashes generated, provenance manifest created
5. **OSCAL Integration** — Evidence referenced in SSP/SAP/SAR/POA&M
6. **Drift Detection** — Evidence compared across snapshots
7. **Retention** — Evidence stored per tenant retention policy

This lifecycle is immutable, auditable, and machine-verifiable.

---

## 6. The UIAO System Diagram (Conceptual)

    +-----------------------------+
    |      Evidence Sources       |
    | SCuBA | M365 | AAD | SaaS   |
    +-----------------------------+
                  |
                  v
    +---------------------------------------------------------------+
    | Plane 1: Ingestion                                           |
    | Raw Evidence to Raw Zone (immutable)                         |
    +---------------------------------------------------------------+
                  |
                  v
    +---------------------------------------------------------------+
    | Plane 2: Normalization + KSI Evaluation                      |
    | Raw to IR to KSI Results to Drift Deltas                     |
    +---------------------------------------------------------------+
                  |
                  v
    +---------------------------------------------------------------+
    | Plane 3: Evidence Bundle Generation                          |
    | KSI Results to Evidence Bundle + Provenance                  |
    +---------------------------------------------------------------+
                  |
                  v
    +---------------------------------------------------------------+
    | Plane 4: OSCAL Output Generation                             |
    | Evidence to SSP/SAP/SAR/POA&M                                |
    +---------------------------------------------------------------+
                  |
         +--------+--------+
         v                 v
    +----------+    +-------------------+
    | Auditor  |    | Compliance        |
    | API      |    | Dashboard         |
    +----------+    +-------------------+

---

## Summary

The UIAO Reference Architecture Layer establishes:

1. **Four-Plane Architecture** — Ingestion, Normalization/KSI, Evidence Bundle, OSCAL Output
2. **Data Model** — IR, KSI Results, Evidence Bundle, OSCAL Artifacts (four strictly-derived layers)
3. **Control Model** — Control Packs, Control Mapping, Control Evaluation
4. **Enforcement Model** — EPL Policies, Enforcement Adapters, Enforcement Runtime
5. **Evidence Lifecycle** — Collection through Retention (7 stages, immutable and auditable)
6. **System Diagram** — Canonical conceptual architecture diagram

This is the source of truth for engineering, auditors, integrators, analysts, documentation, product marketing, and category evangelism.
