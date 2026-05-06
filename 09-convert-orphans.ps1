# 09-convert-orphans.ps1
# Converts the remaining ORPHAN-MD files in docs/ to .qmd.
# Splits into two groups:
#   CONVERT — clear site content, converted automatically
#   REVIEW  — internal/ambiguous, listed but not touched
#
# Usage:  .\09-convert-orphans.ps1
# Dry run: .\09-convert-orphans.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$converted = 0
$skipped   = 0
$errors    = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function Convert-MdToQmd {
    param(
        [string]$MdPath,
        [string]$Title,
        [string]$Subtitle  = "",
        [string]$Description = ""
    )

    if (-not (Test-Path $MdPath)) {
        Write-Host "NOT FOUND: $MdPath" -ForegroundColor Red
        $script:errors++
        return
    }

    $qmdPath = $MdPath -replace '\.md$', '.qmd'
    if (Test-Path $qmdPath) {
        Write-Action "SKIP (.qmd already exists)" $qmdPath "Gray"
        $script:skipped++
        return
    }

    $content = Get-Content $MdPath -Raw -ErrorAction Stop
    $hasYaml = $content.TrimStart().StartsWith("---")

    $newContent = $content
    if (-not $hasYaml) {
        $yaml  = "---`n"
        $yaml += "title: `"$Title`"`n"
        if ($Subtitle)    { $yaml += "subtitle: `"$Subtitle`"`n" }
        if ($Description) { $yaml += "description: `"$Description`"`n" }
        $yaml += "---`n`n"
        $newContent = $yaml + $content
    }

    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $newContent -Encoding UTF8 -NoNewline
        Remove-Item $MdPath -Force
    }
    $leaf = Split-Path $qmdPath -Leaf
    Write-Action "CONVERTED" "$(($MdPath -replace [regex]::Escape($RepoRoot+'\')))  →  $leaf" "Green"
    $script:converted++
}

Write-Host ""
Write-Host "09-convert-orphans.ps1" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# GROUP 1: CONVERT — clear site content
# ---------------------------------------------------------------------------

Write-Host "GROUP 1: Converting clear site-content files" -ForegroundColor Yellow
Write-Host ""

# docs\appendices\ — technical appendices
Write-Host "  docs\appendices\" -ForegroundColor White
$appendices = @(
    @{ File="Appendix-B-UIAO-SCuBA-Pipeline.md";    Title="Appendix B — SCuBA Pipeline";        Subtitle="UIAO SCuBA integration pipeline overview" }
    @{ File="Appendix-C-KSI-Mapping-Tables.md";     Title="Appendix C — KSI Mapping Tables";    Subtitle="Key security indicator mapping reference" }
    @{ File="Appendix-D-ADR-Index.md";              Title="Appendix D — ADR Index";             Subtitle="Architecture decision record index" }
    @{ File="Appendix-E-SCuBA-Field-Dictionary.md"; Title="Appendix E — SCuBA Field Dictionary";Subtitle="SCuBA field reference and definitions" }
)
foreach ($a in $appendices) {
    Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\appendices\$($a.File)") `
                    -Title $a.Title -Subtitle $a.Subtitle
}

# docs\ato\ — ATO package template
Write-Host "  docs\ato\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\ato\UIAO-ATO-Package-Template.md") `
                -Title "ATO Package Template" `
                -Subtitle "Authorization to Operate package template for UIAO deployments"

# docs\governance\ — governance architecture documents
Write-Host "  docs\governance\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\governance\ARCHITECTURE.md") `
                -Title "Governance Architecture" `
                -Subtitle "UIAO governance architecture specification" `
                -Description "Comprehensive governance architecture covering control planes, enforcement model, and operational structure."
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\governance\CONMON.md") `
                -Title "Continuous Monitoring" `
                -Subtitle "UIAO continuous monitoring specification"
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\governance\VISION.md") `
                -Title "Program Vision" `
                -Subtitle "UIAO program vision and strategic direction"

# docs\narrative\ — program narrative documents
Write-Host "  docs\narrative\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\narrative\2026-04-fedramp-gcc-moderate-three-assessments.md") `
                -Title "FedRAMP GCC Moderate — Three Assessments" `
                -Subtitle "April 2026 assessment narrative"
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\narrative\governance-os-directory-migration.md") `
                -Title "Governance OS and Directory Migration" `
                -Subtitle "How UIAO governs the AD to Entra ID migration"
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\narrative\UIAO-Narrative-Layer.md") `
                -Title "UIAO Narrative Layer" `
                -Subtitle "Program narrative and positioning"

# docs\runbook\ — operational runbook
Write-Host "  docs\runbook\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\runbook\UIAO-Operational-Runbook.md") `
                -Title "UIAO Operational Runbook" `
                -Subtitle "Day-to-day operational procedures for UIAO deployments"

# docs\security\ — security architecture
Write-Host "  docs\security\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\security\UIAO-Security-Architecture.md") `
                -Title "UIAO Security Architecture" `
                -Subtitle "Security architecture, boundaries, and control model"

# docs\customer-documents\validation-suites\adapters\bluecat-address-manager\
Write-Host "  docs\customer-documents\validation-suites\adapters\" -ForegroundColor White
Convert-MdToQmd -MdPath (Join-Path $RepoRoot "docs\customer-documents\validation-suites\adapters\bluecat-address-manager\bluecat-address-manager.md") `
                -Title "BlueCat Address Manager Validation Suite" `
                -Subtitle "Conformance tests for the BlueCat IPAM adapter"

# ---------------------------------------------------------------------------
# GROUP 2: REVIEW — internal or ambiguous, not auto-converted
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "GROUP 2: Files flagged for manual review (not converted)" -ForegroundColor Yellow
Write-Host ""

$reviewFiles = @(
    @{ Path="docs\customer-documents\TREE.md";           Reason="Internal nav map — decide if this should be a published page or deleted" }
    @{ Path="docs\diagrams\README.md";                   Reason="Diagram README — internal tooling doc, probably not a customer page" }
    @{ Path="docs\exports\README.md";                    Reason="246 bytes — likely internal; confirm and delete if so" }
    @{ Path="docs\governance\CODE_OF_CONDUCT.md";        Reason="Check: may duplicate root CODE_OF_CONDUCT.md; delete duplicate if confirmed" }
    @{ Path="docs\planning\customer-documents-taxonomy.md"; Reason="23 KB planning doc — internal or publish as governance reference?" }
    @{ Path="docs\publications\INDEX.md";                Reason="Publications index — convert if this section is live, delete if internal" }
    @{ Path="docs\reports\cli-surface-audit-v0.4.0.md"; Reason="Audit report — publish as historical record or keep internal?" }
    @{ Path="docs\reports\public-surface-audit-v0.5.0.md"; Reason="Audit report — same question as v0.4.0" }
    @{ Path="docs\reports\SCuBA-Canonical-Report.md";    Reason="SCuBA report — publish alongside SCuBA findings or keep internal?" }
    @{ Path="docs\session-log.md";                       Reason="Development session log — internal, recommend delete from docs/" }
    @{ Path="docs\SUMMARY.md";                           Reason="Summary doc — review content; may overlap with index.qmd" }
    @{ Path="docs\visuals\README.md";                    Reason="Visuals README — internal tooling doc" }
)

foreach ($item in $reviewFiles) {
    $fullPath = Join-Path $RepoRoot $item.Path
    $size = if (Test-Path $fullPath) { (Get-Item $fullPath).Length } else { 0 }
    Write-Host ("  REVIEW  {0,-65} {1,7} bytes" -f $item.Path, $size) -ForegroundColor DarkYellow
    Write-Host ("          → $($item.Reason)") -ForegroundColor Gray
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  Converted : $converted files" -ForegroundColor Green
Write-Host "  Skipped   : $skipped files (already .qmd)" -ForegroundColor Gray
Write-Host "  For review: $($reviewFiles.Count) files (not touched)" -ForegroundColor Yellow
if ($errors -gt 0) {
    Write-Host "  Errors    : $errors" -ForegroundColor Red
}
Write-Host ""
if ($WhatIf) {
    Write-Host "Dry run complete — rerun without -WhatIf to apply changes." -ForegroundColor Yellow
} else {
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. quarto preview docs/  — verify new pages render" -ForegroundColor White
    Write-Host "  2. Check each converted page is reachable from site nav or its parent index" -ForegroundColor White
    Write-Host "  3. Work through the REVIEW list above — decide publish, convert, or delete" -ForegroundColor White
    Write-Host "  4. git add -A && git commit -m 'fix: convert orphaned governance/narrative/runbook docs'" -ForegroundColor White
    Write-Host "  5. Run .\UIAO-DocAudit-v3.ps1 — ORPHAN-MD should drop from 26 to ~12" -ForegroundColor White
    Write-Host "  6. Next: 10-delete-micro-shells.ps1 (36 x 47-byte governance placeholders)" -ForegroundColor White
}
Write-Host ""
