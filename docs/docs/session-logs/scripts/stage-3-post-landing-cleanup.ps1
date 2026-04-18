# Phase D — Stage 3 post-landing cleanup
# Addresses three residual items from Stage 2/3 execution:
#  (1) force-track branded DOCX/PPTX in uiao-docs that were blocked by .gitignore
#  (2) prune uiao-docs .gitignore so "exports/" as a directory isn't blanket-ignored
#  (3) remove filesystem-only cruft from uiao-core (never tracked, but still on disk)

$ErrorActionPreference = 'Stop'

# ------------------------------------------------------------------
# Part A — uiao-docs: let the three branded deliverables be tracked
# ------------------------------------------------------------------

Set-Location 'C:\Users\whale\uiao-docs'

Write-Host "--- Pre-flight: uiao-docs ---" -ForegroundColor Cyan
git status
git pull --rebase origin main

Write-Host "--- Trimming .gitignore: keep *.docx/*.pptx wildcard-block, drop bare exports/ blanket ---" -ForegroundColor Cyan
# Remove the two lines that blanket-ignore the whole exports/ dir.
# Keeps 'exports/**/*.docx' and 'exports/**/*.pptx' which block generated outputs,
# but allows explicit -f add of specific branded files, and allows tracking
# exports/README.md / exports/<other files>.
$gi = Get-Content .gitignore
$giNew = $gi | Where-Object { $_ -notmatch '^exports/$' -and $_ -notmatch '^exports/\*\*$' }
Set-Content .gitignore $giNew
git add .gitignore

Write-Host "--- Force-adding branded deliverables (-f overrides remaining wildcard rules) ---" -ForegroundColor Cyan
git add -f exports/docx/UIAO_003_Adapter_Segmentation_Overview_v1.0.docx
git add -f exports/docx/UIAO_SCuBA_Technical_Specification.docx
if (Test-Path 'exports/pptx/UIAO_Leadership_Briefing_v1.0.pptx') {
    git add -f exports/pptx/UIAO_Leadership_Briefing_v1.0.pptx
}

Write-Host "--- Review ---" -ForegroundColor Cyan
git status
git diff --cached -- .gitignore

Write-Host "--- Committing + pushing uiao-docs ---" -ForegroundColor Cyan
git commit -m "[UIAO-DOCS] FIX: Phase D Stage 3 follow-up — track 3 branded deliverables, trim redundant .gitignore"
git push

# ------------------------------------------------------------------
# Part B — uiao-core: purge filesystem-only cruft
# ------------------------------------------------------------------

Set-Location 'C:\Users\whale\uiao-core'

Write-Host "--- Removing untracked branded DOCX and plantuml.jar from uiao-core working tree ---" -ForegroundColor Cyan
Remove-Item -Force -ErrorAction SilentlyContinue `
    'UIAO_003_Adapter_Segmentation_Overview_v1.0.docx', `
    'UIAO_SCuBA_Technical_Specification.docx', `
    'plantuml.jar'

Write-Host "--- Purging orphaned gitignored directories (assets/, exports/) ---" -ForegroundColor Cyan
# These were left on disk because they contained untracked files Stage 3 git rm couldn't touch.
# Post-Stage-3 .gitignore now blocks them, so they're pure filesystem clutter.
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue assets
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue exports

# Also zap the egg-info / build / dryrun-output / site leftovers if present
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue build
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue dryrun-output
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue site
Remove-Item -Force -Recurse -ErrorAction SilentlyContinue UNKNOWN.egg-info

Write-Host "--- Verifying uiao-core is clean ---" -ForegroundColor Cyan
git status

Write-Host "--- Done. No git commit needed in uiao-core (all removed files were untracked). ---" -ForegroundColor Green
