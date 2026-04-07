---
title: "UIAO Governance Canon"
status: ACTIVE
version: "1.0"
last_updated: "2026-04-07"
---

# UIAO Governance Canon

The UIAO Governance Canon is the authoritative body of rules, definitions, decisions, and specifications that govern the Universal Integration Adapter Orchestration (UIAO) framework.

## What Is the Canon?

The Canon is not a single document — it is a structured collection of governance artifacts that together define how UIAO is designed, operated, and evolved. The Canon includes:

- **Canonical Rules (CR-001 through CR-005):** The five immutable governance constraints that all UIAO artifacts must conform to.
- **Glossary:** Authoritative definitions for all UIAO terminology.
- **Migration Plan:** The structured plan for transitioning documentation from flat to hierarchical canonical structure.
- **PDF Layout Specification:** Requirements for the printable/archival PDF export of the Canon.
- **Architectural Decision Records (ADR-005 through ADR-027):** Immutable records of all significant architectural decisions.
- **Appendices A through E:** Detailed specifications for each major UIAO subsystem.

## Canon Authority

The Canon is maintained by the **Governance Plane**, which consists of:
- The UIAO Governance Board (human authority)
- The Canon Master Document (DOCX) — the authoritative source per CR-002
- This Canonical Rules file — the machine-readable policy

All changes to Canon content require Governance Plane ratification. See [Canonical Rules](canonical-rules.md) for the formal ratification process.

## Canon Structure

```
docs/canon/
├── index.md              ← This file
├── canonical-rules.md    ← CR-001 through CR-005
├── glossary.md           ← Authoritative UIAO terminology
├── migration-plan.md     ← Flat-to-hierarchical migration plan
└── pdf-layout-spec.md    ← PDF export layout requirements
```

## Navigating the Canon

| Section | Description |
|---|---|
| [Canonical Rules](canonical-rules.md) | The five governance constraints all UIAO artifacts must satisfy |
| [Glossary](glossary.md) | Definitions for all UIAO terms — start here if a term is unfamiliar |
| [Migration Plan](migration-plan.md) | How the documentation structure was migrated and what remains |
| [PDF Layout Spec](pdf-layout-spec.md) | Requirements for the PDF export of this Canon |
| [Appendix A — Adapter Plane](../appendix/a/index.md) | Adapter registration, schema, and lifecycle |
| [Appendix B — Truth Fabric](../appendix/b/index.md) | Canonical state model and query API |
| [Appendix C — Drift Fabric](../appendix/c/index.md) | Drift detection and reconciliation |
| [Appendix D — Evidence Fabric](../appendix/d/index.md) | Audit events and compliance attestations |
| [Appendix E — Governance Plane](../appendix/e/index.md) | Governance review process and Canon change protocol |
| [ADR Index](../adr/index.md) | All architectural decision records |

## Status Definitions

All Canon files carry a `status` field in their frontmatter:

| Status | Meaning |
|---|---|
| `MISSING` | Stub placeholder — no content yet |
| `DRAFT` | Content inserted but not yet ratified |
| `ACTIVE` | Ratified by Governance Plane — authoritative |
| `DEPRECATED` | Superseded by newer content — kept for audit trail |

## Canon Pointer

The `uiao-core` repository contains a `docs/CANON_POINTER.md` file that links back to this Canon. Machine consumers that need to locate governance documentation should start from the Canon Pointer.
