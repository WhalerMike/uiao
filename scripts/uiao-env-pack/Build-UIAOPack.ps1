<#
.SYNOPSIS
    Build-UIAOPack.ps1
    Assemble a UIAO PowerShell offline pack as a downloadable zip artifact.

.DESCRIPTION
    Reads manifest.json and produces a self-contained zip bundle that
    can be downloaded from GitHub Releases and installed offline:

        build\<pack-name>-<version>\
            pwsh\<PowerShell-runtime-msi>
            modules\<Name>\<Version>\...           (one folder per Save-Module)
            tools\<installer files>
            manifest.json                          (resolved, with sha256 fields filled)
            Install-UIAOPack.ps1                   (bundled offline installer)
            README.md
        build\<pack-name>-<version>.zip

    All output is line-by-line. No backticks, no continuation
    characters, no heredocs. Resolved manifest records sha256 of
    every fetched artifact so the offline installer can verify
    integrity before executing anything.

.PARAMETER ManifestPath
    Path to manifest.json. Defaults to manifest.json next to this script.

.PARAMETER BuildRoot
    Directory where the staged pack tree and final zip are written.
    Defaults to build\ next to this script.

.PARAMETER SkipDownload
    Skip downloads if a previous build already populated build\. Useful
    for re-running just the zip step after editing Install-UIAOPack.ps1.

.PARAMETER SkipZip
    Build the staged tree but do not Compress-Archive at the end.

.EXAMPLE
    .\Build-UIAOPack.ps1
    .\Build-UIAOPack.ps1 -ManifestPath .\manifest.json -BuildRoot .\build
#>

[CmdletBinding()]
param(
    [string]$ManifestPath = (Join-Path $PSScriptRoot "manifest.json"),
    [string]$BuildRoot = (Join-Path $PSScriptRoot "build"),
    [switch]$SkipDownload,
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------
# Load manifest
# ---------------------------------------------------------------
if (-not (Test-Path $ManifestPath)) { throw "Manifest not found: $ManifestPath" }
$manifestText = Get-Content -Path $ManifestPath -Raw
$manifest = $manifestText | ConvertFrom-Json

$packName = $manifest.pack.name
$packVersion = $manifest.pack.version
$packDirName = "$packName-$packVersion"
$stageDir = Join-Path $BuildRoot $packDirName
$zipPath = Join-Path $BuildRoot "$packDirName.zip"

Write-Host "[uiao-pwsh-pack] Building $packDirName"
Write-Host "  manifest : $ManifestPath"
Write-Host "  stage    : $stageDir"
Write-Host "  zip      : $zipPath"

# ---------------------------------------------------------------
# Prepare stage directories
# ---------------------------------------------------------------
$pwshDir = Join-Path $stageDir "pwsh"
$modulesDir = Join-Path $stageDir "modules"
$toolsDir = Join-Path $stageDir "tools"

if (-not $SkipDownload) {
    if (Test-Path $stageDir) {
        Write-Host "[uiao-pwsh-pack] Cleaning previous stage at $stageDir"
        Remove-Item -Path $stageDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $pwshDir -Force | Out-Null
    New-Item -ItemType Directory -Path $modulesDir -Force | Out-Null
    New-Item -ItemType Directory -Path $toolsDir -Force | Out-Null
}
else {
    Write-Host "[uiao-pwsh-pack] -SkipDownload set; reusing existing stage"
}

# ---------------------------------------------------------------
# Helper: download a URL to a destination path, return sha256
# ---------------------------------------------------------------
function Invoke-UIAODownload {
    param(
        [string]$Url,
        [string]$Destination
    )
    Write-Host "    GET    $Url"
    $ProgressPreference = "SilentlyContinue"
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing
    $sha = (Get-FileHash -Path $Destination -Algorithm SHA256).Hash
    $sizeMB = [math]::Round((Get-Item -Path $Destination).Length / 1MB, 2)
    Write-Host "    OK     $Destination ($sizeMB MB, sha256=$sha)"
    return $sha
}

# ---------------------------------------------------------------
# Step 01 — PowerShell runtime
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 01 — PowerShell runtime"
$rt = $manifest.runtime.powershell
$rtDest = Join-Path $pwshDir $rt.filename

if (-not $SkipDownload) {
    $rt.sha256 = Invoke-UIAODownload -Url $rt.url -Destination $rtDest
}
else {
    Write-Host "    SKIP   $rtDest (-SkipDownload)"
}

# ---------------------------------------------------------------
# Step 02 — PSGallery modules (Save-Module, not Install-Module)
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 02 — PSGallery modules ($($manifest.modules.Count))"
if (-not $SkipDownload) {
    foreach ($mod in $manifest.modules) {
        try {
            if ($mod.version -eq "latest" -or [string]::IsNullOrEmpty($mod.version)) {
                Save-Module -Name $mod.name -Path $modulesDir -Force
                Write-Host "    OK     $($mod.name) (latest)"
            }
            else {
                Save-Module -Name $mod.name -RequiredVersion $mod.version -Path $modulesDir -Force
                Write-Host "    OK     $($mod.name) $($mod.version)"
            }
        }
        catch {
            Write-Host "    FAIL   $($mod.name) $($mod.version) :: $($_.Exception.Message)"
            throw
        }
    }
}
else {
    Write-Host "    SKIP   module downloads (-SkipDownload)"
}

# ---------------------------------------------------------------
# Step 03 — Third-party tooling
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 03 — Third-party tools ($($manifest.tools.Count))"
if (-not $SkipDownload) {
    foreach ($tool in $manifest.tools) {
        $toolDest = Join-Path $toolsDir $tool.filename
        $tool.sha256 = Invoke-UIAODownload -Url $tool.url -Destination $toolDest
    }
}
else {
    Write-Host "    SKIP   tool downloads (-SkipDownload)"
}

# ---------------------------------------------------------------
# Step 04 — Resolved manifest + Install script + README
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 04 — Bundling manifest and installer"
$resolvedManifestPath = Join-Path $stageDir "manifest.json"
$manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $resolvedManifestPath -Encoding UTF8
Write-Host "    OK     $resolvedManifestPath"

$installerSrc = Join-Path $PSScriptRoot "Install-UIAOPack.ps1"
$installerDst = Join-Path $stageDir "Install-UIAOPack.ps1"
Copy-Item -Path $installerSrc -Destination $installerDst -Force
Write-Host "    OK     $installerDst"

$readmeSrc = Join-Path $PSScriptRoot "README.md"
$readmeDst = Join-Path $stageDir "README.md"
if (Test-Path $readmeSrc) {
    Copy-Item -Path $readmeSrc -Destination $readmeDst -Force
    Write-Host "    OK     $readmeDst"
}

# ---------------------------------------------------------------
# Step 05 — Zip
# ---------------------------------------------------------------
if ($SkipZip) {
    Write-Host "[uiao-pwsh-pack] Step 05 — Zip skipped (-SkipZip)"
}
else {
    Write-Host "[uiao-pwsh-pack] Step 05 — Compressing"
    if (Test-Path $zipPath) {
        Remove-Item -Path $zipPath -Force
    }
    Compress-Archive -Path $stageDir -DestinationPath $zipPath -CompressionLevel Optimal
    $zipSizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 2)
    $zipSha = (Get-FileHash -Path $zipPath -Algorithm SHA256).Hash
    Write-Host "    OK     $zipPath ($zipSizeMB MB)"
    Write-Host "    sha256 $zipSha"
}

Write-Host "[uiao-pwsh-pack] Build complete."
Write-Host "  Pack:  $packDirName"
Write-Host "  Stage: $stageDir"
if (-not $SkipZip) {
    Write-Host "  Zip:   $zipPath"
    Write-Host ""
    Write-Host "  Next: upload to GitHub Releases"
    Write-Host "    gh release create v$packVersion $zipPath --title 'UIAO PowerShell Pack v$packVersion' --notes 'See README.md inside the zip'"
}
