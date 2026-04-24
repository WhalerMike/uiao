<#
.SYNOPSIS
    Checks for drift between docs/ and machine/ according to separation rules.
.DESCRIPTION
    - Fails if Markdown is found under machine/
    - Fails if JSON/YAML/OSCAL is found under docs/
    - Supports CI integration for automated enforcement
#>

param (
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "Running UIAO doc/machine separation drift checks..." -ForegroundColor Cyan

$exitCode = 0

# 1. Markdown under machine/
$machinePath = Join-Path $repoRoot "machine"
if (Test-Path $machinePath) {
    $mdInMachine = Get-ChildItem -Path $machinePath -Recurse -Include *.md -ErrorAction SilentlyContinue
    if ($mdInMachine) {
        Write-Host "ERROR: Markdown files found under machine/:" -ForegroundColor Red
        $mdInMachine | ForEach-Object { Write-Host "  - $($_.FullName)" }
        $exitCode = 1
    }
}

# 2. JSON/YAML/OSCAL under docs/
$docsPath = Join-Path $repoRoot "docs"
if (Test-Path $docsPath) {
    $configInDocs = Get-ChildItem -Path $docsPath -Recurse -Include *.json,*.yaml,*.yml,*.xml,*.oscal,*.toml -ErrorAction SilentlyContinue
    if ($configInDocs) {
        Write-Host "ERROR: Machine config files found under docs/:" -ForegroundColor Red
        $configInDocs | ForEach-Object { Write-Host "  - $($_.FullName)" }
        $exitCode = 1
    }
}

# 3. Results
if ($exitCode -eq 0) {
    Write-Host "Drift checks passed." -ForegroundColor Green
    if ($VerboseOutput) {
        Write-Host "No Markdown in machine/, no machine configs in docs/." -ForegroundColor DarkGray
    }
} else {
    Write-Host "Drift checks FAILED. Fix the above violations before merging." -ForegroundColor Red
}

exit $exitCode
