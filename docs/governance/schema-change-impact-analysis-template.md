---
id: schema-change-impact-analysis-template
title: Metadata Schema Change Impact Analysis Template
owner: governance-steward
status: DRAFT
---

# UIAO Metadata Schema Change Impact Analysis Template

## Required Assessment Before Any Schema Modification

This template ensures schema changes are evaluated for risk, compatibility, and governance impact.

---

## 1. Change Summary

- Proposed change:
- Category (Additive / Transitional / Breaking):
- Schema version impact:
- Proposed effective date:

---

## 2. Rationale

- Why is this change needed?
- What problem does it solve?
- What governance principle does it support?

---

## 3. Impact Assessment

### A. Metadata Impact

- Required fields affected:
- Deprecated fields affected:
- Field ordering impact:
- YAML structure impact:

### B. Document Impact

- Number of documents affected:
- Appendices affected:
- Migration required (Yes/No):

### C. Owner Impact

- Owner training required:
- Ownership changes required:

### D. Automation Impact

- CI validator updates required:
- Webhook handler updates required:
- Dashboard updates required:
- Workflow updates required:

### E. Runtime Impact

- PostgreSQL schema impact:
- API contract impact:

---

## 4. Risk Assessment

### Risk Level (Low / Medium / High / Critical)

- Drift risk:
- SLA risk:
- Automation risk:
- Systemic drift risk:

---

## 5. Migration Plan

- Required steps:
- Automated migration (Yes/No):
- Manual remediation required:
- Timeline:

---

## 6. Testing Plan

- CI validator tests:
- Schema validation tests:
- Dashboard tests:
- Workflow tests:

---

## 7. Communication Plan

- Owner notification:
- Maintainer notification:
- Governance announcement:

---

## 8. Approval

- Governance steward approval:
- Maintainer approval:
- Effective date:

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
