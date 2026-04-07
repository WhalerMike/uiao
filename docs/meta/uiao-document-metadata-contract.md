---
title: UIAO Document Metadata Contract
uiao_id: UIAO_META_DOC_01
status: Current
owner: Governance Board
tags: [metadata, governance, contract]
date: 2026-04-07
---

# UIAO Document Metadata Contract

This contract defines the canonical frontmatter schema for all **non-ADR UIAO documents**, including:
Canon Overview, Appendices A-E, appendix sub-documents, governance documents, contributor guide,
access page, dashboard, meta documents, and any future UIAO document.

All UIAO documents **must** conform to this schema. CI validation enforces required fields,
allowed values, and naming patterns.

---

## 1. Required Frontmatter Schema

```yaml
---
title: <Human-readable title>

uiao:
  id: UIAO_<AppendixLetter>_<Number>   # REQUIRED, canonical ID
  status: Current                      # REQUIRED: Current | Draft | Needs Replacing | Needs Creating | Deprecated
  owner: team@example.com              # REQUIRED: accountable owner
  tags:                                # REQUIRED: cross-fabric tags
    - identity
    - governance
  created: 2026-04-07                  # REQUIRED: ISO date
  lastUpdated: 2026-04-07              # REQUIRED: ISO date
  commit: <short-hash>                 # REQUIRED: provenance commit hash

summary: >                             # REQUIRED: 1-3 sentence summary
  Short description of the document purpose and scope.

version: 1.0                           # OPTIONAL: semantic version for stable documents
fabric: identity                       # OPTIONAL: primary fabric
---
```

## 2. Field Definitions

**title** -- Human-readable document title. Must match the H1 heading.

**uiao.id** -- Canonical identifier for the document.
Pattern: `UIAO_<AppendixLetter>_<Number>`

Examples:

- `UIAO_A_01` -- Appendix A document
- `UIAO_E_03` -- Governance Plane document
- `UIAO_META_DOC_01` -- Meta contract (non-appendix)

**uiao.status** -- Allowed values:

| Value | Meaning |
|-------|---------|
| Current | Authoritative and up to date |
| Draft | Under development |
| Needs Replacing | Outdated; requires rewrite |
| Needs Creating | Placeholder exists but content missing |
| Deprecated | Superseded or retired |

**uiao.owner** -- Team or role responsible for the document.

**uiao.tags** -- Cross-fabric classification. Allowed values: `identity`, `drift`, `evidence`,
`adapter`, `governance`, `meta`, `architecture`, `operations`, `compliance`.

**uiao.created / uiao.lastUpdated** -- ISO dates. `lastUpdated` must match the commit that introduced the change.

**uiao.commit** -- Short git commit hash for provenance. Automatically updated by CI on merge.

**summary** -- 1-3 sentence description of the document purpose.

**version** (optional) -- Semantic version for stable documents.

**fabric** (optional) -- Primary fabric the document belongs to.

## 3. Example: Appendix Document

```yaml
---
title: Adapter Lifecycle
uiao:
  id: UIAO_A_01
  status: Current
  owner: Governance Board
  tags:
    - adapter
    - governance
  created: 2026-03-01
  lastUpdated: 2026-04-07
  commit: a1b2c3d
summary: >
  Defines the canonical lifecycle for UIAO adapters, including registration,
  validation, versioning, and deprecation workflows.
fabric: adapter
version: 1.2
---
```

## 4. Example: Canon Overview

```yaml
---
title: UIAO Canon Overview
uiao:
  id: UIAO_CANON_01
  status: Current
  owner: Governance Board
  tags:
    - governance
    - meta
  created: 2026-03-15
  lastUpdated: 2026-04-07
  commit: d4e5f6a
summary: >
  The authoritative overview of the Unified Identity and Access Operations (UIAO)
  architecture, its fabrics, governance model, and cross-fabric interactions.
fabric: governance
version: 1.0
---
```

## 5. Validation Rules (CI-Enforced)

**Required:**

- `uiao.id` present and matches pattern
- `uiao.status` is allowed value
- `uiao.owner` present
- `uiao.tags` non-empty
- `uiao.created` and `uiao.lastUpdated` valid ISO dates
- `uiao.commit` present
- `summary` present
- `title` matches H1

**Recommended:**

- `fabric` present
- `version` present for stable documents

**Prohibited:**

- Duplicate `uiao.id`
- Missing status badge in top 8 lines
- Missing provenance footer

## 6. Governance Notes

- This contract is immutable except via ADR.
- All new documents must be created using this schema.
- CI will block merges that violate this contract.
- Dashboard and footer rendering depend on these fields.
- This contract is the single source of truth for UIAO document metadata.

## See Also

- [ADR Metadata Contract](uiao-adr-metadata-contract.md)
- [ADR-000 ADR Process](../adr/adr-000-adr-process.md)
- [Corpus Status Dashboard](../canon/corpus-status-dashboard.md)
