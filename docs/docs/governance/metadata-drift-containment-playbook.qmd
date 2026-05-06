---
id: metadata-drift-containment-playbook
title: Metadata Drift Containment Playbook
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Drift Containment Playbook

## Canonical Actions for Stopping Drift Spread Across the Corpus

This playbook defines the containment strategy for preventing local drift from escalating into systemic drift.

---

## 1. Containment Triggers

- Drift cluster forming within 7 days
- Same CI signature across multiple documents
- SLA pressure rising across multiple owners
- Schema divergence > 5%
- Automation anomalies detected

---

## 2. Containment Workflow

### Step 1 - Isolate the Drift

- Freeze related PRs
- Flag affected documents
- Notify owners

### Step 2 - Identify Drift Type

- Structural
- Referential
- Ownership
- Semantic
- Automation

### Step 3 - Apply Containment Controls

#### Structural

- Enforce schema validation
- Patch CI validator

#### Referential

- Validate all IDs
- Repair cross-appendix references

#### Ownership

- Reassign inactive owners
- Require owner training

#### Semantic

- Correct status/classification
- Update documentation

#### Automation

- Patch webhook handler
- Patch workflow logic

### Step 4 - Verify Containment

- Drift cluster dissolves
- SLA pressure decreases
- Dashboard stabilizes

### Step 5 - Prevent Recurrence

- Update schema
- Update CI validator
- Update workflows
- Update governance charter if needed

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
