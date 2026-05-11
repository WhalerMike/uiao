# 12-resolve-orphan-group2.ps1
# Resolves the 12 remaining ORPHAN-MD files (Group 2 — internal/ambiguous).
# Clear deletes are handled automatically.
# Borderline files are listed for review and left untouched.
#
# Usage:  .\12-resolve-orphan-group2.ps1
# Dry run: .\12-resolve-orphan-group2.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$deleted  = 0
$moved    = 0
$skipped  = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function Remove-OrphanFile {
    param([string]$RelPath, [string]$Reason)
    $fullPath = Join-Path $RepoRoot $RelPath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ALREADY GONE: $RelPath" -ForegroundColor Gray
        $script:skipped++
        return
    }
    if (-not $WhatIf) { Remove-Item $fullPath -Force }
    Write-Action "DELETED ($Reason)" $RelPath "DarkGray"
    $script:deleted++
}

function Move-ToInbox {
    param([string]$RelPath, [string]$Reason)
    $fullPath  = Join-Path $RepoRoot $RelPath
    $leaf      = Split-Path $RelPath -Leaf
    $destPath  = Join-Path $RepoRoot "inbox\drafts\$leaf"
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ALREADY GONE: $RelPath" -ForegroundColor Gray
        $script:skipped++
        return
    }
    if (-not $WhatIf) {
        if (-not (Test-Path (Join-Path $RepoRoot "inbox\drafts"))) {
            New-Item -ItemType Directory -Path (Join-Path $RepoRoot "inbox\drafts") -Force | Out-Null
        }
        Move-Item $fullPath $destPath -Force
    }
    Write-Action "MOVED to inbox\drafts\ ($Reason)" $RelPath "Yellow"
    $script:moved++
}

Write-Host ""
Write-Host "12-resolve-orphan-group2.ps1" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# CLEAR DELETES — duplicates, dev logs, tiny internal READMEs
# ---------------------------------------------------------------------------
Write-Host "Clear deletes" -ForegroundColor Yellow

Remove-OrphanFile "docs\session-log.md"          "development session log, not site content"
Remove-OrphanFile "docs\exports\README.md"        "246 bytes, internal tooling README"
Remove-OrphanFile "docs\visuals\README.md"        "internal tooling README"
Remove-OrphanFile "docs\diagrams\README.md"       "internal tooling README (diagrams\ spec lives in repo root diagrams\)"
Remove-OrphanFile "docs\governance\CODE_OF_CONDUCT.md" "duplicate of root CODE_OF_CONDUCT.md"
Remove-OrphanFile "docs\customer-documents\TREE.md"    "internal nav map, superseded by site navigation"

# ---------------------------------------------------------------------------
# MOVE TO INBOX — valuable internal docs, not ready to publish
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Move to inbox\drafts\ (valuable but internal)" -ForegroundColor Yellow

Move-ToInbox "docs\planning\customer-documents-taxonomy.md" "22 KB planning doc — useful reference, not a customer page"
Move-ToInbox "docs\SUMMARY.md"                              "internal summary, may overlap with index.qmd"

# ---------------------------------------------------------------------------
# REPORTS — convert to .qmd (reports section index exists as LIVE-QMD)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Reports — converting to .qmd (reports section is live)" -ForegroundColor Yellow

$reports = @(
    @{ File="docs\reports\cli-surface-audit-v0.4.0.md";      Title="CLI Surface Audit v0.4.0";      Subtitle="Public surface audit of the UIAO CLI — version 0.4.0" }
    @{ File="docs\reports\public-surface-audit-v0.5.0.md";   Title="Public Surface Audit v0.5.0";   Subtitle="Public surface audit of the UIAO documentation site — version 0.5.0" }
    @{ File="docs\reports\SCuBA-Canonical-Report.md";         Title="SCuBA Canonical Report";        Subtitle="SCuBA canonical configuration assessment report" }
)

foreach ($r in $reports) {
    $fullPath = Join-Path $RepoRoot $r.File
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ALREADY GONE: $($r.File)" -ForegroundColor Gray
        $script:skipped++
        continue
    }
    $qmdPath = $fullPath -replace '\.md$', '.qmd'
    if (Test-Path $qmdPath) {
        Write-Host "  SKIP (.qmd exists): $($r.File)" -ForegroundColor Gray
        $script:skipped++
        continue
    }
    $content = Get-Content $fullPath -Raw
    $hasYaml = $content.TrimStart().StartsWith("---")
    $newContent = $content
    if (-not $hasYaml) {
        $yaml  = "---`ntitle: `"$($r.Title)`"`nsubtitle: `"$($r.Subtitle)`"`n---`n`n"
        $newContent = $yaml + $content
    }
    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $newContent -Encoding UTF8 -NoNewline
        Remove-Item $fullPath -Force
    }
    Write-Action "CONVERTED" "$($r.File)  →  $(Split-Path $qmdPath -Leaf)" "Green"
    $script:moved++
}

# ---------------------------------------------------------------------------
# PUBLICATIONS INDEX — convert if publications section should be live
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Publications index" -ForegroundColor Yellow

$pubIndex = Join-Path $RepoRoot "docs\publications\INDEX.md"
if (Test-Path $pubIndex) {
    $size = (Get-Item $pubIndex).Length
    Write-Host "  docs\publications\INDEX.md ($size bytes)" -ForegroundColor Yellow
    Write-Host "  → Check: is the publications section in the site nav?" -ForegroundColor Gray
    Write-Host "    If YES: run manually: rename to INDEX.qmd and add YAML header" -ForegroundColor Gray
    Write-Host "    If NO:  run manually: Remove-Item docs\publications\INDEX.md" -ForegroundColor Gray
    Write-Host "    Left untouched — your decision." -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would delete : $deleted files" -ForegroundColor Cyan
    Write-Host "  Would move   : $moved files (to inbox\drafts\)" -ForegroundColor Cyan
    Write-Host "  Would skip   : $skipped" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Deleted : $deleted files" -ForegroundColor Green
    Write-Host "  Moved   : $moved files" -ForegroundColor Yellow
    Write-Host "  Skipped : $skipped" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Decide docs\publications\INDEX.md (see note above)" -ForegroundColor White
    Write-Host "  2. git add -A && git commit -m 'chore: resolve Group 2 orphaned docs'" -ForegroundColor White
    Write-Host "  3. git push" -ForegroundColor White
    Write-Host "  4. .\UIAO-DocAudit-v3.ps1 — ORPHAN-MD should drop to 1 (publications)" -ForegroundColor White
    Write-Host "  5. Final remaining work: LEGACY-DOCS triage (docs\docs\ — 158 files)" -ForegroundColor White
    Write-Host "     Priority: gcc-boundary-*.md (31 KB) → convert to .qmd first" -ForegroundColor White
}
Write-Host ""
