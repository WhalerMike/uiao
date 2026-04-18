# =============================================================================
# stage-4-batch-5.1.8-uiao-002-fix.ps1
# Phase D Stage 5, Batch 5.1.8 - surgical frontmatter + body fix for UIAO_002
# -----------------------------------------------------------------------------
# Context:
#   After 5.1.7, canon's validator blocking count is 7, all on
#   canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md. This batch rewrites
#   that one file to resolve every finding and drive blocking to 0.
#
# Findings addressed:
#   1. Missing required field: title            (via rename document_title)
#   2. Missing required field: created_at       (via rename/split of 'date')
#   3. Missing required field: updated_at       (via rename/split of 'date')
#   4. Missing required field: boundary         (via rename 'compliance')
#   5. Invalid classification: 'UIAO Canon ... Controlled'
#                                               (normalize to CANONICAL)
#   6. Invalid status: 'CANONICAL'              (split -> status Current)
#   7. Body boundary violation                  (3 line rewrites, no
#                                                boundary-exception used)
#
# Safety:
#   - Python driver is idempotent; re-running is a no-op.
#   - BEFORE smoke expected: blocking=7 on UIAO_002 only.
#   - AFTER  smoke expected: blocking=0 site-wide.
#   - Reads/writes BYTES -> preserves CRLF line endings. Git diff is surgical,
#     not a file-wide rewrite.
#   - Commit message written without BOM (unlike 5.1.7).
#   - No push.
# =============================================================================

$ErrorActionPreference = 'Stop'
$CoreDir  = 'C:\Users\whale\uiao-core'
$DocsDir  = 'C:\Users\whale\uiao-docs'
$Driver   = Join-Path $DocsDir 'docs\session-logs\scripts\fix_uiao_002.py'
$Target   = Join-Path $CoreDir 'canon\UIAO_002_SCuBA_Technical_Specification_v1.0.md'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Push-Location $CoreDir
try {
    # --- 0. Preflight -------------------------------------------------------
    Write-Step 'Preflight'
    $branch = git rev-parse --abbrev-ref HEAD
    if ($branch -ne 'main') { Write-Fail "not on main (on $branch)"; exit 1 }
    if (-not (Test-Path $Driver)) { Write-Fail "missing driver: $Driver"; exit 1 }
    if (-not (Test-Path $Target)) { Write-Fail "missing target: $Target"; exit 1 }
    git diff --quiet;          $dirtyWT  = $LASTEXITCODE
    git diff --cached --quiet; $dirtyIdx = $LASTEXITCODE
    if ($dirtyWT -ne 0 -or $dirtyIdx -ne 0) {
        Write-Host '  working tree has pending changes; review with git status' -ForegroundColor Yellow
        git status --short
        Write-Fail 'aborting: working tree not clean'
        exit 1
    }
    Write-OK 'on main; driver present; target present; tree clean'

    # --- 1. BEFORE smoke ---------------------------------------------------
    Write-Step 'Step 1 - BEFORE smoke (expect blocking=7, all on UIAO_002)'
    New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-8-before.json `
        --ci 2>&1 | Out-Null
    $beforeReport = Get-Content reports/_5-1-8-before.json -Raw | ConvertFrom-Json
    $beforeBlocking = $beforeReport.blocking
    Write-OK "before: blocking=$beforeBlocking"
    if ($beforeBlocking -ne 7) {
        Write-Host "  expected blocking=7 after 5.1.7; got $beforeBlocking" -ForegroundColor Yellow
        Write-Host '  continuing - script will still abort at end if AFTER is not 0' -ForegroundColor Yellow
    }
    $nonU002 = $beforeReport.findings | Where-Object { $_.file -notlike '*UIAO_002*' }
    if ($nonU002) {
        Write-Fail 'unexpected: BEFORE findings outside UIAO_002'
        $nonU002 | ForEach-Object { Write-Host "   $($_.file): $($_.issue)" -ForegroundColor Red }
        exit 1
    }

    # --- 2. Dry run --------------------------------------------------------
    Write-Step 'Step 2 - DRY RUN'
    python $Driver --file $Target --dry-run
    if ($LASTEXITCODE -ne 0) { Write-Fail 'dry run failed'; exit 1 }
    Write-OK 'dry run OK'

    # --- 3. Live run -------------------------------------------------------
    Write-Step 'Step 3 - LIVE run'
    python $Driver --file $Target
    if ($LASTEXITCODE -ne 0) { Write-Fail 'live run failed'; exit 1 }
    Write-OK 'live run OK'

    # --- 4. Single-file validator check -----------------------------------
    Write-Step 'Step 4 - Single-file validator check (UIAO_002 must be clean)'
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path $Target `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-8-single.json `
        --ci 2>&1 | Out-Null
    $singleReport = Get-Content reports/_5-1-8-single.json -Raw | ConvertFrom-Json
    Write-OK ("single-file: files={0} blocking={1} warning={2}" -f $singleReport.files_scanned, $singleReport.blocking, $singleReport.warning)
    if ($singleReport.blocking -ne 0) {
        Write-Fail 'UIAO_002 still has BLOCKING findings'
        $singleReport.findings | Where-Object { $_.severity -eq 'BLOCKING' } | ForEach-Object {
            Write-Host ("   {0}" -f $_.issue) -ForegroundColor Red
        }
        exit 1
    }

    # --- 5. AFTER smoke (canon-wide) --------------------------------------
    Write-Step 'Step 5 - AFTER smoke (canon-wide, expect blocking=0)'
    python -W ignore::DeprecationWarning tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-8-after.json `
        --ci 2>&1 | Out-Null
    $afterReport = Get-Content reports/_5-1-8-after.json -Raw | ConvertFrom-Json
    $afterBlocking = $afterReport.blocking
    $afterWarning  = $afterReport.warning
    Write-OK "after: blocking=$afterBlocking warning=$afterWarning"

    Write-Host ''
    Write-Host ("Delta: blocking {0} -> {1}" -f $beforeBlocking, $afterBlocking) -ForegroundColor Cyan

    if ($afterBlocking -ne 0) {
        Write-Fail 'canon still has BLOCKING findings; aborting before commit'
        $afterReport.findings | Where-Object { $_.severity -eq 'BLOCKING' } | ForEach-Object {
            Write-Host ("   {0}: {1}" -f $_.file, $_.issue) -ForegroundColor Red
        }
        exit 1
    }
    Write-OK 'canon validator is CLEAN (blocking=0)'

    # --- 6. Cleanup temp reports -----------------------------------------
    Remove-Item reports/_5-1-8-before.json -Force -ErrorAction SilentlyContinue
    Remove-Item reports/_5-1-8-single.json -Force -ErrorAction SilentlyContinue
    Remove-Item reports/_5-1-8-after.json  -Force -ErrorAction SilentlyContinue

    # --- 7. Stage + commit (no push) --------------------------------------
    Write-Step 'Step 7 - Stage + commit (no push)'
    git add canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md

    Write-Host ''
    Write-Host '--- staged summary ---' -ForegroundColor Cyan
    git status --short

    Write-Host ''
    Write-Host '--- diff preview (frontmatter region) ---' -ForegroundColor Cyan
    git --no-pager diff --cached -- canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md | Select-Object -First 80

    # Build commit message with a BOM-free UTF-8 file (fixes the 5.1.7
    # cosmetic where Set-Content -Encoding UTF8 prepended a BOM to the
    # subject line).
    $msgFile = Join-Path $env:TEMP 'uiao-core-5-1-8-msg.txt'
    $msg = @"
[UIAO-CORE] FIX: UIAO_002 frontmatter and body boundary references

Surgical rewrite of canon/UIAO_002_SCuBA_Technical_Specification_v1.0.md
to resolve the remaining 7 metadata-validator blockers after 5.1.7.

Frontmatter renames and value fixes:
  document_title                       -> title
  date                                 -> created_at (same value) +
                                          updated_at (today)
  compliance: "GCC-Moderate Only"      -> boundary: "GCC-Moderate"
  classification: "UIAO Canon ..."     -> classification: CANONICAL
  status: CANONICAL                    -> status: Current

Preserved: document_id, version, author, owner, no_hallucination_mode,
nhp, and the full provenance block.

Body rewrites (3 lines, no boundary-exception used; document remains
strictly GCC-Moderate scoped):
  - "with no Azure IaaS/PaaS dependencies."
    -> "with no dependencies on out-of-scope cloud infrastructure."
  - "No GCC-High, DoD, or Azure IaaS/PaaS services are referenced..."
    -> "No services outside the GCC-Moderate M365 SaaS scope are
        referenced or required."
  - "No GCC-High, DoD, or Azure IaaS/PaaS references present."
    -> "No out-of-boundary cloud environment references present."

Validator delta: canon blocking 7 -> 0. This closes the Stage 5
metadata cleanup and unblocks 5.2 branch protection.
"@
    [System.IO.File]::WriteAllText(
        $msgFile,
        $msg,
        (New-Object System.Text.UTF8Encoding($false))
    )

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
    Write-Host '  5.2 - branch protection: require metadata-validator as a required' -ForegroundColor Yellow
    Write-Host '        status check on uiao-core/main (now safe; blocking=0)' -ForegroundColor Yellow
}
finally {
    Pop-Location
}
