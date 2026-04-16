# =============================================================================
# stage-4-batch-4.1b-fixups.ps1
# Phase D Stage 4, Batch 4.1b — Post-populate fix-ups for uiao-impl
# -----------------------------------------------------------------------------
# Fixes three issues surfaced by the Batch 4.1 pytest run:
#   1. Git merge-conflict markers in src/uiao_impl/generators/ssp_inject.py.
#   2. Residual 'uiao_core' refs in 24 files (comments + path strings).
#   3. Missing scripts/__init__.py causing 2 pytest collection errors.
#   4. Realigns pyproject version to 0.1.0 to match the v0.1.0 tag.
# Then amends the Batch-4.1 commit (safe — NOT yet pushed) and re-tags.
# Runs pytest again to verify.
# STOPS before push.
# -----------------------------------------------------------------------------
# PRECONDITION: Batch 4.1 has committed locally on uiao-impl/main, v0.1.0 tagged,
# NOTHING pushed yet.
# =============================================================================

$ErrorActionPreference = 'Stop'
$ImplDir = 'C:\Users\whale\uiao-impl'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Confirm-Or-Exit($prompt) {
    $ans = Read-Host "$prompt [y/N]"
    if ($ans -ne 'y' -and $ans -ne 'Y') { Write-Host 'Aborted.' -ForegroundColor Yellow; exit 1 }
}

Set-Location $ImplDir

# --- Preflight: has anything been pushed? -------------------------------------
Write-Step 'Preflight — verify nothing has been pushed yet'
$remoteBranches = git ls-remote --heads origin main 2>$null
if ($remoteBranches) {
    Write-Host 'WARNING: origin/main already exists. Amending a pushed commit requires --force.' -ForegroundColor Yellow
    Confirm-Or-Exit 'Continue (will require git push --force on main after)?'
    $script:NeedsForcePush = $true
} else {
    Write-Host 'origin/main does not yet exist — safe to amend.' -ForegroundColor Green
    $script:NeedsForcePush = $false
}

# --- Fix 1: resolve ssp_inject.py merge conflict ------------------------------
Write-Step 'Fix 1 — resolve merge conflict in src/uiao_impl/generators/ssp_inject.py'
$target = 'src\uiao_impl\generators\ssp_inject.py'
if (-not (Test-Path $target)) { throw "expected file not found: $target" }

$raw = Get-Content -Raw $target
if ($raw -notmatch '^<<<<<<<') {
    Write-Host '  no conflict markers found — skipping' -ForegroundColor Yellow
} else {
    # Keep the upstream branch (it uses ssp_plan which is referenced below in json.dump).
    # Regex: match from <<<<<<< Updated upstream through >>>>>>> Stashed changes,
    # spanning lines; capture the upstream body between <<<<<<< and =======.
    $pattern = '(?ms)^<<<<<<< Updated upstream\r?\n(.*?)^=======\r?\n.*?^>>>>>>> Stashed changes\r?\n'
    $resolved = [regex]::Replace($raw, $pattern, { param($m) $m.Groups[1].Value })

    # Sanity: no markers remain
    if ($resolved -match '^<<<<<<<|^=======$|^>>>>>>>') {
        throw 'Conflict markers still present after resolution — inspect ssp_inject.py manually.'
    }
    Set-Content -LiteralPath $target -Value $resolved -NoNewline:$false
    Write-Host "  resolved — kept upstream branch (ssp_plan = build_ssp_skeleton...)" -ForegroundColor Green
}

# Compile-check
python -m py_compile $target 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'ssp_inject.py failed to compile after conflict resolution' }
Write-Host '  py_compile OK' -ForegroundColor Green

# --- Fix 2: broader uiao_core -> uiao_impl sweep ------------------------------
Write-Step 'Fix 2 — broader sweep: \buiao_core\b -> uiao_impl (catches comments and path refs)'
$pyFiles = Get-ChildItem -Path . -Recurse -Include *.py -File |
    Where-Object { $_.FullName -notmatch '\\\.git\\' -and $_.FullName -notmatch '\\__pycache__\\' }

$touched = 0
foreach ($f in $pyFiles) {
    $orig = Get-Content -Raw -LiteralPath $f.FullName
    if ($orig -match '\buiao_core\b') {
        # Broad word-boundary replacement catches:
        #   src/uiao_core/foo.py  ->  src/uiao_impl/foo.py
        #   # uiao_core something  ->  # uiao_impl something
        #   "path/uiao_core/"  ->  "path/uiao_impl/"
        $new = $orig -replace '\buiao_core\b', 'uiao_impl'
        if ($new -ne $orig) {
            Set-Content -LiteralPath $f.FullName -Value $new -NoNewline:$false
            $touched++
        }
    }
}
Write-Host "  broad-sweep rewrote $touched additional .py files"

# Verify no .py still has uiao_core
$remaining = Select-String -Path (Get-ChildItem -Recurse -Include *.py -File |
                                  Where-Object { $_.FullName -notmatch '\\\.git\\' -and
                                                 $_.FullName -notmatch '\\__pycache__\\' }).FullName `
                           -Pattern 'uiao_core' -List -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host 'Residual after broad sweep (these may be intentional — review):' -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  $($_.Path)" }
} else {
    Write-Host '  no uiao_core references remain in *.py' -ForegroundColor Green
}

# --- Fix 3: scripts/__init__.py ----------------------------------------------
Write-Step 'Fix 3 — scripts/__init__.py for test imports'
if (-not (Test-Path 'scripts\__init__.py')) {
    @'
"""uiao_impl scripts — one-off generators and orchestrators.

This package exists so tests can do `from scripts.<module> import ...`.
Long-term, these should migrate to uiao_impl/ or be exposed as CLI subcommands.
"""
'@ | Set-Content 'scripts\__init__.py' -Encoding UTF8
    Write-Host '  created scripts/__init__.py' -ForegroundColor Green
} else {
    Write-Host '  scripts/__init__.py already exists' -ForegroundColor Yellow
}

# --- Fix 4: pyproject version alignment --------------------------------------
Write-Step 'Fix 4 — align pyproject version to 0.1.0 (matches v0.1.0 tag)'
$py = Get-Content -Raw 'pyproject.toml'
$before = $py
$py = $py -replace '(?m)^version\s*=\s*"[^"]*"', 'version = "0.1.0"'
if ($py -ne $before) {
    Set-Content 'pyproject.toml' -Value $py -NoNewline:$false
    Write-Host '  version set to 0.1.0' -ForegroundColor Green
} else {
    Write-Host '  pyproject.toml version unchanged — check manually' -ForegroundColor Yellow
}

# Also align src/uiao_impl/__version__.py if it has a string version
$verFile = 'src\uiao_impl\__version__.py'
if (Test-Path $verFile) {
    $vf = Get-Content -Raw $verFile
    $vfNew = $vf -replace '__version__\s*=\s*"[^"]*"', '__version__ = "0.1.0"'
    if ($vfNew -ne $vf) {
        Set-Content -LiteralPath $verFile -Value $vfNew -NoNewline:$false
        Write-Host "  $verFile version set to 0.1.0" -ForegroundColor Green
    }
}

# --- Verify with pytest again -------------------------------------------------
Write-Step 'Re-run pytest (collection should now succeed)'
# Re-install to pick up version change
python -m pip install -e . --quiet 2>&1 | Out-Host
pytest -q --maxfail=10 --co 2>&1 | Tee-Object -Variable collectOut | Out-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host 'pytest collection still has errors. Review above.' -ForegroundColor Red
    Confirm-Or-Exit 'Amend commit despite collection errors?'
} else {
    Write-Host '  collection clean' -ForegroundColor Green
}

# --- Amend the commit + retag -------------------------------------------------
Write-Step 'git status preview before amend'
git status --short | Select-Object -First 40

Confirm-Or-Exit 'Stage all + amend the Batch 4.1 commit + retag v0.1.0?'

git add -A
git commit --amend --no-edit

# Retag — delete old tag (local) and recreate on amended commit
git tag -d v0.1.0 2>$null
git tag -a v0.1.0 -m 'Initial uiao-impl release — migrated from uiao-core Phase D Stage 4 (amended: conflict-fix + broad rename + scripts pkg + version align)'

Write-Step 'Batch 4.1b complete'
Write-Host "HEAD is now: $(git log --oneline -1)" -ForegroundColor Green
Write-Host "Tag v0.1.0: $(git show --no-patch --pretty=format:'%h %s' v0.1.0)" -ForegroundColor Green
Write-Host ''
if ($script:NeedsForcePush) {
    Write-Host 'Push with force (origin/main existed):' -ForegroundColor Yellow
    Write-Host '  git push --force origin main'        -ForegroundColor Yellow
    Write-Host '  git push --force origin v0.1.0'      -ForegroundColor Yellow
} else {
    Write-Host 'Push (fresh remote):'                  -ForegroundColor Green
    Write-Host '  git push -u origin main'             -ForegroundColor Green
    Write-Host '  git push origin v0.1.0'              -ForegroundColor Green
}
Write-Host 'Then proceed to Batch 4.2 (strip uiao-core).' -ForegroundColor Green
