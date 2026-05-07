---
id: drift-root-cause-analysis-template
title: Metadata Drift Root-Cause Analysis Template
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Drift Root-Cause Analysis (RCA) Template

## Required for Critical Drift, Repeated Drift, or Systemic Drift Events

This template ensures drift causes are identified, corrected, and prevented.

---

## 1. Drift Summary

- Drift issue link:
- Severity:
- Appendix:
- Owner:
- Date detected:
- Detection source (CI / workflow / manual):

---

## 2. Drift Description

- What drift occurred?
- Which metadata fields were affected?
- What schema rules were violated?

---

## 3. Impact Assessment

- Number of documents affected:
- Downstream impact:
- SLA impact:
- Automation impact:
- Governance impact:

---

## 4. Root-Cause Analysis

### A. Structural Cause

- Missing fields?
- Deprecated fields?
- YAML formatting?

### B. Referential Cause

- Broken references?
- Incorrect IDs?

### C. Ownership Cause

- Incorrect owner?
- Owner untrained or unavailable?

### D. Semantic Cause

- Incorrect status?
- Outdated classification?

### E. Automation Cause

- CI validator outdated?
- Workflow failure?
- Webhook mislabeling?

---

## 5. Contributing Factors

- Schema ambiguity
- Owner turnover
- Lack of training
- Automation drift
- Process gaps

---

## 6. Corrective Actions

- Metadata fixes
- Schema updates
- CI validator updates
- Workflow updates
- Owner training
- Governance intervention

---

## 7. Preventive Actions

- Documentation updates
- Automation enhancements
- Governance cadence adjustments
- Owner reassignment

---

## 8. Verification

- CI validator passes
- Dashboard updated
- Drift cleared
- SLA closed

---

## 9. Sign-Off

- Owner:
- Maintainer:
- Governance steward:

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
