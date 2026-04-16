<#
.SYNOPSIS
    Plane 3 orchestrator: KSI result JSON -> Evidence bundle directory.

.DESCRIPTION
    Resolves input/output paths, creates the output directory when absent,
    and delegates to:
        python -m uiao_core.cli evidence build --input <ksi> --output <dir> [--config <cfg>]

    Mirrors the structure of uiao-ir-to-ksi.ps1 (Plane 2).

.PARAMETER SourceName
    Base name of the KSI file WITHOUT extension (e.g. "tenant-a").
    The script appends ".ksi.json" for the input and creates a matching
    sub-directory under OutputRoot for the bundle output.

.PARAMETER PythonExe
    Python interpreter to use (default: "python").

.PARAMETER KSIRoot
    Directory that holds the KSI JSON files produced by Plane 2.
    Default: .\output\ksi

.PARAMETER OutputRoot
    Parent directory where evidence bundle sub-directories will be written.
    The script creates OutputRoot\SourceName\ automatically.
    Default: .\output\evidence

.PARAMETER ConfigPath
    Optional path to evidence-build.json config.  If the file exists it is
    forwarded via --config; otherwise the flag is omitted.
    Default: .\config\evidence-build.json

.EXAMPLE
    .\uiao-ksi-to-evidence.ps1 -SourceName "tenant-a" -PythonExe "python"

.EXAMPLE
    .\uiao-ksi-to-evidence.ps1 `
        -SourceName  "tenant-b" `
        -PythonExe   ".venv\Scripts\python.exe" `
        -KSIRoot     ".\data\ksi" `
        -OutputRoot  ".\data\evidence" `
        -ConfigPath  ".\config\evidence-build-strict.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourceName,

    [Parameter(Mandatory = $false)]
    [string] $PythonExe   = "python",

    [string] $KSIRoot     = ".\output\ksi",
    [string] $OutputRoot  = ".\output\evidence",
    [string] $ConfigPath  = ".\config\evidence-build.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
$ksiPath   = Join-Path $KSIRoot    "$SourceName.ksi.json"
$bundleDir = Join-Path $OutputRoot $SourceName

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-Path $ksiPath)) {
    throw "KSI input not found: $ksiPath"
}

if (-not (Test-Path $OutputRoot)) {
    Write-Verbose "Creating output root: $OutputRoot"
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

if (-not (Test-Path $bundleDir)) {
    Write-Verbose "Creating bundle directory: $bundleDir"
    New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Build argument list
# ---------------------------------------------------------------------------
$arguments = @(
    "-m", "uiao_core.cli",
    "evidence", "build",
    "--input",  $ksiPath,
    "--output", $bundleDir
)

if (Test-Path $ConfigPath) {
    Write-Verbose "Using config: $ConfigPath"
    $arguments += @("--config", $ConfigPath)
} else {
    Write-Verbose "Config not found at '$ConfigPath' — running without --config"
}

# ---------------------------------------------------------------------------
# Invoke the builder
# ---------------------------------------------------------------------------
Write-Host "KSI -> Evidence build starting ..."
Write-Host "  Source : $SourceName"
Write-Host "  In     : $ksiPath"
Write-Host "  Out    : $bundleDir"

& $PythonExe $arguments

if ($LASTEXITCODE -ne 0) {
    throw "KSI -> Evidence build failed with exit code $LASTEXITCODE"
}

# ---------------------------------------------------------------------------
# Success summary
# ---------------------------------------------------------------------------
$bundleJson = Join-Path $bundleDir "bundle.json"
Write-Host ""
Write-Host "KSI -> Evidence build complete:"
Write-Host "  In          : $ksiPath"
Write-Host "  Bundle dir  : $bundleDir"
if (Test-Path $bundleJson) {
    $bundle = Get-Content $bundleJson -Raw | ConvertFrom-Json
    Write-Host "  Total records : $($bundle.manifest.total_records)"
    Write-Host "  Bundle hash   : $($bundle.bundle_hash.Substring(0, 16))..."
}
