# 08-convert-findings.ps1
# P1 fix: converts all .md files in docs\findings\ to .qmd and adds YAML headers.
# Safe to rerun — skips files that are already .qmd or already have a YAML header.
#
# Also converts the 5 executive-briefs .md files (P1-B).
# Also adds YAML headers to 5 live .qmd files missing them (P2-E).
#
# Usage: .\08-convert-findings.ps1
# Dry run: .\08-convert-findings.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$errors  = 0
$fixed   = 0
$skipped = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function Get-TitleFromFilename {
    param([string]$Stem)
    $t = $Stem -replace '-', ' '
    $t = $t -replace 'fedramp gcc moderate ', 'FedRAMP GCC Moderate — '
    $t = $t -replace 'fedramp 20x moderate pilot', 'FedRAMP 20x Moderate Pilot'
    $words = $t -split ' '
    $titled = $words | ForEach-Object {
        if ($_ -match '^(gcc|uiao|fedramp|cae|cqd|euii|wufb|siem|pki|dns|ato|scuba|ms|api|kb|id|v\d)$') {
            $_.ToUpper()
        } else { (Get-Culture).TextInfo.ToTitleCase($_) }
    }
    return $titled -join ' '
}

function Get-TitleFromContent {
    param([string]$Content)
    $lines = $Content -split "`n"
    foreach ($line in $lines) {
        if ($line -match '^#\s+(.+)') { return $Matches[1].Trim() }
    }
    return $null
}

function Add-YamlHeader {
    param(
        [string]$FilePath,
        [string]$Title,
        [string]$Subtitle = "",
        [string]$Description = ""
    )

    $content = Get-Content $FilePath -Raw -ErrorAction Stop

    if ($content.TrimStart().StartsWith("---")) {
        Write-Action "SKIP (already has YAML)" $FilePath "Gray"
        $script:skipped++
        return
    }

    $yaml = "---`ntitle: `"$Title`""
    if ($Subtitle)    { $yaml += "`nsubtitle: `"$Subtitle`"" }
    if ($Description) { $yaml += "`ndescription: `"$Description`"" }
    $yaml += "`n---`n`n"

    if (-not $WhatIf) {
        Set-Content -Path $FilePath -Value ($yaml + $content) -Encoding UTF8 -NoNewline
    }
    Write-Action "YAML added" $FilePath "Green"
    $script:fixed++
}

function Convert-MdToQmd {
    param(
        [string]$MdPath,
        [string]$Title,
        [string]$Subtitle = "",
        [string]$Description = ""
    )

    $qmdPath = $MdPath -replace '\.md$', '.qmd'

    if (Test-Path $qmdPath) {
        Write-Action "SKIP (.qmd already exists)" $qmdPath "Gray"
        $script:skipped++
        return
    }

    $content = Get-Content $MdPath -Raw -ErrorAction Stop

    $titleToUse = $Title
    if (-not $titleToUse) {
        $titleToUse = Get-TitleFromContent $content
    }
    if (-not $titleToUse) {
        $titleToUse = Get-TitleFromFilename ([System.IO.Path]::GetFileNameWithoutExtension($MdPath))
    }

    $hasYaml = $content.TrimStart().StartsWith("---")

    $newContent = $content
    if (-not $hasYaml) {
        $yaml = "---`ntitle: `"$titleToUse`""
        if ($Subtitle)    { $yaml += "`nsubtitle: `"$Subtitle`"" }
        if ($Description) { $yaml += "`ndescription: `"$Description`"" }
        $yaml += "`n---`n`n"
        $newContent = $yaml + $content
    }

    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $newContent -Encoding UTF8 -NoNewline
        Remove-Item $MdPath -Force
    }
    Write-Action "CONVERTED" "$MdPath  →  $(Split-Path $qmdPath -Leaf)" "Green"
    $script:fixed++
}

Write-Host ""
Write-Host "08-convert-findings.ps1" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# P1-A: docs\findings\ — 10 finding .md files + README.md
# ---------------------------------------------------------------------------
Write-Host "P1-A: docs\findings\ — FedRAMP GCC Moderate findings" -ForegroundColor Yellow

$findingsMeta = @{
    'fedramp-20x-moderate-pilot'                                        = @{ Title='FedRAMP 20x Moderate Pilot'; Subtitle='Program overview and UIAO alignment' }
    'fedramp-gcc-moderate-adoption-score-unavailable'                   = @{ Title='Finding: Adoption Score Unavailable'; Subtitle='FedRAMP GCC Moderate telemetry gap' }
    'fedramp-gcc-moderate-cae-realtime-degraded'                        = @{ Title='Finding: CAE Realtime Degraded'; Subtitle='Call Analytics Enablement in GCC Moderate' }
    'fedramp-gcc-moderate-cqd-euii-28day-cliff'                         = @{ Title='Finding: CQD EUII 28-Day Cliff'; Subtitle='Call Quality Dashboard data retention gap' }
    'fedramp-gcc-moderate-endpoint-analytics-advanced-inferred-blocked' = @{ Title='Finding: Endpoint Analytics Advanced Blocked'; Subtitle='Inferred capability block in GCC Moderate' }
    'fedramp-gcc-moderate-entra-identity-protection-inferred-blocked'   = @{ Title='Finding: Entra Identity Protection Blocked'; Subtitle='Inferred capability block in GCC Moderate' }
    'fedramp-gcc-moderate-informed-network-routing'                     = @{ Title='Finding: Informed Network Routing'; Subtitle='Network routing limitation in GCC Moderate' }
    'fedramp-gcc-moderate-purview-audit-180day-cliff'                   = @{ Title='Finding: Purview Audit 180-Day Cliff'; Subtitle='Audit log retention limit in GCC Moderate' }
    'fedramp-gcc-moderate-thousandeyes-coverage-scope'                  = @{ Title='Finding: ThousandEyes Coverage Scope'; Subtitle='Network visibility gap in GCC Moderate' }
    'fedramp-gcc-moderate-wufb-reporting-inferred-blocked'              = @{ Title='Finding: WUfB Reporting Blocked'; Subtitle='Windows Update for Business reporting gap' }
    'README'                                                            = @{ Title='GCC Moderate Findings'; Subtitle='FedRAMP GCC Moderate capability gap analysis' }
}

$findingsDir = Join-Path $RepoRoot "docs\findings"
Get-ChildItem $findingsDir -Filter "*.md" -ErrorAction SilentlyContinue | ForEach-Object {
    $stem = $_.BaseName
    $meta = $findingsMeta[$stem]
    $title = if ($meta) { $meta.Title } else { $null }
    $sub   = if ($meta) { $meta.Subtitle } else { "" }
    Convert-MdToQmd -MdPath $_.FullName -Title $title -Subtitle $sub
}

# ---------------------------------------------------------------------------
# P1-B: docs\customer-documents\executive-briefs\ — 5 brief .md files
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "P1-B: docs\customer-documents\executive-briefs\ — leadership briefs" -ForegroundColor Yellow

$briefsMeta = @{
    'drift-engine-overview'    = @{ Title='Drift Engine Overview';     Subtitle='How UIAO detects and quantifies configuration drift' }
    'evidence-fabric-overview' = @{ Title='Evidence Fabric Overview';  Subtitle='Provenance and evidence pipeline brief' }
    'governance-os-overview'   = @{ Title='Governance OS Overview';    Subtitle='The UIAO Governance OS in one page' }
    'modernization-overview'   = @{ Title='Modernization Overview';    Subtitle='End-to-end modernization program brief' }
    'zero-trust-overview'      = @{ Title='Zero Trust Overview';       Subtitle='Zero-trust identity model brief' }
}

$briefsDir = Join-Path $RepoRoot "docs\customer-documents\executive-briefs"
Get-ChildItem $briefsDir -Filter "*.md" -ErrorAction SilentlyContinue | ForEach-Object {
    $stem = $_.BaseName
    $meta = $briefsMeta[$stem]
    $title = if ($meta) { $meta.Title } else { $null }
    $sub   = if ($meta) { $meta.Subtitle } else { "" }
    Convert-MdToQmd -MdPath $_.FullName -Title $title -Subtitle $sub
}

# ---------------------------------------------------------------------------
# P2-E: 5 live .qmd files missing YAML headers
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "P2-E: Live .qmd files missing YAML headers" -ForegroundColor Yellow

$missingYaml = @(
    @{ Path="docs\docs\appendix\README.qmd";       Title="Appendix Index";       Subtitle="Technical appendices for the UIAO platform" }
    @{ Path="docs\docs\architecture\README.qmd";   Title="Architecture Index";   Subtitle="UIAO architecture reference" }
    @{ Path="docs\docs\onboarding\README.qmd";     Title="Onboarding Index";     Subtitle="Developer and operator onboarding" }
    @{ Path="docs\docs\patterns\README.qmd";       Title="Pattern Library";      Subtitle="Reusable governance patterns" }
    @{ Path="docs\docs\user-guides\README.qmd";    Title="User Guides";          Subtitle="End-user documentation" }
)

foreach ($item in $missingYaml) {
    $fullPath = Join-Path $RepoRoot $item.Path
    if (Test-Path $fullPath) {
        Add-YamlHeader -FilePath $fullPath -Title $item.Title -Subtitle $item.Subtitle
    } else {
        Write-Host "NOT FOUND: $($item.Path)" -ForegroundColor Red
        $script:errors++
    }
}

# ---------------------------------------------------------------------------
# P2-A: Delete executive-governance-series 00-08 shell pages (superseded)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "P2-A: Delete superseded executive-governance-series 00-08 shell pages" -ForegroundColor Yellow

$egsDirs = @(
    "docs\customer-documents\executive-governance-series\00-introduction\index.md"
    "docs\customer-documents\executive-governance-series\01-modernization-arc\index.md"
    "docs\customer-documents\executive-governance-series\02-governance-os-overview\index.md"
    "docs\customer-documents\executive-governance-series\03-boundary-impact-model\index.md"
    "docs\customer-documents\executive-governance-series\04-evidence-chain\index.md"
    "docs\customer-documents\executive-governance-series\05-governance-through-specification-and-validation\index.md"
    "docs\customer-documents\executive-governance-series\06-program-model\index.md"
    "docs\customer-documents\executive-governance-series\07-leadership-alignment\index.md"
    "docs\customer-documents\executive-governance-series\08-executive-summary\index.md"
)

foreach ($rel in $egsDirs) {
    $fullPath = Join-Path $RepoRoot $rel
    if (Test-Path $fullPath) {
        if (-not $WhatIf) { Remove-Item $fullPath -Force }
        Write-Action "DELETED (0-byte shell, superseded by ch01-ch09)" $rel "DarkGray"
        $script:fixed++
    } else {
        Write-Host "ALREADY GONE: $rel" -ForegroundColor Gray
        $script:skipped++
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
Write-Host "  Converted / fixed : $fixed"  -ForegroundColor Green
Write-Host "  Skipped (already OK): $skipped" -ForegroundColor Gray
if ($errors -gt 0) {
    Write-Host "  Errors            : $errors" -ForegroundColor Red
}
if ($WhatIf) {
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply changes." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "Next steps after running this script:" -ForegroundColor Cyan
Write-Host "  1. Rebuild the site: quarto render" -ForegroundColor White
Write-Host "  2. Verify findings pages appear at localhost:PORT/findings/" -ForegroundColor White
Write-Host "  3. Verify executive-briefs pages appear and index table links work" -ForegroundColor White
Write-Host "  4. Run .\UIAO-DocAudit-v3.ps1 again — ORPHAN-MD should drop by 16" -ForegroundColor White
Write-Host ""
