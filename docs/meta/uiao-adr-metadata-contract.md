---
title: UIAO ADR Metadata Contract
uiao_id: UIAO_META_ADR_02
status: Current
owner: Governance Board
tags: [adr, metadata, governance]
date: 2026-04-07
---

# UIAO ADR Metadata Contract

This contract defines the canonical frontmatter schema for all UIAO ADRs.
It is parallel to the UIAO Document Metadata Contract and must be enforced by CI.

## Required Frontmatter Schema

```yaml
---
title: Federated Drift Detection

id: ADR-012                    # ADR identifier (ADR-<number>)
status: Accepted               # Proposed | Accepted | Superseded | Deprecated | Replaced
date: 2026-04-07               # Decision date (ISO)

deciders:                      # Required: accountable decision-makers
  - architecture-board@example.com

consulted:                     # Optional: consulted stakeholders
  - data-governance@example.com

tags:                          # Required: cross-fabric tags
  - drift
  - evidence
  - governance

affects:                       # Required: impacted UIAO documents
  - UIAO_C_01
  - UIAO_D_02

supersedes: ADR-005            # Optional
supersededBy: ADR-020          # Optional

uiao:
  id: UIAO_ADR_012             # UIAO id for this ADR document
  status: Current              # Current | Draft | Needs Replacing | Needs Creating | Deprecated
  owner: Governance Board
  tags:
    - adr
    - governance
  created: 2026-04-07
  lastUpdated: 2026-04-07
  commit: <short-hash>

summary: >
  Defines the decision to implement federated drift detection across the Drift
  and Evidence Fabrics, including responsibilities and integration contracts.

fabric: governance             # Optional primary fabric
version: 1.0                   # Optional semantic version
---
```

## Key Rules

- `id` must match `^ADR-[0-9]{3,}$`.
- `status` must be one of: `Proposed`, `Accepted`, `Superseded`, `Deprecated`, `Replaced`.
- `affects` must contain valid `UIAO_...` ids.
- `uiao` block follows the UIAO Document Metadata Contract.
- Any change to this contract requires an ADR.

## Validation Rules

| Field | Rule |
|-------|------|
| `id` | Required, pattern `^ADR-[0-9]{3,}$` |
| `status` | Required, one of five allowed values |
| `date` | Required, ISO 8601 |
| `deciders` | Required, non-empty array |
| `tags` | Required, non-empty array |
| `affects` | Required, each entry matches `UIAO_...` pattern |
| `uiao.id` | Required, pattern `^UIAO_ADR_[0-9]+$` |
| `summary` | Required, 1-3 sentences |
| `consulted` | Optional |
| `supersedes` | Optional, pattern `^ADR-[0-9]{3,}$` |
| `supersededBy` | Optional, pattern `^ADR-[0-9]{3,}$` |

## See Also

- [UIAO Document Metadata Contract](uiao-document-metadata-contract.md)
- [ADR-000 ADR Process](../adr/adr-000-adr-process.md)
- [ADR Index](../adr/index.md)
