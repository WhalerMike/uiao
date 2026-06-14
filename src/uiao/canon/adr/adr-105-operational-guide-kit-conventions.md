---
adr_id: adr-105
title: "Operational-Guide Kit Conventions — In-Repo Scripts and Paired Manual/Governed Delivery"
status: PROPOSED
decided: 2026-06-14
deciders: Michael Stratton
updated: 2026-06-14
next_review: 2026-12-14
review_trigger: A new downloadable operational-guide kit is proposed; a kit is proposed to ship its runnable scripts only as a release artifact (no in-repo source); the docs/ source-extension rule in AGENTS.md is revised; Pester coverage is proposed for kit scripts under docs/; ADR-083 or ADR-089 is revised
impact: "Ratifies the structural conventions that make a docs/ operational guide a 'kit' — already realized by the intune-arc-modernization, zero-trust-assessment, and GPO platform-tooling kits but never written down. Two rules: (1) a kit's runnable scripts + shared module are committed in-repo under the guide's scripts/ subdirectory and linked from the download page via in-repo relative paths (the release .zip is a built convenience artifact, not the source of truth); (2) a kit that describes a transformation an operator could perform without UIAO ships a without-governance 'manual path' baseline plus a UIAO/OrgPath 'governed path' companion that converge on the same end state (ADR-089 layered refinement, as intune-arc's manual-path/governed-path). Amends the AGENTS.md 'docs/ is source-only (.qmd/.md/.yml/.yaml/.puml)' rule to permit .ps1/.psm1 under operational-guide scripts/ directories. Doctrine + a one-line AGENTS.md edit only — no script moves or new guides land with this ADR; it unblocks the Help Desk / Cloud Services kit conversion, the one kit non-conformant on both rules."
supersedes: null
superseded_by: null
amends: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-105-operational-guide-kit-conventions.html
---

# ADR-105: Operational-Guide Kit Conventions — In-Repo Scripts and Paired Manual/Governed Delivery

## Status

**PROPOSED** — June 14, 2026.

## Context

Several operational guides under `docs/customer-documents/operational-guides/` are
**kits**: a guide paired with a downloadable bundle of runnable PowerShell that an
agency can adapt and run. The download index ([`docs/download/index.qmd`](../../../../docs/download/index.qmd))
lists six: the Zero Trust Assessment Dashboard, two GPO migration tools, the UIAO
PowerShell Pack, the **Intune + Azure Arc Modernization** kit, and the **Help Desk /
Cloud Services** kit.

These kits were built incrementally, and a convention emerged in practice but was
never ratified. Two structural facts are true of every recent kit **except** the
Help Desk kit:

1. **Scripts live in-repo.** `intune-arc-modernization/scripts/` (a shared
   `.psm1` module + 12 scripts), `zero-trust-assessment/scripts/Invoke-ZtDashboard.ps1`,
   and `substrate/platform-tooling/scripts/` all commit their runnable PowerShell in
   the tree, and the download page links those in-repo paths directly. The release
   `.zip` is a convenience bundle built from those sources. The **Help Desk kit is the
   lone exception**: it has no `scripts/` directory, and the download page can only
   point at the `helpdesk-entra-kit-v1.5` release zip — there is no in-repo source.

2. **Transformation kits ship paired paths.** The intune-arc kit ships a
   [Manual Path](../../../../docs/customer-documents/operational-guides/intune-arc-modernization/manual-path.qmd)
   ("no governance control plane … each operator owns the decision under local change
   control") and a [Governed Path](../../../../docs/customer-documents/operational-guides/intune-arc-modernization/governed-path.qmd)
   ("the same end state, bound to canon governance"), run **from the same scripts** via
   the `-OrgPath` / `-ApprovalRef` seam, converging on the same Microsoft surface. This
   is the [ADR-089](adr-089-program-narrative-pillars.md) layered-refinement principle
   made concrete: the operational baseline stands alone; governance is an additive
   companion, not a precondition. The **Help Desk kit is governed-only** — every
   document assumes UIAO/OrgPath context, with no standalone baseline a reader without
   UIAO can run.

This convention also collides with a standing repo rule. [`AGENTS.md`](../../../../AGENTS.md)
states *"`docs/` is human-readable documentation source only. Source extensions:
`.qmd`, `.md`, `.yml`, `.yaml`, `.puml`,"* and `CHANGELOG.md` records PowerShell being
*relocated out* of `docs/` on those grounds. Yet the intune-arc, zero-trust, and GPO
kits all commit `.ps1`/`.psm1` under `docs/` today. The rule and the practice
disagree, and that unresolved disagreement is exactly why the Help Desk kit
conversion has been held: converting it would add **more** `.ps1` under `docs/` before
the repo has decided whether that is allowed. This ADR makes the decision so the
conversion can proceed.

This ADR is structural only. It does not move any script, author any guide, or change
any runtime; it ratifies the pattern and amends one AGENTS.md sentence.

## Decision

A downloadable **operational-guide kit** — an operational guide under
`docs/customer-documents/operational-guides/` that is listed on the download index and
ships runnable scripts — conforms to the following conventions.

### D1 — Scripts are committed in-repo under the guide's `scripts/` directory

A kit's runnable scripts and its shared module live under
`docs/customer-documents/operational-guides/<kit>/scripts/`. The download index links
those scripts by **in-repo relative path**, not by release-only URL. A release `.zip`
MAY still be published as a convenience bundle, but it is **built from the in-repo
sources** and is not their system of record. There is exactly one copy of each script,
in the tree, so the published kit cannot drift from what the guide documents.

### D2 — `docs/` permits `.ps1`/`.psm1` only inside a kit `scripts/` directory

The AGENTS.md "`docs/` is documentation source only" rule is amended: `.ps1` and `.psm1`
are permitted **only** under an operational-guide `scripts/` directory (D1). Everywhere
else in `docs/`, the source-extension rule stands unchanged — PowerShell that is
workspace tooling, not a customer-facing kit artifact, still belongs in top-level
[`scripts/`](../../../../scripts/) or [`tools/`](../../../../tools/). Kit scripts are
customer deliverables that are versioned and rendered *with* their guide; tooling is
not. (The matching one-line edit lands in AGENTS.md with this ADR.)

### D3 — Transformation kits ship a paired manual + governed delivery

A kit whose subject is a **transformation an operator could perform without UIAO** ships
two converging paths:

- a **manual path** — the standalone runbook under local change control, with no
  governance control plane, runnable by any reader; and
- a **governed path** — the same end state bound to UIAO/OrgPath governance
  (OrgPath scoping, the actuation ladder, approval references, drift detection),

run from the **same scripts** via the governance seam (`-OrgPath` / `-ApprovalRef`),
per [ADR-089](adr-089-program-narrative-pillars.md). A retrofit path (layer governance
onto an estate already modernized the manual way) is offered where it applies.

**Exemptions.** Kits that are pure assessment/reporting (Zero Trust Assessment, GPO
audits) have no "manual vs governed" transformation to split and are exempt. A kit
whose entire subject *is* a governance model may be delivered governed-only, but the
exemption MUST be stated in the kit's `index.qmd` with its rationale — silence is
treated as non-conformance.

### D4 — Every state-changing script honors `-WhatIf`

Unchanged house practice, restated here as a kit-conformance criterion: every kit
script that mutates a live tenant supports `-WhatIf` for a dry run.

### Out of scope

Pester coverage for kit scripts. The Pester CI path
([`pester.yml`](../../../../.github/workflows/pester.yml)) tests the `tools/powershell/`
modules only; kit scripts under `docs/` are customer-adaptable illustrations, not
runtime modules, and are not added to that gate by this ADR. Whether they warrant
PSScriptAnalyzer linting or smoke tests is tracked separately.

## Consequences

### Conformance status of existing kits

| Kit | D1 in-repo scripts | D3 paired paths | Status |
|---|---|---|---|
| Intune + Azure Arc Modernization | ✅ `scripts/` (module + 12) | ✅ manual + governed + retrofit | **Reference implementation** |
| Zero Trust Assessment | ✅ `scripts/Invoke-ZtDashboard.ps1` | — exempt (assessment) | Conformant |
| GPO Migration Triage / Obsolete Audit | ✅ `platform-tooling/scripts/` | — exempt (assessment) | Conformant |
| UIAO PowerShell Pack | ✅ `scripts/uiao-env-pack/` (built zip) | — exempt (operator tooling) | Conformant |
| **Help Desk / Cloud Services** | ❌ release zip only | ❌ governed-only, no stated exemption | **Non-conformant → conversion** |

The first four are retro-blessed by this ADR (already conformant). The Help Desk kit is
the only one that fails, on both D1 and D3 — which is precisely the "Help Desk kit
conversion" this ADR unblocks.

### What the Help Desk kit conversion entails (follow-up work, not this ADR)

1. **D1:** add `helpdesk-entra-operations/scripts/` with the shared module and the six
   Microsoft Graph scripts currently shipped only inside `helpdesk-entra-kit-v1.5`
   (request triage, Enterprise App inventory, PAG + PIM setup, group-to-app assignment,
   ImmutableID repair, access-certification export), and relink
   [`docs/download/index.qmd`](../../../../docs/download/index.qmd) to the in-repo paths.
2. **D3:** either add a without-UIAO "manual path" baseline for the Help Desk operations
   the kit documents and recast the existing pages as the governed companion, **or**
   record a D3 exemption in the kit's `index.qmd` on the grounds that the kit's subject
   *is* the governance/approval-routing model. The conversion PR decides this explicitly
   rather than leaving it silent.

The release zip's scripts are the source for step 1; that PR cannot be authored without
them in hand.

## Relationship to other ADRs

- **[ADR-083](adr-083-docs-architecture-reorganization.md)** placed operational guides
  under `/customer-documents/operational-guides/`. This ADR governs what lives *inside* a
  kit's directory; it does not move any directory.
- **[ADR-089](adr-089-program-narrative-pillars.md)** established layered refinement
  (reference + how-to + explanation). D3 is that principle applied to a single kit:
  manual baseline (how-to) + governed companion (how-to + the governance "why").
- **[ADR-093](adr-093-image-generation-svg.md)** already treats committed non-source
  artifacts (rasterized PNGs) as build outputs living beside their SVG sources under
  `docs/`; D2 is the analogous, narrower allowance for kit scripts.

## Review triggers

- A new downloadable kit is proposed — check it against D1/D3 at design time.
- A kit is proposed to ship scripts only as a release artifact (re-evaluate D1).
- The AGENTS.md `docs/` source-extension rule is revised (re-evaluate D2).
- Pester or PSScriptAnalyzer coverage is proposed for kit scripts (revisit Out of scope).
- [ADR-083](adr-083-docs-architecture-reorganization.md) or
  [ADR-089](adr-089-program-narrative-pillars.md) is revised.

## References

- [`docs/download/index.qmd`](../../../../docs/download/index.qmd) — the kit catalog.
- [`AGENTS.md`](../../../../AGENTS.md) — the `docs/` source-extension rule amended by D2.
- Reference kit:
  [`intune-arc-modernization/`](../../../../docs/customer-documents/operational-guides/intune-arc-modernization/index.qmd)
  (manual + governed + retrofit, scripts in-repo).
- Conversion target:
  [`helpdesk-entra-operations/`](../../../../docs/customer-documents/operational-guides/helpdesk-entra-operations/index.qmd).
