# =============================================================================
# stage-4-batch-4.4-reindent-canon-tools.ps1
# Phase D Stage 4, Batch 4.4 — Fix canon tools broken in commit 64b25416
# -----------------------------------------------------------------------------
# Context:
#   Commit 64b25416 "Deploy Claude Code integration layer" committed four
#   canon enforcement scripts in tools/ with ALL indentation stripped
#   (0 indented lines each). They have never compiled under CPython since:
#       - tools/metadata_validator.py
#       - tools/drift_detector.py
#       - tools/dashboard_exporter.py
#       - tools/appendix_indexer.py
#   Batch 4.3 smoke test surfaced this as `canon-tools` FAIL.
#
# What this does:
#   - Verifies the four files are already reindented in place (Cowork mount
#     already wrote them); confirms each compiles via `python -m py_compile`.
#   - Also compiles tools/sync_canon.py (the one canon tool that WAS fine)
#     as a regression guard.
#   - Stages only the four reindented files (the working tree has unrelated
#     CRLF-noise on many other files which we deliberately do NOT commit).
#   - Commits one atomic fix commit.
#   - STOPS before push.
#
# Prereqs:
#   - Batch 4.3 run (smoke test). `canon-tools` was the only non-cosmetic fail.
#   - uiao-core working tree may have unrelated M lines; that's fine. This
#     script only touches the four tool files.
#
# Safety:
#   - py_compile gates BEFORE any git operation. Any compile failure aborts.
#   - `git add` uses explicit paths — no `git add -A` or `-u`.
#   - Dry-run flag: pass -DryRun to preview without committing.
# =============================================================================

param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$RepoRoot = 'C:\Users\whale'
$CoreDir  = Join-Path $RepoRoot 'uiao-core'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "    $msg"   -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "    $msg"   -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    $msg"   -ForegroundColor Red }

# -----------------------------------------------------------------------------
# 0. Preflight
# -----------------------------------------------------------------------------
Write-Step 'Batch 4.4 — Reindent canon tools'
Write-Host "Repo: $CoreDir"
Write-Host "DryRun: $DryRun"

if (-not (Test-Path $CoreDir)) {
    Write-Err "Repo not found: $CoreDir"
    exit 1
}
Push-Location $CoreDir

try {
    # Ensure we're on main
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($branch -ne 'main') {
        Write-Err "Expected branch 'main', got '$branch'. Aborting."
        exit 1
    }
    Write-OK "Branch: main"

    # -------------------------------------------------------------------------
    # 1. Compile gate — all 5 canon tools must py_compile cleanly.
    # -------------------------------------------------------------------------
    Write-Step 'Compile gate: python -m py_compile on all 5 canon tools'
    $tools = @(
        'tools/metadata_validator.py',
        'tools/drift_detector.py',
        'tools/dashboard_exporter.py',
        'tools/appendix_indexer.py',
        'tools/sync_canon.py'
    )
    $failed = @()
    foreach ($t in $tools) {
        if (-not (Test-Path $t)) {
            Write-Err "Missing: $t"
            $failed += $t
            continue
        }
        python -m py_compile $t 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-OK "compile OK: $t"
        } else {
            Write-Err "compile FAIL: $t"
            $failed += $t
        }
    }
    if ($failed.Count -gt 0) {
        Write-Err "One or more tools failed to compile. Aborting."
        exit 1
    }

    # -------------------------------------------------------------------------
    # 2. AST structure sanity check (catch semantic reindent bugs py_compile misses)
    # -------------------------------------------------------------------------
    Write-Step 'AST structure check'
    $astScript = @'
import ast, sys
expected = {
    'tools/metadata_validator.py': {'top': 6, 'total': 7},
    'tools/drift_detector.py':     {'top': 15, 'total': 16},
    'tools/dashboard_exporter.py': {'top': 10, 'total': 10},
    'tools/appendix_indexer.py':   {'top': 9,  'total': 9},
}
bad = 0
for f, e in expected.items():
    tree = ast.parse(open(f, encoding='utf-8').read())
    total = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    top = sum(1 for n in tree.body if isinstance(n, ast.FunctionDef))
    ok = (top == e['top'] and total == e['total'])
    marker = 'OK ' if ok else 'BAD'
    print(f'  {marker} {f}: top={top} total={total} (expected top={e["top"]} total={e["total"]})')
    if not ok:
        bad += 1
sys.exit(0 if bad == 0 else 1)
'@
    $astScript | python -
    if ($LASTEXITCODE -ne 0) {
        Write-Err "AST structure check failed. Aborting."
        exit 1
    }

    # -------------------------------------------------------------------------
    # 3. Stage only the 4 reindented files.
    # -------------------------------------------------------------------------
    Write-Step 'Stage the four reindented files'
    $toStage = @(
        'tools/metadata_validator.py',
        'tools/drift_detector.py',
        'tools/dashboard_exporter.py',
        'tools/appendix_indexer.py'
    )

    if ($DryRun) {
        Write-Warn '[DryRun] Would stage:'
        $toStage | ForEach-Object { Write-Warn "  $_" }
    } else {
        foreach ($f in $toStage) {
            git add -- $f
            if ($LASTEXITCODE -ne 0) {
                Write-Err "git add failed: $f"
                exit 1
            }
        }
        Write-OK "Staged $($toStage.Count) files."
    }

    # Show staged diff summary
    Write-Step 'Staged diff summary'
    git diff --cached --stat -- 'tools/metadata_validator.py' 'tools/drift_detector.py' 'tools/dashboard_exporter.py' 'tools/appendix_indexer.py'

    # -------------------------------------------------------------------------
    # 4. Commit.
    # -------------------------------------------------------------------------
    Write-Step 'Commit'
    $msg = @"
[UIAO-CORE] FIX: tools/*.py — restore indentation stripped in 64b25416

Four canon enforcement scripts were committed in 64b25416
("Deploy Claude Code integration layer") with all indentation removed,
so they never compiled under CPython:

  - tools/metadata_validator.py
  - tools/drift_detector.py
  - tools/dashboard_exporter.py
  - tools/appendix_indexer.py

Surfaced by Batch 4.3 smoke test as ``canon-tools`` FAIL. Re-indented by
hand to preserve original logic; verified via ``python -m py_compile`` and
an AST structure check (top-level + nested function counts match the
design intent of each file). No behavioral changes.

No-op for any workflow that was not actually invoking these tools — the
CI jobs referencing them (metadata-validator.yml, drift-scan.yml,
appendix-sync.yml, dashboard-export.yml) have been ghosts since 64b25416
and will be reconciled in Stage 5.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
"@

    if ($DryRun) {
        Write-Warn '[DryRun] Would commit with message:'
        Write-Host $msg
    } else {
        # Use a temp file for the multi-line message to avoid PowerShell quoting games.
        $msgFile = Join-Path $env:TEMP "uiao-core-4.4-commit-$([guid]::NewGuid().ToString('N').Substring(0,8)).txt"
        Set-Content -LiteralPath $msgFile -Value $msg -Encoding UTF8
        try {
            git commit --file=$msgFile
            if ($LASTEXITCODE -ne 0) {
                Write-Err "git commit failed."
                exit 1
            }
            Write-OK "Commit created."
            git log -1 --stat
        } finally {
            Remove-Item -LiteralPath $msgFile -ErrorAction SilentlyContinue
        }
    }

    # -------------------------------------------------------------------------
    # 5. Done — STOP before push.
    # -------------------------------------------------------------------------
    Write-Step 'Done'
    Write-OK 'Batch 4.4 complete. Review the commit; push when ready:'
    Write-Host '    git push origin main' -ForegroundColor Gray
    Write-OK 'Then re-run Batch 4.3 smoke test to confirm canon-tools now passes.'
}
finally {
    Pop-Location
}
