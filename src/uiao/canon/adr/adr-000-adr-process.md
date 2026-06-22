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

### ADRs Are Decision Records, Not Sources of Truth

An ADR is the single source of truth (SSOT) **only for the decision it records** —
the position taken, its rationale, and the program-internal commitments that follow
(phasing, sequencing, target postures, owners, and the dates the program sets for
itself).

An ADR is **not** a source of truth for the **external facts** it cites — statutory or
regulatory mandates, vendor product behavior, standards-body requirements, or any
claim whose authority originates outside this program. For an external fact, the ADR
carries authority **only if it directly and traceably links to the authoritative
source** (the external SSOT) at the point the fact is asserted. An ADR that states an
external fact without a direct link to its authority is, for that fact, unsourced, and
MUST NOT be treated as canonical for it.

Two obligations follow:

1. **ADRs link their external facts.** Every external fact an ADR relies on carries an
   inline, resolvable reference to the authoritative source (URL, document ID, or
   clause) at the point of assertion. A References section is necessary but not
   sufficient — the link must be traceable from the claim itself.
2. **Downstream documents must trace external facts to an authoritative source.** When
   a guide, narrative, or spec repeats an external fact, the citation must *resolve* to
   the authority. This is satisfied either by citing the authoritative source directly,
   **or** by citing an ADR that itself carries the inline, traceable link to that source
   — in which case the ADR serves as the provenance-anchored pointer (the chain
   document → ADR → source resolves). What is never acceptable is citing an ADR that
   does **not** carry the link, or asserting an external fact with no traceable source
   at all. Direct citation of the upstream source is *preferred* for customer-facing
   clarity but not required when the ADR carries the link. Where a document separates the
   external fact from the program's response, attribute each to its proper source, e.g.
   *"CCM BIR adoption is mandatory by 2027-04-01 ([FedRAMP Notice 0009](https://www.fedramp.gov/20x/notice-0009/)); this program
   delivers the adapter by 2026-Q4 (ADR-043)."*

This sharpens operating principle #1 ("every claim has exactly one canonical source"):
for a **decision**, that source is the ADR; for an **external fact**, it is the
authoritative source the ADR points to, never the ADR itself.

## Consequences

- All 23 existing ADRs (ADR-005 through ADR-027) are retroactively subject
  to this process.
- New ADRs require Governance Board ratification before status advances
  from PROPOSED to ACCEPTED.
- ADRs in SUPERSEDED or DEPRECATED state remain in the corpus permanently
  for audit trail purposes.
- The CI validation workflow (`validate-uiao-frontmatter.yml`) enforces
  required frontmatter fields on all ADR files.
- An ADR that asserts an external fact without a direct, traceable link to its
  authoritative source is a documentation defect; reviewers reject it as they would a
  missing `UIAO_NNN` allocation.
- A downstream document that cites, for an external fact, an ADR that does **not** carry
  an inline traceable link to the authority — or that asserts the fact with no traceable
  source at all — is a provenance-drift signal to be corrected. Citing an ADR that *does*
  carry the link is acceptable (the chain resolves); citing the upstream source directly
  is preferred for customer-facing documents.

## Amendments

- **2026-06-06** — Added "ADRs Are Decision Records, Not Sources of Truth." ADRs are
  SSOT for the decisions they record but not for external facts; external facts require
  a direct, traceable link to their authoritative source, and downstream documents must
  trace external facts to that source — either directly, or via an ADR that carries the
  inline link (the ADR then serves as the resolving provenance pointer; direct upstream
  citation preferred for customer-facing docs). Decision basis otherwise unchanged.

## See Also

- [ADR Index](index.md)
- [Canonical Rules](../canonical-rules.md)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
