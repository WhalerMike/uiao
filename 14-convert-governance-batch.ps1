# 14-convert-governance-batch.ps1
# Converts the final LEGACY-DOCS files:
#   - docs\docs\adapter-authoring-tutorial.md  (no academy version — only copy)
#   - docs\docs\governance\*.md               (84 files — all legitimate spec content)
#   - docs\docs\diagrams\*.md                 (7 files — diagram text specs)
#
# Uses filename-to-title conversion rather than a lookup table for the large governance folder.
#
# Usage:  .\14-convert-governance-batch.ps1
# Dry run: .\14-convert-governance-batch.ps1 -WhatIf

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

function Stem-To-Title {
    param([string]$Stem)
    # Replace hyphens with spaces, title-case each word
    $words = $Stem -replace '-', ' ' -split ' '
    $titled = $words | ForEach-Object {
        $w = $_
        # Keep known acronyms uppercase
        if ($w -match '^(uiao|slo|sli|arb|rl|adr|sla|api|rfc|gcc|ato|id|ci|os|rlm)$') {
            $w.ToUpper()
        } else {
            if ($w.Length -gt 0) { $w[0].ToString().ToUpper() + $w.Substring(1) }
        }
    }
    return ($titled -join ' ')
}

function Convert-BatchMd {
    param(
        [string]$FullPath,
        [string]$Title = "",
        [string]$Subtitle = ""
    )
    if (-not (Test-Path $FullPath)) {
        Write-Host "  NOT FOUND: $FullPath" -ForegroundColor Red; $script:errors++; return
    }
    $qmdPath = $FullPath -replace '\.md$', '.qmd'
    if (Test-Path $qmdPath) {
        $leaf = Split-Path $FullPath -Leaf
        Write-Host "  SKIP (.qmd exists): $leaf" -ForegroundColor Gray
        $script:skipped++; return
    }
    $content = Get-Content $FullPath -Raw
    $hasYaml = $content.TrimStart().StartsWith("---")
    $newContent = $content
    if (-not $hasYaml) {
        $stem  = [System.IO.Path]::GetFileNameWithoutExtension($FullPath)
        $t     = if ($Title) { $Title } else { Stem-To-Title $stem }
        $yaml  = "---`ntitle: `"$t`""
        if ($Subtitle) { $yaml += "`nsubtitle: `"$Subtitle`"" }
        $yaml += "`n---`n`n"
        $newContent = $yaml + $content
    }
    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $newContent -Encoding UTF8 -NoNewline
        Remove-Item $FullPath -Force
    }
    $rel = $FullPath.Replace($RepoRoot + "\", "")
    Write-Action "CONVERTED" "$rel  →  $(Split-Path $qmdPath -Leaf)" "Green"
    $script:converted++
}

Write-Host ""
Write-Host "14-convert-governance-batch.ps1" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# 1. adapter-authoring-tutorial.md — only copy, convert directly
# ---------------------------------------------------------------------------
Write-Host "adapter-authoring-tutorial.md (no academy version — convert)" -ForegroundColor Yellow

Convert-BatchMd `
    -FullPath (Join-Path $RepoRoot "docs\docs\adapter-authoring-tutorial.md") `
    -Title "Adapter Authoring Tutorial" `
    -Subtitle "Step-by-step guide to building a UIAO adapter"

# ---------------------------------------------------------------------------
# 2. docs\docs\governance\ — 84 files, batch convert by glob
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "docs\docs\governance\ — batch converting all .md files" -ForegroundColor Yellow

$govDir = Join-Path $RepoRoot "docs\docs\governance"
$govFiles = Get-ChildItem $govDir -Filter "*.md" -Recurse -ErrorAction SilentlyContinue |
    Sort-Object FullName

Write-Host "  Found $($govFiles.Count) .md files to convert" -ForegroundColor Gray
Write-Host ""

foreach ($f in $govFiles) {
    Convert-BatchMd -FullPath $f.FullName
}

# ---------------------------------------------------------------------------
# 3. docs\docs\diagrams\ — 7 small diagram spec files
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "docs\docs\diagrams\ — diagram text specs" -ForegroundColor Yellow

$diagrams = @(
    @{ File="adapter-plane.md";        Title="Adapter Plane Diagram";       Subtitle="Text specification for the adapter plane diagram" }
    @{ File="drift-fabric.md";         Title="Drift Fabric Diagram";        Subtitle="Text specification for the drift fabric diagram" }
    @{ File="evidence-fabric.md";      Title="Evidence Fabric Diagram";     Subtitle="Text specification for the evidence fabric diagram" }
    @{ File="governance-hierarchy.md"; Title="Governance Hierarchy Diagram"; Subtitle="Text specification for the governance hierarchy diagram" }
    @{ File="governance-plane.md";     Title="Governance Plane Diagram";    Subtitle="Text specification for the governance plane diagram" }
    @{ File="truth-fabric.md";         Title="Truth Fabric Diagram";        Subtitle="Text specification for the truth fabric diagram" }
    @{ File="index.md";                Title="Diagram Specifications Index"; Subtitle="Index of UIAO diagram text specifications" }
)
foreach ($d in $diagrams) {
    Convert-BatchMd `
        -FullPath (Join-Path $RepoRoot "docs\docs\diagrams\$($d.File)") `
        -Title $d.Title `
        -Subtitle $d.Subtitle
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would convert : ~$($converted + $govFiles.Count + $diagrams.Count + 1) files" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Converted : $converted files" -ForegroundColor Green
    Write-Host "  Skipped   : $skipped (already .qmd)" -ForegroundColor Gray
    if ($errors -gt 0) { Write-Host "  Errors    : $errors" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. git add -A && git commit -m 'fix: convert 92 governance/diagram legacy files to .qmd'" -ForegroundColor White
    Write-Host "  2. git push" -ForegroundColor White
    Write-Host "  3. .\UIAO-DocAudit-v3.ps1 — LEGACY-DOCS should drop from 92 to ~0" -ForegroundColor White
    Write-Host "  4. quarto preview docs/ — verify governance pages render" -ForegroundColor White
    Write-Host ""
    Write-Host "After this, LEGACY-DOCS is cleared. Remaining work:" -ForegroundColor Cyan
    Write-Host "  - Add other-formats: [pdf] to docs\_quarto.yml (site-wide downloads)" -ForegroundColor White
    Write-Host "  - Fix executive-briefs index table slug links (clickable hrefs)" -ForegroundColor White
    Write-Host "  - Review STAGING-INBOX (inbox\HRIT and inbox\KYC canon candidates)" -ForegroundColor White
}
Write-Host ""
