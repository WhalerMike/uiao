---
title: "UIAO Documentation Migration Plan"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# UIAO Documentation Migration Plan

## Overview

This document describes the migration of UIAO governance documentation from a flat, ad-hoc directory structure to the hierarchical canonical structure defined by the Canon and enforced by `Initialize-UIAOCanonStructure.ps1`.

The migration has two phases:

- **Phase 1 — Structural Migration:** Scaffold the canonical directory structure in `uiao-docs` and stub all required files.
- **Phase 2 — Content Migration:** Populate stub files with authoritative content sourced from the Canon DOCX, ratified by the Governance Plane.

Phase 1 is complete as of April 2026. Phase 2 is ongoing.

---

## Phase 1 — Structural Migration (Complete)

### Goals
- Establish the canonical directory hierarchy under `docs/`
- Create stub files for all 18 appendices, 23 ADRs, and 5 canon documents
- Validate that mkdocs.yml nav reflects the canonical structure
- Commit PlantUML diagram sources for all 6 architecture diagrams
- Establish the Canon Pointer in `uiao-core`

### Deliverables
All deliverables below were completed and committed to `uiao-docs/main` and `uiao-core/main` between January and April 2026.

| Deliverable | Repository | Status |
|---|---|---|
| `Initialize-UIAOCanonStructure.ps1` | uiao-docs/scripts/ | ✅ Complete |
| Canonical directory structure (9 dirs, 70 files) | uiao-docs/docs/ | ✅ Complete |
| `diagrams/*.puml` (6 PlantUML sources) | uiao-docs/diagrams/ | ✅ Complete |
| `mkdocs.yml` hierarchical nav | uiao-docs/ | ✅ Complete |
| `docs/CANON_POINTER.md` | uiao-core/docs/ | ✅ Complete |
| `.gitignore` patterns for stray files | uiao-docs/ | ✅ Complete |

---

## Phase 2 — Content Migration (In Progress)

### Goals
- Replace all `status: MISSING` stubs with authoritative content from the Canon DOCX
- Achieve `status: DRAFT` for all files
- Submit all content for Governance Plane ratification
- Achieve `status: ACTIVE` for all ratified files

### Canon Documents (5 files)

| File | Target Status | Ratification Required |
|---|---|---|
| `uiao-core/canon/canonical-rules.md` | MIGRATED to uiao-core (Phase D, 2026-04-16) | — |
| `docs/canon/glossary.md` | ACTIVE | Governance Board sign-off |
| `docs/canon/migration-plan.md` | ACTIVE | Governance Board sign-off |
| `docs/canon/pdf-layout-spec.md` | ACTIVE | Governance Board sign-off |
| `docs/canon/index.md` | ACTIVE | Governance Board sign-off |

### Appendix Files (18 files)

| Appendix | Title | Target Status |
|---|---|---|
| A-01 | Adapter Registration Protocol | DRAFT → ACTIVE |
| A-02 | Adapter Schema Standard | DRAFT → ACTIVE |
| A-03 | Adapter Lifecycle Management | DRAFT → ACTIVE |
| A-04 | Adapter Plane Index | DRAFT → ACTIVE |
| B-01 | Truth Fabric Architecture | DRAFT → ACTIVE |
| B-02 | Canonical State Model | DRAFT → ACTIVE |
| B-03 | Truth Fabric Query API | DRAFT → ACTIVE |
| B-04 | Truth Fabric Index | DRAFT → ACTIVE |
| C-01 | Drift Detection Algorithm | DRAFT → ACTIVE |
| C-02 | Drift Reconciliation Protocol | DRAFT → ACTIVE |
| C-03 | Drift Fabric Index | DRAFT → ACTIVE |
| D-01 | Evidence Record Schema | DRAFT → ACTIVE |
| D-02 | Audit Event Taxonomy | DRAFT → ACTIVE |
| D-03 | Compliance Attestation Process | DRAFT → ACTIVE |
| D-04 | Evidence Fabric Index | DRAFT → ACTIVE |
| E-01 | Governance Review Process | DRAFT → ACTIVE |
| E-02 | Canon Change Protocol | DRAFT → ACTIVE |
| E-03 | Governance Plane Index | DRAFT → ACTIVE |

### ADR Files (23 files)

ADR-005 through ADR-027 — all require content population from the Canon DOCX and Governance Board acceptance.

---

## Migration Constraints

The following constraints apply to Phase 2 content migration:

1. **Canon DOCX is authoritative.** All content MUST be traceable to a specific section of the Canon DOCX per CR-002.

2. **No speculative content.** Content labeled `[NEW (Proposed)]` is acceptable for structural completeness but MUST be flagged for ratification. It MUST NOT be promoted to `status: ACTIVE` without explicit Governance Board sign-off.

3. **ADR immutability applies immediately.** Once an ADR is set to `status: ACCEPTED`, CR-003 applies and the Decision field is immutable.

4. **Machine artifacts stay in uiao-core.** Any content discovered during migration that is a machine artifact (schema, algorithm, manifest) MUST be routed to `uiao-core`, not committed to `uiao-docs`.

---

## Rollback Plan

If Phase 2 migration introduces errors:

1. Revert the offending commit(s) on `uiao-docs/main` using `git revert`
2. Re-stub the affected files using `Initialize-UIAOCanonStructure.ps1 -TargetFiles` (selective mode)
3. File an ADR documenting the rollback event and root cause
4. Resume migration after root cause is resolved

---

## Completion Criteria

Phase 2 is complete when:
- All 46 stub files have `status: ACTIVE`
- All ADRs have `status: ACCEPTED`
- The Canon DOCX has been reviewed and a final ratification commit is made to `docs/canon/`
- MkDocs site builds without errors and all nav links resolve
- Governance Board has formally signed off on the complete Canon

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
