---
id: uiao-governance-green-book
title: "UIAO Governance OS Green Book"
owner: governance-board
status: DRAFT
---

# UIAO Governance OS Green Book

## Schema Standards - Metadata Standards - Normalization Standards

The Green Book defines the canonical standards for schema, metadata, and corpus normalization across UIAO.

---

## 1. Purpose

To establish:

- Canonical schema rules
- Metadata field standards
- Normalization requirements
- Schema evolution rules
- Metadata quality thresholds

---

## 2. Canonical Schema Standards

### 2.1 Required Fields

Every governance document must contain:

- id
- owner
- appendix
- status
- classification
- description
- schemaVersion

### 2.2 Field Ordering

Fields must appear in canonical order:

1. Metadata identity (id, title)
2. Ownership (owner, appendix)
3. Classification (status, classification)
4. Description
5. Schema metadata (schemaVersion)
6. Operational metadata (created, updated)

### 2.3 Deprecated Fields

- Deprecated fields must be removed within one schema version cycle
- CI validator must flag deprecated fields on every commit
- Normalization engine must auto-remove deprecated fields for Low severity violations

---

## 3. Metadata Standards

### 3.1 Status Values

Canonical status values are:

- current: document is active and in good standing
- at-risk: document has open drift or SLA concerns
- deprecated: document is scheduled for removal
- archived: document is retained for historical reference only

### 3.2 Classification Values

Canonical classification values are:

- core: foundational document required by governance charter
- supporting: document that augments a core artifact
- auxiliary: supplemental reference, not required for governance operations

### 3.3 Description Standards

- Must be written in complete sentences
- Must be provenance-aligned (references canonical terms only)
- Must be accurate to document content at time of commit

---

## 4. Normalization Standards

### 4.1 Structural Normalization

- All required fields must be present
- All deprecated fields must be removed
- Canonical field ordering must be enforced

### 4.2 Referential Normalization

- All cross-document ID references must resolve
- No orphan references permitted
- All referenced documents must exist in the corpus

### 4.3 Ownership Normalization

- Owner must be an active, recognized domain steward
- Owner must be the correct steward for the document's domain
- Inactive owners trigger reassignment workflow

### 4.4 Semantic Normalization

- Status values must be from the canonical set
- Classification values must be from the canonical set
- Descriptions must not reference deprecated or non-canonical terms

---

## 5. Schema Evolution Rules

### 5.1 Versioning

- UIAO uses semantic versioning (MAJOR.MINOR.PATCH)
- Breaking changes require a migration plan before rollout
- Non-breaking additions require schema steward approval

### 5.2 Evolution Workflow

    Propose -> Simulate -> Validate -> Approve -> Rollout

Each stage requires sign-off from the schema steward. The Schema Evolution Simulator must be run before Approve.

### 5.3 Schema Divergence Threshold

- Schema divergence must remain below 1%
- Divergence above 1% triggers the normalization enforcement engine
- Divergence above 5% triggers a governance intervention

---

## 6. Metadata Quality Thresholds

| Index | Minimum Required |
|-------|-----------------|
| Metadata Quality Score (MQS) | 90 |
| Drift-Resilience Index (DG-RI) | 75 |
| Metadata Governance Reliability Index (MG-RI) | 80 |

Any index below its threshold triggers a remediation workflow.

---

## 7. Normalization Enforcement

| Severity | Condition | Action |
|----------|-----------|--------|
| Low | Single field error, auto-correctable | Automated fix committed |
| Medium | Cross-document impact | Remediation PR opened |
| High | Owner reassignment or governance vote required | Governance intervention triggered |
| Critical | Corpus-wide schema failure | Merge freeze declared |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
