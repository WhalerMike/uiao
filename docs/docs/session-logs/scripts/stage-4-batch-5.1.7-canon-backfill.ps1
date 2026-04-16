# =============================================================================
# stage-4-batch-5.1.7-canon-backfill.ps1
# Phase D Stage 5, Batch 5.1.7 - canon frontmatter backfill + document-registry
# -----------------------------------------------------------------------------
# Context:
#   Triage (5.1.5) found 23 canon .md files with NO YAML frontmatter
#   (Pattern 1) and 1 file with broken frontmatter (UIAO_002, Pattern 2,
#   handled in 5.1.8). This batch prepends a canonical stub to every Pattern-1
#   file and creates canon/document-registry.yaml as the SSOT for UIAO_NNN
#   identifier allocations.
#
# Identifier plan (executed by canon_backfill.py):
#   UIAO_001            canon/UIAO-SSOT.md
#   UIAO_002            (skipped, surgical fix in Batch 5.1.8)
#   UIAO_003            canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md
#   UIAO_100 - UIAO_120 canon/specs/*.md (alphabetical by filename)
#
# Safety:
#   - Python driver is idempotent: skips files that already start with '---'.
#   - Canary run on ONE file first; validator must show the canary transition
#     from "no frontmatter" to clean before the full run.
#   - Expected validator delta: blocking 30 -> ~7 (remainder is UIAO_002).
#   - No push. 5.1.8 lands before branch protection flips.
# =============================================================================

$ErrorActionPreference = 'Stop'
$CoreDir     = 'C:\Users\whale\uiao-core'
$DocsDir     = 'C:\Users\whale\uiao-docs'
$Driver      = Join-Path $DocsDir 'docs\session-logs\scripts\canon_backfill.py'
$CanonDir    = Join-Path $CoreDir 'canon'
$RegistryOut = Join-Path $CanonDir 'document-registry.yaml'
$CanaryRel   = 'specs/cli.md'   # small, self-contained, easy to eyeball

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Push-Location $CoreDir
try {
    # --- 0. Preflight -------------------------------------------------------
    Write-Step 'Preflight'
    $branch = git rev-parse --abbrev-ref HEAD
    if ($branch -ne 'main') { Write-Fail "not on main (on $branch)"; exit 1 }
    if (-not (Test-Path $Driver))   { Write-Fail "missing driver: $Driver"; exit 1 }
    if (-not (Test-Path $CanonDir)) { Write-Fail "missing canon dir: $CanonDir"; exit 1 }
    git diff --quiet;        $dirtyWT  = $LASTEXITCODE
    git diff --cached --quiet; $dirtyIdx = $LASTEXITCODE
    if ($dirtyWT -ne 0 -or $dirtyIdx -ne 0) {
        Write-Host '  working tree has pending changes; review with git status' -ForegroundColor Yellow
        git status --short
        Write-Fail 'aborting: working tree not clean'
        exit 1
    }
    Write-OK 'on main; driver present; canon present; tree clean'

    # --- 1. BEFORE smoke ----------------------------------------------------
    Write-Step 'Step 1 - BEFORE smoke (expect blocking=30 per 5.1.5 triage)'
    New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-7-before.json `
        --ci 2>&1 | Out-Null
    $beforeExit = $LASTEXITCODE
    $beforeBlocking = (Get-Content reports/_5-1-7-before.json -Raw | ConvertFrom-Json).blocking
    Write-OK "before: exit=$beforeExit blocking=$beforeBlocking"
    if ($beforeBlocking -lt 23) {
        Write-Fail "before blocking=$beforeBlocking is lower than expected (>=23). Canon state drifted since triage. Investigate before proceeding."
        exit 1
    }

    # --- 2. Canary dry-run --------------------------------------------------
    Write-Step "Step 2 - Canary DRY-RUN on $CanaryRel"
    python $Driver `
        --canon-dir  $CanonDir `
        --registry-out $RegistryOut `
        --only $CanaryRel `
        --dry-run
    if ($LASTEXITCODE -ne 0) { Write-Fail 'canary dry-run failed'; exit 1 }
    Write-OK 'canary dry-run OK'

    # --- 3. Canary live run -------------------------------------------------
    Write-Step "Step 3 - Canary LIVE run on $CanaryRel"
    python $Driver `
        --canon-dir  $CanonDir `
        --registry-out $RegistryOut `
        --only $CanaryRel
    if ($LASTEXITCODE -ne 0) { Write-Fail 'canary live run failed'; exit 1 }
    Write-OK 'canary live run OK'

    # --- 4. Canary validator check -----------------------------------------
    Write-Step 'Step 4 - Canary validator check (single-file must be clean)'
    $canaryAbs = Join-Path $CanonDir ($CanaryRel -replace '/','\')
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path $canaryAbs `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-7-canary.json `
        --ci 2>&1 | Out-Null
    $canaryReport = Get-Content reports/_5-1-7-canary.json -Raw | ConvertFrom-Json
    Write-OK ("canary: files={0} blocking={1} warning={2}" -f $canaryReport.files_scanned, $canaryReport.blocking, $canaryReport.warning)
    if ($canaryReport.blocking -ne 0) {
        Write-Fail 'canary file still has BLOCKING findings after backfill; aborting before full run'
        $canaryReport.findings | ForEach-Object { Write-Host ("   {0} {1}" -f $_.severity, $_.issue) -ForegroundColor Yellow }
        exit 1
    }
    Write-OK 'canary file is clean; safe to proceed with full run'

    # --- 5. Full run --------------------------------------------------------
    Write-Step 'Step 5 - FULL run (all remaining Pattern-1 files + registry)'
    python $Driver `
        --canon-dir  $CanonDir `
        --registry-out $RegistryOut
    if ($LASTEXITCODE -ne 0) { Write-Fail 'full run failed'; exit 1 }
    Write-OK 'full run complete'

    if (-not (Test-Path $RegistryOut)) {
        Write-Fail "registry not written: $RegistryOut"
        exit 1
    }
    Write-OK "registry written: $RegistryOut"

    # --- 6. AFTER smoke -----------------------------------------------------
    Write-Step 'Step 6 - AFTER smoke (expect blocking drop to ~7; UIAO_002 residue)'
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-7-after.json `
        --ci 2>&1 | Out-Null
    $afterExit = $LASTEXITCODE
    $afterReport = Get-Content reports/_5-1-7-after.json -Raw | ConvertFrom-Json
    $afterBlocking = $afterReport.blocking
    Write-OK "after: exit=$afterExit blocking=$afterBlocking"

    Write-Host ''
    Write-Host ("Delta: blocking {0} -> {1}  (expected ~23 resolved)" -f $beforeBlocking, $afterBlocking) -ForegroundColor Cyan

    if ($afterBlocking -ge $beforeBlocking) {
        Write-Fail 'blocking count did not decrease. Something went wrong; aborting before commit.'
        exit 1
    }

    # Residual findings should all be on UIAO_002
    $residualFiles = $afterReport.findings | ForEach-Object { $_.file } | Sort-Object -Unique
    Write-Host 'Residual offending files:' -ForegroundColor Yellow
    $residualFiles | ForEach-Object { Write-Host ("   {0}" -f $_) -ForegroundColor Yellow }
    $nonU002 = $residualFiles | Where-Object { $_ -notlike '*UIAO_002*' }
    if ($nonU002) {
        Write-Fail 'Residual findings outside UIAO_002; investigate before committing'
        $afterReport.findings | Where-Object { $_.file -notlike '*UIAO_002*' } | ForEach-Object {
            Write-Host ("   {0}: {1} {2}" -f $_.file, $_.severity, $_.issue) -ForegroundColor Red
        }
        exit 1
    }
    Write-OK 'all remaining blockers are on UIAO_002 (Batch 5.1.8 territory)'

    # --- 7. Cleanup temp reports -------------------------------------------
    Remove-Item reports/_5-1-7-before.json -Force -ErrorAction SilentlyContinue
    Remove-Item reports/_5-1-7-canary.json -Force -ErrorAction SilentlyContinue
    Remove-Item reports/_5-1-7-after.json  -Force -ErrorAction SilentlyContinue

    # --- 8. Stage + commit (no push) ---------------------------------------
    Write-Step 'Step 8 - Stage + commit (no push)'
    git add canon/UIAO-SSOT.md
    git add canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md
    git add canon/specs/
    git add canon/document-registry.yaml

    Write-Host ''
    Write-Host '--- staged summary ---' -ForegroundColor Cyan
    git status --short

    $msgFile = Join-Path $env:TEMP 'uiao-core-5-1-7-msg.txt'
    $lines = @(
        '[UIAO-CORE] CREATE: canon frontmatter backfill + document-registry',
        '',
        'Prepends canonical YAML frontmatter to every canon .md file that',
        'was missing it (23 files total) and introduces',
        'canon/document-registry.yaml as the single source of truth for',
        'UIAO_NNN identifier allocations.',
        '',
        'Identifier allocations:',
        '  UIAO_001            canon/UIAO-SSOT.md',
        '  UIAO_003            canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md',
        '  UIAO_100 to UIAO_120   canon/specs/ alphabetical by filename',
        '',
        'Reserved ranges (recorded in the registry header):',
        '  UIAO_001                SSOT',
        '  UIAO_002 to UIAO_099    Top-level canon documents',
        '  UIAO_100 to UIAO_199    canon/specs/ subsystem specifications',
        '  UIAO_200 to UIAO_299    Reserved for operational/runtime artifacts',
        '  UIAO_900 to UIAO_999    Reserved for test fixtures',
        '',
        'Frontmatter template applied per file:',
        '  document_id     assigned UIAO_NNN',
        '  title           extracted from first H1, fallback to plan title',
        '  version         "1.0"',
        '  status          Current',
        '  classification  CANONICAL',
        '  owner           "Michael Stratton"',
        '  created_at      today (ISO date)',
        '  updated_at      today (ISO date)',
        '  boundary        "GCC-Moderate"',
        '',
        'Out of scope:',
        '  UIAO_002 still has broken frontmatter (field renames, mojibake in',
        '  classification, body boundary violation). Surgical fix lands in',
        '  Batch 5.1.8, one commit dedicated to that single file.',
        '',
        ("Validator delta (before/after smoke): blocking {0} -> {1}" -f $beforeBlocking, $afterBlocking),
        'All remaining blockers are on UIAO_002.'
    )
    Set-Content -Path $msgFile -Value $lines -Encoding UTF8

    git commit -F $msgFile
    Remove-Item $msgFile -Force

    Write-Host ''
    Write-OK 'Commit created locally. Review with: git show HEAD --stat'
    Write-Host ''
    Write-Host 'Next steps (manual):' -ForegroundColor Yellow
    Write-Host '  git -C C:\Users\whale\uiao-core pull --rebase origin main' -ForegroundColor Yellow
    Write-Host '  git -C C:\Users\whale\uiao-core push origin main' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'After push:' -ForegroundColor Yellow
    Write-Host '  5.1.8 - surgical frontmatter fix for UIAO_002 (blocking drops to 0)' -ForegroundColor Yellow
    Write-Host '  5.2   - branch protection: require metadata-validator on main' -ForegroundColor Yellow
}
finally {
    Pop-Location
}
