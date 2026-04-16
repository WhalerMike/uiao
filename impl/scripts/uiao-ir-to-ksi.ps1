<#
.SYNOPSIS
    Plane 2 orchestrator: IR JSON -> KSI evaluation result JSON.

.DESCRIPTION
    Resolves input/output paths, creates the output directory when absent,
    and delegates to:
        python -m uiao_core.cli ksi evaluate --ir <ir> --out <out> [--config <cfg>]

    Mirrors the structure of uiao-scuba-to-ir.ps1 (Plane 1).

.PARAMETER SourceName
    Base name of the IR file WITHOUT extension (e.g. "tenant-a").
    The script appends ".ir.json" for the input and ".ksi.json" for the output.

.PARAMETER PythonExe
    Python interpreter to use (default: "python").

.PARAMETER IRRoot
    Directory that holds the IR JSON files produced by Plane 1.
    Default: .\output\ir

.PARAMETER OutputRoot
    Directory where KSI result JSON files will be written.
    Default: .\output\ksi

.PARAMETER ConfigPath
    Optional path to ksi-rules.json config.  If the file exists it is
    forwarded to the evaluator via --config; otherwise the flag is omitted
    and the evaluator uses its built-in defaults.
    Default: .\config\ksi-rules.json

.EXAMPLE
    .\uiao-ir-to-ksi.ps1 -SourceName "tenant-a" -PythonExe "python"

.EXAMPLE
    .\uiao-ir-to-ksi.ps1 `
        -SourceName  "tenant-b" `
        -PythonExe   ".venv\Scripts\python.exe" `
        -IRRoot      ".\data\ir" `
        -OutputRoot  ".\data\ksi" `
        -ConfigPath  ".\config\ksi-rules-strict.json"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $SourceName,

    [Parameter(Mandatory = $false)]
    [string] $PythonExe   = "python",

    [string] $IRRoot      = ".\output\ir",
    [string] $OutputRoot  = ".\output\ksi",
    [string] $ConfigPath  = ".\config\ksi-rules.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
$irPath  = Join-Path $IRRoot     "$SourceName.ir.json"
$outPath = Join-Path $OutputRoot "$SourceName.ksi.json"

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------
if (-not (Test-Path $irPath)) {
    throw "IR input not found: $irPath"
}

if (-not (Test-Path $OutputRoot)) {
    Write-Verbose "Creating output directory: $OutputRoot"
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}

# ---------------------------------------------------------------------------
# Build argument list
# ---------------------------------------------------------------------------
$arguments = @(
    "-m", "uiao_core.cli",
    "ksi", "evaluate",
    "--ir",  $irPath,
    "--out", $outPath
)

if (Test-Path $ConfigPath) {
    Write-Verbose "Using config: $ConfigPath"
    $arguments += @("--config", $ConfigPath)
} else {
    Write-Verbose "Config not found at '$ConfigPath' — running without --config"
}

# ---------------------------------------------------------------------------
# Invoke the evaluator
# ---------------------------------------------------------------------------
Write-Host "IR -> KSI evaluation starting ..."
Write-Host "  Source : $SourceName"
Write-Host "  In     : $irPath"
Write-Host "  Out    : $outPath"

& $PythonExe $arguments

if ($LASTEXITCODE -ne 0) {
    throw "IR -> KSI evaluation failed with exit code $LASTEXITCODE"
}

# ---------------------------------------------------------------------------
# Success summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "IR -> KSI evaluation complete:"
Write-Host "  In : $irPath"
Write-Host "  Out: $outPath"
