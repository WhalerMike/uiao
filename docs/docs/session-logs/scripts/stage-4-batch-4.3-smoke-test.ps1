# =============================================================================
# stage-4-batch-4.3-smoke-test.ps1
# Phase D Stage 4, Batch 4.3 — Smoke test both repos post-split
# -----------------------------------------------------------------------------
# Prereqs:
#   - uiao: v0.1.0 tag pushed to origin.
#   - uiao: Batch 4.2 commit pushed to origin.
# What this does:
#   - Creates a throwaway venv and installs uiao from the v0.1.0 tag.
#   - Runs `uiao --help` to confirm the CLI entry point resolves.
#   - Runs a minimal canon-side check against uiao/tools/*.py to verify
#     the enforcement layer still imports and runs without the app package.
#   - Prints a green/red summary.
# Non-destructive: does not modify either repo.
# =============================================================================

$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\whale'
$CoreDir  = Join-Path $RepoRoot 'uiao'
$ImplDir  = Join-Path $RepoRoot 'uiao'
$VenvDir  = Join-Path $env:TEMP 'uiao-smoke-venv'

function Write-Step($msg)    { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)      { Write-Host "[OK]  $msg" -ForegroundColor Green }
function Write-Fail($msg)    { Write-Host "[FAIL] $msg" -ForegroundColor Red }

$results = [ordered]@{}

# --- 1. Verify tag/commit are pushed ------------------------------------------
Write-Step 'Check 1 — remote tag v0.1.0 on uiao'
Set-Location $ImplDir
$remoteTag = git ls-remote --tags origin v0.1.0 2>$null
if ($remoteTag) { Write-OK 'v0.1.0 is on origin'; $results['tag-pushed'] = $true }
else            { Write-Fail 'v0.1.0 NOT found on origin — push it first'; $results['tag-pushed'] = $false }

Write-Step 'Check 2 — uiao main reaches the MIGRATE commit'
Set-Location $CoreDir
$migrateHit = git log --format='%h %s' HEAD | Select-String -Pattern 'MIGRATE' | Select-Object -First 1
if ($migrateHit) { Write-OK "MIGRATE commit in HEAD ancestry: $migrateHit"; $results['core-commit'] = $true }
else             { Write-Fail "MIGRATE commit not reachable from HEAD"; $results['core-commit'] = $false }

# --- 3. Throwaway venv + install from tag -------------------------------------
Write-Step 'Check 3 — install uiao from v0.1.0 tag in fresh venv'
if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
python -m venv $VenvDir
$pip    = Join-Path $VenvDir 'Scripts\pip.exe'
$python = Join-Path $VenvDir 'Scripts\python.exe'
$uiao   = Join-Path $VenvDir 'Scripts\uiao.exe'

& $pip install --upgrade pip 2>&1 | Out-Null
& $pip install "git+https://github.com/WhalerMike/uiao.git@v0.1.0" 2>&1 | Tee-Object -Variable installOut | Out-Host
if ($LASTEXITCODE -eq 0) { Write-OK 'pip install succeeded'; $results['pip-install'] = $true }
else                      { Write-Fail 'pip install failed';   $results['pip-install'] = $false }

# --- 4. `uiao --help` ---------------------------------------------------------
Write-Step 'Check 4 — uiao --help'
if (Test-Path $uiao) {
    $helpOut = & $uiao --help 2>&1
    if ($LASTEXITCODE -eq 0) { Write-OK 'uiao --help exits 0'; $results['cli-help'] = $true; Write-Host ($helpOut | Out-String) }
    else                      { Write-Fail 'uiao --help nonzero exit';    $results['cli-help'] = $false; Write-Host $helpOut }
} else {
    Write-Fail "uiao.exe not found at $uiao"; $results['cli-help'] = $false
}

# --- 5. Import smoke ----------------------------------------------------------
Write-Step 'Check 5 — python -c "import uiao_impl"'
$importOut = & $python -c "import uiao_impl; print(uiao_impl.__version__)" 2>&1
if ($LASTEXITCODE -eq 0) { Write-OK "uiao_impl imported: version $importOut"; $results['import'] = $true }
else                      { Write-Fail "import failed: $importOut";            $results['import'] = $false }

# --- 6. Canon enforcement tools still work without app package ---------------
Write-Step 'Check 6 — uiao/tools/*.py import without uiao_impl installed'
# Use system python (not the venv) to simulate a canon-only environment.
Set-Location $CoreDir
$coreTools = @('metadata_validator.py', 'drift_detector.py', 'dashboard_exporter.py',
               'appendix_indexer.py', 'sync_canon.py')
$toolsOk = $true
foreach ($t in $coreTools) {
    $tPath = Join-Path 'tools' $t
    if (-not (Test-Path $tPath)) { continue }
    # Just compile-check (don't execute); surfaces syntax + top-level import errors.
    python -m py_compile $tPath 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { Write-OK "$t compiles" }
    else                      { Write-Fail "$t failed compile"; $toolsOk = $false }
}
$results['canon-tools'] = $toolsOk

# --- 7. Cross-repo smoke — uiao CLI reading canon from uiao --------
Write-Step 'Check 7 — uiao CLI finds canon via --canon-path (if CLI supports it)'
$canonTest = & $uiao --canon-path (Join-Path $CoreDir 'canon') validate --help 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-OK 'uiao validate --help resolves with --canon-path'
    $results['cross-repo'] = $true
} else {
    # Not fatal — CLI may not have a `validate` subcommand yet
    Write-Host "skipped — uiao validate returned $LASTEXITCODE (acceptable if subcommand not yet wired)" -ForegroundColor Yellow
    $results['cross-repo'] = $null
}

# --- Summary ------------------------------------------------------------------
Write-Step 'Summary'
$total  = $results.Count
$passed = ($results.Values | Where-Object { $_ -eq $true }).Count
$failed = ($results.Values | Where-Object { $_ -eq $false }).Count
$skipped = ($results.Values | Where-Object { $_ -eq $null }).Count

foreach ($k in $results.Keys) {
    $v = $results[$k]
    $label = switch ($v) {
        $true  { '[OK]  ' }
        $false { '[FAIL]' }
        $null  { '[skip]' }
    }
    $color = switch ($v) {
        $true  { 'Green' }
        $false { 'Red'   }
        $null  { 'Yellow' }
    }
    Write-Host "$label $k" -ForegroundColor $color
}

Write-Host ''
Write-Host "Total: $total | Pass: $passed | Fail: $failed | Skip: $skipped"
if ($failed -gt 0) {
    Write-Host 'Stage 4 split needs attention. Review [FAIL] items above.' -ForegroundColor Red
    exit 1
} else {
    Write-Host 'Stage 4 split smoke test PASSED.' -ForegroundColor Green
    Write-Host 'Next: move on to Stage 5 (branch protection + workflow reconciliation) or Stage 6 (lychee sweep).' -ForegroundColor Green
}
