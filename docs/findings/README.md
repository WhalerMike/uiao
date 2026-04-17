# docs/findings/

Governance findings. Reader-facing operational artifacts that
document constraints the UIAO substrate has identified in its
environment — constraints outside the substrate's direct control,
but material to its capability.

## Artifact class

A finding is **not** canon. Canon documents what IS inside the
substrate. A finding documents what IS outside the substrate and
blocks capability inside it. The two have different ownership
trails, different remediation paths, and different lifecycles.

A finding is **not** narrative. Narrative explains. A finding
records a fact with an owner and a remediation state.

Findings are authorized as a first-class artifact class by
[ADR-030](../../core/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md) §5.2.

## Required structure

Every finding document includes:

1. **Frontmatter** with `artifact-class: governance-finding`,
   `owner`, `created_at`, `updated_at`, `status`, `boundary`, and
   any relevant cross-references to canon documents the finding
   affects.
2. **§1 Constraint** — what the substrate has identified.
3. **§2 Evidence** — citations to authoritative sources, dated.
   Primary sources (vendor documentation, FedRAMP guidance,
   standards bodies) are required; no "best guess" claims.
4. **§3 Capability gap** — what the substrate cannot do because
   of the constraint.
5. **§4 Proposed remedy** — split into **internal** (what UIAO
   could do under its own authority) and **external** (what
   some other party would need to do).
6. **§5 Ownership trail** — who identified the finding, what
   escalations have happened, who currently owns it. If the
   ownership trail includes a stated principle (e.g. "everyone
   owns all problems they identify"), cite the source.
7. **§6 Status and lifecycle** — `Open`, `Awaiting-External-Remediation`,
   `Remediated-Internally`, `Retired-Superseded`.

## Status values

| Status | Meaning |
|---|---|
| `Open` | Finding identified; remediation path not yet chosen |
| `Awaiting-External-Remediation` | Remedy requires action by a party outside the substrate's authority |
| `Remediated-Internally` | UIAO has implemented a workaround or alternative capability; finding retired; supersession pointer to the canon that now handles the capability |
| `Retired-Superseded` | External remediation landed; finding retired; evidence preserved for audit |

## Lifecycle

A finding is never deleted once it has citations. Retirement is a
status transition, not a removal. Evidence of the finding and its
resolution path remains in git history for the audit retention
window declared in UIAO_004.

When a finding is `Remediated-Internally`, it carries a
supersession pointer to the canon document (UIAO_NNN) that now
handles the capability. Readers encountering the finding are
redirected to the canon.

## What a finding is *not*

- Not a vendor complaint. Findings name constraints and remedies,
  not vendors. Vendor-specific behavior goes in registry entries
  under `core/canon/modernization-registry.yaml` or
  `core/canon/adapter-registry.yaml`.
- Not a bug report. Bugs land as GitHub issues against the repo.
- Not advocacy. A finding names a constraint and a remedy; it
  does not demand that any specific external party act. External
  remediations are "proposed" — the finding documents the
  proposal and waits.
- Not canon. Canon documents what the substrate IS. Findings
  document what the substrate's environment constrains it from
  being.

## File naming

`<slug-describing-the-constraint>.md`. Slug should name the
constraint, not the remedy.

Examples (not yet all written):

- `fedramp-gcc-moderate-telemetry-constraint.md`
- `azure-government-feature-gap-identity-protection.md`

## Website rendering

Findings render on the UIAO Modernization Atlas under the
**Findings** sidebar section. See `docs/findings/index.qmd` for
the landing page and the sidebar configuration in
`docs/_quarto.yml`.
