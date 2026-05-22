#!/usr/bin/env pwsh
# scan-doc-eligibility.ps1
#
# Walks the UIAO repo and reports .qmd / .md files that are eligible for:
#   1. Image generation  (mirrors scripts/generate_images.py rules)
#   2. DOCX bundling     (mirrors scripts/bundle_section_docx.py DEFAULT_SECTIONS)
#
# Reports per-file eligibility, per-section counts, and a summary. Does NOT
# modify any files. Read-only audit tool.
#
# Eligibility rules are hand-mirrored from the Python scanners. If the Python
# rules change, update this script's SCAN_ROOTS / EXCLUDE_PATH_PARTS /
# DOCX_BUNDLE_SECTIONS constants to match.
#
# Usage (from any cwd):
#   pwsh -File scripts/scan-doc-eligibility.ps1
#   pwsh -File scripts/scan-doc-eligibility.ps1 -JsonOutput | Out-File audit.json
#   pwsh -File scripts/scan-doc-eligibility.ps1 -ImageOnly
#   pwsh -File scripts/scan-doc-eligibility.ps1 -DocxOnly
#   pwsh -File scripts/scan-doc-eligibility.ps1 -CsvOutput audit.csv

[CmdletBinding()]
param(
    [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")),
    [switch]$JsonOutput,
    [string]$CsvOutput,
    [switch]$ImageOnly,
    [switch]$DocxOnly
)

# ---- Rules mirrored from scripts/generate_images.py ----
$ScanRoots = @(
    "docs",
    "src/uiao/canon/specs",
    "src/uiao/canon/adr"
)
$ScanExts = @(".qmd", ".md")
$ExcludePathParts = @(
    "_site", "_freeze", ".quarto", "node_modules", ".venv",
    "__pycache__", "session-logs", "inbox"
)
$PlaceholderLocalRe = '\[(IMAGE|DIAGRAM|FIGURE)-(\d{2,3}):\s*([^\]]+)\]'
$PlaceholderRefRe   = '\[IMAGE-REF:\s*UIAO-FIG-\d{3}\s*\]'

# ---- Rules mirrored from scripts/bundle_section_docx.py DEFAULT_SECTIONS ----
$DocxBundleSections = @(
    "adapter-specs", "architecture-series", "case-studies", "compliance",
    "executive-briefs", "executive-governance-series", "modernization",
    "modernization-specs", "orgpath-narrative", "platform", "substrate",
    "validation-suites", "whitepapers"
)

function Test-ExcludedPath {
    param([string]$RelPath)
    $parts = $RelPath -split '[/\\]+'
    foreach ($part in $parts) {
        if ($ExcludePathParts -contains $part) { return $true }
    }
    return $false
}

function Get-BundleSection {
    param([string]$RelPath)
    $parts = $RelPath -split '[/\\]+'
    foreach ($section in $DocxBundleSections) {
        if ($parts -contains $section) { return $section }
    }
    return $null
}

# ---- Scan ----
$results = [System.Collections.Generic.List[object]]::new()
$repoRootResolved = (Resolve-Path $RepoRoot).Path

foreach ($scanRoot in $ScanRoots) {
    $fullRoot = Join-Path $repoRootResolved $scanRoot
    if (-not (Test-Path $fullRoot)) {
        Write-Verbose "Scan root missing: $fullRoot"
        continue
    }

    $includeArgs = $ScanExts | ForEach-Object { "*$_" }
    $files = Get-ChildItem -Path $fullRoot -Recurse -File -Include $includeArgs -ErrorAction SilentlyContinue

    foreach ($file in $files) {
        $relPath = $file.FullName.Substring($repoRootResolved.Length).TrimStart('\', '/')
        if (Test-ExcludedPath $relPath) { continue }

        $content = Get-Content -Raw -Path $file.FullName -ErrorAction SilentlyContinue
        if ($null -eq $content) { continue }

        $localMatches = [regex]::Matches($content, $PlaceholderLocalRe)
        $refMatches   = [regex]::Matches($content, $PlaceholderRefRe)
        $totalPlaceholders = $localMatches.Count + $refMatches.Count

        $bundleSection = $null
        if ($file.Extension -eq ".qmd") {
            $bundleSection = Get-BundleSection $relPath
        }
        $isDocxEligible = [bool]$bundleSection

        # Report only if at least one eligibility applies, unless a filter excludes that axis
        $hasImage = $totalPlaceholders -gt 0
        if ($ImageOnly -and -not $hasImage) { continue }
        if ($DocxOnly  -and -not $isDocxEligible) { continue }
        if (-not $hasImage -and -not $isDocxEligible) { continue }

        $results.Add([PSCustomObject]@{
            Path               = $relPath
            Ext                = $file.Extension
            ImagePlaceholders  = $totalPlaceholders
            LocalPlaceholders  = $localMatches.Count
            RefPlaceholders    = $refMatches.Count
            DocxBundleEligible = $isDocxEligible
            BundleSection      = $bundleSection
        })
    }
}

# ---- Output ----
if ($CsvOutput) {
    $results | Sort-Object Path | Export-Csv -Path $CsvOutput -NoTypeInformation
    Write-Host "CSV written: $CsvOutput" -ForegroundColor Green
}
elseif ($JsonOutput) {
    $results | Sort-Object Path | ConvertTo-Json -Depth 3
}
else {
    Write-Host ""
    Write-Host "=== Image-eligible files (placeholders present) ===" -ForegroundColor Cyan
    $imageEligible = $results | Where-Object { $_.ImagePlaceholders -gt 0 } | Sort-Object Path
    if ($imageEligible) {
        $imageEligible | Format-Table Path, ImagePlaceholders, LocalPlaceholders, RefPlaceholders -AutoSize
    }
    else {
        Write-Host "  (none found)" -ForegroundColor DarkGray
    }

    Write-Host "=== DOCX-bundle-eligible files (.qmd in a known section) ===" -ForegroundColor Cyan
    $docxEligible = $results | Where-Object { $_.DocxBundleEligible } | Sort-Object BundleSection, Path
    if ($docxEligible) {
        $docxEligible | Group-Object BundleSection | ForEach-Object {
            Write-Host ""
            Write-Host ("  [{0}]  {1} files" -f $_.Name, $_.Count) -ForegroundColor Yellow
            $_.Group | ForEach-Object { Write-Host "    $($_.Path)" }
        }
    }
    else {
        Write-Host "  (none found)" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "=== Summary ===" -ForegroundColor Cyan
    $imgCount  = ($results | Where-Object { $_.ImagePlaceholders -gt 0 }).Count
    $docxCount = ($results | Where-Object { $_.DocxBundleEligible }).Count
    $bothCount = ($results | Where-Object { $_.ImagePlaceholders -gt 0 -and $_.DocxBundleEligible }).Count
    Write-Host ("  Eligible files total:                  {0}" -f $results.Count)
    Write-Host ("  Image-eligible (placeholders present): {0}" -f $imgCount)
    Write-Host ("  DOCX-bundle-eligible (.qmd in section):{0}" -f $docxCount)
    Write-Host ("  Both image AND docx eligible:          {0}" -f $bothCount)
    Write-Host ""
}
