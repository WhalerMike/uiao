<#
.SYNOPSIS
    Download-UIAODeps.ps1
    Downloads all pip wheels required for a fully offline UIAO install.

.DESCRIPTION
    Targets networks where PyPI is unreachable (proxy 407 / air-gap).  Run this
    script on a machine that CAN reach PyPI, then carry the output folder to the
    restricted machine and run Install-UIAO.ps1 there.

    Downloads into -OutDir (default: deps\):
      * pip, setuptools, wheel, build  — build tooling
      * All uiao runtime dependencies from pyproject.toml
      * All uiao [api] extras (FastAPI, uvicorn, httpx, msal)

    Uses --only-binary :all: so every artifact is a pre-built .whl (no source
    tarballs that would require a C compiler on the target).  Falls back to
    source for any package that has no binary wheel for the current platform
    (--prefer-binary is set so binaries win when both exist).

    The resulting deps\ folder is included in uiao.zip by Build-UIAOSourceZip.ps1
    and consumed by Install-UIAO.ps1 on the target machine.

.PARAMETER OutDir
    Directory to write wheels into (default: deps\, relative to the script's
    parent — the repo root).

.PARAMETER PythonExe
    Python executable to invoke pip from (default: python).

.PARAMETER IncludeApi
    Also download [api] extras: fastapi, uvicorn, httpx, msal (default: true).

.EXAMPLE
    # On an internet-connected machine, from the repo root:
    pwsh .\scripts\Download-UIAODeps.ps1

.EXAMPLE
    # Specify a Python 3.12 interpreter and a custom output path:
    pwsh .\scripts\Download-UIAODeps.ps1 -PythonExe python3.12 -OutDir C:\drops\uiao-deps
#>
[CmdletBinding()]
param(
    [string]$OutDir     = "",
    [string]$PythonExe  = "python",
    [bool]  $IncludeApi = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutDir) { $OutDir = Join-Path $RepoRoot "deps" }

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step { param([string]$Msg) Write-Host "" ; Write-Host "── $Msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$Msg) Write-Host "  [OK]  $Msg" -ForegroundColor Green }
function Write-FAIL { param([string]$Msg) Write-Host "  [ERR] $Msg" -ForegroundColor Red }

# ── Validate Python ───────────────────────────────────────────────────────────

Write-Step "Validate Python interpreter"

try {
    $pyVer = & $PythonExe --version 2>&1
    Write-OK $pyVer
} catch {
    Write-FAIL "Cannot run '$PythonExe'.  Pass -PythonExe <path> to override."
    exit 1
}

# ── Prepare output directory ──────────────────────────────────────────────────

Write-Step "Prepare output directory: $OutDir"

if (Test-Path $OutDir) {
    $existing = (Get-ChildItem $OutDir -Filter "*.whl" | Measure-Object).Count
    Write-OK "$existing .whl file(s) already present (will add / overwrite)"
} else {
    New-Item -ItemType Directory -Path $OutDir | Out-Null
    Write-OK "Created $OutDir"
}

# Pip download wrapper — fails the script on any non-zero exit code.
function Invoke-PipDownload {
    param([string[]]$Args)
    $cmd = @($PythonExe, "-m", "pip", "download",
             "--dest", $OutDir,
             "--prefer-binary") + $Args
    Write-Host "  > $($cmd -join ' ')" -ForegroundColor DarkGray
    & $cmd[0] $cmd[1..($cmd.Length - 1)]
    if ($LASTEXITCODE -ne 0) {
        Write-FAIL "pip download failed (exit $LASTEXITCODE). See output above."
        exit $LASTEXITCODE
    }
}

# ── Build tooling (always needed before pip install . can run) ────────────────

Write-Step "Build tooling — pip, setuptools, wheel, build"

Invoke-PipDownload "pip" "setuptools>=61.0" "wheel" "build"

# ── Runtime dependencies ──────────────────────────────────────────────────────

Write-Step "UIAO runtime dependencies (from pyproject.toml)"

# Download transitive closure of the base install.
# Running from the repo root so pip reads pyproject.toml.
Push-Location $RepoRoot
try {
    Invoke-PipDownload "."
} finally {
    Pop-Location
}

# ── [api] extras ──────────────────────────────────────────────────────────────

if ($IncludeApi) {
    Write-Step "UIAO [api] extras — fastapi, uvicorn, httpx, msal"
    Push-Location $RepoRoot
    try {
        Invoke-PipDownload ".[api]"
    } finally {
        Pop-Location
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host ""
$wheels = Get-ChildItem $OutDir -Filter "*.whl"
$sdists = Get-ChildItem $OutDir | Where-Object { $_.Extension -in ".gz", ".zip" -and $_.Name -ne "uiao.zip" }

Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host "  Download complete" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host "  Wheels:  $($wheels.Count)"
Write-Host "  Sdists:  $($sdists.Count)"
Write-Host "  Folder:  $OutDir"
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor DarkCyan
Write-Host "    1. Copy this deps\ folder alongside the uiao\ source tree"
Write-Host "       on the target machine (or rebuild uiao.zip via CI)."
Write-Host "    2. On the target machine, run:"
Write-Host "         .\Install-UIAO.ps1" -ForegroundColor White
Write-Host ("=" * 60) -ForegroundColor DarkGray
