# =============================================================================
# stage-4-batch-5.1.5-canon-triage.ps1
# Phase D Stage 5, Batch 5.1.5 — READ-ONLY canon backfill triage
# -----------------------------------------------------------------------------
# What this does:
#   1. Runs tools/metadata_validator.py against uiao-core/canon/ to get a fresh
#      JSON report (using the renamed schemas/metadata-schema.json).
#   2. Invokes canon_triage.py to group findings by failure pattern and emit
#      a human-readable markdown report.
#   3. Writes the triage report to:
#        C:\Users\whale\uiao-docs\docs\session-logs\reports\canon-backfill-triage.md
#
# Does NOT modify any canon file, does NOT commit, does NOT push.
# Safe to run multiple times.
#
# Prereqs:
#   - Batch 5.1 landed (commit d1b5ce2b or later) so schemas/metadata-schema.json
#     exists in uiao-core. Local run works whether or not 5.1 has been pushed.
#   - python 3.12 on PATH with pyyaml + jsonschema installed
#     (`pip install pyyaml jsonschema`).
# =============================================================================

$ErrorActionPreference = 'Stop'
$CoreDir    = 'C:\Users\whale\uiao-core'
$DocsDir    = 'C:\Users\whale\uiao-docs'
$ScriptsDir = Join-Path $DocsDir 'docs\session-logs\scripts'
$ReportDir  = Join-Path $DocsDir 'docs\session-logs\reports'
$TriagePy   = Join-Path $ScriptsDir 'canon_triage.py'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

# --- Preflight ---------------------------------------------------------------
Write-Step 'Preflight'
if (-not (Test-Path $CoreDir))  { Write-Fail "missing: $CoreDir";  exit 1 }
if (-not (Test-Path $DocsDir))  { Write-Fail "missing: $DocsDir";  exit 1 }
if (-not (Test-Path $TriagePy)) { Write-Fail "missing: $TriagePy"; exit 1 }
$schemaPath = Join-Path $CoreDir 'schemas\metadata-schema.json'
if (-not (Test-Path $schemaPath)) {
    Write-Fail "missing: $schemaPath — has Batch 5.1 landed?"; exit 1
}
Write-OK 'paths resolved'

New-Item -ItemType Directory -Force -Path $ReportDir | Out-Null

Push-Location $CoreDir
try {
    # --- 1. Fresh validator report ------------------------------------------
    Write-Step 'Step 1 — metadata_validator.py (fresh run)'
    New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
    $reportJson = 'reports\_5-1-5-triage.json'
    python tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output $reportJson `
        --ci 2>&1 | Out-Host
    $vExit = $LASTEXITCODE
    if ($vExit -notin 0,1) {
        Write-Fail "validator crashed (exit $vExit) — aborting triage"
        exit 1
    }
    Write-OK "validator ran (exit $vExit — 0=clean, 1=blockers present, both fine for triage)"

    # --- 2. Build triage report --------------------------------------------
    Write-Step 'Step 2 — generate triage markdown'
    $out = Join-Path $ReportDir 'canon-backfill-triage.md'
    python $TriagePy $reportJson 'schemas\metadata-schema.json' '.' $out
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "canon_triage.py failed (exit $LASTEXITCODE)"
        exit 1
    }
    Write-OK "triage report: $out"

    # --- 3. Clean up the temporary validator JSON --------------------------
    Write-Step 'Step 3 — cleanup'
    if (Test-Path $reportJson) {
        Remove-Item $reportJson -Force
        Write-OK "removed temporary $reportJson"
    }
}
finally {
    Pop-Location
}

Write-Host ''
Write-Host '--- Done. Open the triage report: ---' -ForegroundColor Cyan
Write-Host "  $out" -ForegroundColor Yellow
Write-Host ''
Write-Host 'Read it top-to-bottom, then come back with:' -ForegroundColor Yellow
Write-Host '  (a) scope answer for canon/specs/ (keep / move / out-of-scope)' -ForegroundColor Yellow
Write-Host '  (b) schema-vs-files decision for any enum mismatches' -ForegroundColor Yellow
Write-Host 'Those two answers unblock Batch 5.1.6 + 5.1.7.' -ForegroundColor Yellow
