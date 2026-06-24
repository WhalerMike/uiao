<#
.SYNOPSIS
    Build-UIAOMsi.ps1
    Builds the UIAO governance API MSI installer using WiX v4.

.DESCRIPTION
    Requires:
      - .NET SDK 8+ (for dotnet tool)
      - WiX v4 (installed by this script if missing)

    Output: uiao-setup-<version>.msi in the current directory.

.EXAMPLE
    .\Build-UIAOMsi.ps1 -Version "0.9.1"
#>
[CmdletBinding()]
param(
    [string]$Version   = "0.9.0",
    [string]$RepoRoot  = (Resolve-Path "$PSScriptRoot\..\..\..").Path,
    [string]$OutputDir = $PSScriptRoot
)
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }

# -----------------------------------------------------------------------
# 1. Ensure WiX v4 is installed
# -----------------------------------------------------------------------
Write-Step "Checking WiX v4..."
$wix = Get-Command wix -ErrorAction SilentlyContinue
if (-not $wix) {
    Write-Host "    Installing WiX v4 via dotnet tool..." -ForegroundColor Yellow
    dotnet tool install --global wix
    # Refresh PATH
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")
    $wix = Get-Command wix -ErrorAction SilentlyContinue
    if (-not $wix) { throw "WiX installation failed — ensure .NET SDK 8+ is installed." }
}
Write-Host "    WiX: $(wix --version)"

# -----------------------------------------------------------------------
# 2. Ensure WiX extensions are added
# -----------------------------------------------------------------------
Write-Step "Adding WiX extensions..."
wix osmf --accept 2>&1 | Out-Null
wix extension add --global WixToolset.UI.wixext    2>&1 | Out-Null
wix extension add --global WixToolset.Util.wixext  2>&1 | Out-Null
Write-Host "    Extensions: UI + Util"

# -----------------------------------------------------------------------
# 3. Build the MSI
# -----------------------------------------------------------------------
Write-Step "Building MSI (version $Version)..."

$wxs    = Join-Path $PSScriptRoot "uiao.wxs"
$output = Join-Path $OutputDir "uiao-setup-$Version.msi"

$env:UIAO_SRC = $RepoRoot

wix build $wxs `
    -d "Version=$Version" `
    -ext WixToolset.UI.wixext `
    -ext WixToolset.Util.wixext `
    -o $output

if (Test-Path $output) {
    $size = [math]::Round((Get-Item $output).Length / 1MB, 1)
    Write-Host "`n=== MSI built ===" -ForegroundColor Green
    Write-Host "  Path: $output"
    Write-Host "  Size: ${size} MB"
    Write-Host ""
    Write-Host "Silent install example:"
    Write-Host "  msiexec /i `"$output`" /quiet /l*v install.log ``"
    Write-Host "          TENANT_ID=`"<guid>`" CLIENT_ID=`"<guid>`" CLIENT_SECRET=`"<secret>`""
} else {
    throw "MSI build failed — no output at $output"
}
