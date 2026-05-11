---
document_id: UIAO_010
proposed_id_note: "Reservation pending Canon Steward approval; not yet committed to src/uiao/canon/document-registry.yaml"
title: "UIAO OrgPath Modernization — Narrative Overview"
former_title: "UIAO Governance OS — The Complete Narrative"
version: 0.1.0
status: DRAFT
classification: CONTROLLED
boundary: GCC-Moderate
owner: "UIAO Canon Steward"
author: "UIAO Governance Engineering"
created: 2026-05-08
last_updated: 2026-05-08
review_cadence: "On revision; promote to IN_REVIEW after errata resolved"
repository: github.com/WhalerMike/uiao
supersedes: null
supersedes_drafts:
  - "UIAO Governance OS — The Complete Narrative.docx (UIAO-NARRATIVE-001 v1.0, OneDrive)"
related_canon:
  - UIAO_007  # OrgTree Modernization AD→EntraID
  - adr-035-orgpath-codebook-binding
  - adr-036-dynamic-group-provisioning
  - adr-037-admin-unit-provisioning
  - adr-038-device-plane-orgpath
  - adr-039-policy-targeting
  - adr-040-drift-engine
  - adr-041-uiao-git-infrastructure
  - adr-048-orgpath-attribute-selection
---

# UIAO OrgPath Modernization — Narrative Overview

> **Wrapper document.** This file is the governance wrapper for a narrative
> manuscript drafted in Word and held alongside this file in
> `source-docx/UIAO Governance OS — The Complete Narrative.docx` and 14
> supporting chapter documents. The wrapper exists to (a) retitle the
> manuscript honestly, (b) scope-fence it against the rest of the UIAO
> program, and (c) record errata that must be corrected before the
> manuscript can be promoted to canon. The manuscript itself is preserved
> in its original form in `source-docx/` for audit; nothing in this
> wrapper edits the underlying `.docx` files.

## 1. Purpose

The manuscript is a 23-chapter prose synthesis of the OrgPath/OrgTree
substrate — the structural attribute model that gives a flat Entra ID
directory the organizational shape that Active Directory's Organizational
Unit hierarchy expressed natively. It is written in continuous narrative
voice, without bullets or itemization, as a reading-grade companion to the
canonical specification in
[`UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md`](../../../src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md).
Where `UIAO_007` is normative, this manuscript is explanatory; where the
ADR series (`ADR-035` through `ADR-040`, `ADR-048`) records the binding
architectural decisions, the manuscript walks the reader through the
intuitions that motivated those decisions.

## 2. Scope-Fence

The manuscript was originally titled *UIAO Governance OS — The Complete
Narrative*. That title overstates its coverage. UIAO is a multi-stream
governance program, and this manuscript covers exactly one stream — the
OrgPath/OrgTree modernization track — with a focused excursion into the
Microsoft surfaces that consume the OrgPath attribute. The retitled scope
is therefore *OrgPath Modernization*, not *UIAO Governance OS*.

The following streams are operationally live in canon and are
**deliberately out of scope** for this manuscript. Each is canonical
elsewhere; readers seeking the full UIAO picture must consult the linked
artifacts.

**HRIT Modernization** is governed by `ADR-051` (SAML Trust Anchor),
`ADR-052` (PIV/USAccess Adapter), `ADR-053` (OPM Azure APIM Adapter), and
`ADR-054` (Single-ATO Reciprocity), with execution detail in
`src/uiao/canon/specs/Spec2-D*` (the Joiner/Mover/Leaver/Rehire/Conversion
workflow specifications) and the federal solicitation
24322626R0007 in `inbox/HRIT Modernization/`. The HRIT track is the
authoritative answer to identity lifecycle for federal civilian workforce
populations and is not derivable from OrgPath alone.

**KYC as a first-class customer protocol** is governed by `ADR-055`
(Customer Identity Canon Block) and `ADR-056` (Login.gov Activation
Contract), with normative material in
`src/uiao/canon/specs/customer-identity-model.md` and the operational
runbook `customer-kyc-runbook.md`. KYC's dual scope — agency↔external-citizen
authentication and inter-agency/state/employer SSOT for SSN-equivalent
identifiers — is structurally distinct from the workforce-identity
surface that OrgPath governs.

**SailPoint NERM** is governed by `ADR-059` (SailPoint Adapter Family) as
the second Commercial Cloud exception under the GCC-Moderate boundary
(the first being Azure Arc). The NERM carve-out has its own `sailpoint-nerm`
adapter slot and is not subsumed by the Microsoft-stack chapters of this
manuscript.

**Microsoft Purview conformance** is governed by `ADR-058` (Microsoft
Purview Conformance Adapter Coverage). The `OrgPath and Microsoft
Purview` chapter document in `source-docx/` walks the OrgPath integration
into Purview but does not address Purview's standing as an adapter-side
conformance surface, which `ADR-058` defines.

**The adapter framework itself** is governed by a long ADR series —
`ADR-007` (multi-cloud adapter), `ADR-011` (multi-adapter correlation),
`ADR-013` (adapter failure isolation), `ADR-015` (extensibility),
`ADR-017` (sandbox execution), `ADR-019` (vendor failure containment),
`ADR-021` (hot-swap rollback), `ADR-023` (concurrency), `ADR-025`
(health/liveness), `ADR-027` (retirement), `ADR-049` (Microsoft adapter
coverage expansion), `ADR-050` (reference middleware), and `ADR-057`
(ThousandEyes networks pillar). UIAO is a vendor-neutral adapter substrate
with Microsoft as the heaviest, most mature consumer; the manuscript's
Microsoft-only framing is correct as far as it goes but should not be
read as the program's full architectural posture.

**Evidence determinism and the drift ledger** are governed by `ADR-006`
(evidence determinism), `ADR-009` (drift-ledger immutability), `ADR-016`
(evidence bundle lifecycle), `ADR-020` (correlation determinism), and
`ADR-026` (evidence lifecycle guarantees). These are the substrate
primitives that make UIAO a governance OS rather than a documentation
pipeline. The manuscript describes the OrgPath drift detection engine
(its Chapter 8 and Chapter 19) but does not address the broader
evidence and drift-ledger architecture they sit inside.

**FedRAMP CA-7 continuous monitoring and RFC-0026 alignment** are
governed by `ADR-043` (FedRAMP RFC-0026 / CA-7 integration) and `ADR-047`
(FedRAMP 20x integration / continuous-monitoring program). The
manuscript's compliance chapter (Chapter 16) discusses 20x at
implementation level but does not reference the RFC-0026 work or its
ADRs.

**SCuBA-4-7-2026 and the AI FedRAMP Boundary streams** are operationally
live elsewhere in the repository and are not represented in this
manuscript.

## 3. Errata against the source manuscript

The source `.docx` contains three factually verifiable errors that must
be corrected before the manuscript is promoted past `DRAFT`. Each is
recorded here with the in-text location, the asserted claim, and the
canon-verified correction.

### 3.1 ADR-001 misattribution (Chapter 3, "Building the Substrate")

**Claim in source:** "Architecture Decision Record ADR-001: No, not
alone… ADR-001 recommends Gitea on Windows Server 2025 behind an IIS
reverse proxy."

**Canon:** ADR-001 is
[`adr-001-haadj-deprecated-entra-join-only.md`](../../../src/uiao/canon/adr/adr-001-haadj-deprecated-entra-join-only.md),
which records the architectural decision to deprecate Hybrid Azure AD
Join in favor of Entra-Join-Only device posture. It has nothing to do
with Git infrastructure.

**Correction:** The Gitea-on-Windows-Server-2025-behind-IIS infrastructure
decision is recorded in
[`adr-041-uiao-git-infrastructure.md`](../../../src/uiao/canon/adr/adr-041-uiao-git-infrastructure.md).
All references to "ADR-001" in Chapter 3 of the manuscript should be
read as "ADR-041" until the source document is corrected.

### 3.2 Quarto file count (Chapter 17, "The Documentation Pipeline")

**Claim in source:** "The UIAO docs directory contains 124 Quarto Markdown
files covering every aspect of the modernization program…"

**Canon:** `find docs/ -name "*.qmd"` returns **522** files at the time of
this assessment (2026-05-08).

**Correction:** Replace "124 Quarto Markdown files" with the current
verified count, or with a stable-count phrase such as "several hundred
Quarto Markdown files spanning every aspect of the modernization program."

### 3.3 "23-document UIAO corpus" framing (subtitle, Chapter 8, Chapter 21)

**Claim in source:** Subtitle reads "A Synthesis of the 23-Document UIAO
Corpus." Chapter 21 asserts "Phase 1, Assessment, occupies the first
twelve weeks and produces twenty-three canonical deliverables — one for
each document in the UIAO corpus that corresponds to an assessment
output."

**Canon:** The UIAO canonical document set has no "23 documents"
boundary. The actual canon as of 2026-05-08 includes ten `UIAO_NNN`
top-level documents (`UIAO_001`, `UIAO_002`, `UIAO_003`, `UIAO_005`–
`UIAO_009`, `UIAO_135`, `UIAO_136`, `UIAO_143`), forty-plus
`UIAO_NNN`-numbered specifications under `src/uiao/canon/specs/`, 74
ADRs, 522 `.qmd` files in `docs/`, and a multi-registry artifact set
(`document-registry.yaml`, `adapter-registry.yaml`,
`modernization-registry.yaml`). The "23" appears to be reverse-engineered
from the manuscript's chapter count.

**Correction:** The subtitle and Chapter 21 should describe what the
manuscript actually synthesizes — the OrgPath/OrgTree substrate and the
Microsoft surfaces that consume it — without claiming a numeric corpus
boundary that does not exist. A truthful subtitle is "A Narrative
Synthesis of the OrgPath/OrgTree Substrate." Phase 1 of the master plan
should describe its deliverables in terms of the assessment domains
(forest topology, OU hierarchy, GPO inventory, DNS, PKI, identity,
device, server, trust, replication) rather than as a one-to-one mapping
to manuscript chapters.

## 4. What the manuscript gets right

These observations are recorded so that the post-correction manuscript
retains its strengths.

The OrgPath thesis in Chapter 2 is canon-aligned. Active Directory's OU
hierarchy is recast as a structural vocabulary that Entra ID's flat
directory cannot express, and OrgPath is presented as the governed
attribute that re-encodes that vocabulary as a Directory Schema Extension
on every identity object. This is the position taken by `UIAO_007` and
ratified by `ADR-035` (codebook binding) through `ADR-040` (drift engine).

The canon-supremacy doctrine in Chapter 18 is correct. The six-state
lifecycle (`DRAFT` / `IN_REVIEW` / `APPROVED` / `CURRENT` / `DEPRECATED`
/ `ARCHIVED`), the mandatory YAML frontmatter, the Git pre-receive hook
enforcement, and the AI-assisted regeneration attestation requirement
all reflect the actual governance posture of the repository.

The honest articulation of capability gaps in Chapter 23 is itself a
governance act. Naming the planned-but-unimplemented modules
(`UIAOIdentityAssessment`, `UIAOImportAdapters`, `UIAOPlanGenerators`,
`UIAODriftDetection`), the four NIST 800-53 control families with no
corpus coverage, and the partial implementation status of the OrgPath
drift detection engine is the right governance posture for a program in
mid-execution.

The 52-week phase plan in Chapter 21 is a reasonable execution timeline
for an AD→Entra modernization sequenced against an OrgPath-anchored
dependency graph. After the scope-fence and errata are applied, the plan
remains useful as the OrgPath stream's execution view; it should not be
read as the program-level master plan.

## 5. Lifecycle status and next steps

The manuscript enters this folder in `DRAFT` status. Promotion through
the Chapter 18 lifecycle requires:

1. The author resolves the three errata in §3 in the source `.docx`, or
   commits the manuscript as Markdown in this folder with the corrections
   inline.
2. The retitled manuscript replaces "UIAO Governance OS — The Complete
   Narrative" with "UIAO OrgPath Modernization — Narrative Overview" on
   its title page and document-ID line.
3. The scope-fence in §2 is incorporated into the manuscript itself
   (either as a new "About the Scope of This Manuscript" front-matter
   chapter or as an explicit subtitle qualifier).
4. The Document Registry steward allocates `UIAO_010` (next free
   top-level slot in the `UIAO_002`–`UIAO_099` reserved range) and adds
   the corresponding entry in `src/uiao/canon/document-registry.yaml`.
5. Pull request is opened for `IN_REVIEW`; Canon Steward review proceeds
   per the Chapter 18 governance process; on approval, the document
   transitions to `APPROVED` and is moved to
   `src/uiao/canon/UIAO_010_OrgPath_Modernization_Narrative_Overview_v1.0.md`.
6. Operational use begins after `CURRENT` status is set.

Until step 5 completes, every reader of the manuscript must be referred
to this wrapper for the scope-fence and errata; the source `.docx` set
in `source-docx/` is preserved in its original form for audit and is
not the canonical reading copy.

## 6. Pointer to the assessment record

The formal assessment that produced this wrapper is recorded in
[`assessment-findings.md`](./assessment-findings.md) in this folder. It
includes the verifiable-against-canon evidence for every claim in §3
and the broader scope analysis that motivated §2.
