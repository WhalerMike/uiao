---
uiao_id: UIAO_META_ADR_01
title: ADR Metadata Contract
status: Current
owner: Governance Board
date: 2026-04-07
---

# ADR Metadata Contract

This contract defines the canonical frontmatter schema for all Architecture Decision Records (ADRs) in the UIAO corpus.

## Required Fields

```yaml
---
id: ADR-012                # Unique ADR identifier (ADR-<number>)
title: Federated Drift Detection
status: Accepted           # One of: Proposed, Accepted, Superseded, Deprecated, Replaced
date: 2026-04-07           # ISO date of decision
deciders:                  # People or roles who made the decision
  - architecture-board@example.com
consulted:                 # Optional: stakeholders consulted
  - data-governance@example.com
tags:                      # Cross-fabric tags
  - drift
  - evidence
  - governance
affects:                   # UIAO documents impacted by this ADR
  - UIAO_C_01
  - UIAO_D_02
supersedes: ADR-005        # Optional: ADR this one supersedes
supersededBy: ADR-020      # Optional: ADR that supersedes this one
uiao:
  id: UIAO_ADR_012         # UIAO id for the ADR document itself
  status: Current
  owner: Governance Board
  lastUpdated: 2026-04-07
  commit: <short-hash>
---
```

## Field Semantics

**id** -- Stable ADR identifier (`ADR-<number>`).

**title** -- Short, descriptive decision title.

**status** -- One of:

| Value | Meaning |
|-------|---------|
| Proposed | Under review, not yet binding |
| Accepted | Active and authoritative |
| Superseded | Replaced by another ADR |
| Deprecated | Being phased out |
| Replaced | Explicitly replaced by another ADR |

**date** -- Date the decision was made (or proposed). ISO 8601 format (`YYYY-MM-DD`).

**deciders** -- Roles or groups accountable for the decision.

**consulted** -- Optional list of stakeholders consulted prior to decision.

**tags** -- Used for cross-fabric queries. Canonical values: `identity`, `drift`, `evidence`, `adapter`, `governance`.

**affects** -- List of `UIAO_<AppendixLetter>_<Number>` document IDs impacted by this ADR.

**supersedes / supersededBy** -- Maintain decision lineage across the ADR lifecycle.

**uiao block** -- Aligns ADRs with the general UIAO document metadata contract:

| Sub-field | Meaning |
|-----------|---------|
| `uiao.id` | UIAO document ID for the ADR itself (`UIAO_ADR_NNN`) |
| `uiao.status` | Document lifecycle status (`Current`, `Draft`, etc.) |
| `uiao.owner` | Accountable team or role |
| `uiao.lastUpdated` | Last modification date |
| `uiao.commit` | Short Git commit hash at time of last update |

## Validation Rules

All ADRs must conform to this schema. CI enforces presence and allowed values for:

- `id` -- required, pattern `ADR-[0-9]+`
- `title` -- required, non-empty string
- `status` -- required, one of the five allowed values above
- `date` -- required, ISO 8601 date
- `uiao.id` -- required, pattern `UIAO_ADR_[0-9]+`

Fields `deciders`, `consulted`, `tags`, `affects`, `supersedes`, and `supersededBy` are optional
but strongly recommended for traceability.

## See Also

- [ADR Process and Lifecycle](../adr/adr-000-adr-process.md)
- [ADR Index](../adr/index.md)
- [Corpus Status Dashboard](../canon/corpus-status-dashboard.md)
