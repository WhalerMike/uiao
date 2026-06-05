---
document_id: UIAO_182
title: "UIAOImportAdapters Module Specification"
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

# UIAOImportAdapters — Module Specification

> **Status: Draft / unimplemented.** This specification governs a planned PowerShell module named in [`Book_15_CPT_23`](../../../docs/customer-documents/orgpath-narrative/Book_15_CPT_23.qmd) ("The Gap That Remains") and scaffolded by [ADR-094](adr/adr-094-assessment-to-plan-toolchain.md). It promotes the API-preview roster in [`powershell-module-reference.qmd §7.2`](../../../docs/customer-documents/substrate/platform-tooling/powershell-module-reference.qmd) into governed canon. No implementation exists yet; this document is the contract an implementation PR must satisfy.

## Purpose

UIAOImportAdapters is a **producer** in the assessment-to-plan toolchain (ADR-094). It provides ingestion adapters for third-party assessment tools, normalizing their heterogeneous output into the UIAO schema so that downstream correlation, drift detection, and plan generation operate over one canonical assessment shape rather than vendor-specific exports.

## Scope

In scope: read-only ingestion and schema-normalization of pre-produced third-party assessment artifacts within the M365 GCC-Moderate boundary. Out of scope: live tenant or directory reads (that is UIAOIdentityAssessment, [UIAO_181](UIAO_181_UIAOIdentityAssessment_Module_Specification.md)); plan derivation (that is UIAOPlanGenerators, [UIAO_183](UIAO_183_UIAOPlanGenerators_Module_Specification.md)).

## Function roster

| Function | Source consumed | Normalized target | Notes |
|---|---|---|---|
| `Import-UIAOAzureMigrateReport` | Azure Migrate assessment export | UIAO `ComputerInventory` | `-ReportPath`, `-OutputPath` |
| `Import-UIAOGPOAnalyticsReport` | Intune Group Policy Analytics export | `GPOMigrationTracker` | `-ReportPath`, `-OutputPath` |
| `Import-UIAODefenderFindings` | Defender for Identity Secure Score | `SecurityAssessment` overlay | `-ReportPath`, `-OutputPath` |
| `Import-UIAOSCuBAReport` | CISA ScubaGear compliance output | UIAO conformance evidence | `-ReportPath`, `-OutputPath` |
| `Import-UIAOADReconReport` | ADRecon Excel output | UIAO `ComputerInventory` / identity | `-ReportPath`, `-OutputPath` |
| `Merge-UIAOAssessmentSources` | Multiple normalized sources | Correlated assessment bundle | `-SourcePaths`, `-OutputPath`, `-MergeStrategy` |

## Inputs and outputs

- **Inputs:** file-path references to already-produced third-party reports. The module never reaches a live API; it consumes artifacts an operator or another tool has exported.
- **Outputs:** UIAO-schema JSON normalized assessment artifacts, suitable as input to UIAOPlanGenerators and as canon-anchored evidence through the UIAO IR / OSCAL pipeline.

## Dependency position

UIAOImportAdapters has **no upstream toolchain dependency** and is one of the two producers that UIAOPlanGenerators consumes. Per ADR-094 Decision 2 it must be implementable before UIAOPlanGenerators.

## Non-functional contract (ADR-094 Decision 4)

- Authenticode-signed; SHA-256 hashes published in a signed manifest (`SI-7` / `SA-10`).
- Output round-trips through the UIAO IR / OSCAL pipeline so imported assessments become canon-anchored evidence.
- Authored as `.psd1` + `.psm1` + Pester tests under `tools/powershell/UIAOImportAdapters/`, following the `OrgPathTools` / `OrgTreeValidation` pattern.
- Input data validation and sanitization are documented as a control surface (`SI-10`), per [`compliance-mapping.qmd §7.3`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd).

## Drift and provenance anchoring

Normalized artifacts carry a provenance envelope (source tool, export version, import timestamp). An imported artifact whose envelope is incomplete or whose integrity hash no longer matches its data is a `DRIFT-PROVENANCE` finding by definition (UIAO_150 §Principle 2), detectable by the in-memory classifier in `src/uiao/governance/drift.py`.

## Implementation status

**Implemented** at `tools/powershell/UIAOImportAdapters/` (`.psd1` + `.psm1` + Pester tests, wired into the Pester CI), satisfying the function roster and non-functional contract above. The provenance seal (`content_hash`) is computed by the canonical Python hasher so it is byte-identical to `uiao.ir.models.core.canonical_hash`, making imported artifacts directly `DRIFT-PROVENANCE`-classifiable by `src/uiao/governance/drift.py`. Authenticode signing occurs at release packaging (`pwsh-pack`). Tracked in the gap-closure register [UIAO_184](UIAO_184_Gap_Closure_Register.md), Workstream B.
