---
document_id: UIAO_181
title: "UIAOIdentityAssessment Module Specification"
version: "0.1"
status: Draft
classification: CANONICAL
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-05"
boundary: GCC-Moderate
publish_to_site: true
publication_style: include
---

# UIAOIdentityAssessment — Module Specification

> **Status: Draft / unimplemented.** This specification governs a planned PowerShell module named in [`Book_15_CPT_23`](../../../docs/customer-documents/orgpath-narrative/Book_15_CPT_23.qmd) ("The Gap That Remains") and scaffolded by [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md). It promotes the API-preview roster in [`powershell-module-reference.qmd §7.1`](../../../docs/customer-documents/substrate/platform-tooling/powershell-module-reference.qmd) into governed canon. No implementation exists yet; this document is the contract an implementation PR must satisfy.

## Purpose

UIAOIdentityAssessment is a **producer** in the assessment-to-plan toolchain (ADR-094). It performs hybrid identity assessment by inventorying Entra ID through Microsoft Graph and reconciling that inventory against on-premises Active Directory, emitting a normalized identity assessment that UIAOPlanGenerators consumes.

## Scope

In scope: read-only inventory of Entra ID identity objects (users, groups, app registrations, service principals, Conditional Access policies) within the M365 GCC-Moderate boundary, and AD-vs-Entra reconciliation. Out of scope: third-party report ingestion (that is UIAOImportAdapters, [UIAO_182](UIAO_182_UIAOImportAdapters_Module_Specification.md)); plan derivation (that is UIAOPlanGenerators, [UIAO_183](UIAO_183_UIAOPlanGenerators_Module_Specification.md)).

## Function roster

| Function | Description | Key parameters |
|---|---|---|
| `Export-UIAOEntraUsers` | Entra ID user inventory via Microsoft Graph | `-TenantId`, `-OutputPath` |
| `Export-UIAOEntraGroups` | Entra ID groups and memberships | `-TenantId`, `-OutputPath`, `-IncludeDynamic` |
| `Export-UIAOEntraApps` | App registrations and service principals | `-TenantId`, `-OutputPath` |
| `Export-UIAOConditionalAccess` | Conditional Access policy inventory | `-TenantId`, `-OutputPath` |
| `Compare-UIAOIdentitySources` | AD-vs-Entra reconciliation report | `-ADAssessmentPath`, `-EntraAssessmentPath`, `-OutputPath` |
| `Invoke-UIAOIdentityAssessment` | Master orchestrator for the assessment | `-TenantId`, `-Domain`, `-OutputPath` |

## Graph endpoint resolution

Live Graph reads MUST resolve their endpoint via the cloud-aware resolution convention (the PowerShell analogue of `uiao.adapters._graph_clouds.resolve_graph_base`), defaulting to the boundary appropriate for GCC-Moderate, rather than hardcoding a Graph hostname. Unknown clouds fail closed.

## Inputs and outputs

- **Inputs:** a tenant id and (for reconciliation) an on-prem AD assessment path. The AD side may itself be produced by UIAOImportAdapters (e.g., an ADRecon import).
- **Outputs:** UIAO-schema JSON identity assessment artifacts and an AD-vs-Entra reconciliation report, consumable by UIAOPlanGenerators and the UIAO IR / OSCAL pipeline.

## Dependency position

UIAOIdentityAssessment has **no upstream toolchain dependency** and is one of the two producers that UIAOPlanGenerators consumes. Per ADR-094 Decision 2 it must be implementable before UIAOPlanGenerators.

## Non-functional contract (ADR-094 Decision 4)

- Authenticode-signed; SHA-256 hashes published in a signed manifest (`SI-7` / `SA-10`).
- Output round-trips through the UIAO IR / OSCAL pipeline so assessments become canon-anchored evidence.
- Authored as `.psd1` + `.psm1` + Pester tests under `tools/powershell/UIAOIdentityAssessment/`, following the `OrgPathTools` / `OrgTreeValidation` pattern.

## Drift and provenance anchoring

Identity assessment artifacts carry a provenance envelope (tenant id, Graph API version, capture timestamp). Identity-object inconsistencies surfaced during reconciliation (orphaned, missing, or lifecycle-inconsistent principals) map to `DRIFT-IDENTITY`; an assessment artifact with a broken or unattributed envelope is `DRIFT-PROVENANCE`, per `src/uiao/governance/drift.py`.

## Implementation status

Unimplemented. Tracked in the gap-closure register [UIAO_184](UIAO_184_Gap_Closure_Register.md), Workstream B.
