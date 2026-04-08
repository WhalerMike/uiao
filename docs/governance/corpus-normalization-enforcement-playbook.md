---
id: corpus-normalization-enforcement-playbook
title: Governance Corpus Normalization Enforcement Playbook
owner: governance-steward
status: DRAFT
---

# UIAO Governance Corpus Normalization Enforcement Playbook

## Canonical Procedures for Enforcing Metadata Consistency and Schema Alignment

This playbook defines how governance stewards enforce normalization across the corpus.

---

## 1. Enforcement Triggers

- Schema divergence > 1%
- Drift velocity spike
- Deprecated field reappearance
- Owner inconsistency
- Reference integrity failures
- Automation misalignment

---

## 2. Enforcement Workflow

### Step 1 - Detect Violations

- Structural
- Referential
- Ownership
- Semantic
- Schema
- Automation

### Step 2 - Classify Severity

- Low: auto-fix
- Medium: remediation PR
- High: governance intervention
- Critical: freeze merges

### Step 3 - Apply Enforcement Controls

#### Structural

- Fix required fields
- Remove deprecated fields
- Normalize ordering

#### Referential

- Validate IDs
- Repair references

#### Ownership

- Reassign inactive owners
- Validate owner correctness

#### Semantic

- Normalize status/classification
- Update descriptions

#### Schema

- Enforce schema version
- Remove deprecated fields

#### Automation

- Patch CI validator
- Patch workflows
- Patch webhook handler

### Step 4 - Verify Enforcement

- CI validator passes
- Dashboard updated
- Drift resolved
- SLA closed

### Step 5 - Prevent Recurrence

- Update schema
- Update CI validator
- Update workflows
- Update governance charter
