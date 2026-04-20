<#
.SYNOPSIS
    Plane 1 orchestrator: SCuBA -> IR transformation.

.DESCRIPTION
    Invokes `uiao scuba transform` for a single SCuBA source file and
    writes the canonical IR JSON artefact to ./output/ir/.

    Input  : ./input/scuba/{SourceName}.json  (or .yaml)
    Output : ./output/ir/{SourceName}.ir.json
    Config : ./config/scuba-transform.json    (optional)

.PARAMETER SourceName
    Stem of the SCuBA source file (no extension).
    The script tries .json first, then .yaml.

.PARAMETER PythonExe
    Path to the Python interpreter.  Defaults to "python".

.PARAMETER InputRoot
    Root directory for SCuBA input files.  Defaults to ".\input\scuba".

.PARAMETER OutputRoot
    Root directory for IR output files.  Defaults to ".\output\ir".

.PARAMETER ConfigPath
    Optional transform config path.
    Defaults to ".\config\scuba-transform.json".

.EXAMPLE
    .\scripts\uiao-scuba-to-ir.ps1 -SourceName "tenant-a" -PythonExe "python"
#>

[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string] $SourceName,

    [string] $PythonExe  = "python",
    [string] $InputRoot  = ".\input\scuba",
    [string] $OutputRoot = ".\output\ir",
    [string] $ConfigPath = ".\config\scuba-transform.json"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve input path (.json then .yaml then .yml)
$inputPath = $null
foreach ($ext in @(".json", ".yaml", ".yml")) {
    $candidate = Join-Path $InputRoot "$SourceName$ext"
    if (Test-Path $candidate) { $inputPath = $candidate; break }
}
if (-not $inputPath) {
    throw "SCuBA input not found for '$SourceName' under '$InputRoot'"
}

# Ensure output directory exists
if (-not (Test-Path $OutputRoot)) {
    New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
}
$outputPath = Join-Path $OutputRoot "$SourceName.ir.json"

# Build arguments
$arguments = @("-m","uiao_core.cli","scuba","transform","--input",$inputPath,"--out",$outputPath)
if (Test-Path $ConfigPath) { $arguments += @("--config", $ConfigPath) }

# Invoke
Write-Host "SCuBA -> IR" -ForegroundColor Cyan
Write-Host "  In  : $inputPath"
Write-Host "  Out : $outputPath"

& $PythonExe @arguments
if ($LASTEXITCODE -ne 0) { throw "SCuBA -> IR failed (exit $LASTEXITCODE)" }

Write-Host "[OK] $outputPath" -ForegroundColor Green
