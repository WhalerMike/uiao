---
uiao_id: UIAO_ADR_000
title: "ADR-000: ADR Process and Lifecycle"
status: ACCEPTED
owner: Governance Board
date: 2026-04-07
---

# ADR-000: ADR Process and Lifecycle

## Status

ACCEPTED

## Context

The UIAO governance corpus requires a consistent, auditable process for recording
architectural decisions. Without a defined process, decisions are made informally,
are hard to trace, and cannot be challenged or superseded in a principled way.

This ADR establishes the ADR lifecycle itself -- the meta-process that all other
ADRs follow.

## Decision

All significant architectural decisions that affect UIAO core behavior, adapter
contracts, evidence standards, or governance policy MUST be recorded as ADRs
in `docs/adr/` using the filename pattern `adr-NNN-short-title.md`.

### ADR Lifecycle

```
PROPOSED --> ACCEPTED --> SUPERSEDED
                      --> DEPRECATED
```

| Status | Meaning |
|--------|---------|
| PROPOSED | Draft ADR under review. Not yet binding. |
| ACCEPTED | Ratified by Governance Board. Binding on all new work. |
| SUPERSEDED | Replaced by a newer ADR. Link to successor required. |
| DEPRECATED | No longer applicable. May reference archived context. |

### Numbering

ADRs are numbered sequentially from 000. ADR-000 is reserved for this
process document. ADR-001 through ADR-004 are reserved for foundational
adapter plane decisions (to be ratified). ADR-005 onwards are assigned
in merge order.

### Required Frontmatter

Every ADR file MUST include:

```yaml
---
uiao_id: UIAO_ADR_NNN
title: "ADR-NNN: Short Title"
status: PROPOSED | ACCEPTED | SUPERSEDED | DEPRECATED
owner: <team or individual>
date: YYYY-MM-DD
---
```

### Required Sections

Every ADR MUST include:

- **Status** -- current lifecycle state
- **Context** -- the problem, constraints, and forces at play
- **Decision** -- what was decided and why
- **Consequences** -- what becomes easier, harder, or required as a result

Optional: **Superseded By** (link to successor ADR when status = SUPERSEDED)

## Consequences

- All 23 existing ADRs (ADR-005 through ADR-027) are retroactively subject
  to this process.
- New ADRs require Governance Board ratification before status advances
  from PROPOSED to ACCEPTED.
- ADRs in SUPERSEDED or DEPRECATED state remain in the corpus permanently
  for audit trail purposes.
- The CI validation workflow (`validate-uiao-frontmatter.yml`) enforces
  required frontmatter fields on all ADR files.

## See Also

- [ADR Index](index.md)
- [Corpus Status Dashboard](../canon/corpus-status-dashboard.md)
- [Canonical Rules](../canon/canonical-rules.md)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
