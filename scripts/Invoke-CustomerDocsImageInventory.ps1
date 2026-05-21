<#
.SYNOPSIS
    Inventory images per customer-documents subfolder; flag orphans and
    broken references.

.DESCRIPTION
    For each subfolder of docs/customer-documents/ that contains at least
    one .qmd file, reports:

      Qmds         Total .qmd files (recursive)
      PNGs         Total PNG files on disk (recursive)
      ImageRefs    Total ![](...png) references in all .qmd files
      UniqueRefs   Distinct PNG paths referenced
      Orphans      PNGs on disk that no .qmd in the section references
      Broken       Referenced PNG paths that don't exist on disk
      Status       Aggregate:
                     OK                 nothing to do
                     NeedsIntegration   orphans > 0 (images generated
                                          but not embedded in any .qmd)
                     BrokenRefs         broken > 0 (.qmd points at a
                                          PNG that isn't on disk)
                     NoImages           section has no images at all
                     Mixed              both orphans AND broken refs

    Read-only — never modifies files.

    Honors only the explicit `![](image.png)` Quarto / Markdown figure
    syntax. PNG-only; SVG / PDF / other formats are not counted. Build
    directories (_freeze, _site, .quarto, node_modules, __pycache__) are
    excluded from both the PNG and .qmd scans.

.PARAMETER Detail
    Print per-section lists of orphan PNGs and broken references for any
    section whose Status is not OK or NoImages.

.PARAMETER Section
    Limit the scan to a single section (folder name directly under
    docs/customer-documents/).

.PARAMETER Root
    Override the customer-documents root. Defaults to
    docs/customer-documents/ under the repo root.

.EXAMPLE
    pwsh scripts/Invoke-CustomerDocsImageInventory.ps1
    Section-by-section summary table for every section under
    customer-documents/.

.EXAMPLE
    pwsh scripts/Invoke-CustomerDocsImageInventory.ps1 -Detail
    Same summary plus per-file lists for any section with drift.

.EXAMPLE
    pwsh scripts/Invoke-CustomerDocsImageInventory.ps1 -Section whitepapers -Detail
    Detail only for the whitepapers section.

.NOTES
    Exit codes:
        0   no orphans and no broken refs across scanned sections
        1   at least one section has orphans or broken refs
        2   precondition failure (root or section path missing)
#>
[CmdletBinding()]
param(
    [switch]$Detail,
    [string]$Section,
    [string]$Root
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
if (-not $Root) {
    $Root = Join-Path $repoRoot 'docs\customer-documents'
}
if (-not (Test-Path $Root)) {
    Write-Error "Root not found: $Root"
    exit 2
}

$excludeDirs = @('_freeze', '_site', '.quarto', 'node_modules', '__pycache__')
$rxImageRef  = [regex]'!\[[^\]]*\]\((?<src>[^)]+\.png)\)'

function Test-PathInExcludedDir {
    param([string]$AbsPath, [string]$Base, [string[]]$Excluded)
    $rel = $AbsPath.Substring($Base.Length).TrimStart('\','/')
    foreach ($seg in $rel.Split([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)) {
        if ($Excluded -contains $seg) { return $true }
    }
    return $false
}

function Get-FilteredChildren {
    param([string]$Base, [string]$Filter, [string[]]$Excluded)
    @(Get-ChildItem -Path $Base -Filter $Filter -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { -not (Test-PathInExcludedDir -AbsPath $_.FullName -Base $Base -Excluded $Excluded) })
}

# Pick which subfolders to scan.
$subfolders = if ($Section) {
    $p = Join-Path $Root $Section
    if (-not (Test-Path $p)) {
        Write-Error "Section not found: $Section ($p)"
        exit 2
    }
    @(Get-Item $p)
} else {
    @(Get-ChildItem -Path $Root -Directory | Where-Object {
        $qmdCount = @(Get-FilteredChildren -Base $_.FullName -Filter '*.qmd' -Excluded $excludeDirs).Count
        $qmdCount -gt 0
    })
}

$rows = @(foreach ($folder in $subfolders) {
    $sectionRoot = $folder.FullName

    # Always @-wrap: function-pipeline returns unwrap to scalar (one item) or
    # $null (zero items), and strict mode then chokes on .Count.
    $qmds = @(Get-FilteredChildren -Base $sectionRoot -Filter '*.qmd' -Excluded $excludeDirs)
    $pngs = @(Get-FilteredChildren -Base $sectionRoot -Filter '*.png' -Excluded $excludeDirs)

    # PNG set on disk: section-relative paths, lowercased for case-insensitive set ops.
    $pngSet = [System.Collections.Generic.HashSet[string]]::new()
    foreach ($p in $pngs) {
        $rel = $p.FullName.Substring($sectionRoot.Length).TrimStart('\','/').Replace('\','/').ToLower()
        [void]$pngSet.Add($rel)
    }

    $refSet   = [System.Collections.Generic.HashSet[string]]::new()
    $refCount = 0
    foreach ($q in $qmds) {
        $text = Get-Content -Path $q.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if (-not $text) { continue }
        foreach ($m in $rxImageRef.Matches($text)) {
            $refCount++
            $src = $m.Groups['src'].Value.Trim()
            # Skip external URLs and absolute web paths — we only audit local files.
            if ($src -match '^(https?:|/)') { continue }
            # Resolve relative to the .qmd's directory.
            $absRef = [IO.Path]::GetFullPath((Join-Path $q.DirectoryName $src))
            # Only count refs that point INTO this section's tree.
            if (-not $absRef.StartsWith($sectionRoot, [StringComparison]::OrdinalIgnoreCase)) { continue }
            $rel = $absRef.Substring($sectionRoot.Length).TrimStart('\','/').Replace('\','/').ToLower()
            [void]$refSet.Add($rel)
        }
    }

    $orphans = @($pngSet | Where-Object { -not $refSet.Contains($_) })
    $broken  = @($refSet | Where-Object { -not $pngSet.Contains($_) })

    $status =
        if ($pngs.Count -eq 0 -and $refSet.Count -eq 0)            { 'NoImages' }
        elseif ($broken.Count -gt 0 -and $orphans.Count -gt 0)     { 'Mixed' }
        elseif ($broken.Count -gt 0)                               { 'BrokenRefs' }
        elseif ($orphans.Count -gt 0)                              { 'NeedsIntegration' }
        else                                                       { 'OK' }

    [pscustomobject]@{
        Section      = $folder.Name
        Qmds         = $qmds.Count
        PNGs         = $pngs.Count
        ImageRefs    = $refCount
        UniqueRefs   = $refSet.Count
        Orphans      = $orphans.Count
        Broken       = $broken.Count
        Status       = $status
        _Orphans     = $orphans
        _Broken      = $broken
    }
})

$rows = @($rows | Sort-Object Section)

Write-Host "Customer-documents image inventory" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""
$rows | Format-Table -AutoSize -Property Section,Qmds,PNGs,ImageRefs,UniqueRefs,Orphans,Broken,Status |
    Out-String | Write-Host

if ($Detail) {
    foreach ($row in $rows) {
        if ($row.Orphans -eq 0 -and $row.Broken -eq 0) { continue }
        Write-Host ""
        Write-Host "=== $($row.Section) ===" -ForegroundColor Cyan
        if ($row.Orphans -gt 0) {
            Write-Host "  Orphan PNGs (on disk, not referenced by any .qmd):" -ForegroundColor Yellow
            foreach ($o in $row._Orphans) { Write-Host "    $o" }
        }
        if ($row.Broken -gt 0) {
            Write-Host "  Broken refs (referenced by a .qmd, not on disk):" -ForegroundColor Red
            foreach ($b in $row._Broken) { Write-Host "    $b" }
        }
    }
}

$totalSections   = $rows.Count
$okCount         = @($rows | Where-Object Status -eq 'OK').Count
$needCount       = @($rows | Where-Object Status -eq 'NeedsIntegration').Count
$brokenCount     = @($rows | Where-Object Status -eq 'BrokenRefs').Count
$mixedCount      = @($rows | Where-Object Status -eq 'Mixed').Count
$noImagesCount   = @($rows | Where-Object Status -eq 'NoImages').Count
$problemSections = $needCount + $brokenCount + $mixedCount

Write-Host ""
Write-Host ("Sections: {0}    OK: {1}    NeedsIntegration: {2}    BrokenRefs: {3}    Mixed: {4}    NoImages: {5}" -f `
    $totalSections, $okCount, $needCount, $brokenCount, $mixedCount, $noImagesCount) `
    -ForegroundColor $(if ($problemSections -gt 0) { 'Yellow' } else { 'Green' })

if ($problemSections -gt 0) { exit 1 } else { exit 0 }
