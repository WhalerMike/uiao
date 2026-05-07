# 10-delete-micro-shells.ps1
# Deletes the 36 x 47-byte micro-shell files in docs\docs\governance\.
# These are YAML-header-only placeholders with no body content — they were
# created as scaffolding and never written. Deleting them is safe: they render
# as blank pages and pollute the site if Quarto ever picks them up.
#
# Before running: verify none of these topics are actively planned for the
# current sprint. The list is printed in -WhatIf mode for your review.
#
# Usage:  .\10-delete-micro-shells.ps1
# Dry run: .\10-delete-micro-shells.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$deleted  = 0
$skipped  = 0
$kept     = 0

Write-Host ""
Write-Host "10-delete-micro-shells.ps1" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# The 36 confirmed micro-shell files (all exactly 47 bytes, all in docs\docs\governance\)
$microShells = @(
    "docs\docs\governance\audit-protocol.md"
    "docs\docs\governance\automation-roadmap.md"
    "docs\docs\governance\charter-addendum-automation.md"
    "docs\docs\governance\communications-plan.md"
    "docs\docs\governance\day1-owner-quickstart.md"
    "docs\docs\governance\drift-pattern-taxonomy.md"
    "docs\docs\governance\escalation-communication-templates.md"
    "docs\docs\governance\faq.md"
    "docs\docs\governance\glossary.md"
    "docs\docs\governance\governance-charter.md"
    "docs\docs\governance\intervention-decision-tree.md"
    "docs\docs\governance\intervention-playbook.md"
    "docs\docs\governance\maturity-model.md"
    "docs\docs\governance\maturity-self-assessment.md"
    "docs\docs\governance\metadata-normalization-strategy.md"
    "docs\docs\governance\metadata-quality-score.md"
    "docs\docs\governance\metadata-remediation-playbook.md"
    "docs\docs\governance\onboarding-certification-exam.md"
    "docs\docs\governance\onboarding-quiz.md"
    "docs\docs\governance\onboarding-workbook.md"
    "docs\docs\governance\operating-model-diagram.md"
    "docs\docs\governance\operating-model-onepager.md"
    "docs\docs\governance\operating-rhythm.md"
    "docs\docs\governance\performance-dashboard-spec.md"
    "docs\docs\governance\performance-scorecard.md"
    "docs\docs\governance\policy-compliance-checklist.md"
    "docs\docs\governance\quarterly-review-template.md"
    "docs\docs\governance\red-flags-guide.md"
    "docs\docs\governance\reliability-forecasting-model.md"
    "docs\docs\governance\risk-heatmap-spec.md"
    "docs\docs\governance\risk-register-template.md"
    "docs\docs\governance\schema-evolution-plan.md"
    "docs\docs\governance\steward-playbook.md"
    "docs\docs\governance\systemic-drift-diagnostic-guide.md"
    "docs\docs\governance\training-curriculum.md"
    "docs\docs\governance\training-deck-outline.md"
)

# Safety check: verify each file is still a micro-shell before deleting.
# If a file has grown beyond 100 bytes since the audit, skip it and report.
Write-Host "Verifying file sizes before deletion..." -ForegroundColor Gray
Write-Host ""

$toDelete = @()
foreach ($rel in $microShells) {
    $fullPath = Join-Path $RepoRoot $rel
    if (-not (Test-Path $fullPath)) {
        Write-Host "  ALREADY GONE : $rel" -ForegroundColor Gray
        $skipped++
        continue
    }
    $size = (Get-Item $fullPath).Length
    if ($size -gt 100) {
        Write-Host "  KEEP (grown to $size bytes — review manually): $rel" -ForegroundColor Yellow
        $kept++
        continue
    }
    $toDelete += $fullPath
}

if ($toDelete.Count -eq 0) {
    Write-Host "Nothing to delete — all files already gone or grown beyond micro-shell threshold."
    Write-Host ""
    exit 0
}

Write-Host "Will delete $($toDelete.Count) micro-shell files:" -ForegroundColor $(if ($WhatIf) { "Cyan" } else { "Red" })
Write-Host ""
foreach ($path in $toDelete) {
    $rel = $path.Replace($RepoRoot + "\", "")
    if ($WhatIf) {
        Write-Host "  [WHATIF] DELETE : $rel" -ForegroundColor Cyan
    } else {
        Remove-Item $path -Force
        Write-Host "  DELETED : $rel" -ForegroundColor DarkGray
        $deleted++
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would delete : $($toDelete.Count) files" -ForegroundColor Cyan
    Write-Host "  Would skip   : $skipped (already gone)" -ForegroundColor Gray
    if ($kept -gt 0) {
        Write-Host "  Would keep   : $kept (grown beyond 100 bytes — review)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Deleted : $deleted files" -ForegroundColor Green
    Write-Host "  Skipped : $skipped (already gone)" -ForegroundColor Gray
    if ($kept -gt 0) {
        Write-Host "  Kept    : $kept (grown beyond 100 bytes — review manually)" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. git add -A && git commit -m 'chore: delete 36 micro-shell governance placeholders'" -ForegroundColor White
    Write-Host "  2. git push" -ForegroundColor White
    Write-Host "  3. .\UIAO-DocAudit-v3.ps1 — MICRO-SHELL should drop to 0" -ForegroundColor White
    Write-Host "  4. Next: 11-promote-shell-pages.ps1 (whitepapers, case-studies, architecture-series)" -ForegroundColor White
}
Write-Host ""
