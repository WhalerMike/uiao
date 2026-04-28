<#
.SYNOPSIS
    Normalizes new ADR files (ADR-001 through ADR-004, Index, Review Protocol)
    to match the existing UIAO canon ADR naming convention.

.DESCRIPTION
    Existing convention in canon/adr/:
        adr-NNN-descriptive-name.md   (lowercase, hyphen-separated, 3-digit padded, .md)

    New files violate this with uppercase names and underscore separators.

    This script:
        1. Renames files to match the existing convention
        2. Updates all internal cross-references (links between ADR files)
        3. Updates YAML frontmatter values (adr_id, document_id) to match
        4. Produces a manifest of all changes for git commit message

.PARAMETER AdrPath
    Path to the ADR directory. Defaults to the canonical location.

.EXAMPLE
    .\Normalize-NewADRFiles.ps1
    .\Normalize-NewADRFiles.ps1 -WhatIf
    .\Normalize-NewADRFiles.ps1 -AdrPath "D:\repos\uiao\src\uiao\canon\adr"
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [Parameter()]
    [string]$AdrPath = "C:\Users\whale\git\uiao\src\uiao\canon\adr"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Rename Map ──────────────────────────────────────────────────────────────
# Key   = current filename (as dropped into the directory)
# Value = target filename (matching existing convention)

$RenameMap = [ordered]@{
    'ADR-001_HAADJ_Deprecated_Entra_Join_Only.md'     = 'adr-001-haadj-deprecated-entra-join-only.md'
    'ADR-002_Arc_Entra_Join_No_Domain_Join.md'         = 'adr-002-arc-entra-join-no-domain-join.md'
    'ADR-003_API_Driven_Inbound_Provisioning.md'       = 'adr-003-api-driven-inbound-provisioning.md'
    'ADR-004_Workload_Identity_Federation_Default.md'  = 'adr-004-workload-identity-federation-default.md'
    'UIAO_ADR_INDEX.md'                                = 'adr-index.md'
    'UIAO_ADR_REVIEW_PROTOCOL.md'                      = 'adr-review-protocol.md'
}

# ── Internal Reference Replacements ─────────────────────────────────────────
# Cross-references inside file content (markdown links, Related Documents, etc.)

$ContentReplacements = [ordered]@{
    # File link references
    'ADR-001_HAADJ_Deprecated_Entra_Join_Only.md'      = 'adr-001-haadj-deprecated-entra-join-only.md'
    'ADR-002_Arc_Entra_Join_No_Domain_Join.md'          = 'adr-002-arc-entra-join-no-domain-join.md'
    'ADR-003_API_Driven_Inbound_Provisioning.md'        = 'adr-003-api-driven-inbound-provisioning.md'
    'ADR-004_Workload_Identity_Federation_Default.md'   = 'adr-004-workload-identity-federation-default.md'
    'UIAO_ADR_REVIEW_PROTOCOL.md'                       = 'adr-review-protocol.md'

    # YAML frontmatter adr_id / document_id normalization
    'adr_id: ADR-001'                = 'adr_id: adr-001'
    'adr_id: ADR-002'                = 'adr_id: adr-002'
    'adr_id: ADR-003'                = 'adr_id: adr-003'
    'adr_id: ADR-004'                = 'adr_id: adr-004'
    'document_id: UIAO_ADR_INDEX'    = 'document_id: uiao-adr-index'
    'document_id: UIAO_ADR_REVIEW'   = 'document_id: uiao-adr-review-protocol'
}

# ── Validation ──────────────────────────────────────────────────────────────

if (-not (Test-Path $AdrPath)) {
    Write-Error "ADR directory not found: $AdrPath"
    return
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  UIAO ADR File Normalizer" -ForegroundColor Cyan
Write-Host "  Target: $AdrPath" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# ── Phase 1: File Renames ───────────────────────────────────────────────────

Write-Host "`n-- Phase 1: File Renames --" -ForegroundColor Yellow

$renameLog = @()
$missingFiles = @()

foreach ($entry in $RenameMap.GetEnumerator()) {
    $sourcePath = Join-Path $AdrPath $entry.Key
    $targetPath = Join-Path $AdrPath $entry.Value

    if (-not (Test-Path $sourcePath)) {
        $missingFiles += $entry.Key
        Write-Host "  SKIP  $($entry.Key)  (not found)" -ForegroundColor DarkGray
        continue
    }

    if (Test-Path $targetPath) {
        Write-Host "  SKIP  $($entry.Key) -> $($entry.Value)  (target already exists)" -ForegroundColor DarkYellow
        continue
    }

    if ($PSCmdlet.ShouldProcess($entry.Key, "Rename to $($entry.Value)")) {
        Rename-Item -Path $sourcePath -NewName $entry.Value -Force
        Write-Host "  OK    $($entry.Key)" -ForegroundColor Green
        Write-Host "     -> $($entry.Value)" -ForegroundColor Green
        $renameLog += [PSCustomObject]@{
            OldName = $entry.Key
            NewName = $entry.Value
            Action  = 'Renamed'
        }
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Host "`n  WARNING: $($missingFiles.Count) file(s) not found -- may already be renamed." -ForegroundColor DarkYellow
}

# ── Phase 2: Content Reference Updates ──────────────────────────────────────

Write-Host "`n-- Phase 2: Internal Reference Updates --" -ForegroundColor Yellow

# Only process the new files (now renamed) -- don't touch existing ADRs
$targetFiles = $RenameMap.Values | ForEach-Object {
    $fullPath = Join-Path $AdrPath $_
    if (Test-Path $fullPath) { $fullPath }
}

$contentLog = @()

foreach ($filePath in $targetFiles) {
    $fileName = Split-Path $filePath -Leaf
    $content = Get-Content -Path $filePath -Raw -Encoding UTF8
    $originalContent = $content
    $replacementCount = 0

    foreach ($entry in $ContentReplacements.GetEnumerator()) {
        if ($content.Contains($entry.Key)) {
            $content = $content.Replace($entry.Key, $entry.Value)
            $replacementCount++
        }
    }

    if ($replacementCount -gt 0) {
        if ($PSCmdlet.ShouldProcess($fileName, "Update $replacementCount internal reference(s)")) {
            # Preserve UTF-8 without BOM
            [System.IO.File]::WriteAllText($filePath, $content, [System.Text.UTF8Encoding]::new($false))
            Write-Host "  OK    $fileName  ($replacementCount replacement(s))" -ForegroundColor Green
            $contentLog += [PSCustomObject]@{
                File         = $fileName
                Replacements = $replacementCount
            }
        }
    }
    else {
        Write-Host "  SKIP  $fileName  (no references to update)" -ForegroundColor DarkGray
    }
}

# ── Phase 3: Collision & Integrity Checks ───────────────────────────────────

Write-Host "`n-- Phase 3: Collision & Integrity Checks --" -ForegroundColor Yellow

# Check for numbering collisions with existing files
$existingADRs = Get-ChildItem -Path $AdrPath -Filter "adr-*.md" |
    Where-Object { $_.Name -match '^adr-(\d{3})-' } |
    ForEach-Object {
        [PSCustomObject]@{
            Number = [int]($Matches[1])
            Name   = $_.Name
        }
    } | Sort-Object Number

$numberGroups = $existingADRs | Group-Object Number | Where-Object { $_.Count -gt 1 }

if ($numberGroups.Count -gt 0) {
    Write-Host "  COLLISION DETECTED:" -ForegroundColor Red
    foreach ($group in $numberGroups) {
        Write-Host "    adr-$($group.Name.ToString().PadLeft(3,'0')): $($group.Group.Name -join ', ')" -ForegroundColor Red
    }
}
else {
    Write-Host "  OK    No numbering collisions" -ForegroundColor Green
}

# Verify all new files have valid YAML frontmatter
foreach ($filePath in $targetFiles) {
    $fileName = Split-Path $filePath -Leaf
    $firstLine = (Get-Content -Path $filePath -TotalCount 1).Trim()
    if ($firstLine -eq '---') {
        Write-Host "  OK    $fileName  (valid YAML frontmatter)" -ForegroundColor Green
    }
    else {
        Write-Host "  WARN  $fileName  (missing YAML frontmatter)" -ForegroundColor Red
    }
}

# List full ADR series for verification
Write-Host "`n-- Current ADR Series (adr-NNN-*.md) --" -ForegroundColor Yellow
$existingADRs | ForEach-Object {
    Write-Host ("  adr-{0:D3}  {1}" -f $_.Number, $_.Name) -ForegroundColor White
}

# ── Summary ─────────────────────────────────────────────────────────────────

Write-Host "`n-- Summary --" -ForegroundColor Yellow
Write-Host "  Files renamed:              $($renameLog.Count)" -ForegroundColor White
Write-Host "  Files with refs updated:    $($contentLog.Count)" -ForegroundColor White
Write-Host "  Files not found (skipped):  $($missingFiles.Count)" -ForegroundColor White

# ── Git Commit Message ──────────────────────────────────────────────────────

Write-Host "`n-- Suggested git commands --" -ForegroundColor Cyan
Write-Host ""
Write-Host "  cd $AdrPath" -ForegroundColor White
Write-Host "  git add -A ." -ForegroundColor White
Write-Host '  git commit -m "chore(adr): normalize identity transformation ADRs to repo convention' -ForegroundColor White
Write-Host '' -ForegroundColor White
Write-Host '  Renamed files to match existing adr-NNN-descriptive-name.md convention.' -ForegroundColor White
Write-Host '  Updated internal cross-references and YAML frontmatter IDs.' -ForegroundColor White
Write-Host '  New ADRs fill the previously empty adr-001 through adr-004 slots:' -ForegroundColor White
Write-Host '    - adr-001: HAADJ Deprecated (Entra ID Join Only)' -ForegroundColor White
Write-Host '    - adr-002: Arc Servers Require Non-Domain-Joined State' -ForegroundColor White
Write-Host '    - adr-003: API-Driven Inbound Provisioning (HR-Agnostic)' -ForegroundColor White
Write-Host '    - adr-004: Workload Identity Federation Default' -ForegroundColor White
Write-Host '    - adr-index: ADR Registry' -ForegroundColor White
Write-Host '    - adr-review-protocol: Review Cadence and Automation' -ForegroundColor White
Write-Host '' -ForegroundColor White
Write-Host '  Ref: UIAO_IDT_001, UIAO_IDT_002"' -ForegroundColor White

Write-Host "`n-- Complete --`n" -ForegroundColor Green
