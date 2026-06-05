# UIAOImportAdapters

Assessment-to-plan toolchain **producer** — [ADR-094](../../../src/uiao/canon/adr/adr-094-assessment-to-plan-toolchain.md) / canonical spec [UIAO_182](../../../src/uiao/canon/UIAO_182_UIAOImportAdapters_Module_Specification.md). Tracked in the gap-closure register [UIAO_184](../../../src/uiao/canon/UIAO_184_Gap_Closure_Register.md), Workstream B (Gap 3).

Read-only, file-based ingestion adapters that normalize heterogeneous third-party assessment exports into **one canonical UIAO assessment shape**, so downstream correlation, drift detection, and plan generation ([UIAOPlanGenerators](../../../src/uiao/canon/UIAO_183_UIAOPlanGenerators_Module_Specification.md)) operate over a single schema rather than vendor formats.

## Functions

| Function | Source consumed | Normalized target |
|---|---|---|
| `Import-UIAOAzureMigrateReport` | Azure Migrate assessment export (`.json`/`.csv`) | `ComputerInventory` |
| `Import-UIAOGPOAnalyticsReport` | Intune Group Policy Analytics export | `GPOMigrationTracker` |
| `Import-UIAODefenderFindings` | Defender for Identity / Secure Score | `SecurityAssessment` |
| `Import-UIAOSCuBAReport` | CISA ScubaGear output | `ConformanceEvidence` |
| `Import-UIAOADReconReport` | ADRecon Computers export (`.csv`/`.json`) | `ComputerInventory` |
| `Merge-UIAOAssessmentSources` | Multiple normalized artifacts | `AssessmentBundle` |

Helpers `ConvertTo-UIAOCanonicalJson`, `Get-UIAOContentHash`, and `New-UIAOAssessmentArtifact` are exported for composing custom adapters.

## Usage

```powershell
Import-Module ./tools/powershell/UIAOImportAdapters/UIAOImportAdapters.psd1

# Normalize a ScubaGear run into canon-anchored conformance evidence.
$art = Import-UIAOSCuBAReport -ReportPath .\ScubaResults.json `
    -OutputPath .\normalized\scuba.json -SourceVersion '1.5.0'

# Correlate several normalized sources into one bundle.
Merge-UIAOAssessmentSources -SourcePaths @('.\normalized\scuba.json', '.\normalized\computers.json') `
    -OutputPath .\bundle.json -MergeStrategy dedupe
```

Pass `-Timestamp '<ISO-8601 UTC>'` for deterministic, reproducible output (same input + timestamp ⇒ identical content hash).

## Provenance seal (DRIFT-PROVENANCE)

Every artifact is `{ schema, provenance, data }`. The `provenance` envelope carries `source`, `timestamp`, `version`, and `content_hash`, where `content_hash` is the SHA-256 of the **canonical JSON** of `data` — byte-for-byte identical to `src/uiao/ir/models/core.py::canonical_hash` (sorted keys, `(',',':')` separators, `ensure_ascii=False`, UTF-8).

This is reimplemented natively in PowerShell so the module is **offline and self-contained** (no Python at runtime). An artifact whose envelope is incomplete or whose seal no longer matches its data is a `DRIFT-PROVENANCE` finding, detectable by `src/uiao/governance/drift.py::classify_provenance_drift` (UIAO_150 §Principle 2). The Pester suite pins the canonical-JSON/hash equivalence against Python-computed ground-truth constants, so the parity is gated offline in CI.

## Input data validation (SI-10)

Adapters validate report existence and extension, tolerate vendor field-name variants, and emit a stable normalized shape. Each adapter documents the report it expects in its comment-based help (`Get-Help Import-UIAOSCuBAReport -Full`). Hardening against the full variety of real vendor exports is incremental; open an issue with a sample export to extend a mapping.

## Code signing (SI-7 / SA-10) — maintainer release step

ADR-094 Decision 4 requires the shipped module to be **Authenticode-signed with SHA-256 hashes in a signed manifest**. Signing requires the UIAO code-signing certificate and is therefore a **maintainer release action**, not a source-tree artifact. To sign a release:

```powershell
$cert = Get-ChildItem Cert:\CurrentUser\My -CodeSigningCert | Select-Object -First 1
Set-AuthenticodeSignature -FilePath .\UIAOImportAdapters.psm1, .\UIAOImportAdapters.psd1 `
    -Certificate $cert -TimestampServer 'http://timestamp.digicert.com'
New-FileCatalog -Path . -CatalogFilePath .\UIAOImportAdapters.cat -CatalogVersion 2.0
Set-AuthenticodeSignature -FilePath .\UIAOImportAdapters.cat -Certificate $cert
```

Until a signed release is cut, the implementation is complete and tested but the module is **unsigned**; treat the Workstream-B UIAOImportAdapters closure as *implemented, signing pending*.
