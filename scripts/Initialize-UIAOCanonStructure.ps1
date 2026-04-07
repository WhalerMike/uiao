<#
.SYNOPSIS
    Initialize-UIAOCanonStructure.ps1
    Scaffolds the full UIAO Governance Canon directory structure across
    uiao-docs and uiao-core. Guards against overwrites. Supports -WhatIf.

.DESCRIPTION
    Creates all missing directories and placeholder stub files for the
    hierarchical appendix canon (A-01 through E-03), 23 ADRs (ADR-005
    through ADR-027), canon docs, diagrams, onboarding, exports, and the
    uiao-core CANON_POINTER.md. Existing files are NEVER overwritten.
    mkdocs.yml is backed up with a timestamp before replacement.

.PARAMETER DocsRoot
    Path to local uiao-docs repo root. Default: C:\Users\whale\uiao-docs

.PARAMETER CoreRoot
    Path to local uiao-core repo root. Default: C:\Users\whale\uiao-core

.PARAMETER WhatIf
    Preview all actions without writing anything.

.EXAMPLE
    .\Initialize-UIAOCanonStructure.ps1 -WhatIf
    .\Initialize-UIAOCanonStructure.ps1
    .\Initialize-UIAOCanonStructure.ps1 -DocsRoot "D:\repos\uiao-docs" -CoreRoot "D:\repos\uiao-core"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$DocsRoot = "C:\Users\whale\uiao-docs",
    [string]$CoreRoot = "C:\Users\whale\uiao-core"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:DirsCreated  = 0
$script:FilesCreated = 0
$script:FilesSkipped = 0
$script:DirsSkipped  = 0

# ---------------------------------------------------------------------------
# Helper: create a directory if it does not exist
# ---------------------------------------------------------------------------
function New-Dir {
    param([string]$Path)
    if (Test-Path $Path) {
        Write-Host "  [SKIP DIR]  $Path" -ForegroundColor DarkGray
        $script:DirsSkipped++
    } else {
        if ($PSCmdlet.ShouldProcess($Path, "Create directory")) {
            New-Item -ItemType Directory -Path $Path -Force | Out-Null
            Write-Host "  [DIR]       $Path" -ForegroundColor Green
            $script:DirsCreated++
        }
    }
}

# ---------------------------------------------------------------------------
# Helper: create a stub file if it does not exist
# ---------------------------------------------------------------------------
function New-Stub {
    param([string]$Path, [string]$Content)
    if (Test-Path $Path) {
        Write-Host "  [SKIP FILE] $Path" -ForegroundColor DarkGray
        $script:FilesSkipped++
    } else {
        if ($PSCmdlet.ShouldProcess($Path, "Create file")) {
            Set-Content -Path $Path -Value $Content -Encoding UTF8
            Write-Host "  [FILE]      $Path" -ForegroundColor Cyan
            $script:FilesCreated++
        }
    }
}

# ---------------------------------------------------------------------------
# Helper: back up mkdocs.yml with timestamp
# ---------------------------------------------------------------------------
function Backup-MkDocs {
    param([string]$MkDocsPath)
    if (Test-Path $MkDocsPath) {
        $ts     = Get-Date -Format "yyyyMMdd-HHmmss"
        $backup = "${MkDocsPath}.backup-${ts}"
        if ($PSCmdlet.ShouldProcess($backup, "Backup mkdocs.yml")) {
            Copy-Item -Path $MkDocsPath -Destination $backup
            Write-Host "  [BACKUP]    $MkDocsPath -> $backup" -ForegroundColor Yellow
        }
    }
}

# ---------------------------------------------------------------------------
# Content generators
# ---------------------------------------------------------------------------
function Get-CanonStub {
    param([string]$Title)
    return @"
---
title: "$Title"
status: MISSING
---

# $Title

> **Status:** MISSING - Awaiting population from canonical source.

<!-- TODO: Populate from UIAO Governance Canon Master Document -->
"@
}

function Get-FamilyIndexStub {
    param([string]$FamilyTitle, [string]$FamilyId, [string[]]$SubItems)
    $links = ($SubItems | ForEach-Object {
        $slug = $_.ToLower() -replace "[^a-z0-9]+", "-"
        "- [$_](./$slug.md)"
    }) -join "`n"
    return @"
---
title: "$FamilyTitle"
family_id: "$FamilyId"
status: MISSING
---

# $FamilyTitle

> **Status:** MISSING - Awaiting population from canonical source.

## Sub-Appendices

$links

## Overview

<!-- TODO: Describe this appendix family -->

## Cross-Plane Summary

<!-- TODO: Summarize cross-plane relationships -->
"@
}

function Get-AppendixStub {
    param([string]$Title, [string]$Family, [string]$SubId)
    return @"
---
title: "$Title"
family: "$Family"
sub_appendix: "$SubId"
status: MISSING
adrs: []
cross_plane_dependencies: []
---

# $Title

> **Status:** MISSING - Awaiting population from canonical source.
> **Sub-Appendix:** $SubId | **Family:** $Family

## Purpose

<!-- TODO: Describe the purpose of this sub-appendix -->

## Scope

<!-- TODO: Define what is in and out of scope -->

## Related ADRs

<!-- TODO: List ADR numbers and titles -->

## Cross-Plane Dependencies

<!-- TODO: List dependencies on other appendix families -->

## Governance Rules

<!-- TODO: List applicable governance rules (CR-001 through CR-004) -->

## Implementation Status

<!-- TODO: Describe current implementation state -->
"@
}

function Get-AdrStub {
    param([string]$AdrId, [string]$Title, [string]$Family)
    $dt = Get-Date -Format "yyyy-MM-dd"
    return @"
---
adr_id: "$AdrId"
title: "$Title"
family: "$Family"
status: "Proposed"
date: "$dt"
---

# $AdrId - $Title

> **Status:** Proposed - [NEW (Proposed)] awaiting ratification.
> **Family:** $Family

## Context

<!-- TODO: Describe the context and problem statement -->

## Decision

<!-- MISSING - Awaiting ratification content -->

## Consequences

<!-- MISSING - Awaiting ratification content -->

## Rationale

<!-- TODO: Describe the rationale for this decision -->

## Related ADRs

<!-- TODO: List related ADR IDs -->
"@
}

function Get-DiagramPageStub {
    param([string]$Title, [string]$PumlFile)
    return @"
---
title: "$Title"
---

# $Title

> Rendered from diagrams/$PumlFile

See raw source: [diagrams/$PumlFile](../../diagrams/$PumlFile)

```plantuml
@startuml
' PLACEHOLDER - Replace with full PlantUML source from Copilot task.
' File: $PumlFile
@enduml
```
"@
}

function Get-CanonPointer {
    return @"
# CANON POINTER

The UIAO Governance Canon lives exclusively in:

  https://github.com/WhalerMike/uiao-docs

Do NOT duplicate canon content in this repository (uiao-core).
uiao-core contains machine artifacts only:
- Adapter schemas and transforms
- KSI evaluation scripts and rules
- Provenance manifests
- GitHub Actions workflows
"@
}

function Get-SummaryMd {
    return @"
# Summary

## Canon Overview
* [Introduction](README.md)
* [Canonical Rules](canon/canonical-rules.md)
* [Glossary](canon/glossary.md)
* [Migration Plan](canon/migration-plan.md)
* [PDF Book Layout Specification](canon/pdf-layout-spec.md)

## Appendix A - Adapter Plane
* [Adapter Plane Overview](appendix/a-adapter-plane/index.md)
* [A-01 Adapter Lifecycle](appendix/a-adapter-plane/a-01-adapter-lifecycle.md)
* [A-02 Adapter Sandbox Execution](appendix/a-adapter-plane/a-02-adapter-sandbox-execution.md)
* [A-03 Adapter Hot-Swap and Rollback](appendix/a-adapter-plane/a-03-adapter-hot-swap-rollback.md)
* [A-04 Adapter Health and Liveness](appendix/a-adapter-plane/a-04-adapter-health-liveness.md)

## Appendix B - Truth Fabric
* [Truth Fabric Overview](appendix/b-truth-fabric/index.md)
* [B-01 Canonical Claim Schema](appendix/b-truth-fabric/b-01-canonical-claim-schema.md)
* [B-02 Identity Anchoring](appendix/b-truth-fabric/b-02-identity-anchoring.md)
* [B-03 Multi-Cloud Identity Matrix](appendix/b-truth-fabric/b-03-multi-cloud-identity-matrix.md)
* [B-04 Control Mapping Governance](appendix/b-truth-fabric/b-04-control-mapping-governance.md)

## Appendix C - Drift Fabric
* [Drift Fabric Overview](appendix/c-drift-fabric/index.md)
* [C-01 Drift Detection](appendix/c-drift-fabric/c-01-drift-detection.md)
* [C-02 Drift Taxonomy](appendix/c-drift-fabric/c-02-drift-taxonomy.md)
* [C-03 Vendor Failure Containment](appendix/c-drift-fabric/c-03-vendor-failure-containment.md)

## Appendix D - Evidence Fabric
* [Evidence Fabric Overview](appendix/d-evidence-fabric/index.md)
* [D-01 Evidence Determinism](appendix/d-evidence-fabric/d-01-evidence-determinism.md)
* [D-02 Evidence Lifecycle](appendix/d-evidence-fabric/d-02-evidence-lifecycle.md)
* [D-03 Evidence Signing](appendix/d-evidence-fabric/d-03-evidence-signing.md)
* [D-04 Evidence Correlation](appendix/d-evidence-fabric/d-04-evidence-correlation.md)

## Appendix E - Governance Plane
* [Governance Plane Overview](appendix/e-governance-plane/index.md)
* [E-01 ARB Coordination](appendix/e-governance-plane/e-01-arb-coordination.md)
* [E-02 Mission-Partner Corridors](appendix/e-governance-plane/e-02-mission-partner-corridors.md)
* [E-03 Cross-Fabric Consistency](appendix/e-governance-plane/e-03-cross-fabric-consistency.md)

## Architecture Decision Records
* [ADR Index](adr/index.md)
* [ADR-005 Canonical Claim Schema Standardization](adr/adr-005-canonical-claim-schema.md)
* [ADR-006 Evidence Fabric Determinism Guarantees](adr/adr-006-evidence-determinism.md)
* [ADR-007 Multi-Cloud Adapter Strategy](adr/adr-007-multi-cloud-adapter.md)
* [ADR-008 Zero-Trust Identity Anchoring](adr/adr-008-zero-trust-identity.md)
* [ADR-009 Drift Ledger Immutability](adr/adr-009-drift-ledger-immutability.md)
* [ADR-010 Vendor Baseline Versioning](adr/adr-010-vendor-baseline-versioning.md)
* [ADR-011 Multi-Adapter Correlation Rules](adr/adr-011-multi-adapter-correlation.md)
* [ADR-012 Canonical Drift Taxonomy](adr/adr-012-canonical-drift-taxonomy.md)
* [ADR-013 Adapter Failure Isolation](adr/adr-013-adapter-failure-isolation.md)
* [ADR-014 Canonical Evidence Severity Model](adr/adr-014-evidence-severity-model.md)
* [ADR-015 Adapter Extensibility Framework](adr/adr-015-adapter-extensibility.md)
* [ADR-016 Evidence Bundle Lifecycle](adr/adr-016-evidence-bundle-lifecycle.md)
* [ADR-017 Adapter Sandbox Execution Model](adr/adr-017-adapter-sandbox-execution.md)
* [ADR-018 Mission-Channel Enforcement Guarantees](adr/adr-018-mission-channel-enforcement.md)
* [ADR-019 Vendor Failure Containment Model](adr/adr-019-vendor-failure-containment.md)
* [ADR-020 Evidence Correlation Determinism](adr/adr-020-evidence-correlation-determinism.md)
* [ADR-021 Adapter Hot-Swap and Rollback Strategy](adr/adr-021-adapter-hot-swap-rollback.md)
* [ADR-022 Canonical Evidence Compression Strategy](adr/adr-022-evidence-compression.md)
* [ADR-023 Adapter Concurrency and Parallelism](adr/adr-023-adapter-concurrency.md)
* [ADR-024 Canonical Evidence Diffing Strategy](adr/adr-024-evidence-diffing.md)
* [ADR-025 Adapter Health and Liveness Guarantees](adr/adr-025-adapter-health-liveness.md)
* [ADR-026 Canonical Evidence Lifecycle Guarantees](adr/adr-026-evidence-lifecycle-guarantees.md)
* [ADR-027 Adapter Retirement and Deprecation](adr/adr-027-adapter-retirement.md)

## Onboarding
* [Onboarding Index](onboarding/index.md)
* [Adapter Developer Guide](onboarding/adapter-developer-guide.md)

## Diagrams
* [Diagram Index](diagrams/index.md)
* [Master Governance Hierarchy](diagrams/governance-hierarchy.md)
* [Adapter Plane Dependencies](diagrams/adapter-plane.md)
* [Truth Fabric Dependencies](diagrams/truth-fabric.md)
* [Drift Fabric Dependencies](diagrams/drift-fabric.md)
* [Evidence Fabric Dependencies](diagrams/evidence-fabric.md)
* [Governance Plane Dependencies](diagrams/governance-plane.md)
"@
}

# ---------------------------------------------------------------------------
# Data: ADR definitions
# ---------------------------------------------------------------------------
$Adrs = @(
    @{ Id="ADR-005"; Title="Canonical Claim Schema Standardization";    Family="B - Truth Fabric";     File="adr-005-canonical-claim-schema" }
    @{ Id="ADR-006"; Title="Evidence Fabric Determinism Guarantees";    Family="D - Evidence Fabric";  File="adr-006-evidence-determinism" }
    @{ Id="ADR-007"; Title="Multi-Cloud Adapter Strategy";              Family="B - Truth Fabric";     File="adr-007-multi-cloud-adapter" }
    @{ Id="ADR-008"; Title="Zero-Trust Identity Anchoring";             Family="B - Truth Fabric";     File="adr-008-zero-trust-identity" }
    @{ Id="ADR-009"; Title="Drift Ledger Immutability";                 Family="C - Drift Fabric";     File="adr-009-drift-ledger-immutability" }
    @{ Id="ADR-010"; Title="Vendor Baseline Versioning";                Family="B - Truth Fabric";     File="adr-010-vendor-baseline-versioning" }
    @{ Id="ADR-011"; Title="Multi-Adapter Correlation Rules";           Family="B - Truth Fabric";     File="adr-011-multi-adapter-correlation" }
    @{ Id="ADR-012"; Title="Canonical Drift Taxonomy";                  Family="C - Drift Fabric";     File="adr-012-canonical-drift-taxonomy" }
    @{ Id="ADR-013"; Title="Adapter Failure Isolation";                 Family="A - Adapter Plane";    File="adr-013-adapter-failure-isolation" }
    @{ Id="ADR-014"; Title="Canonical Evidence Severity Model";         Family="D - Evidence Fabric";  File="adr-014-evidence-severity-model" }
    @{ Id="ADR-015"; Title="Adapter Extensibility Framework";           Family="A - Adapter Plane";    File="adr-015-adapter-extensibility" }
    @{ Id="ADR-016"; Title="Evidence Bundle Lifecycle";                 Family="D - Evidence Fabric";  File="adr-016-evidence-bundle-lifecycle" }
    @{ Id="ADR-017"; Title="Adapter Sandbox Execution Model";           Family="A - Adapter Plane";    File="adr-017-adapter-sandbox-execution" }
    @{ Id="ADR-018"; Title="Mission-Channel Enforcement Guarantees";    Family="E - Governance Plane"; File="adr-018-mission-channel-enforcement" }
    @{ Id="ADR-019"; Title="Vendor Failure Containment Model";          Family="C - Drift Fabric";     File="adr-019-vendor-failure-containment" }
    @{ Id="ADR-020"; Title="Evidence Correlation Determinism";          Family="D - Evidence Fabric";  File="adr-020-evidence-correlation-determinism" }
    @{ Id="ADR-021"; Title="Adapter Hot-Swap and Rollback Strategy";    Family="A - Adapter Plane";    File="adr-021-adapter-hot-swap-rollback" }
    @{ Id="ADR-022"; Title="Canonical Evidence Compression Strategy";   Family="D - Evidence Fabric";  File="adr-022-evidence-compression" }
    @{ Id="ADR-023"; Title="Adapter Concurrency and Parallelism";       Family="A - Adapter Plane";    File="adr-023-adapter-concurrency" }
    @{ Id="ADR-024"; Title="Canonical Evidence Diffing Strategy";       Family="D - Evidence Fabric";  File="adr-024-evidence-diffing" }
    @{ Id="ADR-025"; Title="Adapter Health and Liveness Guarantees";    Family="A - Adapter Plane";    File="adr-025-adapter-health-liveness" }
    @{ Id="ADR-026"; Title="Canonical Evidence Lifecycle Guarantees";   Family="D - Evidence Fabric";  File="adr-026-evidence-lifecycle-guarantees" }
    @{ Id="ADR-027"; Title="Adapter Retirement and Deprecation";        Family="A - Adapter Plane";    File="adr-027-adapter-retirement" }
)

# ---------------------------------------------------------------------------
# Data: Appendix family definitions
# ---------------------------------------------------------------------------
$Families = @(
    @{
        Id="a-adapter-plane"; Title="Appendix A - Adapter Plane"; FamilyId="A"
        Subs=@(
            @{ SubId="A-01"; Title="Adapter Lifecycle";           File="a-01-adapter-lifecycle" }
            @{ SubId="A-02"; Title="Adapter Sandbox Execution";   File="a-02-adapter-sandbox-execution" }
            @{ SubId="A-03"; Title="Adapter Hot-Swap and Rollback"; File="a-03-adapter-hot-swap-rollback" }
            @{ SubId="A-04"; Title="Adapter Health and Liveness"; File="a-04-adapter-health-liveness" }
        )
    }
    @{
        Id="b-truth-fabric"; Title="Appendix B - Truth Fabric"; FamilyId="B"
        Subs=@(
            @{ SubId="B-01"; Title="Canonical Claim Schema";       File="b-01-canonical-claim-schema" }
            @{ SubId="B-02"; Title="Identity Anchoring";           File="b-02-identity-anchoring" }
            @{ SubId="B-03"; Title="Multi-Cloud Identity Matrix";  File="b-03-multi-cloud-identity-matrix" }
            @{ SubId="B-04"; Title="Control Mapping Governance";   File="b-04-control-mapping-governance" }
        )
    }
    @{
        Id="c-drift-fabric"; Title="Appendix C - Drift Fabric"; FamilyId="C"
        Subs=@(
            @{ SubId="C-01"; Title="Drift Detection";              File="c-01-drift-detection" }
            @{ SubId="C-02"; Title="Drift Taxonomy";               File="c-02-drift-taxonomy" }
            @{ SubId="C-03"; Title="Vendor Failure Containment";   File="c-03-vendor-failure-containment" }
        )
    }
    @{
        Id="d-evidence-fabric"; Title="Appendix D - Evidence Fabric"; FamilyId="D"
        Subs=@(
            @{ SubId="D-01"; Title="Evidence Determinism";         File="d-01-evidence-determinism" }
            @{ SubId="D-02"; Title="Evidence Lifecycle";           File="d-02-evidence-lifecycle" }
            @{ SubId="D-03"; Title="Evidence Signing";             File="d-03-evidence-signing" }
            @{ SubId="D-04"; Title="Evidence Correlation";         File="d-04-evidence-correlation" }
        )
    }
    @{
        Id="e-governance-plane"; Title="Appendix E - Governance Plane"; FamilyId="E"
        Subs=@(
            @{ SubId="E-01"; Title="ARB Coordination";             File="e-01-arb-coordination" }
            @{ SubId="E-02"; Title="Mission-Partner Corridors";    File="e-02-mission-partner-corridors" }
            @{ SubId="E-03"; Title="Cross-Fabric Consistency";     File="e-03-cross-fabric-consistency" }
        )
    }
)

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host "  UIAO Canon Structure Initializer" -ForegroundColor Magenta
Write-Host "  uiao-docs : $DocsRoot" -ForegroundColor Magenta
Write-Host "  uiao-core : $CoreRoot" -ForegroundColor Magenta
if ($WhatIfPreference) { Write-Host "  MODE      : WhatIf (no writes)" -ForegroundColor Yellow }
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host ""

# Validate roots exist
foreach ($root in @($DocsRoot, $CoreRoot)) {
    if (-not (Test-Path $root)) {
        Write-Error "Root path not found: $root  -- Aborting."
        exit 1
    }
}

# Backup mkdocs.yml
Write-Host "-- Backing up mkdocs.yml --" -ForegroundColor Magenta
Backup-MkDocs -MkDocsPath (Join-Path $DocsRoot "mkdocs.yml")

# Root-level: SUMMARY.md
Write-Host ""
Write-Host "-- Root-level files --" -ForegroundColor Magenta
New-Stub -Path (Join-Path $DocsRoot "SUMMARY.md") -Content (Get-SummaryMd)

# exports/
Write-Host ""
Write-Host "-- exports/ --" -ForegroundColor Magenta
$exportsDir = Join-Path $DocsRoot "exports"
New-Dir  -Path $exportsDir
New-Stub -Path (Join-Path $exportsDir "README.md") -Content "# exports/`n`nDrop the following files here after downloading from the Copilot publishing task:`n`n- UIAO Governance Canon - Master Publishing Document.docx`n- UIAO Governance Canon - Canonical Index.xlsx"

# diagrams/ (root PlantUML source files)
Write-Host ""
Write-Host "-- diagrams/ (root PlantUML sources) --" -ForegroundColor Magenta
$diagramsRoot = Join-Path $DocsRoot "diagrams"
New-Dir -Path $diagramsRoot
foreach ($puml in @(
    "uiao-governance-hierarchy.puml",
    "uiao-adapter-plane.puml",
    "uiao-truth-fabric.puml",
    "uiao-drift-fabric.puml",
    "uiao-evidence-fabric.puml",
    "uiao-governance-plane.puml"
)) {
    New-Stub -Path (Join-Path $diagramsRoot $puml) -Content "@startuml`n' PLACEHOLDER - replace with full PlantUML source from Copilot task.`n' File: $puml`n@enduml"
}

# docs/canon/
Write-Host ""
Write-Host "-- docs/canon/ --" -ForegroundColor Magenta
$canonDir = Join-Path $DocsRoot (Join-Path "docs" "canon")
New-Dir  -Path $canonDir
New-Stub -Path (Join-Path $canonDir "index.md")           -Content (Get-CanonStub "Canon Overview")
New-Stub -Path (Join-Path $canonDir "canonical-rules.md") -Content (Get-CanonStub "Canonical Rules - CR-001 through CR-004")
New-Stub -Path (Join-Path $canonDir "glossary.md")        -Content (Get-CanonStub "UIAO Canonical Glossary (44 Terms)")
New-Stub -Path (Join-Path $canonDir "migration-plan.md")  -Content (Get-CanonStub "Migration Plan - Flat to Hierarchical A-01 through E-03")
New-Stub -Path (Join-Path $canonDir "pdf-layout-spec.md") -Content (Get-CanonStub "PDF Book Layout Specification")

# docs/appendix/{family}/
Write-Host ""
Write-Host "-- docs/appendix/{family}/ --" -ForegroundColor Magenta
foreach ($fam in $Families) {
    $famDir = Join-Path $DocsRoot (Join-Path "docs" (Join-Path "appendix" $fam.Id))
    New-Dir -Path $famDir
    $subTitles = $fam.Subs | ForEach-Object { "$($_.SubId) $($_.Title)" }
    New-Stub -Path (Join-Path $famDir "index.md") `
             -Content (Get-FamilyIndexStub -FamilyTitle $fam.Title -FamilyId $fam.FamilyId -SubItems $subTitles)
    foreach ($sub in $fam.Subs) {
        New-Stub -Path (Join-Path $famDir "$($sub.File).md") `
                 -Content (Get-AppendixStub -Title "$($sub.SubId) $($sub.Title)" -Family $fam.Title -SubId $sub.SubId)
    }
}

# docs/adr/ — new hierarchical ADR stubs (guards existing .qmd files)
Write-Host ""
Write-Host "-- docs/adr/ (hierarchical ADR stubs) --" -ForegroundColor Magenta
$adrDir = Join-Path $DocsRoot (Join-Path "docs" "adr")
New-Dir -Path $adrDir
$adrLinks = ($Adrs | ForEach-Object { "- [$($_.Id) - $($_.Title)](./$($_.File).md)" }) -join "`n"
New-Stub -Path (Join-Path $adrDir "index.md") -Content "---`ntitle: ADR Index`n---`n`n# Architecture Decision Records`n`n$adrLinks"
foreach ($adr in $Adrs) {
    New-Stub -Path (Join-Path $adrDir "$($adr.File).md") `
             -Content (Get-AdrStub -AdrId $adr.Id -Title $adr.Title -Family $adr.Family)
}

# docs/diagrams/
Write-Host ""
Write-Host "-- docs/diagrams/ --" -ForegroundColor Magenta
$docsDiagDir = Join-Path $DocsRoot (Join-Path "docs" "diagrams")
New-Dir -Path $docsDiagDir
New-Stub -Path (Join-Path $docsDiagDir "index.md") -Content "---`ntitle: Diagram Gallery`n---`n`n# UIAO Governance Diagrams`n`n| Diagram | Description |`n|---|---|`n| [Master Governance Hierarchy](./governance-hierarchy.md) | Full hierarchical taxonomy A through E |`n| [Adapter Plane](./adapter-plane.md) | Appendix A dependencies |`n| [Truth Fabric](./truth-fabric.md) | Appendix B dependencies |`n| [Drift Fabric](./drift-fabric.md) | Appendix C dependencies |`n| [Evidence Fabric](./evidence-fabric.md) | Appendix D dependencies |`n| [Governance Plane](./governance-plane.md) | Appendix E dependencies |"
foreach ($dp in @(
    @{ File="governance-hierarchy"; Title="Master Governance Hierarchy Diagram";      Puml="uiao-governance-hierarchy.puml" }
    @{ File="adapter-plane";        Title="Appendix A - Adapter Plane Dependencies";  Puml="uiao-adapter-plane.puml" }
    @{ File="truth-fabric";         Title="Appendix B - Truth Fabric Dependencies";   Puml="uiao-truth-fabric.puml" }
    @{ File="drift-fabric";         Title="Appendix C - Drift Fabric Dependencies";   Puml="uiao-drift-fabric.puml" }
    @{ File="evidence-fabric";      Title="Appendix D - Evidence Fabric Dependencies"; Puml="uiao-evidence-fabric.puml" }
    @{ File="governance-plane";     Title="Appendix E - Governance Plane Dependencies"; Puml="uiao-governance-plane.puml" }
)) {
    New-Stub -Path (Join-Path $docsDiagDir "$($dp.File).md") `
             -Content (Get-DiagramPageStub -Title $dp.Title -PumlFile $dp.Puml)
}

# docs/onboarding/
Write-Host ""
Write-Host "-- docs/onboarding/ --" -ForegroundColor Magenta
$onboardDir = Join-Path $DocsRoot (Join-Path "docs" "onboarding")
New-Dir  -Path $onboardDir
New-Stub -Path (Join-Path $onboardDir "index.md") `
         -Content "---`ntitle: Onboarding`n---`n`n# Onboarding`n`n- [Adapter Developer Guide](./adapter-developer-guide.md)"
New-Stub -Path (Join-Path $onboardDir "adapter-developer-guide.md") `
         -Content (Get-CanonStub "Adapter Developer Onboarding Guide")

# uiao-core/docs/CANON_POINTER.md
Write-Host ""
Write-Host "-- uiao-core/docs/CANON_POINTER.md --" -ForegroundColor Magenta
$coreDocsDir = Join-Path $CoreRoot "docs"
New-Dir  -Path $coreDocsDir
New-Stub -Path (Join-Path $coreDocsDir "CANON_POINTER.md") -Content (Get-CanonPointer)

# Summary
Write-Host ""
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host "  COMPLETE" -ForegroundColor Green
Write-Host "  Directories created : $script:DirsCreated"  -ForegroundColor Green
Write-Host "  Directories skipped : $script:DirsSkipped"  -ForegroundColor DarkGray
Write-Host "  Files created       : $script:FilesCreated" -ForegroundColor Cyan
Write-Host "  Files skipped       : $script:FilesSkipped" -ForegroundColor DarkGray
Write-Host "================================================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Paste 6 PlantUML sources into diagrams/*.puml" -ForegroundColor Yellow
Write-Host "  2. Drop DOCX + XLSX into exports/" -ForegroundColor Yellow
Write-Host "  3. Update mkdocs.yml nav (use appendix/ and adr/ singular paths)" -ForegroundColor Yellow
Write-Host "  4. Populate MISSING stubs from Canon DOCX content" -ForegroundColor Yellow
Write-Host "  5. Run: mkdocs serve" -ForegroundColor Yellow
