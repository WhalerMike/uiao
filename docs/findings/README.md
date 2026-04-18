# `docs/findings/` — UIAO Governance Findings

Governance findings are **operational artifacts** that document
constraints the UIAO substrate has identified in its environment —
conditions the substrate does not control but which block or
degrade capability. Findings are not canon (they don't declare
how UIAO works); they are not pure narrative (they carry structured
evidence and ownership). They occupy a distinct artifact class
established by [ADR-030
§5.2](../../src/uiao/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md).

## When to create a finding

A governance finding is appropriate when:

1. The substrate has identified a constraint with evidence (docs,
   citations, agency transcripts, vendor notices).
2. The constraint blocks or degrades substrate capability — the
   substrate **cannot fully deliver** some behavior its canon
   describes.
3. The resolution requires action **outside** the substrate's
   authority (agency policy, vendor roadmap, federal boundary
   definition, etc.).
4. A named owner takes responsibility for tracking the finding
   through to remediation or formal closure.

## Finding contract (five required sections)

Every finding document has five mandatory sections:

1. **Constraint.** What the substrate has identified. Stated as
   a fact, not an opinion.
2. **Evidence.** Citations that establish the constraint. Must
   include at least one primary source (vendor docs, agency
   policy document, Microsoft Learn, FedRAMP guidance, etc.)
   with a URL and access date.
3. **Capability gap.** What the substrate cannot do as a result
   of the constraint. Tied to specific UIAO_NNN capability
   statements.
4. **Proposed remedy.** The action that would resolve the
   constraint. Split between (a) internal actions inside
   substrate scope and (b) external actions requiring third-party
   change.
5. **Ownership trail.** Who identified the finding, when it was
   escalated, who responded, and what the current ownership
   resolution is. Escalation history is preserved — "X said Y
   on date Z" entries are append-only.

Optional sections: related findings, superseded-by pointer,
timeline of remediation milestones.

## Frontmatter

Every finding carries YAML frontmatter with:

```yaml
---
title: "<Finding name>"
finding_id: "FINDING-NNN"        # simple sequential; see registry
status: Open | Awaiting-External-Remediation | Resolved | Withdrawn
severity: P1 | P2 | P3            # matches drift-class severities
created_at: "YYYY-MM-DD"
updated_at: "YYYY-MM-DD"
owner: "<human name>"
related_canon: ["UIAO_NNN", "UIAO_MMM"]
supersedes: []
superseded_by: []
---
```

## Status lifecycle

- **Open** — finding documented, no remediation path agreed.
- **Awaiting-External-Remediation** — remedy requires external
  action (agency policy change, vendor roadmap, FedRAMP
  boundary adjustment). Substrate-side mitigation documented if
  available.
- **Resolved** — remedy landed; finding describes the
  historical constraint and the mechanism that now handles it.
  The finding stays in this directory as an audit trail.
- **Withdrawn** — finding determined to be incorrect or
  duplicate; reason documented. Not deleted.

## Relationship to the substrate

- **Not canon.** Findings do not declare UIAO behavior. They
  describe the environment around the substrate.
- **Not ADR-able.** ADRs decide what UIAO will do. Findings
  name things UIAO cannot do until external constraints lift.
- **Aspirational-adjacent, not aspirational.** A finding is NOT
  tagged `aspirational: true` — it describes something real (a
  constraint that exists today), even if the resolution is
  aspirational.
- **Rendered on the site.** Findings render on the
  Modernization Atlas under `/uiao/findings/` so readers can
  see what UIAO is operating around.

## Authoring workflow

1. Draft the finding in `inbox/drafts/finding-<slug>.md` using the
   CoPilot roundtrip if appropriate.
2. Land via PR with the five required sections filled.
3. Add frontmatter with status + owner.
4. Cross-reference the finding from any canon doc whose capability
   is affected (the canon doc cites the finding; the finding
   cites the canon doc).
5. Announce in the session log if the finding blocks an
   in-flight workstream.

## Registry

Planned: a thin `docs/findings/registry.yaml` that enumerates
every finding with its `finding_id`, status, owner, and
last-updated date. Lands with the first concrete finding (the
FedRAMP-INR telemetry constraint) in a follow-on PR.

## Not in this directory

- Agency-specific runbooks → `src/uiao/canon/specs/`
- Risk assessments of UIAO itself → security review process, not
  findings
- Open bugs in UIAO code → GitHub Issues
- Feature requests → GitHub Issues with `roadmap` label
