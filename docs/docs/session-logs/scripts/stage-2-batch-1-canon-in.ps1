# Phase D — Stage 2 Batch 2.1: canon content INTO uiao-core
# Run from anywhere; script self-locates. Expects C:\Users\whale\uiao-core and C:\Users\whale\uiao-docs to exist side-by-side.

$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\whale\uiao-core'

Write-Host "--- Pre-flight: uiao-core ---" -ForegroundColor Cyan
git status
git pull --rebase origin main

Write-Host "--- Pre-flight: uiao-docs ---" -ForegroundColor Cyan
Set-Location 'C:\Users\whale\uiao-docs'
git status
git pull --rebase origin main

Set-Location 'C:\Users\whale\uiao-core'

Write-Host "--- Creating canon/data target ---" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path 'canon\data' | Out-Null

$canonYamls = @(
    'control-planes.yml',
    'core-stack.yml',
    'crosswalk-index.yml',
    'fedramp-20x.yml',
    'fedramp_ssp_template_structure.yaml',
    'inventory-items.yml',
    'monitoring-sources.yml',
    'overlay-config.yml',
    'poam-findings.yml',
    'management-stack.yml',
    'program.yml',
    'vendor-stack.yml'
)

Write-Host "--- Copying 12 canon YAMLs from uiao-docs/data ---" -ForegroundColor Cyan
foreach ($f in $canonYamls) {
    Copy-Item "..\uiao-docs\data\$f" -Destination "canon\data\$f"
    Write-Host "  + canon\data\$f"
}

Write-Host "--- Copying UIAO-SSOT.md ---" -ForegroundColor Cyan
Copy-Item '..\uiao-docs\ssot\UIAO-SSOT.md' -Destination 'canon\UIAO-SSOT.md'

Write-Host "--- Copying uiao-governance.schema.json ---" -ForegroundColor Cyan
Copy-Item '..\uiao-docs\schemas\uiao-governance.schema.json' -Destination 'schemas\uiao-governance.schema.json'

Write-Host "--- Staging + committing ---" -ForegroundColor Cyan
git add canon/ schemas/
git commit -m "[UIAO-CORE] MIGRATE: Phase D Stage 2 — pull 12 canon YAMLs, UIAO-SSOT.md, governance schema from uiao-docs"

Write-Host "--- Pushing ---" -ForegroundColor Cyan
git push

Write-Host "--- Done. Verify then run stage-2-batch-2-canon-out.ps1 ---" -ForegroundColor Green
