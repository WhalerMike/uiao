<#
.SYNOPSIS
    Compare-UIAOEnvironment.ps1
    Standalone drift detection for the UIAO PowerShell substrate.

.DESCRIPTION
    Captures the current host state to *.current.csv ledgers and
    compares against the source ledgers (packages.csv, modules.csv,
    devmodules.csv) to produce *.drift.csv files.

    Use this when you want to check drift without re-installing the
    substrate (Import-UIAOEnvironment.ps1 -SkipDriftReport plus this
    script gives you full control). Identical drift semantics to
    steps 06 and 07 inside Import-UIAOEnvironment.ps1.

    All output is line-by-line. No backticks, no continuation
    characters, no heredocs. Rows are sorted for deterministic diffing.

.PARAMETER InputDirectory
    Directory containing the source ledgers (packages.csv,
    modules.csv, devmodules.csv). Defaults to current directory.

.PARAMETER OutputDirectory
    Directory where current and drift ledgers are written.
    Defaults to InputDirectory.

.PARAMETER IncludeSystemProviders
    Switch. When set, current-state capture includes every
    PackageManagement provider (msu / msi / Programs etc.).
    Default OFF matches the Export-UIAOEnvironment.ps1 default
    so source and target ledgers are compared on the same scope.

.PARAMETER ReplicableProviders
    Allowlist used to filter Get-Package on the target host when
    -IncludeSystemProviders is not set. Defaults to
    PowerShellGet, NuGet, Chocolatey.

.EXAMPLE
    .\Compare-UIAOEnvironment.ps1
    .\Compare-UIAOEnvironment.ps1 -InputDirectory C:\uiao-env-ledger
    .\Compare-UIAOEnvironment.ps1 -IncludeSystemProviders
#>

[CmdletBinding()]
param(
    [string]$InputDirectory = (Get-Location).Path,
    [string]$OutputDirectory = $null,
    [switch]$IncludeSystemProviders,
    [string[]]$ReplicableProviders = @("PowerShellGet", "NuGet", "Chocolatey")
)

$ErrorActionPreference = "Stop"

if (-not $OutputDirectory) {
    $OutputDirectory = $InputDirectory
}

if (-not (Test-Path -Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$srcPackages = Join-Path $InputDirectory "packages.csv"
$srcModules = Join-Path $InputDirectory "modules.csv"
$srcDevmodules = Join-Path $InputDirectory "devmodules.csv"

if (-not (Test-Path $srcPackages)) { throw "Missing source ledger: $srcPackages" }
if (-not (Test-Path $srcModules)) { throw "Missing source ledger: $srcModules" }
if (-not (Test-Path $srcDevmodules)) { throw "Missing source ledger: $srcDevmodules" }

$packagesSrc = Import-Csv $srcPackages
$modulesSrc = Import-Csv $srcModules
$devmodulesSrc = Import-Csv $srcDevmodules

Write-Host "[uiao-env-pack] Loaded source ledgers"
Write-Host "  packages   : $($packagesSrc.Count)"
Write-Host "  modules    : $($modulesSrc.Count)"
Write-Host "  devmodules : $($devmodulesSrc.Count)"

Write-Host "[uiao-env-pack] Capturing current state"
$packagesCurRaw = Get-Package

if ($IncludeSystemProviders) {
    Write-Host "  -IncludeSystemProviders set; capturing every provider ($($packagesCurRaw.Count) rows)"
    $packagesCur = $packagesCurRaw | Select-Object Name, Version, ProviderName, Source | Sort-Object Name, Version
}
else {
    $filtered = $packagesCurRaw | Where-Object { $ReplicableProviders -contains $_.ProviderName }
    $droppedCount = $packagesCurRaw.Count - $filtered.Count
    Write-Host "  Filtered to replicable providers ($($ReplicableProviders -join ', ')); kept $($filtered.Count), dropped $droppedCount system rows"
    $packagesCur = $filtered | Select-Object Name, Version, ProviderName, Source | Sort-Object Name, Version
}

$modulesCur = Get-InstalledModule | Select-Object Name, Version, Repository, InstalledLocation | Sort-Object Name, Version

$devmodulesCur = @()
if (Get-Command -Name Get-InstalledDevModule -ErrorAction SilentlyContinue) {
    $devmodulesCur = Get-InstalledDevModule | Select-Object Name, Path, Version | Sort-Object Name
}

$curPackages = Join-Path $OutputDirectory "packages.current.csv"
$curModules = Join-Path $OutputDirectory "modules.current.csv"
$curDevmodules = Join-Path $OutputDirectory "devmodules.current.csv"

$packagesCur | Export-Csv -Path $curPackages -NoTypeInformation -Encoding UTF8
$modulesCur | Export-Csv -Path $curModules -NoTypeInformation -Encoding UTF8
$devmodulesCur | Export-Csv -Path $curDevmodules -NoTypeInformation -Encoding UTF8

Write-Host "  packages.current.csv    : $($packagesCur.Count) entries"
Write-Host "  modules.current.csv     : $($modulesCur.Count) entries"
Write-Host "  devmodules.current.csv  : $($devmodulesCur.Count) entries"

Write-Host "[uiao-env-pack] Computing drift"
$driftPackages = Join-Path $OutputDirectory "packages.drift.csv"
$driftModules = Join-Path $OutputDirectory "modules.drift.csv"
$driftDevmodules = Join-Path $OutputDirectory "devmodules.drift.csv"

Compare-Object -ReferenceObject $packagesSrc -DifferenceObject $packagesCur -Property Name, Version, ProviderName | Export-Csv -Path $driftPackages -NoTypeInformation -Encoding UTF8
Compare-Object -ReferenceObject $modulesSrc -DifferenceObject $modulesCur -Property Name, Version | Export-Csv -Path $driftModules -NoTypeInformation -Encoding UTF8
Compare-Object -ReferenceObject $devmodulesSrc -DifferenceObject $devmodulesCur -Property Name, Path | Export-Csv -Path $driftDevmodules -NoTypeInformation -Encoding UTF8

$packagesDriftRows = Import-Csv $driftPackages
$modulesDriftRows = Import-Csv $driftModules
$devmodulesDriftRows = Import-Csv $driftDevmodules

Write-Host "[uiao-env-pack] Drift ledger complete."
Write-Host "  packages.drift.csv    : $($packagesDriftRows.Count) drifted rows"
Write-Host "  modules.drift.csv     : $($modulesDriftRows.Count) drifted rows"
Write-Host "  devmodules.drift.csv  : $($devmodulesDriftRows.Count) drifted rows"

if (($packagesDriftRows.Count -eq 0) -and ($modulesDriftRows.Count -eq 0) -and ($devmodulesDriftRows.Count -eq 0)) {
    Write-Host "[uiao-env-pack] CLEAN — target host matches source ledgers."
}
else {
    Write-Host "[uiao-env-pack] DRIFTED — review *.drift.csv for SideIndicator: '<=' missing on target, '=>' extra on target."
}
