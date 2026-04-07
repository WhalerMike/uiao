---
title: Governance Metadata Reviewer Checklist
uiao_id: UIAO_META_REVIEW_01
status: Current
owner: Governance Board
tags: [governance, metadata, review]
date: 2026-04-07
---

# Governance Metadata Reviewer Checklist

Reviewers must confirm all items below before approving a PR.

---

## 1. Identity & Provenance

- [ ] `uiao.id` exists and matches `UIAO_<AppendixLetter>_<Number>`
- [ ] ID is **immutable** (unchanged from previous version)
- [ ] `uiao.created` is unchanged
- [ ] `uiao.lastUpdated` is updated for this PR
- [ ] `uiao.commit` placeholder present (CI will populate)
- [ ] Status badge present in top 8 lines

---

## 2. Status & Ownership

- [ ] `uiao.status` is one of: `Current` / `Draft` / `Needs Replacing` / `Needs Creating` / `Deprecated`
- [ ] Status accurately reflects document maturity
- [ ] `uiao.owner` is a team or role, not an individual
- [ ] Ownership is correct for the appendix or governance area

---

## 3. Tags & Fabric Alignment

- [ ] `uiao.tags` present and non-empty
- [ ] Tags correctly reflect cross-fabric domain
- [ ] `fabric` field (if present) matches primary domain

---

## 4. Summary & Title

- [ ] `summary` exists and is 1-3 sentences
- [ ] `title` matches the H1 heading
- [ ] Document purpose is clear and aligned with canon

---

## 5. ADR-Specific (if ADR)

- [ ] `id` matches `ADR-<number>`
- [ ] `status` is valid (`Proposed` / `Accepted` / `Superseded` / `Deprecated` / `Replaced`)
- [ ] `date` is ISO-correct
- [ ] `deciders` present
- [ ] `affects` contains valid UIAO ids
- [ ] `supersedes` / `supersededBy` correct if present

---

## 6. Cross-Fabric Integrity

- [ ] Document does not contradict other fabrics
- [ ] Cross-references updated if needed
- [ ] ADR impacts reflected in affected documents
- [ ] No references to deprecated or superseded documents

---

## 7. Governance & Drift Resistance

- [ ] No references to previous versions
- [ ] No duplicated content across appendices
- [ ] No ambiguous ownership
- [ ] No missing metadata fields
- [ ] Document follows canonical structure

---

## 8. Final Checks

- [ ] CI metadata validator passes
- [ ] Links validated
- [ ] Diagrams include alt text
- [ ] Document renders correctly in site preview

---

> If any item fails, the PR must not be approved.

## See Also

- [Governance Metadata Playbook](governance-metadata-playbook.md)
- [UIAO Document Metadata Contract](uiao-document-metadata-contract.md)
- [UIAO ADR Metadata Contract](uiao-adr-metadata-contract.md)
