<#
.SYNOPSIS
    Install-UIAO.ps1
    Fully offline installer for the UIAO CLI — no internet required.

.DESCRIPTION
    Installs the UIAO CLI from this bundle on a machine with no PyPI access
    (proxy 407 / air-gap).  All required wheels are pre-downloaded in deps\.

    Install sequence:
      1. Verify Python 3.10+ is installed and on PATH.
      2. Upgrade pip from deps\ (offline, --no-index).
      3. Install build tooling (setuptools, wheel, build) from deps\.
      4. Install uiao base package from deps\ (--no-index --find-links deps\).
      5. Optionally install [api] extras from deps\.
      6. Smoke-test: run `uiao --version` to confirm the CLI entry point works.

    Everything in steps 2-5 uses --no-index --find-links, so pip never
    attempts to contact PyPI.  The script fails fast with a clear message
    if any step does not exit 0.

.PARAMETER ApiExtras
    Also install [api] extras (fastapi, uvicorn, httpx, msal).
    Default: false.  Pass -ApiExtras to enable.

.PARAMETER PythonExe
    Python executable to use (default: python).
    Pass -PythonExe python3.12 (or a full path) if needed.

.PARAMETER DepsDir
    Path to the pre-downloaded wheels folder (default: .\deps, relative to
    this script).

.PARAMETER WhatIf
    Print commands without executing them.

.EXAMPLE
    # Basic install (no API extras) from the extracted uiao.zip folder:
    .\Install-UIAO.ps1

.EXAMPLE
    # Install with API extras:
    .\Install-UIAO.ps1 -ApiExtras

.EXAMPLE
    # Use a specific Python and a custom deps folder:
    .\Install-UIAO.ps1 -PythonExe C:\Python312\python.exe -DepsDir D:\offline-wheels
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$ApiExtras,
    [string]$PythonExe = "python",
    [string]$DepsDir   = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Resolve DepsDir relative to this script's location
if (-not $DepsDir) {
    $DepsDir = Join-Path $PSScriptRoot "deps"
}

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step { param([string]$N, [string]$T) Write-Host ""; Write-Host "Step $N — $T" -ForegroundColor Cyan; Write-Host ("-" * 60) -ForegroundColor DarkGray }
function Write-OK   { param([string]$M) Write-Host "  [OK]  $M" -ForegroundColor Green }
function Write-FAIL { param([string]$M) Write-Host "  [ERR] $M" -ForegroundColor Red }
function Write-INFO { param([string]$M) Write-Host "  [--]  $M" -ForegroundColor DarkGray }

function Invoke-Pip {
    param([string[]]$PipArgs)
    $full = @($PythonExe, "-m", "pip") + $PipArgs
    Write-INFO "$($full -join ' ')"
    if ($PSCmdlet.ShouldProcess($PipArgs -join " ", "pip")) {
        & $full[0] $full[1..($full.Length - 1)]
        if ($LASTEXITCODE -ne 0) {
            Write-FAIL "pip exited with code $LASTEXITCODE.  See output above."
            exit $LASTEXITCODE
        }
    }
}

# ── Step 1 — Verify Python ────────────────────────────────────────────────────

Write-Step "1" "Verify Python 3.10+"

try {
    $ver = & $PythonExe --version 2>&1
    Write-OK $ver
    $verNum = $ver -replace "Python ", ""
    $parts  = $verNum.Split(".")
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        Write-FAIL "Python 3.10 or higher is required.  Found: $ver"
        exit 1
    }
} catch {
    Write-FAIL "Cannot run '$PythonExe'.  Install Python 3.10+ and ensure it is on PATH."
    Write-FAIL "Download: https://www.python.org/downloads/"
    exit 1
}

# ── Step 2 — Verify deps\ folder ─────────────────────────────────────────────

Write-Step "2" "Verify offline wheels folder"

if (-not (Test-Path $DepsDir)) {
    Write-FAIL "Deps folder not found: $DepsDir"
    Write-FAIL "Run Download-UIAODeps.ps1 on an internet-connected machine first,"
    Write-FAIL "then copy the deps\ folder here."
    exit 1
}

$wheelCount = (Get-ChildItem $DepsDir -Filter "*.whl" | Measure-Object).Count
Write-OK "$wheelCount wheel(s) found in $DepsDir"

if ($wheelCount -lt 5) {
    Write-Host "  [WARN] Only $wheelCount wheels found — bundle may be incomplete." -ForegroundColor Yellow
}

# ── Step 3 — Upgrade pip from deps\ ─────────────────────────────────────────

Write-Step "3" "Upgrade pip (offline)"

Invoke-Pip @("install", "--no-index", "--find-links", $DepsDir, "--upgrade", "pip")

# ── Step 4 — Install build tooling ───────────────────────────────────────────

Write-Step "4" "Install build tooling (setuptools, wheel, build)"

Invoke-Pip @("install", "--no-index", "--find-links", $DepsDir, "setuptools", "wheel", "build")

# ── Step 5 — Install UIAO base package ───────────────────────────────────────

Write-Step "5" "Install UIAO base package"

# Install from the source tree (the src\ folder in this zip), pointing pip
# at the pre-downloaded wheels so it never contacts PyPI.
Invoke-Pip @("install", "--no-index", "--find-links", $DepsDir, ".")

# ── Step 6 — Install [api] extras (optional) ─────────────────────────────────

if ($ApiExtras) {
    Write-Step "6" "Install [api] extras (fastapi, uvicorn, httpx, msal)"
    Invoke-Pip @("install", "--no-index", "--find-links", $DepsDir, ".[api]")
} else {
    Write-Step "6" "Install [api] extras — skipped (pass -ApiExtras to enable)"
    Write-INFO "Skipped.  Re-run with -ApiExtras when needed."
}

# ── Step 7 — Smoke test ───────────────────────────────────────────────────────

Write-Step "7" "Smoke test — uiao --version"

if ($PSCmdlet.ShouldProcess("uiao --version", "Run")) {
    try {
        $result = & $PythonExe -m uiao.cli.app --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-OK "CLI responds: $result"
        } else {
            # Try the installed console-script entry point
            $result2 = uiao --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-OK "CLI entry point: $result2"
            } else {
                Write-Host "  [WARN] uiao --version returned a non-zero exit code.  The package may still be installed correctly." -ForegroundColor Yellow
                Write-Host "         Try running: python -c `"import uiao; print(uiao.__version__.__version__)`"" -ForegroundColor Yellow
            }
        }
    } catch {
        Write-Host "  [WARN] Could not run smoke test: $_.  Verify manually." -ForegroundColor Yellow
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host "  UIAO installed successfully (offline)." -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Quick start:" -ForegroundColor DarkCyan
Write-Host "    uiao --help"
Write-Host "    uiao substrate walk"
Write-Host "    uiao ksi evaluate --help"
Write-Host ""
if (-not $ApiExtras) {
    Write-Host "  To enable the REST API:" -ForegroundColor DarkGray
    Write-Host "    .\Install-UIAO.ps1 -ApiExtras" -ForegroundColor White
    Write-Host ""
}
Write-Host "  Full docs: https://whalermike.github.io/uiao/" -ForegroundColor DarkGray
Write-Host ("=" * 60) -ForegroundColor DarkGray
