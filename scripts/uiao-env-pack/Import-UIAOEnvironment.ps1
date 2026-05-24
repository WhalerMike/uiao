<#
.SYNOPSIS
    Import-UIAOEnvironment.ps1
    Deterministic replication of a UIAO PowerShell substrate from CSV ledgers.

.DESCRIPTION
    Reads the three ledgers produced by Export-UIAOEnvironment.ps1 and
    reconstructs the substrate on the target host. Step layout follows
    the UIAO canonical envelope:

        Step 01 — Import CSVs
        Step 02 — Ensure NuGet provider + PowerShellGet
        Step 03 — Install all PackageManagement packages
        Step 04 — Install all PowerShell modules
        Step 05 — Re-bind PoShDevModules dev modules
        Step 06 — Capture current state to *.current.csv
        Step 07 — Compare source vs target -> *.drift.csv

    All output is line-by-line. No backticks, no continuation
    characters, no heredocs. Per-row failures are logged to stdout
    and do not abort the run, so the drift ledger is always produced.

.PARAMETER InputDirectory
    Directory containing packages.csv, modules.csv, devmodules.csv.
    Defaults to current directory.

.PARAMETER OutputDirectory
    Directory where *.current.csv and *.drift.csv are written.
    Defaults to InputDirectory.

.PARAMETER SkipDriftReport
    Skip steps 06 and 07. Use when you only want to replicate and
    will run Compare-UIAOEnvironment.ps1 separately later.

.PARAMETER ReplicableProviders
    Allowlist of ProviderName values that Step 03 will attempt to
    Install-Package. Rows whose ProviderName is outside this list
    are logged as SKIP rather than attempted. Defaults to
    PowerShellGet, NuGet, Chocolatey. Use this to drop msu / msi /
    Programs rows that snuck in from a firehose export.

.EXAMPLE
    .\Import-UIAOEnvironment.ps1
    .\Import-UIAOEnvironment.ps1 -InputDirectory C:\uiao-env-ledger
    .\Import-UIAOEnvironment.ps1 -InputDirectory . -SkipDriftReport
#>

[CmdletBinding()]
param(
    [string]$InputDirectory = (Get-Location).Path,
    [string]$OutputDirectory = $null,
    [switch]$SkipDriftReport,
    [string[]]$ReplicableProviders = @("PowerShellGet", "NuGet", "Chocolatey")
)

$ErrorActionPreference = "Continue"

if (-not $OutputDirectory) {
    $OutputDirectory = $InputDirectory
}

if (-not (Test-Path -Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$packagesCsv = Join-Path $InputDirectory "packages.csv"
$modulesCsv = Join-Path $InputDirectory "modules.csv"
$devmodulesCsv = Join-Path $InputDirectory "devmodules.csv"

if (-not (Test-Path $packagesCsv)) { throw "Missing ledger: $packagesCsv" }
if (-not (Test-Path $modulesCsv)) { throw "Missing ledger: $modulesCsv" }
if (-not (Test-Path $devmodulesCsv)) { throw "Missing ledger: $devmodulesCsv" }

# ---------------------------------------------------------------
# Step 01 — Import CSVs
# ---------------------------------------------------------------
$packages = Import-Csv $packagesCsv
$modules = Import-Csv $modulesCsv
$devmodules = Import-Csv $devmodulesCsv

Write-Host "[uiao-env-pack] Step 01 — Loaded ledgers"
Write-Host "  packages   : $($packages.Count)"
Write-Host "  modules    : $($modules.Count)"
Write-Host "  devmodules : $($devmodules.Count)"

# ---------------------------------------------------------------
# Step 02 — Ensure NuGet provider + PowerShellGet
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 02 — Bootstrap NuGet provider"
try {
    Install-PackageProvider -Name NuGet -Force -Scope CurrentUser | Out-Null
    Write-Host "  OK     NuGet provider"
}
catch {
    Write-Host "  FAIL   NuGet provider :: $($_.Exception.Message)"
}

Write-Host "[uiao-env-pack] Step 02 — Bootstrap PowerShellGet"
try {
    Install-Module -Name PowerShellGet -Force -Scope CurrentUser -AllowClobber | Out-Null
    Write-Host "  OK     PowerShellGet"
}
catch {
    Write-Host "  FAIL   PowerShellGet :: $($_.Exception.Message)"
}

# ---------------------------------------------------------------
# Step 03 — Install all PackageManagement packages
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 03 — Installing PackageManagement packages (allowlist: $($ReplicableProviders -join ', '))"
$skippedCount = 0
$attemptedCount = 0
foreach ($pkg in $packages) {
    if ($ReplicableProviders -notcontains $pkg.ProviderName) {
        Write-Host "  SKIP   $($pkg.Name) $($pkg.Version) [$($pkg.ProviderName)] :: provider not in replicable allowlist"
        $skippedCount = $skippedCount + 1
        continue
    }
    $attemptedCount = $attemptedCount + 1
    try {
        Install-Package -Name $pkg.Name -RequiredVersion $pkg.Version -ProviderName $pkg.ProviderName -Force -Scope CurrentUser | Out-Null
        Write-Host "  OK     $($pkg.Name) $($pkg.Version) [$($pkg.ProviderName)]"
    }
    catch {
        Write-Host "  FAIL   $($pkg.Name) $($pkg.Version) [$($pkg.ProviderName)] :: $($_.Exception.Message)"
    }
}
Write-Host "[uiao-env-pack] Step 03 summary: $attemptedCount attempted, $skippedCount skipped (non-replicable provider)"

# ---------------------------------------------------------------
# Step 04 — Install all PowerShell modules
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 04 — Installing $($modules.Count) PowerShell modules"
foreach ($mod in $modules) {
    try {
        Install-Module -Name $mod.Name -RequiredVersion $mod.Version -Force -Scope CurrentUser -AllowClobber | Out-Null
        Write-Host "  OK     $($mod.Name) $($mod.Version)"
    }
    catch {
        Write-Host "  FAIL   $($mod.Name) $($mod.Version) :: $($_.Exception.Message)"
    }
}

# ---------------------------------------------------------------
# Step 05 — Re-bind PoShDevModules dev modules
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 05 — Re-binding $($devmodules.Count) dev modules"
$devCmd = Get-Command -Name Install-DevModule -ErrorAction SilentlyContinue
if (-not $devCmd) {
    Write-Host "  PoShDevModules not loaded; attempting bootstrap"
    try {
        Install-Module -Name PoShDevModules -Force -Scope CurrentUser -AllowClobber | Out-Null
        Import-Module PoShDevModules -Force
        Write-Host "  OK     PoShDevModules bootstrap"
    }
    catch {
        Write-Host "  FAIL   PoShDevModules bootstrap :: $($_.Exception.Message)"
    }
}

foreach ($dev in $devmodules) {
    try {
        Install-DevModule -Name $dev.Name -Path $dev.Path -Force | Out-Null
        Write-Host "  OK     $($dev.Name) <- $($dev.Path)"
    }
    catch {
        Write-Host "  FAIL   $($dev.Name) <- $($dev.Path) :: $($_.Exception.Message)"
    }
}

if ($SkipDriftReport) {
    Write-Host "[uiao-env-pack] Replication complete. Drift report skipped (-SkipDriftReport)."
    return
}

# ---------------------------------------------------------------
# Step 06 — Capture current state to *.current.csv
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 06 — Capturing current state"
$packagesCur = Get-Package | Select-Object Name, Version, ProviderName, Source | Sort-Object Name, Version
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

# ---------------------------------------------------------------
# Step 07 — Compare source vs target -> *.drift.csv
# ---------------------------------------------------------------
Write-Host "[uiao-env-pack] Step 07 — Computing drift"
$driftPackages = Join-Path $OutputDirectory "packages.drift.csv"
$driftModules = Join-Path $OutputDirectory "modules.drift.csv"
$driftDevmodules = Join-Path $OutputDirectory "devmodules.drift.csv"

Compare-Object -ReferenceObject $packages -DifferenceObject $packagesCur -Property Name, Version, ProviderName | Export-Csv -Path $driftPackages -NoTypeInformation -Encoding UTF8
Compare-Object -ReferenceObject $modules -DifferenceObject $modulesCur -Property Name, Version | Export-Csv -Path $driftModules -NoTypeInformation -Encoding UTF8
Compare-Object -ReferenceObject $devmodules -DifferenceObject $devmodulesCur -Property Name, Path | Export-Csv -Path $driftDevmodules -NoTypeInformation -Encoding UTF8

$packagesDriftRows = Import-Csv $driftPackages
$modulesDriftRows = Import-Csv $driftModules
$devmodulesDriftRows = Import-Csv $driftDevmodules

Write-Host "[uiao-env-pack] Replication + drift ledger complete."
Write-Host "  packages.drift.csv    : $($packagesDriftRows.Count) drifted rows"
Write-Host "  modules.drift.csv     : $($modulesDriftRows.Count) drifted rows"
Write-Host "  devmodules.drift.csv  : $($devmodulesDriftRows.Count) drifted rows"
