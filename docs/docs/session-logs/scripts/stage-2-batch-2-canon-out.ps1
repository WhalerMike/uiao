# Phase D — Stage 2 Batch 2.2: canon content OUT of uiao-docs + dashboard-export workflow patch
# Run AFTER stage-2-batch-1-canon-in.ps1 has pushed successfully to uiao-core.

$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\whale\uiao-docs'

Write-Host "--- Pre-flight: uiao-docs ---" -ForegroundColor Cyan
git status
git pull --rebase origin main

Write-Host "--- Removing 12 YAMLs that moved to uiao-core ---" -ForegroundColor Cyan
git rm `
    data/control-planes.yml `
    data/core-stack.yml `
    data/crosswalk-index.yml `
    data/fedramp-20x.yml `
    data/fedramp_ssp_template_structure.yaml `
    data/inventory-items.yml `
    data/monitoring-sources.yml `
    data/overlay-config.yml `
    data/poam-findings.yml `
    data/management-stack.yml `
    data/program.yml `
    data/vendor-stack.yml

Write-Host "--- Removing SSOT markdown ---" -ForegroundColor Cyan
git rm ssot/UIAO-SSOT.md

Write-Host "--- Removing governance schema ---" -ForegroundColor Cyan
git rm schemas/uiao-governance.schema.json

Write-Host "--- Removing truncated dashboard-schema.json (canonical copy lives in uiao-core) ---" -ForegroundColor Cyan
git rm schemas/dashboard-schema.json

Write-Host "--- Retiring validate-uiao-metadata.yml (canon-validation.yml in uiao-core covers this) ---" -ForegroundColor Cyan
git rm .github/workflows/validate-uiao-metadata.yml

Write-Host "--- Cleaning up empty directories ---" -ForegroundColor Cyan
if ((Get-ChildItem 'ssot' -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
    Remove-Item 'ssot' -Force -ErrorAction SilentlyContinue
    Write-Host "  - ssot/ (empty)"
}
if ((Get-ChildItem 'schemas' -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
    Remove-Item 'schemas' -Force -ErrorAction SilentlyContinue
    Write-Host "  - schemas/ (empty)"
}

Write-Host "--- Patching dashboard-export.yml to read schema from uiao-core ---" -ForegroundColor Cyan
(Get-Content .github/workflows/dashboard-export.yml) `
    -replace '--schema schemas/dashboard-schema\.json', '--schema ../uiao-core/schemas/dashboard-schema.json' `
    | Set-Content .github/workflows/dashboard-export.yml
git add .github/workflows/dashboard-export.yml

Write-Host "--- Staged changes (review before push) ---" -ForegroundColor Cyan
git status

Write-Host "--- Workflow diff (should be exactly one changed line) ---" -ForegroundColor Cyan
git diff --cached -- .github/workflows/dashboard-export.yml

Write-Host "--- Committing + pushing ---" -ForegroundColor Cyan
git commit -m "[UIAO-DOCS] MIGRATE: Phase D Stage 2 — release canon content to uiao-core + rewire dashboard-export workflow"
git push

Write-Host "--- Stage 2 complete. Verify then run Stage 3 scripts. ---" -ForegroundColor Green
