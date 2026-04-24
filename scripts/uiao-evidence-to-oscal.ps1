<#
.SYNOPSIS
    Plane 4 orchestrator: Evidence bundle directory -> OSCAL artifacts (POA&M + SSP).

.DESCRIPTION
    Resolves input/output paths, validates the evidence bundle exists,
    creates the output directory when absent, and delegates to:
        python -m uiao_core.cli oscal generate --evidence <dir> --output <dir> [--config <cfg>]

    Mirrors the structure of uiao-ksi-to-evidence.ps1 (Plane 3).

.PARAMETER SourceName
    Base name of the source (e.g. "tenant-a").
    The script resolves EvidenceRoot\SourceName\ as the input bundle directory
    and creates OutputRoot\SourceName\ for OSCAL artifact output.

.PARAMETER PythonExe
    Python interpreter to use (default: "python").

.PARAMETER EvidenceRoot
    Parent directory of evidence bundle sub-directories from Plane 3.
    Default: .\output\evidence

.PARAMETER OutputRoot
    Parent directory where OSCAL artifact sub-directories will be written.
    Default: .\output\artifacts

.PARAMETER ConfigPath
    Optional path to oscal-generate.json config.  If the file exists it is
    forwarded via --config; otherwise the flag is omitted.
    Default: .\config\oscal-generate.json

.EXAMPLE
    .\uiao-evidence-to-oscal.ps1 -SourceName "tenant-a" -PythonExe "python"

.EXAMPLE
    .\uiao-evidence-to-oscal.ps1 `
        -SourceName    "tenant-b" `
        -PythonExe     ".venv\Scripts\python.exe" `
        -EvidenceRoot  ".\data\evidence" `
        -OutputRoot    ".\data\artifacts" `
        -ConfigPath    ".\config\oscal-generate-strict.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourceName,

    [Parameter(Mandatory = $false)]
    [string] $PythonExe     = "python",

    [string] $EvidenceRoot  = ".\output\evidence",
    [string] $OutputRoot    = ".\output\artifacts",
    [string] $ConfigPath    = ".\config\oscal-generate.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
$evidenceDir = Join-Path $EvidenceRoot $SourceName
$outputDir   = Join-Path $OutputRoot   $SourceName
$bundleJson  = Join-Path $evidenceDir  "bundle.json"
$evidenceJsonl = Join-Path $evidenceDir "evidence.jsonl"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-Path $evidenceDir)) {
    throw "Evidence bundle directory not found: $evidenceDir"
}

if (-not (Test-Path $bundleJson)) {
    throw "bundle.json not found in evidence directory: $evidenceDir"
}

if (-not (Test-Path $evidenceJsonl)) {
    throw "evidence.jsonl not found in evidence directory: $evidenceDir"
}

if (-not (Test-Path $OutputRoot)) {
    Write-Verbose "Creating output root: $OutputRoot"
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

if (-not (Test-Path $outputDir)) {
    Write-Verbose "Creating artifact output directory: $outputDir"
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Build argument list
# ---------------------------------------------------------------------------
$arguments = @(
    "-m", "uiao_core.cli",
    "oscal", "generate",
    "--evidence", $evidenceDir,
    "--output",   $outputDir
)

if (Test-Path $ConfigPath) {
    Write-Verbose "Using config: $ConfigPath"
    $arguments += @("--config", $ConfigPath)
} else {
    Write-Verbose "Config not found at '$ConfigPath' — running without --config"
}

# ---------------------------------------------------------------------------
# Invoke the generator
# ---------------------------------------------------------------------------
Write-Host "Evidence -> OSCAL generation starting ..."
Write-Host "  Source       : $SourceName"
Write-Host "  Evidence dir : $evidenceDir"
Write-Host "  Output dir   : $outputDir"

& $PythonExe $arguments

if ($LASTEXITCODE -ne 0) {
    throw "Evidence -> OSCAL generation failed with exit code $LASTEXITCODE"
}

# ---------------------------------------------------------------------------
# Success summary
# ---------------------------------------------------------------------------
$indexPath = Join-Path $outputDir "artifact-index.json"
Write-Host ""
Write-Host "Evidence -> OSCAL generation complete:"
Write-Host "  Evidence dir : $evidenceDir"
Write-Host "  Artifacts    : $outputDir"
if (Test-Path $indexPath) {
    $index = Get-Content $indexPath -Raw | ConvertFrom-Json
    $poamItems  = $index.artifacts.poam.total_items
    $sspControls = $index.artifacts.ssp.total_controls
    $coverage    = [math]::Round($index.artifacts.ssp.coverage * 100, 1)
    Write-Host "  POA&M items  : $poamItems"
    Write-Host "  SSP controls : $sspControls  (coverage: $coverage%)"
}
Write-Host ""
Write-Host "Artifacts written:"
Write-Host "  $outputDir\poam.json"
Write-Host "  $outputDir\ssp.json"
Write-Host "  $outputDir\artifact-index.json"
