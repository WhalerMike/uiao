---
document_id: UIAO_183
title: "UIAOPlanGenerators Module Specification"
version: "0.1"
status: Draft
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-05"
publish_to_site: true
publication_style: include
---

# UIAOPlanGenerators — Module Specification

> **Status: Draft / unimplemented.** This specification governs the planned PowerShell module that [`Book_15_CPT_23`](../../../docs/customer-documents/orgpath-narrative/Book_15_CPT_23.qmd) ("The Gap That Remains") names as "the most consequential of the planned capabilities." Scaffolded by [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md); promotes the API-preview roster in [`powershell-module-reference.qmd §7.3`](../../../docs/customer-documents/substrate/platform-tooling/powershell-module-reference.qmd) into governed canon. No implementation exists yet; this document is the contract an implementation PR must satisfy.

## Purpose

UIAOPlanGenerators is the **consumer** at the end of the assessment-to-plan toolchain (ADR-094). It derives the migration sequence automatically from assessment data — computing the OrgPath dependency graph, identifying the correct decommissioning order for every domain controller from the server dependency registry, and emitting a draft migration plan that an architect reviews and approves rather than constructs from scratch. This is the capability that reduces time-from-assessment-to-approved-plan from weeks to hours and eliminates the class of sequencing errors that arise when manual interpretation misses a cross-domain dependency the assessment data already records.

## Scope

In scope: deterministic derivation of per-device, per-policy, per-identity, DNS, and PKI migration plans from normalized assessment artifacts within the M365 GCC-Moderate boundary, plus master-plan assembly. Out of scope: live tenant or directory reads of any kind — UIAOPlanGenerators consumes **only** the normalized outputs of UIAOImportAdapters ([UIAO_182](UIAO_182_UIAOImportAdapters_Module_Specification.md)) and UIAOIdentityAssessment ([UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md)).

## Function roster

| Function | Description | Key parameters |
|---|---|---|
| `New-UIAOComputerModernizationPlan` | Per-device migration plan from computer inventory | `-AssessmentPath`, `-OutputPath`, `-TargetOS` |
| `New-UIAOGPOMigrationPlan` | GPO-to-Intune migration plan | `-AssessmentPath`, `-OutputPath`, `-AnalyticsReport` |
| `New-UIAOIdentityMigrationPlan` | User/group migration roadmap (waves) | `-AssessmentPath`, `-OutputPath`, `-WaveSize` |
| `New-UIAODNSMigrationPlan` | DNS zone migration sequence and dependencies | `-AssessmentPath`, `-OutputPath` |
| `New-UIAOPKIMigrationPlan` | PKI / CA migration sequence | `-AssessmentPath`, `-OutputPath` |
| `Export-UIAOMasterPlan` | Combined modernization plan document | `-PlanPaths`, `-OutputPath`, `-Format` |

## Core algorithm — OrgPath dependency graph (ADR-094 Decision 3)

Decommissioning order is computed from the OrgPath cross-plane dependency graph defined in [`UIAO_007`](UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) §3.1, **not** from an architect's manual reading. The module:

1. Builds the dependency graph from the normalized assessment (server dependency registry + identity/DNS/PKI dependencies).
2. Topologically orders domain controllers so no controller is decommissioned before its dependents are migrated.
3. Flags any cycle or cross-domain service dependency as a blocker requiring architect resolution before the plan is approvable.

A generated sequence that contradicts a recorded cross-domain dependency is a **defect in the generator**, not an acceptable judgment call. This determinism is precisely why ADR-094 forbids UIAOPlanGenerators from reading state directly: its inputs must be the reviewable, provenance-anchored producer artifacts.

## Inputs and outputs

- **Inputs:** normalized assessment artifacts emitted by UIAO_181 and UIAO_182.
- **Outputs:** draft migration plans (per-device / GPO / identity / DNS / PKI) and an assembled master plan. Plans are draft-for-approval, never auto-applied. `New-UIAOIdentityMigrationPlan` and the POA&M-shaped outputs round-trip through the UIAO IR / OSCAL pipeline; FedRAMP-compliant POA&M output addresses `CA-5` per [`compliance-mapping.qmd §7.3`](../../../docs/customer-documents/uiao-aan-integration/09-compliance-mapping.qmd).

## Dependency position

UIAOPlanGenerators is **downstream of both producers** and per ADR-094 Decision 2 MUST be implemented after UIAO_181 and UIAO_182 (or against stubbed producer outputs conforming to their schemas).

## Non-functional contract (ADR-094 Decision 4)

- Authenticode-signed; SHA-256 hashes published in a signed manifest (`SI-7` / `SA-10`).
- Plan artifacts round-trip through the UIAO IR / OSCAL pipeline so they become canon-anchored evidence.
- Authored as `.psd1` + `.psm1` + Pester tests under `tools/powershell/UIAOPlanGenerators/`, following the `OrgPathTools` / `OrgTreeValidation` pattern.

## Drift and provenance anchoring

Each generated plan cites the assessment artifact id and version it derives from. A plan whose cited assessment no longer resolves, or whose provenance envelope is incomplete, is a `DRIFT-PROVENANCE` finding (UIAO_150 §Principle 2), detectable by `src/uiao/governance/drift.py`.

## Implementation status

**Implemented** at `tools/powershell/UIAOPlanGenerators/` (`.psd1` + `.psm1` + Pester tests, wired into the Pester CI), satisfying the function roster, the core OrgPath-dependency-graph algorithm, and the non-functional contract above. Decommissioning / migration order is computed by a deterministic topological sort (`Get-UIAOTopologicalOrder`, Kahn) of the recorded dependency edges; cycles and cross-domain service dependencies are surfaced as blockers that make a plan not approvable, never silently reordered. Each plan cites its source assessment under `derived_from` and is sealed with the canonical `content_hash` (byte-identical to `uiao.ir.models.core.canonical_hash`); the sealed plan data omits timestamps, so identical assessments yield identical plan hashes (reproducible plans). Plans consume only producer artifacts (no live reads), per ADR-094 Decision 2. Authenticode signing occurs at release packaging (`pwsh-pack`). Tracked in the gap-closure register [UIAO_184](UIAO_184_Gap_Closure_Register.md), Workstream B.
