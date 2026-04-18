# =============================================================================
# stage-4-batch-4.2-strip-uiao-core.ps1
# Phase D Stage 4, Batch 4.2 — Strip app-code from uiao-core, consolidate specs
# -----------------------------------------------------------------------------
# Prereqs:
#   - Batch 4.1 committed + tagged v0.1.0 on uiao-impl (ideally pushed, but
#     local tag is enough — Batch 4.3 will verify the push state).
#   - uiao-core working tree clean.
# What this does:
#   - git rm Bucket A (Python app code).
#   - rm -rf Bucket C (Stage 3 residue + build cruft). Uses git rm where tracked,
#     plain Remove-Item where untracked (with ls-files guard for safety).
#   - Moves Bucket D (18 single-.md spec dirs) into canon/specs/.
#   - Rewrites pyproject.toml as canon-only.
#   - Updates .gitignore.
#   - Stages + commits ONE atomic migration commit.
#   - STOPS before push.
# Safety:
#   - Per-path `git ls-files --error-unmatch` guard before any delete, to
#     distinguish tracked vs untracked (the Part-B cleanup-script lesson).
#   - Dry-run flag: pass -DryRun to preview without executing.
# =============================================================================

param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\whale'
$CoreDir  = Join-Path $RepoRoot 'uiao-core'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Confirm-Or-Exit($prompt) {
    $ans = Read-Host "$prompt [y/N]"
    if ($ans -ne 'y' -and $ans -ne 'Y') { Write-Host 'Aborted.' -ForegroundColor Yellow; exit 1 }
}
function Is-Tracked($path) {
    git ls-files --error-unmatch -- $path 2>$null | Out-Null
    return ($LASTEXITCODE -eq 0)
}
function Safe-Remove($path) {
    if (-not (Test-Path $path)) { return }
    if (Is-Tracked $path) {
        if ($DryRun) { Write-Host "  [dry] git rm -r -- $path" }
        else         { git rm -r --quiet -- $path; Write-Host "  git rm $path" }
    } else {
        if ($DryRun) { Write-Host "  [dry] Remove-Item -Recurse -Force $path" }
        else         { Remove-Item -Recurse -Force -- $path; Write-Host "  rm   $path" }
    }
}

# --- Preflight ----------------------------------------------------------------
Set-Location $CoreDir
Write-Step 'Preflight'
$status = git status --porcelain
if ($status) {
    Write-Host 'uiao-core has uncommitted changes — resolve before proceeding:' -ForegroundColor Red
    Write-Host $status
    exit 1
}
Write-Host "uiao-core clean at $(git rev-parse --short HEAD)" -ForegroundColor Green

if ($DryRun) { Write-Host 'DRY-RUN MODE — no filesystem or git changes will be made.' -ForegroundColor Yellow }

# --- 1. Bucket A — git rm Python app code ------------------------------------
Write-Step 'Bucket A — remove Python app code'
$bucketA = @(
    'src\uiao_core',
    'src\uiao_core.egg-info',
    'tests',
    'scripts',
    'adapters',
    'inject_ssp.py',
    'write_engine.py',
    '.coveragerc',
    '.coverage'
)
# orchestrator/ needs split handling (Compliance-Orchestrator.md goes to canon/specs/)
foreach ($p in $bucketA) { Safe-Remove $p }

# orchestrator/ — split: .md to canon/specs, the rest to /dev/null
Write-Step 'orchestrator/ — split: .md to canon/specs, rest removed'
if (Test-Path 'orchestrator') {
    $md = Get-ChildItem -Path 'orchestrator' -Filter '*.md' -File -ErrorAction SilentlyContinue
    foreach ($mdFile in $md) {
        $target = Join-Path 'canon\specs' ($mdFile.BaseName + '.md')
        if ($DryRun) { Write-Host "  [dry] move $($mdFile.FullName) -> $target" }
        else {
            New-Item -ItemType Directory -Force -Path 'canon\specs' | Out-Null
            # Use git mv where tracked (preserves history)
            $rel = $mdFile.FullName.Substring($CoreDir.Length + 1)
            if (Is-Tracked $rel) { git mv -- $rel $target }
            else                  { Move-Item -LiteralPath $rel -Destination $target -Force }
            Write-Host "  moved $rel -> $target"
        }
    }
    Safe-Remove 'orchestrator'
}

# Top-level src/ — if empty after uiao_core removal, purge the shell
if ((Test-Path 'src') -and (-not (Get-ChildItem 'src' -Force -ErrorAction SilentlyContinue))) {
    if ($DryRun) { Write-Host '  [dry] rmdir src' }
    else         { Remove-Item -Force 'src'; Write-Host '  rmdir src' }
}

# --- 2. Bucket C — purge Stage 3 residue + build cruft ------------------------
Write-Step 'Bucket C — purge build/output residue'
$bucketC = @(
    'dryrun-output',
    'scuba-real-run',
    'site',
    'artifacts',
    'reports',
    'provenance',
    'dashboard\_quarto.yml',
    'dashboard\index.qmd',
    'machine'
)
foreach ($p in $bucketC) { Safe-Remove $p }
# dashboard/ directory itself — if now empty, purge
if ((Test-Path 'dashboard') -and (-not (Get-ChildItem 'dashboard' -Force -ErrorAction SilentlyContinue))) {
    if ($DryRun) { Write-Host '  [dry] rmdir dashboard' }
    else         { Remove-Item -Force 'dashboard'; Write-Host '  rmdir dashboard' }
}

# --- 3. Bucket D — consolidate spec dirs into canon/specs/ --------------------
Write-Step 'Bucket D — consolidate single-.md spec dirs into canon/specs/'
if (-not $DryRun) { New-Item -ItemType Directory -Force -Path 'canon\specs' | Out-Null }

# Map: source-dir -> target-filename (if dir holds a single .md, flatten; else keep names)
$specDirs = @(
    @{ src='api';         flat='api-contract.md' },
    @{ src='cli';         flat='cli.md' },
    @{ src='cql';         flat='cql.md' },
    @{ src='drift';       flat='drift.md' },
    @{ src='enforcement'; flat=$null },   # has nested runtime/ — handle below
    @{ src='evidence';    flat=$null },   # 2 files — keep names
    @{ src='governance';  flat='governance.md' },
    @{ src='ha';          flat='ha.md' },
    @{ src='performance'; flat='performance.md' },
    @{ src='platform';    flat=$null },   # 2 files
    @{ src='policy';      flat='policy.md' },
    @{ src='recovery';    flat='recovery.md' },
    @{ src='release';     flat='release.md' },
    @{ src='tenancy';     flat='tenancy.md' },
    @{ src='testing';     flat=$null },   # 2 files
    @{ src='zero-trust';  flat='zero-trust.md' },
    @{ src='data-lake';   flat='data-lake.md' }
)
foreach ($spec in $specDirs) {
    $dir = $spec.src
    if (-not (Test-Path $dir)) { continue }
    $mdFiles = Get-ChildItem -Path $dir -Recurse -Filter '*.md' -File -ErrorAction SilentlyContinue
    foreach ($mdFile in $mdFiles) {
        if ($spec.flat -and $mdFiles.Count -eq 1) {
            $target = Join-Path 'canon\specs' $spec.flat
        } else {
            $target = Join-Path 'canon\specs' $mdFile.Name
        }
        $rel = $mdFile.FullName.Substring($CoreDir.Length + 1)
        if ($DryRun) { Write-Host "  [dry] git mv $rel -> $target" }
        else {
            if (Is-Tracked $rel) { git mv -- $rel $target }
            else                  { Move-Item -LiteralPath $rel -Destination $target -Force }
            Write-Host "  $rel -> $target"
        }
    }
    # Purge the now-empty spec dir
    Safe-Remove $dir
}

# --- 4. Rewrite pyproject.toml (canon-only) -----------------------------------
Write-Step 'Rewriting pyproject.toml as canon-only'
$canonPyproject = @'
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "uiao-core"
version = "0.2.0"
description = "UIAO canonical governance artifacts — YAMLs, schemas, playbooks, and canon enforcement tooling. Consumed by uiao-impl for generators and validators."
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Apache-2.0" }
authors = [{ name = "Michael Stratton", email = "michael.francis.stratton@gmail.com" }]

# Canon-enforcement tooling dependencies only (tools/*.py).
dependencies = [
    "pyyaml>=6.0",
    "jsonschema>=4.0",
]

# No [project.scripts] — CLI lives in uiao-impl.
# No [tool.setuptools.packages.find] — uiao-core is not a Python package.
'@
if ($DryRun) {
    Write-Host '  [dry] would overwrite pyproject.toml'
} else {
    Set-Content 'pyproject.toml' -Value $canonPyproject -Encoding UTF8
}

# --- 5. Update .gitignore (drop src/, tests/, build outputs) ------------------
Write-Step 'Updating .gitignore'
$gi = @'
# Python (defensive — canon has no src/, but contributors may vendor tools)
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.eggs/
*.egg

# venv
.venv/
venv/
env/

# pytest / coverage (canon tools only — keep minimal)
.pytest_cache/
.coverage
.coverage.*
htmlcov/

# IDE / OS
.vscode/
.idea/
*.swp
.DS_Store
Thumbs.db

# Quarto render outputs (canon never renders site/)
_site/
.quarto/
_book/

# Generator outputs must never be committed to canon
out/
dryrun-output/
scuba-real-run/
artifacts/
reports/
provenance/

# Branded deliverables that belong in uiao-docs, not canon
exports/**/*.docx
exports/**/*.pptx
'@
if ($DryRun) { Write-Host '  [dry] would overwrite .gitignore' }
else         { Set-Content '.gitignore' -Value $gi -Encoding UTF8 }

# --- 6. Commit ----------------------------------------------------------------
Write-Step 'Git status preview'
git status --short | Select-Object -First 60
$count = (git status --porcelain | Measure-Object -Line).Lines
Write-Host "Total paths changed: $count"

if ($DryRun) { Write-Host '[dry-run end — no commit made]' -ForegroundColor Yellow; exit 0 }

Confirm-Or-Exit 'Stage all + commit as [UIAO-CORE] MIGRATE?'
git add -A
git commit -m @"
[UIAO-CORE] MIGRATE: uiao_impl - app code split out; canon spec consolidation

- Removed: src/, tests/, scripts/, adapters/, orchestrator/, inject_ssp.py,
  write_engine.py, .coveragerc (moved to WhalerMike/uiao-impl @ v0.1.0)
- Purged: dryrun-output/, scuba-real-run/, site/, artifacts/, reports/,
  provenance/, machine/, dashboard/_quarto.yml, dashboard/index.qmd
- Consolidated: 18 single-.md spec dirs -> canon/specs/
- Rewrote: pyproject.toml as canon-only (removed [project.scripts] + packages.find)
- Updated: .gitignore to ignore generator outputs and branded DOCX/PPTX

Canon-side tools/ and workflows untouched; tools/*.py has zero uiao_core imports.
"@

Write-Step 'Batch 4.2 complete'
Write-Host "uiao-core is now canon+enforcement-only. Review with: git show --stat HEAD" -ForegroundColor Green
Write-Host 'Push when ready:  git push origin main'                                    -ForegroundColor Green
Write-Host 'Then run Batch 4.3 (smoke test).'                                          -ForegroundColor Green
