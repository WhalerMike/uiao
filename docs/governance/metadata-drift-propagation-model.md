---
id: metadata-drift-propagation-model
title: Metadata Drift Propagation Model
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Drift Propagation Model

## Modeling How Drift Spreads Across Documents, Owners, and Appendices

This model predicts how metadata drift propagates through the corpus based on structural, referential, and systemic dependencies.

---

## 1. Purpose

To understand and forecast how drift spreads, enabling proactive governance intervention.

---

## 2. Drift Propagation Factors

### A. Structural Coupling (SC)

Degree to which documents share schema-dependent fields.

### B. Referential Coupling (RC)

Degree to which documents reference each other.

### C. Ownership Coupling (OC)

Degree to which the same owner maintains multiple documents.

### D. Automation Coupling (AC)

Degree to which CI, workflows, and webhook logic affect multiple documents.

---

## 3. Propagation Probability Formula

P_propagation = 1 - (1 - SC)(1 - RC)(1 - OC)(1 - AC)

Where each factor is normalized 0-1.

---

## 4. Propagation Stages

### Stage 1 - Local Drift

- Single document
- Single owner
- No cross-appendix impact

### Stage 2 - Cluster Drift

- Multiple documents
- Same appendix
- Same owner or same schema version

### Stage 3 - Systemic Drift

- Multiple appendices
- Multiple owners
- Shared CI error signature

### Stage 4 - Corpus-Wide Drift

- Schema divergence
- Automation drift
- SLA system stress

---

## 5. Governance Actions by Stage

### Local

- Owner remediation

### Cluster

- Schema review
- CI validator update

### Systemic

- Workflow update
- Owner reassignment
- Governance intervention

### Corpus-Wide

- Freeze merges
- Full runtime audit
- Executive notification

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
