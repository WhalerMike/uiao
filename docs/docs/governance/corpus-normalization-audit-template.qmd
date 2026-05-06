---
id: corpus-normalization-audit-template
title: Governance Corpus Normalization Audit Template
owner: governance-steward
status: DRAFT
---

# UIAO Governance Corpus Normalization Audit Template

## Quarterly Audit Template for Ensuring Metadata Consistency and Schema Alignment

This template ensures the corpus remains normalized, drift-resistant, and aligned with the canonical schema.

---

## 1. Audit Metadata

- Audit date:
- Auditor:
- Corpus version:
- Schema version:

---

## 2. Structural Normalization

- [ ] Required fields present
- [ ] Deprecated fields removed
- [ ] Field ordering correct
- [ ] YAML formatting valid
- Violations:
- Notes:

---

## 3. Referential Normalization

- [ ] All IDs valid
- [ ] All references resolve
- [ ] Cross-appendix links correct
- Violations:
- Notes:

---

## 4. Ownership Normalization

- [ ] Owner field populated
- [ ] Owner active
- [ ] Ownership correct
- Violations:
- Notes:

---

## 5. Semantic Normalization

- [ ] Status values correct
- [ ] Classification fields correct
- [ ] Descriptions accurate
- Violations:
- Notes:

---

## 6. Schema Alignment

- [ ] Schema version correct
- [ ] No schema drift
- [ ] No undocumented fields
- Violations:
- Notes:

---

## 7. Automation Alignment

- [ ] CI validator aligned
- [ ] Workflow aligned
- [ ] Webhook aligned
- [ ] Dashboard aligned
- Violations:
- Notes:

---

## 8. Integrity Score

IntegrityScore = 100 - (Violations * SeverityWeight)

- Score:
- Classification: Excellent / Strong / Moderate / At Risk / Critical

---

## 9. Corrective Actions

- Required fixes:
- Owners involved:
- Automation updates:
- Schema updates:
- Timeline:

---

## 10. Sign-Off

- Auditor:
- Governance steward:
- Maintainer:

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
