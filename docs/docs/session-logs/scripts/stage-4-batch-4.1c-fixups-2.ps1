# =============================================================================
# stage-4-batch-4.1c-fixups-2.ps1
# Phase D Stage 4, Batch 4.1c — Second-round fix-ups for uiao-impl
# -----------------------------------------------------------------------------
# Fixes what Batch 4.1b didn't actually fix:
#   1. ssp_inject.py merge-conflict markers still present (my PS regex didn't
#      match because it lacked the (?m) multiline flag). This version uses a
#      Python one-liner to do a line-by-line rewrite — bulletproof.
#   2. Adds [tool.pytest.ini_options] pythonpath = ["."] so pytest can import
#      scripts.* from repo root (fixes 2 collection errors).
# Amends the b591e0e commit. Still nothing pushed, so safe to amend.
# STOPS before push.
# =============================================================================

$ErrorActionPreference = 'Stop'
$ImplDir = 'C:\Users\whale\uiao-impl'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Confirm-Or-Exit($prompt) {
    $ans = Read-Host "$prompt [y/N]"
    if ($ans -ne 'y' -and $ans -ne 'Y') { Write-Host 'Aborted.' -ForegroundColor Yellow; exit 1 }
}

Set-Location $ImplDir

# --- Preflight ----------------------------------------------------------------
Write-Step 'Preflight'
$remoteBranches = git ls-remote --heads origin main 2>$null
if ($remoteBranches) {
    Write-Host 'origin/main already exists; amend will need --force.' -ForegroundColor Yellow
    Confirm-Or-Exit 'Continue?'
    $script:NeedsForcePush = $true
} else {
    Write-Host 'origin/main does not exist yet — safe to amend.' -ForegroundColor Green
    $script:NeedsForcePush = $false
}

# --- Fix 1: resolve ssp_inject.py conflict via Python -------------------------
Write-Step 'Fix 1 — resolve ssp_inject.py merge conflict (Python rewrite)'
$target = 'src\uiao_impl\generators\ssp_inject.py'
if (-not (Test-Path $target)) { throw "file not found: $target" }

# Quick check: are markers still there?
$hasMarkers = (Select-String -LiteralPath $target -Pattern '^<<<<<<< Updated upstream' -ErrorAction SilentlyContinue)
if (-not $hasMarkers) {
    Write-Host '  no markers detected — skipping' -ForegroundColor Yellow
} else {
    # Use Python: find <<<<<<<, =======, >>>>>>> line indices; keep everything
    # except the ======= block (i.e., keep "upstream" branch).
    $pyScript = @'
from pathlib import Path
p = Path(r"src/uiao_impl/generators/ssp_inject.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

start = sep = end = None
for i, line in enumerate(lines):
    if line.startswith("<<<<<<< Updated upstream") and start is None:
        start = i
    elif line.startswith("=======") and start is not None and sep is None:
        sep = i
    elif line.startswith(">>>>>>> Stashed changes") and sep is not None:
        end = i
        break

if start is None or sep is None or end is None:
    raise SystemExit(f"could not locate full marker triple: start={start} sep={sep} end={end}")

# Keep upstream: lines[0:start] + lines[start+1:sep] + lines[end+1:]
resolved = lines[:start] + lines[start+1:sep] + lines[end+1:]
p.write_text("".join(resolved), encoding="utf-8")

# Final sanity: no markers remain
content = p.read_text(encoding="utf-8")
bad = [m for m in ("<<<<<<<", "=======", ">>>>>>>") if m in content and any(
    line.startswith(m) for line in content.splitlines()
)]
if bad:
    raise SystemExit(f"markers still present: {bad}")

print(f"resolved ssp_inject.py: removed stashed branch (lines {sep}-{end}), kept upstream (lines {start+1}-{sep-1})")
'@
    $pyScript | python -
    if ($LASTEXITCODE -ne 0) { throw 'Python fixup for ssp_inject.py failed' }
}

# Compile-check (this actually runs now)
python -m py_compile $target
if ($LASTEXITCODE -ne 0) { throw 'ssp_inject.py still fails to compile' }
Write-Host '  py_compile OK' -ForegroundColor Green

# --- Fix 2: pythonpath for pytest --------------------------------------------
Write-Step 'Fix 2 — pyproject [tool.pytest.ini_options] pythonpath = ["."]'
$py = Get-Content -Raw 'pyproject.toml'

if ($py -match '(?ms)\[tool\.pytest\.ini_options\]') {
    # Section exists — check if pythonpath is already set
    if ($py -match '(?m)^pythonpath\s*=') {
        Write-Host '  pythonpath already set — leaving alone' -ForegroundColor Yellow
    } else {
        # Insert pythonpath = ["."] right after the section header
        $py = $py -replace '(?m)^\[tool\.pytest\.ini_options\]\s*$', "[tool.pytest.ini_options]`npythonpath = [`".`"]"
        Set-Content 'pyproject.toml' -Value $py -NoNewline:$false
        Write-Host '  added pythonpath = ["."] to existing [tool.pytest.ini_options]' -ForegroundColor Green
    }
} else {
    # Section doesn't exist — append new section at end
    $addition = @'

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
'@
    Add-Content 'pyproject.toml' -Value $addition
    Write-Host '  appended new [tool.pytest.ini_options] section with pythonpath and testpaths' -ForegroundColor Green
}

# Show the pytest section for confirmation
Write-Step 'Current [tool.pytest.ini_options] block'
(Get-Content 'pyproject.toml' | Select-String -Pattern '^\[tool\.pytest' -Context 0,8).ToString() | Out-Host

# --- Reinstall + re-run pytest collection ------------------------------------
Write-Step 'Reinstall + pytest --co'
python -m pip install -e . --quiet 2>&1 | Out-Host
pytest -q --maxfail=10 --co 2>&1 | Tee-Object -Variable coOut | Select-Object -Last 30 | Out-Host

# Count errors
$errorCount = ($coOut | Select-String '^ERROR ' | Measure-Object).Count
if ($errorCount -eq 0) {
    Write-Host "  collection clean — 0 errors" -ForegroundColor Green
} else {
    Write-Host "  collection still has $errorCount error(s) — review tail above" -ForegroundColor Red
    Confirm-Or-Exit 'Amend commit anyway?'
}

# --- Amend + retag -----------------------------------------------------------
Write-Step 'git status'
git status --short

Confirm-Or-Exit 'Stage all + amend + retag v0.1.0?'
git add -A
git commit --amend --no-edit

git tag -d v0.1.0 2>$null
git tag -a v0.1.0 -m 'Initial uiao-impl release (amended 2: ssp_inject conflict + pytest pythonpath)'

Write-Step 'Batch 4.1c complete'
Write-Host "HEAD: $(git log --oneline -1)" -ForegroundColor Green
Write-Host "Tag:  v0.1.0 -> $(git rev-parse --short v0.1.0^{commit})" -ForegroundColor Green
Write-Host ''
if ($script:NeedsForcePush) {
    Write-Host 'Push with force:' -ForegroundColor Yellow
    Write-Host '  git push --force origin main'   -ForegroundColor Yellow
    Write-Host '  git push --force origin v0.1.0' -ForegroundColor Yellow
} else {
    Write-Host 'Push (fresh remote):' -ForegroundColor Green
    Write-Host '  git push -u origin main'   -ForegroundColor Green
    Write-Host '  git push origin v0.1.0'    -ForegroundColor Green
}
