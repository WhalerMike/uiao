# Phase D — Stage 3 Batch 3.1: pull static doc assets INTO uiao-docs
# Run AFTER Stage 2 has completed on both repos.

$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\whale\uiao-docs'

Write-Host "--- Pre-flight ---" -ForegroundColor Cyan
git status
git pull --rebase origin main
Set-Location 'C:\Users\whale\uiao-core'
git status
git pull --rebase origin main

Set-Location 'C:\Users\whale\uiao-docs'

Write-Host "--- Creating target directories ---" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path 'visuals' | Out-Null
New-Item -ItemType Directory -Force -Path 'assets' | Out-Null
New-Item -ItemType Directory -Force -Path 'assets\images' | Out-Null
New-Item -ItemType Directory -Force -Path 'exports\docx' | Out-Null
New-Item -ItemType Directory -Force -Path 'exports\pptx' | Out-Null

Write-Host "--- Copying visuals/ (PlantUML + PNG + README) ---" -ForegroundColor Cyan
Copy-Item '..\uiao-core\visuals\*' -Destination 'visuals\' -Recurse -Force

Write-Host "--- Copying assets/demo.svg ---" -ForegroundColor Cyan
Copy-Item '..\uiao-core\assets\demo.svg' -Destination 'assets\demo.svg' -Force

if (Test-Path '..\uiao-core\assets\images') {
    Write-Host "--- Copying assets/images/ ---" -ForegroundColor Cyan
    Copy-Item '..\uiao-core\assets\images\*' -Destination 'assets\images\' -Recurse -Force
}

Write-Host "--- Copying branded DOCX exports ---" -ForegroundColor Cyan
Copy-Item '..\uiao-core\UIAO_003_Adapter_Segmentation_Overview_v1.0.docx' `
          -Destination 'exports\docx\UIAO_003_Adapter_Segmentation_Overview_v1.0.docx' -Force
Copy-Item '..\uiao-core\UIAO_SCuBA_Technical_Specification.docx' `
          -Destination 'exports\docx\UIAO_SCuBA_Technical_Specification.docx' -Force

if (Test-Path '..\uiao-core\exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx') {
    Write-Host "--- Copying leadership briefing PPTX ---" -ForegroundColor Cyan
    Copy-Item '..\uiao-core\exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx' `
              -Destination 'exports\pptx\UIAO_Leadership_Briefing_v1.0.pptx' -Force
}

Write-Host "--- Staging + committing ---" -ForegroundColor Cyan
git add visuals/ assets/ exports/docx/ exports/pptx/
git status
git commit -m "[UIAO-DOCS] MIGRATE: Phase D Stage 3 — pull visuals, assets, and branded DOCX/PPTX exports from uiao-core"
git push

Write-Host "--- Done. Run stage-3-batch-2-pipeline-out.ps1 next. ---" -ForegroundColor Green
