# =============================================================================
# stage-4-batch-4.1-populate-uiao-impl.ps1
# Phase D Stage 4, Batch 4.1 — Populate uiao-impl from uiao-core
# -----------------------------------------------------------------------------
# Prereqs:
#   - Batch 4.0 already committed+pushed on uiao-impl.
#   - uiao-core clone at C:\Users\whale\uiao-core is at HEAD 02af2e63 or later,
#     working tree clean (verify with: git status).
# What this does:
#   - Copies Bucket A (Python app code) from uiao-core -> uiao-impl WITHOUT
#     touching uiao-core's tree (Batch 4.2 will do the uiao-core deletions).
#   - Renames src/uiao_core/ -> src/uiao_impl/.
#   - Sed-sweeps 'from uiao_core' / 'import uiao_core' -> uiao_impl across
#     *.py and pyproject.toml.
#   - Runs pip install -e . and pytest locally to verify.
#   - Commits + tags v0.1.0.
#   - STOPS before push — user confirms manually.
# Idempotent: robocopy /MIR would be destructive; we use Copy-Item -Recurse
# -Force and rely on Batch 4.0 having an empty skeleton for src/uiao_impl.
# =============================================================================

$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\whale'
$CoreDir  = Join-Path $RepoRoot 'uiao-core'
$ImplDir  = Join-Path $RepoRoot 'uiao-impl'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Confirm-Or-Exit($prompt) {
    $ans = Read-Host "$prompt [y/N]"
    if ($ans -ne 'y' -and $ans -ne 'Y') { Write-Host 'Aborted.' -ForegroundColor Yellow; exit 1 }
}

# --- Preflight -----------------------------------------------------------------
Write-Step 'Preflight checks'
if (-not (Test-Path $CoreDir)) { throw "uiao-core not found at $CoreDir" }
if (-not (Test-Path $ImplDir)) { throw "uiao-impl not found at $ImplDir — run Batch 4.0 first" }

Push-Location $CoreDir
$coreStatus = git status --porcelain
if ($coreStatus) {
    Write-Host 'uiao-core has uncommitted changes — resolve before proceeding:' -ForegroundColor Red
    Write-Host $coreStatus
    Pop-Location
    exit 1
}
Pop-Location

Push-Location $ImplDir
$implStatus = git status --porcelain
if ($implStatus) {
    Write-Host 'uiao-impl has uncommitted changes — resolve before proceeding:' -ForegroundColor Red
    Write-Host $implStatus
    Pop-Location
    exit 1
}
Pop-Location

Set-Location $ImplDir

# --- 1. Copy Bucket A from uiao-core ------------------------------------------
Write-Step 'Copying Bucket A (Python app code) from uiao-core'

# 1a. Package source: src/uiao_core/ -> src/uiao_impl/
# Remove the Batch 4.0 placeholder before copying
if (Test-Path 'src\uiao_impl') { Remove-Item -Recurse -Force 'src\uiao_impl' }
Copy-Item -Path (Join-Path $CoreDir 'src\uiao_core')      -Destination 'src\uiao_impl' -Recurse -Force

# 1b. Top-level code dirs: adapters, scripts, tests, orchestrator
foreach ($d in @('adapters', 'scripts', 'tests', 'orchestrator')) {
    $src = Join-Path $CoreDir $d
    if (Test-Path $src) {
        if (Test-Path $d) { Remove-Item -Recurse -Force $d }
        Copy-Item -Path $src -Destination $d -Recurse -Force
        Write-Host "  copied $d"
    }
}

# 1c. Root .py files
foreach ($f in @('inject_ssp.py', 'write_engine.py')) {
    $src = Join-Path $CoreDir $f
    if (Test-Path $src) { Copy-Item -Path $src -Destination $f -Force; Write-Host "  copied $f" }
}

# 1d. .coveragerc
$srcCov = Join-Path $CoreDir '.coveragerc'
if (Test-Path $srcCov) { Copy-Item -Path $srcCov -Destination '.coveragerc' -Force }

# 1e. pyproject.toml — carry over the full uiao-core version, then rename
Copy-Item -Path (Join-Path $CoreDir 'pyproject.toml') -Destination 'pyproject.toml' -Force

# 1f. Prune compiled + build artifacts that tag along
foreach ($pat in @('src\uiao_impl\__pycache__',
                   'src\uiao_impl\**\__pycache__',
                   'tests\__pycache__',
                   'tests\**\__pycache__',
                   'scripts\__pycache__',
                   'adapters\__pycache__',
                   'adapters\**\__pycache__',
                   'orchestrator\__pycache__')) {
    Get-ChildItem -Path . -Recurse -Force -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -like "*$pat*" -and $_.Name -eq '__pycache__' } |
        ForEach-Object { Remove-Item -Recurse -Force $_.FullName; Write-Host "  pruned $($_.FullName)" }
}
# Also prune any uiao_core.egg-info that hitched a ride
Get-ChildItem -Path . -Recurse -Force -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'uiao_core\.egg-info|uiao_impl\.egg-info' } |
    ForEach-Object { Remove-Item -Recurse -Force $_.FullName; Write-Host "  pruned $($_.FullName)" }

# --- 2. Rename uiao_core -> uiao_impl across *.py and pyproject.toml ----------
Write-Step 'Sed-sweep: uiao_core -> uiao_impl'

$pyFiles = Get-ChildItem -Path . -Recurse -Include *.py -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\' -and $_.FullName -notmatch '\\__pycache__\\' }

$touched = 0
foreach ($f in $pyFiles) {
    $orig = Get-Content -Raw -LiteralPath $f.FullName
    if ($orig -match 'uiao_core') {
        $new = $orig `
            -replace 'from uiao_core', 'from uiao_impl' `
            -replace 'import uiao_core', 'import uiao_impl' `
            -replace '\buiao_core\.',   'uiao_impl.'    `
            -replace "'uiao_core'",     "'uiao_impl'"   `
            -replace '"uiao_core"',     '"uiao_impl"'
        if ($new -ne $orig) {
            Set-Content -LiteralPath $f.FullName -Value $new -NoNewline:$false
            $touched++
        }
    }
}
Write-Host "  rewrote uiao_core -> uiao_impl in $touched .py files"

# pyproject.toml updates
$py = Get-Content -Raw 'pyproject.toml'
$py = $py `
    -replace 'name\s*=\s*"uiao-core"',            'name = "uiao-impl"' `
    -replace 'uiao_core\.cli\.app:app',           'uiao_impl.cli.app:app' `
    -replace '\buiao_core\b',                     'uiao_impl'
Set-Content 'pyproject.toml' -Value $py -NoNewline:$false
Write-Host '  rewrote pyproject.toml'

# --- 3. Residual sanity check -------------------------------------------------
Write-Step 'Verifying no uiao_core references remain'
$leftover = Select-String -Path (Get-ChildItem -Recurse -Include *.py,*.toml,*.cfg -File |
                                 Where-Object { $_.FullName -notmatch '\\\.git\\' }).FullName `
                          -Pattern 'uiao_core' -List -ErrorAction SilentlyContinue
if ($leftover) {
    Write-Host 'WARNING: residual uiao_core references found:' -ForegroundColor Yellow
    $leftover | ForEach-Object { Write-Host "  $($_.Path)" }
    Confirm-Or-Exit 'Continue despite residuals?'
} else {
    Write-Host '  none — clean' -ForegroundColor Green
}

# --- 4. Local install + pytest ------------------------------------------------
Write-Step 'pip install -e . (editable install)'
python -m pip install -e . 2>&1 | Tee-Object -Variable pipOut | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host 'pip install failed' -ForegroundColor Red; exit 1 }

Write-Step 'pytest (smoke — may be slow)'
pytest -q --maxfail=5 2>&1 | Tee-Object -Variable testOut | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host 'pytest had failures. Review above; Ctrl-C to abort or confirm to commit anyway.' -ForegroundColor Yellow
    Confirm-Or-Exit 'Commit despite test failures?'
}

# --- 5. Commit + tag ----------------------------------------------------------
Write-Step 'git status preview'
git status --short | Select-Object -First 40
$totalChanges = (git status --porcelain | Measure-Object -Line).Lines
Write-Host "Total changed paths: $totalChanges"

Confirm-Or-Exit 'Stage all, commit as feat(split), and tag v0.1.0?'

git add -A
git commit -m "[UIAO-IMPL] CREATE: migrate app code from uiao-core; rename uiao_core -> uiao_impl"
git tag -a v0.1.0 -m 'Initial uiao-impl release — migrated from uiao-core Phase D Stage 4'

Write-Step 'Batch 4.1 complete'
Write-Host 'Push when ready:'                           -ForegroundColor Green
Write-Host '  git push origin main'                     -ForegroundColor Green
Write-Host '  git push origin v0.1.0'                   -ForegroundColor Green
Write-Host 'Then proceed to Batch 4.2 (strip uiao-core).' -ForegroundColor Green
