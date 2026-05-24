<#
.SYNOPSIS
    Export-UIAOEnvironment.ps1
    Deterministic export of the current PowerShell substrate to CSV ledgers.

.DESCRIPTION
    Captures the three CSV ledgers that fully describe the installed
    PowerShell substrate on a UIAO operator workstation:

        packages.csv    — PackageManagement packages (Get-Package)
        modules.csv     — PowerShell modules from gallery (Get-InstalledModule)
        devmodules.csv  — Local / Git path modules registered with PoShDevModules

    Pairs with Import-UIAOEnvironment.ps1 (replication) and
    Compare-UIAOEnvironment.ps1 (drift detection).

    Output is line-by-line, no backticks, no continuation characters,
    no heredocs. Rows are sorted for deterministic diffing.

.PARAMETER OutputDirectory
    Directory where the three CSV ledgers are written.
    Defaults to the current directory.

.PARAMETER IncludeSystemProviders
    Switch. When set, packages.csv captures every PackageManagement
    provider including msu / msi / Programs (the Windows-system
    firehose). Default is OFF — only the replicable allowlist of
    PowerShellGet / NuGet / Chocolatey is captured.

    Windows PowerShell 5.1 typically returns 1000+ rows when this
    switch is on; almost none of them are replicable via Install-
    Package, which is why the default filters them out.

.PARAMETER ReplicableProviders
    Optional override for the replicable-provider allowlist when
    -IncludeSystemProviders is NOT set. Defaults to
    PowerShellGet, NuGet, Chocolatey.

.EXAMPLE
    .\Export-UIAOEnvironment.ps1
    .\Export-UIAOEnvironment.ps1 -OutputDirectory C:\uiao-env-ledger
    .\Export-UIAOEnvironment.ps1 -IncludeSystemProviders
#>

[CmdletBinding()]
param(
    [string]$OutputDirectory = (Get-Location).Path,
    [switch]$IncludeSystemProviders,
    [string[]]$ReplicableProviders = @("PowerShellGet", "NuGet", "Chocolatey")
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$packagesCsv = Join-Path $OutputDirectory "packages.csv"
$modulesCsv = Join-Path $OutputDirectory "modules.csv"
$devmodulesCsv = Join-Path $OutputDirectory "devmodules.csv"

Write-Host "[uiao-env-pack] Exporting PackageManagement packages -> $packagesCsv"
$packagesRaw = Get-Package

if ($IncludeSystemProviders) {
    Write-Host "[uiao-env-pack] -IncludeSystemProviders set; capturing every provider ($($packagesRaw.Count) rows)"
    $packages = $packagesRaw
}
else {
    $packages = $packagesRaw | Where-Object { $ReplicableProviders -contains $_.ProviderName }
    $droppedCount = $packagesRaw.Count - $packages.Count
    Write-Host "[uiao-env-pack] Filtered to replicable providers ($($ReplicableProviders -join ', ')); kept $($packages.Count), dropped $droppedCount system rows"
}

$packages | Select-Object Name, Version, ProviderName, Source | Sort-Object Name, Version | Export-Csv -Path $packagesCsv -NoTypeInformation -Encoding UTF8

Write-Host "[uiao-env-pack] Exporting installed PowerShell modules -> $modulesCsv"
$modules = Get-InstalledModule
$modules | Select-Object Name, Version, Repository, InstalledLocation | Sort-Object Name, Version | Export-Csv -Path $modulesCsv -NoTypeInformation -Encoding UTF8

Write-Host "[uiao-env-pack] Exporting PoShDevModules dev modules -> $devmodulesCsv"
$devModulesAvailable = $null -ne (Get-Command -Name Get-InstalledDevModule -ErrorAction SilentlyContinue)

if ($devModulesAvailable) {
    $devmodules = Get-InstalledDevModule
    $devmodules | Select-Object Name, Path, Version | Sort-Object Name | Export-Csv -Path $devmodulesCsv -NoTypeInformation -Encoding UTF8
}
else {
    Write-Host "[uiao-env-pack] PoShDevModules not installed; writing empty devmodules ledger"
    @() | Export-Csv -Path $devmodulesCsv -NoTypeInformation -Encoding UTF8
}

Write-Host "[uiao-env-pack] Export complete."
Write-Host "  packages.csv    : $($packages.Count) entries"
Write-Host "  modules.csv     : $($modules.Count) entries"

if ($devModulesAvailable) {
    Write-Host "  devmodules.csv  : $($devmodules.Count) entries"
}
else {
    Write-Host "  devmodules.csv  : 0 entries (PoShDevModules absent on this host)"
}
