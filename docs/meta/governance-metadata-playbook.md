---
title: UIAO Governance Metadata Playbook
uiao_id: UIAO_META_PLAYBOOK_01
status: Current
owner: Governance Board
tags: [governance, metadata, provenance, contract]
date: 2026-04-07
---

# UIAO Governance Metadata Playbook

> A practical, operator-ready guide explaining how UIAO metadata works, why it exists,
> and how contributors must use it to maintain a drift-free, provenance-correct documentation corpus.

## 1. Purpose of This Playbook

UIAO is a governance-first system. Metadata is not decoration -- it is the control plane for:
provenance, drift detection, cross-fabric relationships, document lifecycle, dashboard population,
ADR impact analysis, contributor workflows, and auditability.

This playbook explains: what metadata is required, why it exists, how it is validated,
how it flows through the system, and how contributors must work with it.

This is the human-readable companion to:

- [UIAO Document Metadata Contract](uiao-document-metadata-contract.md)
- [UIAO ADR Metadata Contract](uiao-adr-metadata-contract.md)
- [ADR Metadata Reviewer Checklist](governance-metadata-reviewer-checklist.md)

## 2. The Metadata Model: Three Layers

### Layer 1 -- Human-Readable Metadata (Frontmatter)

This is what contributors edit: `title`, `summary`, `uiao.id`, `uiao.status`, `uiao.owner`,
`uiao.tags`, `uiao.created`, `uiao.lastUpdated`, `uiao.commit`, and ADR-only fields.
This layer is authoritative for humans.

### Layer 2 -- Machine-Readable Metadata (JSON Schema)

This is what CI validates: required fields, allowed enum values, ID patterns, date formats,
non-empty tags, and ADR references to valid UIAO documents.
This layer is authoritative for machines.

### Layer 3 -- Derived Metadata (Dashboards & Indexes)

Generated automatically: `corpus-index.json`, dashboard tables, cross-fabric impact maps,
and governance footer provenance. This layer is authoritative for reporting.

## 3. The Five Metadata Responsibilities

### Responsibility 1 -- Every Document Must Have a Canonical ID

Pattern: `UIAO_<AppendixLetter>_<Number>`

| Example | Scope |
|---------|-------|
| `UIAO_A_01` | Appendix A document |
| `UIAO_E_03` | Governance Plane document |
| `UIAO_META_DOC_01` | Meta document |
| `UIAO_ADR_012` | ADR document |

IDs are immutable once assigned.

### Responsibility 2 -- Every Document Must Declare Its Status

Allowed values: `Current`, `Draft`, `Needs Replacing`, `Needs Creating`, `Deprecated`.

Status drives: dashboard alerts, governance banner health, review prioritization,
and cross-fabric risk analysis.

### Responsibility 3 -- Every Document Must Declare Its Owner

Owners are accountable for correctness, updates, cross-fabric alignment, and
responding to ADR impacts. Owners must be roles or teams, not individuals.

### Responsibility 4 -- Every Document Must Declare Its Tags

Tags enable cross-fabric queries, dashboard filtering, ADR impact analysis,
and governance plane reporting.

Allowed tags: `identity`, `drift`, `evidence`, `adapter`, `governance`, `meta`,
`architecture`, `operations`, `compliance`.

### Responsibility 5 -- Every Document Must Declare Provenance

Provenance includes `uiao.created`, `uiao.lastUpdated`, and `uiao.commit`.
The commit hash is updated automatically by CI on merge.

## 4. Metadata Flow Through the System

| Step | Actor | Action |
|------|-------|--------|
| 1 | Contributor | Writes frontmatter (`title`, `summary`, `uiao` block) |
| 2 | CI | Validates required fields, allowed values, ID patterns |
| 3 | CI (on merge) | Updates `corpus-index.json`, dashboard, provenance footer |
| 4 | MkDocs build | Renders dashboard tables, ADR index, governance footer |
| 5 | Governance | Metadata powers drift detection, cross-fabric analysis, audit trails |

## 5. Contributor Workflow (Metadata-Focused)

**Before editing:** Check dashboard for document status. Check ADR index for impacts.
Confirm correct `uiao.id` and ownership.

**While editing:** Update `summary` and `uiao.lastUpdated`. Do not change `uiao.created`
or `uiao.id`. Add or update tags. Ensure status badge is correct.

**Before opening PR:** Ensure frontmatter matches contract. Ensure ADRs reference valid UIAO ids.

**During review:** Reviewers check metadata correctness, cross-fabric impacts, ADR implications,
ownership correctness, and status accuracy.

**After merge:** CI updates commit hash, dashboard, and provenance footer.
Contributor verifies dashboard entry and notifies owners if cross-fabric impact exists.

## 6. Metadata Anti-Patterns (Prohibited)

These are merge blockers:

- Missing `uiao.id`
- Duplicate IDs
- Missing tags or owner
- Missing summary
- Incorrect status or date formats
- Missing provenance
- ADRs without `affects`
- Documents without status badges
- Documents referencing deprecated IDs

## 7. Governance Rules for Metadata Evolution

Metadata contracts may only be changed via ADR (structural changes) or Governance Plane
decision (operational changes). All changes must be backward compatible, include migration
scripts, CI updates, and dashboard updates.

## 8. Metadata Quick Reference

**Required for all documents:** `title`, `summary`, `uiao.id`, `uiao.status`, `uiao.owner`,
`uiao.tags`, `uiao.created`, `uiao.lastUpdated`, `uiao.commit`.

**Required for ADRs additionally:** `id`, `status`, `date`, `deciders`, `tags`, `affects`,
`summary`, `uiao` block.

## 9. Closing Principle

> **Metadata is governance.**
> It is the mechanism by which UIAO maintains correctness, provenance, sovereignty,
> auditability, drift resistance, and cross-fabric integrity.

## See Also

- [UIAO Document Metadata Contract](uiao-document-metadata-contract.md)
- [UIAO ADR Metadata Contract](uiao-adr-metadata-contract.md)
- [Governance Metadata Reviewer Checklist](governance-metadata-reviewer-checklist.md)
- [Metadata Drift Detection Report](metadata-drift-detection-report.md)
