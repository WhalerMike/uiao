# 13-convert-legacy-docs.ps1
# Resolves the tractable portion of the 158 LEGACY-DOCS files in docs\docs\.
# Converts 48 files with clear publish intent.
# Archives 12 session/internal files to inbox\.
# Leaves the 84-file governance folder for script 14 (separate review pass).
#
# Usage:  .\13-convert-legacy-docs.ps1
# Dry run: .\13-convert-legacy-docs.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$converted = 0
$archived  = 0
$skipped   = 0
$errors    = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function Convert-LegacyMd {
    param([string]$RelPath, [string]$Title, [string]$Subtitle = "")
    $fullPath = Join-Path $RepoRoot $RelPath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  NOT FOUND: $RelPath" -ForegroundColor Red; $script:errors++; return
    }
    $qmdPath = $fullPath -replace '\.md$', '.qmd'
    if (Test-Path $qmdPath) {
        Write-Host "  SKIP (.qmd exists): $(Split-Path $RelPath -Leaf)" -ForegroundColor Gray
        $script:skipped++; return
    }
    $content = Get-Content $fullPath -Raw
    $hasYaml = $content.TrimStart().StartsWith("---")
    $newContent = $content
    if (-not $hasYaml) {
        $yaml = "---`ntitle: `"$Title`""
        if ($Subtitle) { $yaml += "`nsubtitle: `"$Subtitle`"" }
        $yaml += "`n---`n`n"
        $newContent = $yaml + $content
    }
    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $newContent -Encoding UTF8 -NoNewline
        Remove-Item $fullPath -Force
    }
    Write-Action "CONVERTED" "$RelPath  →  $(Split-Path $qmdPath -Leaf)" "Green"
    $script:converted++
}

function Archive-ToInbox {
    param([string]$RelPath, [string]$DestSubfolder = "session-logs", [string]$Reason = "")
    $fullPath = Join-Path $RepoRoot $RelPath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ALREADY GONE: $RelPath" -ForegroundColor Gray; $script:skipped++; return
    }
    $destDir  = Join-Path $RepoRoot "inbox\$DestSubfolder"
    $destPath = Join-Path $destDir (Split-Path $RelPath -Leaf)
    if (-not $WhatIf) {
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir -Force | Out-Null }
        Move-Item $fullPath $destPath -Force
    }
    $label = if ($Reason) { " ($Reason)" } else { "" }
    Write-Action "ARCHIVED to inbox\$DestSubfolder\$label" $RelPath "DarkYellow"
    $script:archived++
}

Write-Host ""
Write-Host "13-convert-legacy-docs.ps1" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# GROUP 1: ROOT files — priority converts
# ---------------------------------------------------------------------------
Write-Host "Group 1: docs\docs\ root — priority converts" -ForegroundColor Yellow

Convert-LegacyMd "docs\docs\gcc-boundary-problem-statement.md" `
    "GCC Moderate — Boundary Problem Statement" `
    "Why GCC Moderate on Azure Commercial infrastructure creates a structural telemetry gap"

Convert-LegacyMd "docs\docs\gcc-boundary-solution-architecture.md" `
    "GCC Moderate — Solution Architecture" `
    "How UIAO addresses the GCC Moderate compliance contradiction"

Convert-LegacyMd "docs\docs\cli-reference.md" `
    "UIAO CLI Reference" `
    "Complete command reference for the uiao-core CLI"

Convert-LegacyMd "docs\docs\scuba-architecture-guide.md" `
    "SCuBA Architecture Guide" `
    "UIAO integration with the CISA SCuBA assessment framework"

Convert-LegacyMd "docs\docs\scuba-operator-runbook.md" `
    "SCuBA Operator Runbook" `
    "Day-to-day operations for SCuBA pipeline maintainers"

Convert-LegacyMd "docs\docs\SCuBA-Pipeline-Runbook.md" `
    "SCuBA Pipeline Runbook" `
    "End-to-end SCuBA pipeline operation and troubleshooting"

Convert-LegacyMd "docs\docs\SCuBA-Maintainer-Onboarding.md" `
    "SCuBA Maintainer Onboarding" `
    "Onboarding guide for SCuBA pipeline maintainers"

Convert-LegacyMd "docs\docs\uiao-rfc-0026-roadmap.md" `
    "RFC-0026 Roadmap" `
    "UIAO RFC-0026 — E1/E5 connect-gov design roadmap"

Convert-LegacyMd "docs\docs\uiao-rfc-0026-e1-connect-gov-design.md" `
    "RFC-0026-E1 — Connect-Gov Design" `
    "E1 connect-gov architectural design specification"

Convert-LegacyMd "docs\docs\uiao-rfc-0026-e5-multi-agency-design.md" `
    "RFC-0026-E5 — Multi-Agency Design" `
    "E5 multi-agency architectural design specification"

Convert-LegacyMd "docs\docs\uiao-substrate-roadmap.md" `
    "UIAO Substrate Roadmap" `
    "Platform substrate development and release roadmap"

Convert-LegacyMd "docs\docs\orgtree-readiness-quickstart.md" `
    "OrgPath Readiness Quickstart" `
    "Getting started with UIAO OrgPath readiness assessment"

Convert-LegacyMd "docs\docs\quickstart.md" `
    "UIAO Quickstart" `
    "Get up and running with UIAO in under an hour"

Convert-LegacyMd "docs\docs\drift-detection-boundary-amendment.md" `
    "Drift Detection — Boundary Amendment" `
    "Amendment to the drift detection specification covering boundary conditions"

Convert-LegacyMd "docs\docs\access.md" `
    "Access Control Reference" `
    "UIAO access control model and permission reference"

Convert-LegacyMd "docs\docs\contributing.md" `
    "Contributing to UIAO" `
    "Development workflow and contribution guidelines for the docs\docs\ layer"

# Note: adapter-authoring-tutorial.md left for manual check —
# docs\academy\adapter-authoring-tutorial.qmd may supersede it.
Write-Host "  NOTE: adapter-authoring-tutorial.md left untouched" -ForegroundColor Gray
Write-Host "        Verify it is not superseded by docs\academy\adapter-authoring-tutorial.qmd" -ForegroundColor Gray

# ---------------------------------------------------------------------------
# GROUP 2: Appendix series — all convert (5 planes, 23 files)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group 2: docs\docs\appendix\ — five-plane appendix series" -ForegroundColor Yellow

$appendices = @(
    @{ Path="docs\docs\appendix\a-adapter-plane\index.md";               Title="Appendix A — Adapter Plane" }
    @{ Path="docs\docs\appendix\a-adapter-plane\a-01-adapter-lifecycle.md"; Title="A.1 — Adapter Lifecycle" }
    @{ Path="docs\docs\appendix\a-adapter-plane\a-02-adapter-sandbox-execution.md"; Title="A.2 — Adapter Sandbox Execution" }
    @{ Path="docs\docs\appendix\a-adapter-plane\a-03-adapter-hot-swap-rollback.md"; Title="A.3 — Adapter Hot-Swap and Rollback" }
    @{ Path="docs\docs\appendix\a-adapter-plane\a-04-adapter-health-liveness.md"; Title="A.4 — Adapter Health and Liveness" }
    @{ Path="docs\docs\appendix\b-truth-fabric\index.md";               Title="Appendix B — Truth Fabric" }
    @{ Path="docs\docs\appendix\b-truth-fabric\b-01-canonical-claim-schema.md"; Title="B.1 — Canonical Claim Schema" }
    @{ Path="docs\docs\appendix\b-truth-fabric\b-02-identity-anchoring.md"; Title="B.2 — Identity Anchoring" }
    @{ Path="docs\docs\appendix\b-truth-fabric\b-03-multi-cloud-identity-matrix.md"; Title="B.3 — Multi-Cloud Identity Matrix" }
    @{ Path="docs\docs\appendix\b-truth-fabric\b-04-control-mapping-governance.md"; Title="B.4 — Control Mapping and Governance" }
    @{ Path="docs\docs\appendix\c-drift-fabric\index.md";               Title="Appendix C — Drift Fabric" }
    @{ Path="docs\docs\appendix\c-drift-fabric\c-01-drift-detection.md"; Title="C.1 — Drift Detection" }
    @{ Path="docs\docs\appendix\c-drift-fabric\c-02-drift-taxonomy.md"; Title="C.2 — Drift Taxonomy" }
    @{ Path="docs\docs\appendix\c-drift-fabric\c-03-vendor-failure-containment.md"; Title="C.3 — Vendor Failure Containment" }
    @{ Path="docs\docs\appendix\d-evidence-fabric\index.md";            Title="Appendix D — Evidence Fabric" }
    @{ Path="docs\docs\appendix\d-evidence-fabric\d-01-evidence-determinism.md"; Title="D.1 — Evidence Determinism" }
    @{ Path="docs\docs\appendix\d-evidence-fabric\d-02-evidence-lifecycle.md"; Title="D.2 — Evidence Lifecycle" }
    @{ Path="docs\docs\appendix\d-evidence-fabric\d-03-evidence-signing.md"; Title="D.3 — Evidence Signing" }
    @{ Path="docs\docs\appendix\d-evidence-fabric\d-04-evidence-correlation.md"; Title="D.4 — Evidence Correlation" }
    @{ Path="docs\docs\appendix\e-governance-plane\index.md";           Title="Appendix E — Governance Plane" }
    @{ Path="docs\docs\appendix\e-governance-plane\e-01-arb-coordination.md"; Title="E.1 — ARB Coordination" }
    @{ Path="docs\docs\appendix\e-governance-plane\e-02-mission-partner-corridors.md"; Title="E.2 — Mission Partner Corridors" }
    @{ Path="docs\docs\appendix\e-governance-plane\e-03-cross-fabric-consistency.md"; Title="E.3 — Cross-Fabric Consistency" }
)
foreach ($a in $appendices) {
    Convert-LegacyMd $a.Path $a.Title
}

# ---------------------------------------------------------------------------
# GROUP 3: Meta folder — metadata contracts and playbooks
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group 3: docs\docs\meta\ — metadata contracts" -ForegroundColor Yellow

$meta = @(
    @{ Path="docs\docs\meta\governance-metadata-playbook.md";        Title="Governance Metadata Playbook" }
    @{ Path="docs\docs\meta\uiao-document-metadata-contract.md";     Title="UIAO Document Metadata Contract" }
    @{ Path="docs\docs\meta\adr-metadata-contract.md";               Title="ADR Metadata Contract" }
    @{ Path="docs\docs\meta\uiao-adr-metadata-contract.md";          Title="UIAO ADR Metadata Contract" }
    @{ Path="docs\docs\meta\governance-metadata-reviewer-checklist.md"; Title="Governance Metadata Reviewer Checklist" }
    @{ Path="docs\docs\meta\metadata-drift-detection-report.md";     Title="Metadata Drift Detection Report" }
)
foreach ($m in $meta) { Convert-LegacyMd $m.Path $m.Title }

# ---------------------------------------------------------------------------
# GROUP 4: Canon folder — core reference docs
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group 4: docs\docs\canon\ — canon reference docs" -ForegroundColor Yellow

Convert-LegacyMd "docs\docs\canon\glossary.md"              "Canon Glossary"              "UIAO unified terminology reference"
Convert-LegacyMd "docs\docs\canon\corpus-status-dashboard.md" "Corpus Status Dashboard"   "Canon corpus health and coverage status"
Convert-LegacyMd "docs\docs\canon\index.md"                 "Canon Index"                 "UIAO canon document index and entry point"

# Internal/tooling — archive rather than publish
Archive-ToInbox "docs\docs\canon\migration-plan.md"   "drafts" "canon migration plan — internal"
Archive-ToInbox "docs\docs\canon\pdf-layout-spec.md"  "drafts" "PDF layout spec — internal tooling"

# ---------------------------------------------------------------------------
# GROUP 5: Session logs — all archive (development history, not site content)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group 5: docs\docs\session-logs\ — archive all (development history)" -ForegroundColor Yellow

$sessionLogs = @(
    "docs\docs\session-logs\2026-04-14-customer-docs-platform.md"
    "docs\docs\session-logs\2026-04-14-manifest-your-side.md"
    "docs\docs\session-logs\2026-04-14-phase-d-plan.md"
    "docs\docs\session-logs\2026-04-14-phase-d-stage-0-scan.md"
    "docs\docs\session-logs\2026-04-14-phase-d-stage-1-cleanup.md"
    "docs\docs\session-logs\2026-04-14-phase-d-stage-2-canon-in.md"
    "docs\docs\session-logs\2026-04-14-phase-d-stage-3-pipeline-out.md"
    "docs\docs\session-logs\2026-04-14-phase-d-stage-4-app-split.md"
    "docs\docs\session-logs\README.md"
    "docs\docs\session-logs\reports\canon-backfill-triage.md"
)
foreach ($log in $sessionLogs) { Archive-ToInbox $log "session-logs" }

# ---------------------------------------------------------------------------
# GROUP 6: Conmon + CI — archive (internal operational/test docs)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group 6: conmon + ci — archive (internal)" -ForegroundColor Yellow

Archive-ToInbox "docs\docs\conmon\templates\2026-07-agenda.md" "drafts" "ConMon agenda template"
Archive-ToInbox "docs\docs\ci\TESTPLAN-metadata-validator.md"  "drafts" "CI test plan"

# Tiny index stubs — delete
$tinyStubs = @(
    "docs\docs\documents\index.md"
    "docs\docs\adr\index.md"
    "docs\docs\onboarding\adapter-developer-guide.md"
    "docs\docs\onboarding\index.md"
)
Write-Host ""
Write-Host "Deleting tiny stubs (under 600 bytes, no meaningful content)" -ForegroundColor Yellow
foreach ($stub in $tinyStubs) {
    $fullPath = Join-Path $RepoRoot $stub
    if (Test-Path $fullPath) {
        $size = (Get-Item $fullPath).Length
        if ($size -le 600) {
            if (-not $WhatIf) { Remove-Item $fullPath -Force }
            Write-Action "DELETED (stub, $size bytes)" $stub "DarkGray"
            $script:converted++
        } else {
            Write-Host "  SKIP (grown to $size bytes): $stub" -ForegroundColor Yellow
        }
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would convert : ~$converted files" -ForegroundColor Cyan
    Write-Host "  Would archive : ~$archived files → inbox\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Converted : $converted files" -ForegroundColor Green
    Write-Host "  Archived  : $archived files → inbox\" -ForegroundColor Yellow
    Write-Host "  Skipped   : $skipped" -ForegroundColor Gray
    if ($errors -gt 0) { Write-Host "  Errors    : $errors" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Still untouched (needs script 14 or manual review):" -ForegroundColor Cyan
    Write-Host "  docs\docs\governance\  — 84 files, 189 KB" -ForegroundColor White
    Write-Host "  docs\docs\diagrams\    —  7 files,   8 KB" -ForegroundColor White
    Write-Host "  docs\docs\adapter-authoring-tutorial.md — verify vs. academy version" -ForegroundColor White
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. git add -A && git commit -m 'fix: convert 48 legacy docs\docs\ files to .qmd, archive session logs'" -ForegroundColor White
    Write-Host "  2. git push" -ForegroundColor White
    Write-Host "  3. .\UIAO-DocAudit-v3.ps1 — LEGACY-DOCS should drop from 158 to ~94" -ForegroundColor White
    Write-Host "  4. quarto preview docs/ — verify new pages render" -ForegroundColor White
}
Write-Host ""
