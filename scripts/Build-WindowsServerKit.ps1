<#
.SYNOPSIS
    Build-WindowsServerKit.ps1
    Assembles the UIAO Windows Server Deployment Kit zip.

.DESCRIPTION
    Gathers all deployment scripts, the PowerShell management module, web.config
    variants, and the standalone health-check script into a single zip that
    operators can download and run on a fresh Windows Server without internet
    access at install time (except for pip).

    Output: dist/windows-server-kit-<version>.zip
    The zip is attached to the GitHub Release by msi-build.yml.

.PARAMETER Version
    Version string to embed in the zip filename (default: reads from src/uiao/__version__.py).

.PARAMETER OutDir
    Output directory for the zip (default: dist/).

.EXAMPLE
    .\scripts\Build-WindowsServerKit.ps1
    .\scripts\Build-WindowsServerKit.ps1 -Version "1.2.0" -OutDir "C:\drops"
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$OutDir  = "dist"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# Resolve version from __version__.py if not supplied
if (-not $Version) {
    $verFile = Join-Path $RepoRoot "src\uiao\__version__.py"
    if (Test-Path $verFile) {
        $line = (Get-Content $verFile) | Where-Object { $_ -match '__version__' } | Select-Object -First 1
        if ($line -match '"([^"]+)"') { $Version = $Matches[1] }
    }
    if (-not $Version) { $Version = "0.0.0" }
}

Write-Host "Building Windows Server Kit v$Version" -ForegroundColor Cyan

# Staging directory
$Stage = Join-Path $env:TEMP "uiao-windows-server-kit-$Version"
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage | Out-Null

# ── Deployment scripts ──────────────────────────────────────────────────────
$DeployDir = Join-Path $RepoRoot "deploy\windows-server"
$ScriptsDir = Join-Path $RepoRoot "scripts"

$FilesToCopy = @(
    # Core deployment scripts
    (Join-Path $DeployDir "Install-UIAOServer.ps1"),
    (Join-Path $DeployDir "Register-ServiceAccount.ps1"),
    (Join-Path $DeployDir "Install-UIAOService.ps1"),
    # web.config variants
    (Join-Path $DeployDir "web.config"),
    (Join-Path $DeployDir "web.config.service-mode"),
    # Health check standalone
    (Join-Path $ScriptsDir "Test-UIAOHealth.ps1")
)

foreach ($f in $FilesToCopy) {
    if (Test-Path $f) {
        Copy-Item $f -Destination $Stage
        Write-Host "  + $(Split-Path $f -Leaf)" -ForegroundColor DarkGray
    } else {
        Write-Warning "  ! Not found (skipped): $f"
    }
}

# Extract Register-UIAOAPI.ps1 from deploy-scripts.ps1 if it exists as standalone
$RegisterAPI = Join-Path $DeployDir "Register-UIAOAPI.ps1"
if (Test-Path $RegisterAPI) {
    Copy-Item $RegisterAPI -Destination $Stage
    Write-Host "  + Register-UIAOAPI.ps1" -ForegroundColor DarkGray
}

# ── PowerShell management module ────────────────────────────────────────────
$ModuleSrc = Join-Path $DeployDir "powershell-module"
$ModuleDst = Join-Path $Stage "powershell-module"
if (Test-Path $ModuleSrc) {
    Copy-Item $ModuleSrc -Destination $ModuleDst -Recurse
    Write-Host "  + powershell-module\" -ForegroundColor DarkGray
} else {
    Write-Warning "  ! powershell-module\ not found"
}

# ── MSI installer (if pre-built) ────────────────────────────────────────────
$MsiSrc = Join-Path $RepoRoot "dist"
$MsiFile = Get-ChildItem $MsiSrc -Filter "*.msi" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($MsiFile) {
    Copy-Item $MsiFile.FullName -Destination $Stage
    Write-Host "  + $($MsiFile.Name)" -ForegroundColor DarkGray
}

# ── README ──────────────────────────────────────────────────────────────────
$ReadmePath = Join-Path $Stage "README.txt"
[System.IO.File]::WriteAllText($ReadmePath, @"
UIAO Windows Server Deployment Kit v$Version
============================================

Contents
--------
  Install-UIAOServer.ps1      - Step 1: install IIS features, Python, uiao package
  Register-ServiceAccount.ps1 - Step 2: create svc-uiao AD account and SPNs (run on DC/RSAT)
  Register-UIAOAPI.ps1        - Step 3: create IIS site, app pool, TLS binding
  Install-UIAOService.ps1     - Optional: register as Windows Service (pywin32 mode)
  web.config                  - IIS HttpPlatformHandler config (standard mode)
  web.config.service-mode     - IIS ARR reverse-proxy config (Windows Service mode)
  Test-UIAOHealth.ps1         - Standalone health check (delegates to UIAO module if installed)
  powershell-module\          - UIAO.psm1 + UIAO.psd1 management module

Quick start
-----------
  1. Run Install-UIAOServer.ps1 as Administrator on the target server.
  2. Run Register-ServiceAccount.ps1 on a DC or RSAT host.
  3. Run Register-UIAOAPI.ps1 as Administrator on the target server.
  4. Run .\Test-UIAOHealth.ps1 — all checks should PASS.

Full guide: https://whalermike.github.io/uiao/customer-documents/platform/windows-server-deployment.html

Verify this zip
---------------
  Get-FileHash .\windows-server-kit-$Version.zip -Algorithm SHA256

License: Apache-2.0. See https://github.com/WhalerMike/uiao
"@, [System.Text.UTF8Encoding]::new($false))
Write-Host "  + README.txt" -ForegroundColor DarkGray

# ── Zip ─────────────────────────────────────────────────────────────────────
$OutPath = Join-Path $RepoRoot $OutDir
if (-not (Test-Path $OutPath)) { New-Item -ItemType Directory -Path $OutPath | Out-Null }
$ZipName = "windows-server-kit-$Version.zip"
$ZipPath = Join-Path $OutPath $ZipName

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path "$Stage\*" -DestinationPath $ZipPath
$Hash = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()

Write-Host ""
Write-Host "Kit: $ZipPath" -ForegroundColor Green
Write-Host "SHA-256: $Hash" -ForegroundColor Green

# Clean up staging
Remove-Item $Stage -Recurse -Force
