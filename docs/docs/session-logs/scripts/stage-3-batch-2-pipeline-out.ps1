# Phase D — Stage 3 Batch 3.2: strip doc pipeline OUT of uiao-core
# Run AFTER stage-3-batch-1-pipeline-in.ps1 has pushed to uiao-docs.
# This is the largest delete batch in Phase D (~170 MB).

$ErrorActionPreference = 'Stop'

Set-Location 'C:\Users\whale\uiao-core'

Write-Host "--- Pre-flight ---" -ForegroundColor Cyan
git status
git pull --rebase origin main

Write-Host "--- Retiring Jinja2 pipeline (templates/, generation-inputs/, docs/) ---" -ForegroundColor Cyan
git rm -r templates
git rm -r generation-inputs
git rm -r docs

Write-Host "--- Removing static assets (now in uiao-docs) ---" -ForegroundColor Cyan
git rm -r visuals
git rm -r assets

Write-Host "--- Removing _quarto.yml (canonical copy lives in uiao-docs) ---" -ForegroundColor Cyan
git rm _quarto.yml

Write-Host "--- Removing exports/ (regeneratable build artifacts) ---" -ForegroundColor Cyan
git rm -r exports

Write-Host "--- Removing root-level branded DOCX (now in uiao-docs/exports/docx/) ---" -ForegroundColor Cyan
git rm UIAO_003_Adapter_Segmentation_Overview_v1.0.docx
git rm UIAO_SCuBA_Technical_Specification.docx

Write-Host "--- Removing plantuml.jar (use plantweb pip package instead) ---" -ForegroundColor Cyan
git rm plantuml.jar

Write-Host "--- Retiring 7 Jinja2-era workflows ---" -ForegroundColor Cyan
git rm .github/workflows/generate-docs.yml
git rm .github/workflows/generate-docx-exports.yml
git rm .github/workflows/render-and-insert-diagrams.yml
git rm .github/workflows/deploy-docs.yml
git rm .github/workflows/generate-artifacts.yml
git rm .github/workflows/generate_artifacts.yml
git rm .github/workflows/docs.yml

Write-Host "--- Appending .gitignore entries ---" -ForegroundColor Cyan
@"

# Phase D Stage 3 additions — doc pipeline now lives in uiao-docs
_quarto.yml
docs/
templates/
generation-inputs/
visuals/
assets/
exports/
plantuml.jar
"@ | Add-Content -Path .gitignore
git add .gitignore

Write-Host "--- Review staged changes ---" -ForegroundColor Cyan
git status
git diff --cached --stat

Write-Host "--- Committing + pushing (expect ~170 MB of deletions) ---" -ForegroundColor Cyan
git commit -m "[UIAO-CORE] MIGRATE: Phase D Stage 3 — release doc pipeline to uiao-docs, retire Jinja2 template chain"
git push

Write-Host "--- Stage 3 complete. Ping Claude to verify. ---" -ForegroundColor Green
