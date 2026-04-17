---
title: "ADR-030: Reconcile Pre-UIAO Terminology with Canon"
adr: "ADR-030"
status: ACCEPTED
date: "2026-04-17"
deciders: ["WhalerMike"]
extends: ["ADR-028"]
---

# ADR-030: Reconcile Pre-UIAO Terminology with Canon

## Status

ACCEPTED

## Context

A large body of architecture prose (≈30,000 words) was drafted
**before** the UIAO substrate was formalized on GitHub. It lives
outside canon today — Master Outline, Table of Contents, eight
body sections, two appendices, operational runbooks, and
implementation scaffolding. That content carries working labels
("V3 Unified Identity-Addressing-Overlay Architecture") and a
four-layer model (Authority / Control / Overlay / Underlay) that
predate the substrate's canon.

The existing UIAO canon uses two adjacent but not identical
framings:

1. **Six-control-plane model** (from the predecessor `uiao-docs`
   lineage): Identity, Addressing, Overlay, Telemetry,
   Management, Governance. Referenced across `docs/docs/00–19`
   pages and prose in UIAO_101 / UIAO_102.
2. **UIAO_003 Adapter Segmentation taxonomy**: `class` ×
   `mission-class`. The machine-readable model; registries conform
   to it.

Neither the substrate manifest (UIAO_200) nor any canon document
uses the phrase "V3." No ADR has defined it. No schema references
it. The pre-UIAO drafts and the existing canon are not
contradictory — they are at different abstraction levels — but
they disagree on vocabulary, on versioning discipline, and on
where vendor and policy-advocacy content belongs.

Additionally: the pre-UIAO drafts contain a legitimate operational
finding — the FedRAMP GCC-Moderate telemetry constraint blocks
capability the substrate needs to deliver. That finding has
organizational backing ("everyone owns all problems they identify"
— current CIO). Canon alone is the wrong home for it; narrative
alone undersells it. It needs a formal artifact class.

A reconciliation is warranted before any pre-UIAO content promotes
to canon.

## Decision

### 1. No architecture-wide version labels

Neither "V3" nor any future label like "V4" or "2.0" becomes
canonical. The architecture is referred to by its full name —
**Unified Identity-Addressing-Overlay Architecture**, UIAO — or by
canonical document ID (UIAO_001, UIAO_101, etc.). **Per-document
`version` fields in frontmatter are the only governed versioning
surface.** Pre-UIAO content carrying any architecture-wide label
is rewritten on promotion to drop the label entirely, not to
re-label.

**Rationale.** A monolithic version label creates coupling: every
canon document would need to move in lock-step, or documents would
disagree on whether they are "V3-compliant." The existing
per-document `version` field is the governed mechanism.

### 2. Adopt a reconciled layer model at two abstraction tiers

**Tier A — architectural model (prose / Education / Series 5):**

The architecture is described with **four layers**:

1. **Authority Plane** — sources of truth (IPAM, IAM, Certificate
   / Token Services, Policy Engine).
2. **Control Plane** — intent translation, path orchestration,
   QoS mapping, closed-loop automation.
3. **Overlay Fabric** — SDN (data center) + SD-WAN (WAN / edge);
   identity-based segmentation; application classification.
4. **Physical Underlay** — transport primitives, deterministic
   pathing (SR-TE / MPLS-TE), QoS enforcement.

Appropriate for prose canon (UIAO_101, UIAO_102), Series 5
articles, and Education walkthroughs. Reads cleanly for federal
agency audiences.

**Tier B — control-plane decomposition (inside the Control Plane
above):**

Within the Control Plane, the substrate continues to expose its
**six control planes** — Identity, Addressing, Overlay, Telemetry,
Management, Governance — as the decomposition layer. These are
the decision surfaces UIAO acts on. They sit **inside** Tier A's
Control Plane, not adjacent to it.

### 3. Adapter taxonomy (UIAO_003) is unchanged

The dual-axis adapter taxonomy — `class` × `mission-class` —
operates orthogonally to the layer model. It describes what an
adapter does and where it changes state, not which layer it lives
in. UIAO_003 needs no update for this reconciliation.

### 4. Canon update scope

This ADR **authorizes** the following updates to land in bounded
PRs after it is `Accepted`. Each is its own PR with its own test
plan.

| PR | Target | Scope |
|---|---|---|
| Update UIAO_101 | Platform Overview | Restate four-layer model; note six-plane decomposition inside Control Plane |
| Update UIAO_102 | Platform Services Layer | Align service layer to the Tier A four-layer model |
| Update UIAO_120 | Zero-Trust Integration Layer | Restate ZT / SASE boundary at the Overlay Fabric layer |
| New UIAO_129 | Application Identity Model | Consumes Authority Plane definitions; drafted per this ADR |
| New UIAO_130 | Application Identity Onboarding Runbook | Operates across Authority and Control Planes |
| Update `docs/docs/00–02` | Architecture prose | Reconcile legacy six-plane framing with Tier A/B explanation |

PRs outside this scope (e.g. inbox Section 4 HA content) land
under other existing canon (UIAO_114, UIAO_117) without requiring
this ADR.

### 5. Non-canon outputs from the inbox — two classes

Two categories of inbox content are **explicitly non-canon** and
do not fall under this ADR's reconciliation mandate, but each has
a formal home:

**5.1 — Vendor mappings → registries.** Vendor names (Appendix A
of the inbox drop) land in
`core/canon/modernization-registry.yaml` and
`core/canon/adapter-registry.yaml` as registry entries. Vendor
names never appear in canon prose.

**5.2 — Governance findings → `docs/findings/`.** The FedRAMP
GCC-Moderate telemetry constraint (Appendix A §A.2 of the inbox
drop) is a **governance finding**, not advocacy. Findings are
reader-facing operational artifacts that document:

(a) a constraint the substrate has identified in its environment
(b) the evidence supporting the finding
(c) the capability gap the constraint creates
(d) the proposed remedy
(e) the ownership trail

Findings live under `docs/findings/` with frontmatter marking
them as governance findings. They are **not** canon — they
document conditions the substrate does not control — but they
are governed artifacts with a provenance block and a named owner.

A finding whose remedy is implemented inside the substrate
retires the finding with a supersession pointer to the canon
document that now handles the capability. A finding whose remedy
requires external action (e.g. FedRAMP policy change) stays open
with status `Awaiting-External-Remediation` until the external
change lands.

The immediate concrete instance:
`docs/findings/fedramp-gcc-moderate-telemetry-constraint.md`
documenting the M365 Intelligent Network Routing telemetry
blockage, citing the CIO-attested ownership principle ("everyone
owns all problems they identify") as the escalation basis.

### 6. Pre-UIAO content promotion path

The inbox drop is pre-UIAO. **Promotion is not a search-and-replace;
it is a rewrite against the UIAO vocabulary.**

| Pre-UIAO term | UIAO canonical term |
|---|---|
| "V3 architecture" | *(drop entirely)* UIAO, or cite specific UIAO_NNN |
| Monolithic version labels | Per-document `version` in frontmatter |
| "the architecture" (as a named body of work) | UIAO |
| Four-layer model (in prose) | Tier A four-layer + Tier B six-plane per §2 |
| Vendor names in spec prose | Registry entries only (§5.1) |
| Policy advocacy claims | Governance findings (§5.2) |

Every inbox-origin canon PR includes a **provenance block** in the
canon document's frontmatter naming the inbox source filename and
the rewrite date. The CoPilot roundtrip workflow documented in
`inbox/drafts/README.md` is the supported promotion mechanism.

## Consequences

### Positive

- Architecture has one canonical vocabulary, traceable from any
  prose document back to this ADR.
- Pre-UIAO content has a clear promotion path: skeleton drafted by
  the substrate agent → expanded by CoPilot in the user's voice →
  reconciled against §2 Tier A/B and §6 vocabulary → PR'd with
  provenance.
- The ten-series arc (Series 1–10) can reference a single governed
  layer model in every article without re-negotiating terminology
  per series.
- Governance findings (§5.2) get a first-class home. The FedRAMP
  telemetry constraint and future findings are preserved as
  auditable artifacts, not lost in narrative drift.
- The `uiao-docs` legacy six-plane prose is preserved (Tier B)
  rather than deprecated, minimizing rewrite cost.

### Negative

- Existing prose canon using the six-plane model as the **top**
  decomposition (not as a Control-Plane sub-decomposition) must
  be updated in the PRs listed under §4. Expected scope: six
  documents, localized edits.
- "V3" and equivalent labels in pre-UIAO drafts must be rewritten
  on promotion — cannot be mechanical search-and-replace. One-time
  cost during inbox → canon migration.

### Neutral

- Registry schemas are unchanged.
- CI workflows are unchanged.
- Substrate walker and drift engine are unchanged.

## Alternatives considered

1. **Adopt "V3" as canonical.** Rejected. Monolithic version
   labels couple documents that should evolve independently. The
   per-document `version` field already serves this purpose.
2. **Retire the six-plane model entirely.** Rejected. The
   six-plane decomposition is the right granularity inside the
   Control Plane and matches existing uiao-docs lineage;
   discarding it would invalidate UIAO_120 and a dozen pages of
   prose.
3. **Retire the four-layer model (keep only six planes).**
   Rejected. Federal agency audiences and Series 5 prose read
   more cleanly with the four-layer frame; forcing the six-plane
   frame at top level pushes the architecture away from the
   reader.
4. **Treat governance findings as pure narrative.** Rejected per
   §5.2. "Not our responsibility" is the wrong default when the
   CIO has stated "everyone owns all problems they identify."
   Findings need a formal class with ownership trail and
   remediation status.
5. **Leave terminology unreconciled.** Rejected. That is the
   current state; it is active drift. Canon that promotes from
   the inbox drop without this ADR re-imports the ambiguity.

## Implementation

1. **This PR.** ADR lands in
   `core/canon/adr/adr-030-pre-uiao-terminology-reconciliation.md`.
   UIAO_129 + UIAO_130 land with it. Findings directory (`docs/findings/`)
   lands with the first FedRAMP instance.
2. **Document registry.** UIAO_129 and UIAO_130 appended to
   `core/canon/document-registry.yaml`.
3. **Narrative footnote.** Added to
   `docs/narrative/UIAO-Narrative-Layer.md` pointing readers to
   this ADR when they encounter pre-UIAO vocabulary.
4. **Site wiring follow-on.** Sidebar entries in `_quarto.yml`
   for the new ADR, the two new UIAO_NNN, and the Findings
   section — ship in a separate PR after the site-structure v1
   PR merges, to avoid `_quarto.yml` merge conflicts.
5. **Canon update PRs.** The six canon updates in §4 land
   sequentially over the following weeks, each with its own test
   plan.

## Open questions

None blocking promotion of this ADR. The ADR does not require
changes to the registry schemas or impl code.
