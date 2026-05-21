<#
.SYNOPSIS
    Seed [IMAGE-NN: ...] placeholders into customer-documents .qmd files based
    on the Pass 2 image-coverage CSV, then optionally invoke the Nano Banana
    generator to produce PNGs.

.DESCRIPTION
    Reads inbox/.qmd-image-pass2-assessment.csv. For every row where
    Recommended > Current and KeyImageIdeas is non-empty, inserts
    (Recommended - Current) new [IMAGE-NN: ...] placeholders into the .qmd.

    Prompt bodies are built as: "<KeyImageIdea>. <VisualStyleSuffix>" — the
    default suffix matches the orgpath-narrative aesthetic (engineering
    blueprint, neutral slate, federal navy / teal / amber, 16:9 landscape).

    Placeholders land in a single contiguous block immediately after the
    document's first H1 (or after the YAML frontmatter if no H1). Authors are
    expected to reposition each placeholder near the section it serves before
    re-generating; the position chosen here is a parking spot, not a final
    location.

    Numbering starts at (max existing image/diagram number + 1) so the script
    is safe to re-run and won't collide with existing figure-block fig IDs of
    the form fig-<docslug>-image-NN or fig-<docslug>-diagram-NN.

    Idempotent: existing [IMAGE-NN: ...] placeholders are not duplicated. A
    doc with Current=2 and Recommended=4 receives exactly 2 new placeholders.

    Trim cases (Current > Recommended in the CSV) are SKIPPED — this script
    never auto-deletes images.

.PARAMETER CsvPath
    Path to Pass 2 CSV. Defaults to inbox/.qmd-image-pass2-assessment.csv.

.PARAMETER DryRun
    Print planned edits without writing any files.

.PARAMETER Section
    Limit to one section under customer-documents/ (e.g. "whitepapers",
    "modernization", "executive-governance-series").

.PARAMETER TopN
    Only process the top N gap docs, sorted by (Recommended - Current) desc.

.PARAMETER InvokeGenerator
    After seeding, run `python scripts/generate_images.py` from the repo root.
    Requires GEMINI_API_KEY in the environment.

.PARAMETER VisualStyleSuffix
    Override the default visual-style suffix appended to each prompt body.

.EXAMPLE
    pwsh scripts/New-CustomerDocsImagePlaceholders.ps1 -DryRun
    Preview seeding across all 127 gap docs.

.EXAMPLE
    pwsh scripts/New-CustomerDocsImagePlaceholders.ps1 -TopN 10
    Seed only the 10 highest-gap docs.

.EXAMPLE
    pwsh scripts/New-CustomerDocsImagePlaceholders.ps1 -Section whitepapers -InvokeGenerator
    Seed all whitepaper gaps and immediately generate PNGs via Gemini.

.NOTES
    Exit codes:
      0   seeding succeeded (and generator succeeded if -InvokeGenerator)
      2   precondition failure (CSV missing, GEMINI_API_KEY missing on -InvokeGenerator)
      N   non-zero exit code propagated from the generator
#>
[CmdletBinding()]
param(
    [string]$CsvPath,
    [switch]$DryRun,
    [string]$Section,
    [int]$TopN,
    [switch]$InvokeGenerator,
    [string]$VisualStyleSuffix
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
if (-not $CsvPath) {
    $CsvPath = Join-Path $repoRoot 'inbox\.qmd-image-pass2-assessment.csv'
}
if (-not (Test-Path $CsvPath)) {
    Write-Error "CSV not found: $CsvPath"
    exit 2
}

if (-not $VisualStyleSuffix) {
    $VisualStyleSuffix = 'Engineering blueprint style, neutral slate background, federal navy (#1F3A5F) for primary structural elements, teal (#1A9E8F) for secondary/integration elements, amber (#D4A017) for governance/audit/registry overlays, monospace labels for identifiers, no human figures, 16:9 landscape.'
}

# Load and filter rows.
$rows    = @(Import-Csv -Path $CsvPath)
$gapRows = @($rows | Where-Object {
    [int]$_.Recommended -gt [int]$_.Current -and $_.KeyImageIdeas.Trim().Length -gt 0
})
$gapRows = @($gapRows | Sort-Object @{Expression={[int]$_.Recommended - [int]$_.Current}; Descending=$true})

if ($Section) {
    $gapRows = @($gapRows | Where-Object { $_.File -match "customer-documents/$Section/" })
}
if ($PSBoundParameters.ContainsKey('TopN') -and $TopN -gt 0) {
    $gapRows = @($gapRows | Select-Object -First $TopN)
}

if ($gapRows.Count -eq 0) {
    Write-Host "No gap rows matched. Done." -ForegroundColor Yellow
    exit 0
}

function Pad2 { param([int]$n) ([string]$n).PadLeft(2, '0') }
function PadL { param($v, [int]$w) ([string]$v).PadLeft($w, ' ') }

Write-Host "Found $($gapRows.Count) gap doc(s) to process" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified." -ForegroundColor Yellow
}
Write-Host ""

$totalInserted = 0
$skipped       = 0

foreach ($row in $gapRows) {
  try {
    $qmdRel  = $row.File
    $qmdPath = Join-Path $repoRoot ($qmdRel -replace '/', '\')
    if (-not (Test-Path $qmdPath)) {
        Write-Warning "Skipping missing: $qmdRel"
        $skipped++
        continue
    }

    $text = Get-Content -Path $qmdPath -Raw -Encoding UTF8

    # Find max existing image/diagram number across both placeholder and
    # figure-block forms so new numbering starts safely after them.
    $allNums = New-Object System.Collections.Generic.List[int]
    foreach ($m in [regex]::Matches($text, '\[IMAGE-(\d+):')) {
        $allNums.Add([int]$m.Groups[1].Value)
    }
    foreach ($m in [regex]::Matches($text, '#fig-[A-Za-z0-9\-]+-(?:image|diagram)-(\d+)')) {
        $allNums.Add([int]$m.Groups[1].Value)
    }
    $startNum = if ($allNums.Count -gt 0) {
        ($allNums | Measure-Object -Maximum).Maximum + 1
    } else { 1 }

    # Determine gap from LIVE doc state. Count BOTH:
    #   1. [IMAGE-NN: ...] placeholders (already-seeded but ungenerated)
    #   2. ![caption](*.png) image references (rendered figures, with or
    #      without #fig-... IDs)
    # The earlier $allNums only counts numbered refs and misses bare
    # markdown image links — which led to over-seeding docs whose existing
    # figures don't use the fig-<doc>-image-NN convention.
    $placeholderCount = @([regex]::Matches($text, '\[IMAGE-(\d+):')).Count
    $imageRefCount    = @([regex]::Matches($text, '!\[[^\]]*\]\([^)]+\.png\)')).Count
    $currentInDoc     = $placeholderCount + $imageRefCount
    $gap = [int]$row.Recommended - $currentInDoc
    if ($gap -le 0) {
        Write-Verbose "Skipping $qmdRel : already at target ($currentInDoc/$($row.Recommended))"
        continue
    }
    $ideas = @($row.KeyImageIdeas -split ';' | ForEach-Object { $_.Trim() } | Where-Object { $_ })
    $ideasToAdd = @($ideas | Select-Object -First $gap)

    if ($ideasToAdd.Count -eq 0) {
        Write-Warning "No usable KeyImageIdeas for $qmdRel — skipping"
        $skipped++
        continue
    }
    if ($ideasToAdd.Count -lt $gap) {
        Write-Verbose "  $qmdRel`: gap=$gap but only $($ideasToAdd.Count) idea(s) available"
    }

    # Build placeholder block.
    $placeholders = New-Object System.Collections.Generic.List[string]
    $num = $startNum
    foreach ($idea in $ideasToAdd) {
        # Strip any "(current)" or "(existing)" markers from the idea — those
        # were used in Pass 2 to flag what's already in the doc and shouldn't
        # leak into the new prompt body.
        $cleanIdea = $idea -replace '\s*\((?:current|existing|already present)\)\s*$', ''
        $promptBody = "$cleanIdea. $VisualStyleSuffix"
        $padded = Pad2 $num
        $placeholders.Add("[IMAGE-${padded}: $promptBody]")
        $num++
    }
    $block = ($placeholders -join "`n`n")

    # Find insertion point: after first H1, else after frontmatter close.
    $lines = $text -split "`r?`n"
    $fmEnd = -1
    if ($lines.Count -gt 0 -and $lines[0] -eq '---') {
        for ($i = 1; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -eq '---') { $fmEnd = $i; break }
        }
    }
    $insertAt = -1
    $start = if ($fmEnd -ge 0) { $fmEnd + 1 } else { 0 }
    for ($i = $start; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^#\s+\S') { $insertAt = $i + 1; break }
    }
    if ($insertAt -lt 0) {
        $insertAt = if ($fmEnd -ge 0) { $fmEnd + 1 } else { 0 }
    }

    $head = ($lines | Select-Object -First $insertAt) -join "`n"
    $tail = ($lines | Select-Object -Skip  $insertAt) -join "`n"
    $newText = $head + "`n`n" + $block + "`n`n" + $tail

    $cnt   = PadL $ideasToAdd.Count 2
    $start = Pad2 $startNum
    if ($DryRun) {
        Write-Host "  WOULD seed $cnt placeholder(s) starting IMAGE-$start  in  $qmdRel" -ForegroundColor Yellow
    } else {
        Set-Content -Path $qmdPath -Value $newText -Encoding UTF8 -NoNewline
        Write-Host "  Seeded $cnt placeholder(s) starting IMAGE-$start  in  $qmdRel" -ForegroundColor Green
    }
    $totalInserted += $ideasToAdd.Count
  }
  catch {
    Write-Warning "Error processing $($row.File): $($_.Exception.Message)"
    $skipped++
    continue
  }
}

Write-Host ""
$verb = if ($DryRun) { 'Planned' } else { 'Seeded' }
Write-Host "$verb $totalInserted placeholder(s)    Skipped doc(s): $skipped" -ForegroundColor Cyan

if ($InvokeGenerator -and -not $DryRun) {
    Write-Host ""
    Write-Host "Invoking python scripts/generate_images.py ..." -ForegroundColor Cyan
    if (-not $env:GEMINI_API_KEY) {
        Write-Error "GEMINI_API_KEY is not set in the environment."
        exit 2
    }
    Push-Location $repoRoot
    try {
        python scripts/generate_images.py
        $genExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    if ($genExit -ne 0) {
        Write-Error "Generator exited $genExit"
        exit $genExit
    }
}

exit 0
