---
adr_id: adr-094
title: "Assessment-to-Plan PowerShell Toolchain — governed specs for UIAOImportAdapters, UIAOIdentityAssessment, UIAOPlanGenerators"
status: PROPOSED
decided: 2026-06-05
deciders: Michael Stratton
updated: 2026-06-05
next_review: 2026-12-05
review_trigger: Any of the three module specifications (UIAO_181, UIAO_182, UIAO_183) reaches implementation; Microsoft ships a native assessment-to-plan capability that subsumes UIAOPlanGenerators; the OrgPath dependency-graph model in UIAO_007 changes; the PowerShell module authoring pattern in tools/powershell/ is revised
impact: "Promotes the three 'planned' PowerShell modules named in Book_15_CPT_23 (The Gap That Remains) from ungoverned API-preview prose into governed canon specifications with UIAO_NNN allocations, a fixed build-dependency order, and shared code-signing / provenance requirements. Establishes UIAOImportAdapters (UIAO_182) and UIAOIdentityAssessment (UIAO_181) as the assessment-data producers and UIAOPlanGenerators (UIAO_183) as the downstream consumer that derives migration sequence automatically. No implementation lands in this ADR; it is the governance scaffolding that makes implementation buildable under the canon-change process (AGENTS.md I5)."
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-094-assessment-to-plan-toolchain.html
---

# ADR-094: Assessment-to-Plan PowerShell Toolchain

## Status

**PROPOSED** — June 5, 2026

## Context

The OrgPath narrative chapter [`Book_15_CPT_23.qmd`](../../../../docs/customer-documents/orgpath-narrative/Book_15_CPT_23.qmd) ("The Gap That Remains") names three PowerShell modules as having "specifications but not implementations": **UIAOIdentityAssessment**, **UIAOImportAdapters**, and **UIAOPlanGenerators**. The chapter singles out UIAOPlanGenerators as "the most consequential of the planned capabilities" because it would derive the migration sequence automatically from assessment data — computing the OrgPath dependency graph, identifying the decommissioning order for every domain controller, and turning weeks of manual architect interpretation into hours of review-and-approve.

Today those "specifications" are not governed canon. They exist only as an **API-preview table** in [`powershell-module-reference.qmd §7`](../../../../docs/customer-documents/substrate/platform-tooling/powershell-module-reference.qmd) — a function roster (six functions each) explicitly flagged "subject to change." There is:

- **No `UIAO_NNN` allocation** for any of the three modules, so they are invisible to `document-registry.yaml`, the substrate walker, and the drift engine.
- **No declared build order**, even though UIAOPlanGenerators is functionally downstream of the other two (it consumes their assessment output).
- **No shared non-functional contract** — the compliance gap analysis ([`compliance-mapping.qmd §7.3`](../../../../docs/customer-documents/uiao-orgcomp-integration/09-compliance-mapping.qmd)) already requires Authenticode signing (SI-7 / SA-10) and OSCAL-formatted output across these modules, but nothing binds them to it.

Per **AGENTS.md invariant I5**, anything under `src/uiao/canon/` — including a module specification that will govern an implementation — must flow through the canon-change process: a `UIAO_NNN` allocation plus, for a doctrinal decision like "these three modules form a toolchain with a fixed dependency order," an ADR. Implementation cannot legitimately start until that scaffolding exists. This ADR is that scaffolding.

## Decision

1. **The three modules are governed as a single assessment-to-plan toolchain**, each with its own canon specification:

   | Module | Spec | Role in the toolchain |
   |---|---|---|
   | UIAOImportAdapters | UIAO_182 | **Producer** — normalizes third-party assessment output (Azure Migrate, ScubaGear, Defender for Identity, ADRecon, GPO Analytics) into UIAO schema |
   | UIAOIdentityAssessment | UIAO_181 | **Producer** — inventories Entra ID via Microsoft Graph and reconciles it against on-prem AD |
   | UIAOPlanGenerators | UIAO_183 | **Consumer** — derives the migration sequence from the producers' assessment data |

2. **Build-dependency order is fixed: UIAOImportAdapters and UIAOIdentityAssessment before UIAOPlanGenerators.** UIAOPlanGenerators MUST NOT be implemented to read tenant or directory state directly; it consumes only the normalized assessment artifacts emitted by the two producer modules. This is what lets its OrgPath dependency-graph computation be deterministic and reviewable.

3. **The OrgPath dependency graph is the authoritative input to decommissioning order.** UIAOPlanGenerators computes domain-controller decommissioning order from the OrgPath cross-plane dependency graph defined in [`UIAO_007`](../UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) §3.1, not from an architect's manual reading. A planned sequence that contradicts a recorded cross-domain dependency is a defect in the generator, not an acceptable judgment call.

4. **Shared non-functional contract.** All three modules MUST, at implementation time:
   - Ship Authenticode-signed (`SI-7` / `SA-10`) with SHA-256 integrity hashes published in a signed manifest.
   - Emit machine-readable output that round-trips through the UIAO IR / OSCAL pipeline (so plans and assessments become canon-anchored evidence, not loose files).
   - Follow the existing PowerShell authoring pattern in `tools/powershell/` (`.psd1` manifest + `.psm1` implementation + Pester tests), as established by `OrgPathTools` and `OrgTreeValidation`.

5. **Tracking.** Closure of all three modules is tracked in the gap-closure register [`UIAO_184`](../UIAO_184_Gap_Closure_Register.md), which is the machine-readable backing for the Book 15 / Chapter 23 gap table.

## Consequences

**Positive:**

- The three modules become first-class canon: registered, drift-visible, and buildable under the normal canon-change process. Implementation PRs now have a spec to conform to rather than an "API preview subject to change."
- The dependency order is doctrine, so a future contributor cannot accidentally build UIAOPlanGenerators as a direct-read tool and lose determinism.
- The signing / OSCAL / authoring-pattern requirements are stated once, here, instead of being rediscovered per module.

**Negative / costs:**

- Three new canon specs (UIAO_181–183) plus this ADR must be maintained even before code exists; until implementation lands, `powershell-module-reference.qmd §7` and these specs must be kept consistent (the specs are now authoritative; the reference prose is derived).
- The fixed dependency order constrains implementation sequencing; a team that wanted to prototype UIAOPlanGenerators first must instead stub the producer outputs against the UIAO_182 / UIAO_181 schemas.

**Neutral:**

- No runtime behavior changes in this ADR — `src/uiao/` is untouched. The substrate walker will begin tracking UIAO_181–184 once they are registered in `document-registry.yaml`.

## Alternatives considered

- **Leave the modules as API-preview prose.** Rejected: it violates I5 (a "specification" that governs future code belongs in canon) and leaves the highest-value capability in the corpus untracked.
- **One combined spec for all three modules.** Rejected: each module has a distinct producer/consumer role and lifecycle; separate `UIAO_NNN` allocations keep drift attribution and registry traceability precise.
- **Allocate the specs but skip the ADR.** Rejected: the fixed build order and the "no direct read" constraint on UIAOPlanGenerators are doctrinal decisions, and doctrinal decisions require an ADR (I5).
