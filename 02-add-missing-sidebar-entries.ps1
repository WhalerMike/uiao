<#
.SYNOPSIS
  UIAO Fix 02 — Add missing documents to _quarto.yml sidebar.

.DESCRIPTION
  Adds ~30 documents that exist on disk (per TREE.md) but are missing
  from the _quarto.yml sidebar navigation. Targets the "Document families
  (legacy — migration in progress)" section.

  Documents added:
    - 4 executive briefs (drift-engine, evidence-fabric, governance-os,
      modernization, zero-trust overviews)
    - 4 architecture series papers (boundary-impact-model, drift-engine,
      evidence-chain, six-plane-architecture, three-layer-rule-model)
    - 8 executive governance chapters (00–08)
    - 3 case studies
    - 1 whitepaper (governance-os)

.NOTES
  Run from the repo root after 01-fix-link-extensions.ps1.
  Idempotent — checks for existing entries before inserting.
#>

param(
    [switch]$DryRun,
    [string]$RepoRoot = (Get-Location).Path
)

$quartoPath = Join-Path $RepoRoot "docs" "_quarto.yml"
if (-not (Test-Path $quartoPath)) {
    Write-Error "_quarto.yml not found at $quartoPath. Run from the repo root."
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 02: Add Missing Sidebar Entries" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified.`n" -ForegroundColor Yellow
}

$content = Get-Content -Path $quartoPath -Raw -Encoding UTF8
$original = $content

# ── EXECUTIVE BRIEFS ──
# Insert after: - customer-documents/executive-briefs/uiao-executive-brief.qmd
$execBriefAnchor = "- customer-documents/executive-briefs/uiao-executive-brief.qmd"
$execBriefAdditions = @"

        - customer-documents/executive-briefs/drift-engine-overview.qmd
        - customer-documents/executive-briefs/evidence-fabric-overview.qmd
        - customer-documents/executive-briefs/governance-os-overview.qmd
        - customer-documents/executive-briefs/modernization-overview.qmd
        - customer-documents/executive-briefs/zero-trust-overview.qmd
"@

if ($content -match [regex]::Escape("drift-engine-overview")) {
    Write-Host "  [SKIP] Executive brief entries already present." -ForegroundColor DarkGray
} elseif ($content -match [regex]::Escape($execBriefAnchor)) {
    $content = $content.Replace($execBriefAnchor, "$execBriefAnchor$execBriefAdditions")
    Write-Host "  [ADD] 5 executive brief overview documents" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find executive-brief anchor line. Manual edit needed." -ForegroundColor Yellow
}

# ── ARCHITECTURE SERIES ──
# Insert after: - customer-documents/architecture-series/aodim-architecture.qmd
$archAnchor = "- customer-documents/architecture-series/aodim-architecture.qmd"
$archAdditions = @"

        - customer-documents/architecture-series/boundary-impact-model.qmd
        - customer-documents/architecture-series/drift-engine.qmd
        - customer-documents/architecture-series/evidence-chain.qmd
        - customer-documents/architecture-series/six-plane-architecture.qmd
        - customer-documents/architecture-series/three-layer-rule-model.qmd
"@

if ($content -match [regex]::Escape("boundary-impact-model")) {
    Write-Host "  [SKIP] Architecture series entries already present." -ForegroundColor DarkGray
} elseif ($content -match [regex]::Escape($archAnchor)) {
    $content = $content.Replace($archAnchor, "$archAnchor$archAdditions")
    Write-Host "  [ADD] 5 architecture series documents" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find architecture-series anchor line. Manual edit needed." -ForegroundColor Yellow
}

# ── CASE STUDIES ──
# Insert after: - customer-documents/case-studies/index.qmd
$caseAnchor = "- customer-documents/case-studies/index.qmd"
$caseAdditions = @"

        - customer-documents/case-studies/identity-modernization-case-study.qmd
        - customer-documents/case-studies/cloud-boundary-case-study.qmd
        - customer-documents/case-studies/federal-modernization-case-study.qmd
"@

if ($content -match [regex]::Escape("identity-modernization-case-study")) {
    Write-Host "  [SKIP] Case study entries already present." -ForegroundColor DarkGray
} elseif ($content -match [regex]::Escape($caseAnchor)) {
    $content = $content.Replace($caseAnchor, "$caseAnchor$caseAdditions")
    Write-Host "  [ADD] 3 case study documents" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find case-studies anchor line. Manual edit needed." -ForegroundColor Yellow
}

# ── EXECUTIVE GOVERNANCE SERIES ──
# Insert after: - customer-documents/executive-governance-series/governance-os-canonical-suite.qmd
$govAnchor = "- customer-documents/executive-governance-series/governance-os-canonical-suite.qmd"
$govAdditions = @"

        - customer-documents/executive-governance-series/00-introduction.qmd
        - customer-documents/executive-governance-series/01-modernization-arc.qmd
        - customer-documents/executive-governance-series/02-governance-model.qmd
        - customer-documents/executive-governance-series/03-compliance-framework.qmd
        - customer-documents/executive-governance-series/04-identity-transformation.qmd
        - customer-documents/executive-governance-series/05-evidence-fabric.qmd
        - customer-documents/executive-governance-series/06-drift-engine.qmd
        - customer-documents/executive-governance-series/07-operational-model.qmd
        - customer-documents/executive-governance-series/08-executive-summary.qmd
"@

if ($content -match [regex]::Escape("00-introduction")) {
    Write-Host "  [SKIP] Executive governance chapter entries already present." -ForegroundColor DarkGray
} elseif ($content -match [regex]::Escape($govAnchor)) {
    $content = $content.Replace($govAnchor, "$govAnchor$govAdditions")
    Write-Host "  [ADD] 9 executive governance series chapters (00–08)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Could not find executive-governance anchor line. Manual edit needed." -ForegroundColor Yellow
}

# ── WRITE OUTPUT ──
if ($content -ne $original) {
    if ($DryRun) {
        Write-Host "`nDRY RUN COMPLETE: Changes identified but not written." -ForegroundColor Yellow
    } else {
        Set-Content -Path $quartoPath -Value $content -Encoding UTF8 -NoNewline
        Write-Host "`nCOMPLETE: _quarto.yml updated with missing sidebar entries." -ForegroundColor Green
    }
} else {
    Write-Host "`nNo changes needed — all entries already present." -ForegroundColor Green
}

Write-Host ""
Write-Host "IMPORTANT: After running this script, verify that each added .qmd" -ForegroundColor Yellow
Write-Host "file actually exists on disk. If a file is listed in _quarto.yml" -ForegroundColor Yellow
Write-Host "but does not exist, Quarto will fail at render time." -ForegroundColor Yellow
Write-Host ""
Write-Host "Verification command:" -ForegroundColor Cyan
Write-Host '  Get-Content docs\_quarto.yml | Select-String "customer-documents/" | ForEach-Object { $f = ($_.Line.Trim() -replace "^- ",""); if (-not (Test-Path "docs\$f")) { Write-Host "[MISSING] $f" -ForegroundColor Red } }' -ForegroundColor White
Write-Host ""
Write-Host "Next step: Run 03-fix-index-page-links.ps1`n" -ForegroundColor Cyan
