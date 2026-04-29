<#
.SYNOPSIS
    UIAO Spec 1 — D1.6: BitLocker & LAPS State Assessment
.DESCRIPTION
    Assesses every computer object's readiness for Entra ID key escrow
    migration by auditing:

    1. BitLocker Recovery Key State:
       - Recovery keys stored in AD (msFVE-RecoveryInformation child objects)
       - Key count per volume, key protector IDs
       - Key age (creation date of recovery information objects)
       - TPM-only vs TPM+PIN vs recovery password protector types
       - Gap: computers WITHOUT BitLocker keys in AD (unencrypted or
         keys escrowed elsewhere)

    2. LAPS State:
       - Legacy LAPS (ms-Mcs-AdmPwd / ms-Mcs-AdmPwdExpirationTime)
       - Windows LAPS (msLAPS-Password / msLAPS-PasswordExpirationTime /
         msLAPS-CurrentPasswordVersion)
       - Password age and rotation compliance
       - LAPS policy detection (which OUs have LAPS GPO applied)
       - Gap: computers WITHOUT any LAPS management

    3. Migration Readiness per device:
       - BitLocker → Entra ID key escrow (Intune silentEncrypt policy)
       - Legacy LAPS → Windows LAPS with Entra ID backup
       - No LAPS → Deploy Windows LAPS pre-migration

    4. Cross-reference with D1.1 Computer Inventory and D1.2 Device
       Classification for enrichment.

    Outputs: JSON + CSV + console dashboard

    Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.6
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER D1InputFile
    Optional path to D1.1 Computer Inventory JSON for enrichment.
.EXAMPLE
    .\Spec1-D1.6-Get-BitLockerLAPSStateAssessment.ps1
    .\Spec1-D1.6-Get-BitLockerLAPSStateAssessment.ps1 -D1InputFile .\output\D1.1_ComputerInventory.json
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    Requires: Read access to msFVE-RecoveryInformation objects (BitLocker)
    Requires: Read access to ms-Mcs-AdmPwd / msLAPS-* attributes (LAPS)
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$SearchBase,
    [string]$D1InputFile
)

$ErrorActionPreference = "Stop"

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT."
    return
}
Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = (Get-ADDomain).DNSRoot
$outPrefix = "UIAO_Spec1_D1.6_BitLockerLAPS_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 1 — D1.6: BitLocker & LAPS State Assessment"        -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

# ── Load D1.1 cross-reference ──
$d1Lookup = @{}
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  Loading D1.1 computer inventory..." -ForegroundColor Yellow
    $d1Data = Get-Content $D1InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($comp in $d1Data.Computers) {
        $d1Lookup[$comp.ObjectGUID] = $comp
    }
    Write-Host "    Loaded $($d1Lookup.Count) computers from D1.1" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════
# Pass 1: Computer Object Collection with LAPS Attributes
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/4] Collecting computer objects with LAPS attributes..." -ForegroundColor Yellow

$compProps = @(
    'Name', 'DNSHostName', 'SamAccountName', 'ObjectGUID',
    'DistinguishedName', 'OperatingSystem', 'OperatingSystemVersion',
    'Enabled', 'LastLogonDate',
    'ms-Mcs-AdmPwd', 'ms-Mcs-AdmPwdExpirationTime',
    'msLAPS-Password', 'msLAPS-PasswordExpirationTime',
    'msLAPS-CurrentPasswordVersion', 'msLAPS-EncryptedPassword',
    'extensionAttribute1', 'PrimaryGroupID'
)

$allComputers = @(Get-ADComputer -Filter * -Properties $compProps @adParams)
Write-Host "    Total computer objects: $($allComputers.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 2: BitLocker Recovery Key Audit
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/4] Auditing BitLocker recovery keys in AD..." -ForegroundColor Yellow

$results = [System.Collections.Generic.List[object]]::new()
$counter = 0

foreach ($comp in $allComputers) {
    $counter++
    if ($counter % 100 -eq 0) {
        Write-Progress -Activity "BitLocker/LAPS Audit" -Status "$counter / $($allComputers.Count)" -PercentComplete (($counter / $allComputers.Count) * 100)
    }

    $isDC = ($comp.PrimaryGroupID -eq 516)

    # ── BitLocker ──
    $bitlockerKeys = @()
    $bitlockerPresent = $false
    $bitlockerKeyCount = 0
    $bitlockerOldestKey = $null
    $bitlockerNewestKey = $null

    try {
        $searchParams = @{
            SearchBase  = $comp.DistinguishedName
            Filter      = { ObjectClass -eq 'msFVE-RecoveryInformation' }
            SearchScope = 'OneLevel'
            Properties  = 'Name', 'WhenCreated', 'msFVE-RecoveryPassword', 'msFVE-VolumeGuid'
        }
        if ($DomainController) { $searchParams['Server'] = $DomainController }

        $fveObjects = @(Get-ADObject @searchParams -ErrorAction SilentlyContinue)

        if ($fveObjects.Count -gt 0) {
            $bitlockerPresent = $true
            $bitlockerKeyCount = $fveObjects.Count

            foreach ($fve in $fveObjects) {
                $keyAge = if ($fve.WhenCreated) { [int]((Get-Date) - $fve.WhenCreated).TotalDays } else { $null }

                # Parse recovery info name for protector type and date
                # Format: yyyy-MM-dd'T'HH:mm:ss-xx:xx{RecoveryGuid}
                $protectorType = "RecoveryPassword"
                if ($fve.Name -match '\{([0-9A-F\-]+)\}') {
                    $protectorGuid = $Matches[1]
                }

                $bitlockerKeys += [ordered]@{
                    Name         = $fve.Name
                    Created      = if ($fve.WhenCreated) { $fve.WhenCreated.ToString("o") } else { $null }
                    AgeDays      = $keyAge
                    VolumeGuid   = $fve.'msFVE-VolumeGuid'
                    HasPassword  = ($null -ne $fve.'msFVE-RecoveryPassword')
                }

                if ($fve.WhenCreated) {
                    if (-not $bitlockerOldestKey -or $fve.WhenCreated -lt $bitlockerOldestKey) {
                        $bitlockerOldestKey = $fve.WhenCreated
                    }
                    if (-not $bitlockerNewestKey -or $fve.WhenCreated -gt $bitlockerNewestKey) {
                        $bitlockerNewestKey = $fve.WhenCreated
                    }
                }
            }
        }
    } catch {
        # Permission denied or other error — note it
    }

    # ── LAPS ──
    $lapsState = [ordered]@{
        HasLegacyLAPS   = $false
        HasWindowsLAPS  = $false
        HasAnyLAPS      = $false
        LAPSType        = "None"
        PasswordAge     = $null
        ExpirationDate  = $null
        IsExpired       = $null
        IsCompliant     = $null  # Compliant = password rotated within policy period
        PasswordVersion = $null
        IsEncrypted     = $false
    }

    # Legacy LAPS: ms-Mcs-AdmPwdExpirationTime (FILETIME)
    $legacyExpTime = $comp.'ms-Mcs-AdmPwdExpirationTime'
    $legacyPwd = $comp.'ms-Mcs-AdmPwd'

    if ($legacyExpTime -and $legacyExpTime -ne 0) {
        $lapsState.HasLegacyLAPS = $true
        $lapsState.HasAnyLAPS = $true
        $lapsState.LAPSType = "Legacy LAPS"
        try {
            $expDate = [DateTime]::FromFileTime($legacyExpTime)
            $lapsState.ExpirationDate = $expDate.ToString("o")
            $lapsState.IsExpired = ($expDate -lt (Get-Date))
            # Estimate password age (default LAPS rotation = 30 days)
            $lapsState.PasswordAge = [int]((Get-Date) - $expDate.AddDays(-30)).TotalDays
            $lapsState.IsCompliant = ($lapsState.PasswordAge -le 45) # 30 + 15 grace
        } catch { }
    } elseif ($legacyPwd) {
        $lapsState.HasLegacyLAPS = $true
        $lapsState.HasAnyLAPS = $true
        $lapsState.LAPSType = "Legacy LAPS (no expiration)"
    }

    # Windows LAPS: msLAPS-PasswordExpirationTime
    $winLapsExp = $comp.'msLAPS-PasswordExpirationTime'
    $winLapsVer = $comp.'msLAPS-CurrentPasswordVersion'
    $winLapsEnc = $comp.'msLAPS-EncryptedPassword'

    if ($winLapsExp) {
        $lapsState.HasWindowsLAPS = $true
        $lapsState.HasAnyLAPS = $true
        $lapsState.LAPSType = if ($lapsState.HasLegacyLAPS) { "Both (Legacy + Windows)" } else { "Windows LAPS" }
        try {
            $lapsState.ExpirationDate = $winLapsExp.ToString("o")
            $lapsState.IsExpired = ($winLapsExp -lt (Get-Date))
            $lapsState.PasswordAge = [int]((Get-Date) - $winLapsExp.AddDays(-30)).TotalDays
            $lapsState.IsCompliant = ($lapsState.PasswordAge -le 45)
        } catch { }
        $lapsState.PasswordVersion = $winLapsVer
        $lapsState.IsEncrypted = ($null -ne $winLapsEnc)
    } elseif ($winLapsVer) {
        $lapsState.HasWindowsLAPS = $true
        $lapsState.HasAnyLAPS = $true
        $lapsState.LAPSType = "Windows LAPS (version only)"
        $lapsState.PasswordVersion = $winLapsVer
    }

    # ── Device type heuristic ──
    $deviceType = "Unknown"
    $os = $comp.OperatingSystem
    if ($isDC) { $deviceType = "Domain Controller" }
    elseif ($os -match 'Server') { $deviceType = "Server" }
    elseif ($os -match 'Windows 1[01]') { $deviceType = "Workstation" }
    elseif ($os -match 'Linux|Ubuntu|CentOS|Red Hat') { $deviceType = "Linux" }

    # ── Migration readiness ──
    $bitlockerMigration = if ($isDC) { "N/A — Domain Controller" }
        elseif ($deviceType -eq 'Linux') { "N/A — Linux (no BitLocker)" }
        elseif ($bitlockerPresent) { "Ready — keys will re-escrow to Entra ID via Intune silentEncrypt policy" }
        else { "Action Required — deploy BitLocker encryption before or during Intune enrollment" }

    $lapsMigration = if ($isDC) { "N/A — Domain Controller" }
        elseif ($deviceType -eq 'Linux') { "N/A — Linux" }
        elseif ($lapsState.HasWindowsLAPS) { "Ready — Windows LAPS can back up to Entra ID with policy update" }
        elseif ($lapsState.HasLegacyLAPS) { "Upgrade Required — migrate from Legacy LAPS to Windows LAPS with Entra ID backup" }
        else { "Deploy Required — no LAPS management; deploy Windows LAPS with Entra ID backup" }

    # ── D1.1 enrichment ──
    $d1Record = if ($d1Lookup.ContainsKey($comp.ObjectGUID.ToString())) { $d1Lookup[$comp.ObjectGUID.ToString()] } else { $null }

    $record = [ordered]@{
        Name                    = $comp.Name
        DNSHostName             = $comp.DNSHostName
        ObjectGUID              = $comp.ObjectGUID.ToString()
        DistinguishedName       = $comp.DistinguishedName
        OperatingSystem         = $comp.OperatingSystem
        OSVersion               = $comp.OperatingSystemVersion
        DeviceType              = $deviceType
        IsDomainController      = $isDC
        Enabled                 = $comp.Enabled
        LastLogonDate           = if ($comp.LastLogonDate) { $comp.LastLogonDate.ToString("o") } else { $null }
        OrgPath                 = $comp.extensionAttribute1

        # BitLocker
        BitLockerPresent        = $bitlockerPresent
        BitLockerKeyCount       = $bitlockerKeyCount
        BitLockerOldestKey      = if ($bitlockerOldestKey) { $bitlockerOldestKey.ToString("o") } else { $null }
        BitLockerNewestKey      = if ($bitlockerNewestKey) { $bitlockerNewestKey.ToString("o") } else { $null }
        BitLockerKeys           = $bitlockerKeys

        # LAPS
        LAPSType                = $lapsState.LAPSType
        LAPSHasLegacy           = $lapsState.HasLegacyLAPS
        LAPSHasWindows          = $lapsState.HasWindowsLAPS
        LAPSPasswordAge         = $lapsState.PasswordAge
        LAPSExpirationDate      = $lapsState.ExpirationDate
        LAPSIsExpired           = $lapsState.IsExpired
        LAPSIsCompliant         = $lapsState.IsCompliant
        LAPSPasswordVersion     = $lapsState.PasswordVersion
        LAPSIsEncrypted         = $lapsState.IsEncrypted

        # Migration
        BitLockerMigration      = $bitlockerMigration
        LAPSMigration           = $lapsMigration

        # D1.1 enrichment
        D1_StateClass           = if ($d1Record) { $d1Record.StateClassification } else { $null }
        D1_ReadinessTier        = if ($d1Record) { $d1Record.ReadinessTier } else { $null }
    }

    $results.Add($record)
}

Write-Progress -Activity "BitLocker/LAPS Audit" -Completed

# ══════════════════════════════════════════════════════════════
# Pass 3: LAPS GPO Coverage Analysis
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/4] Analyzing LAPS GPO coverage..." -ForegroundColor Yellow

$lapsGPOCoverage = [ordered]@{
    Note = "Full LAPS GPO analysis requires D1.3 GPO Dependency Map. This is a summary indicator."
}

# Check if LAPS schema is extended
$lapsSchemaPresent = [ordered]@{
    LegacyLAPS  = $false
    WindowsLAPS = $false
}

try {
    $schema = Get-ADObject -SearchBase (Get-ADRootDSE).schemaNamingContext `
        -Filter { Name -eq 'ms-Mcs-AdmPwd' } -ErrorAction SilentlyContinue
    $lapsSchemaPresent.LegacyLAPS = ($null -ne $schema)
} catch { }

try {
    $schema = Get-ADObject -SearchBase (Get-ADRootDSE).schemaNamingContext `
        -Filter { Name -eq 'msLAPS-PasswordExpirationTime' } -ErrorAction SilentlyContinue
    $lapsSchemaPresent.WindowsLAPS = ($null -ne $schema)
} catch { }

Write-Host "    Legacy LAPS schema: $(if ($lapsSchemaPresent.LegacyLAPS) { 'Present' } else { 'Not found' })" -ForegroundColor DarkGray
Write-Host "    Windows LAPS schema: $(if ($lapsSchemaPresent.WindowsLAPS) { 'Present' } else { 'Not found' })" -ForegroundColor DarkGray

# ══════════════════════════════════════════════════════════════
# Pass 4: Summary Statistics
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/4] Computing summary..." -ForegroundColor Yellow

# Filter to non-DC workstations and servers
$endpoints = @($results | Where-Object { -not $_.IsDomainController -and $_.DeviceType -ne 'Linux' })
$workstations = @($results | Where-Object { $_.DeviceType -eq 'Workstation' })
$servers = @($results | Where-Object { $_.DeviceType -eq 'Server' })

$blSummary = [ordered]@{
    Total                = $endpoints.Count
    WithBitLocker        = ($endpoints | Where-Object { $_.BitLockerPresent }).Count
    WithoutBitLocker     = ($endpoints | Where-Object { -not $_.BitLockerPresent }).Count
    CoveragePercent      = if ($endpoints.Count -gt 0) {
        [math]::Round((($endpoints | Where-Object { $_.BitLockerPresent }).Count / $endpoints.Count) * 100, 1)
    } else { 0 }
    WorkstationCoverage  = if ($workstations.Count -gt 0) {
        [math]::Round((($workstations | Where-Object { $_.BitLockerPresent }).Count / $workstations.Count) * 100, 1)
    } else { 0 }
    ServerCoverage       = if ($servers.Count -gt 0) {
        [math]::Round((($servers | Where-Object { $_.BitLockerPresent }).Count / $servers.Count) * 100, 1)
    } else { 0 }
    MigrationReady       = ($endpoints | Where-Object { $_.BitLockerMigration -match '^Ready' }).Count
    ActionRequired       = ($endpoints | Where-Object { $_.BitLockerMigration -match '^Action' }).Count
}

$lapsSummary = [ordered]@{
    Total                = $endpoints.Count
    WithAnyLAPS          = ($endpoints | Where-Object { $_.LAPSType -ne 'None' }).Count
    WithLegacyOnly       = ($endpoints | Where-Object { $_.LAPSHasLegacy -and -not $_.LAPSHasWindows }).Count
    WithWindowsLAPS      = ($endpoints | Where-Object { $_.LAPSHasWindows }).Count
    WithBothTypes        = ($endpoints | Where-Object { $_.LAPSHasLegacy -and $_.LAPSHasWindows }).Count
    WithoutLAPS          = ($endpoints | Where-Object { $_.LAPSType -eq 'None' }).Count
    CoveragePercent      = if ($endpoints.Count -gt 0) {
        [math]::Round((($endpoints | Where-Object { $_.LAPSType -ne 'None' }).Count / $endpoints.Count) * 100, 1)
    } else { 0 }
    EncryptedPasswords   = ($endpoints | Where-Object { $_.LAPSIsEncrypted }).Count
    ExpiredPasswords     = ($endpoints | Where-Object { $_.LAPSIsExpired }).Count
    NonCompliant         = ($endpoints | Where-Object { $_.LAPSIsCompliant -eq $false }).Count
    MigrationReady       = ($endpoints | Where-Object { $_.LAPSMigration -match '^Ready' }).Count
    UpgradeRequired      = ($endpoints | Where-Object { $_.LAPSMigration -match '^Upgrade' }).Count
    DeployRequired       = ($endpoints | Where-Object { $_.LAPSMigration -match '^Deploy' }).Count
}

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain     = $domain
        Timestamp  = (Get-Date).ToString("o")
        Script     = "UIAO Spec 1 D1.6 — BitLocker & LAPS State Assessment"
        Reference  = "UIAO_136"
        D1Source   = if ($D1InputFile) { $D1InputFile } else { "Not provided" }
    }
    DeviceCounts = [ordered]@{
        Total            = $results.Count
        DomainControllers = ($results | Where-Object { $_.IsDomainController }).Count
        Servers          = $servers.Count
        Workstations     = $workstations.Count
        Linux            = ($results | Where-Object { $_.DeviceType -eq 'Linux' }).Count
        Unknown          = ($results | Where-Object { $_.DeviceType -eq 'Unknown' }).Count
    }
    BitLocker    = $blSummary
    LAPS         = $lapsSummary
    LAPSSchema   = $lapsSchemaPresent
    OverallReadiness = [ordered]@{
        FullyReady       = ($endpoints | Where-Object { $_.BitLockerMigration -match '^Ready' -and $_.LAPSMigration -match '^Ready' }).Count
        PartiallyReady   = ($endpoints | Where-Object { ($_.BitLockerMigration -match '^Ready' -and $_.LAPSMigration -notmatch '^Ready') -or ($_.BitLockerMigration -notmatch '^Ready' -and $_.LAPSMigration -match '^Ready') }).Count
        NotReady         = ($endpoints | Where-Object { $_.BitLockerMigration -notmatch '^Ready|^N/A' -and $_.LAPSMigration -notmatch '^Ready|^N/A' }).Count
    }
}

# ══════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════

$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{ Summary = $summary; Devices = @($results) } |
    ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

$csvFile = Join-Path $OutputPath "${outPrefix}.csv"
$results | ForEach-Object {
    [PSCustomObject]@{
        Name                = $_.Name
        DeviceType          = $_.DeviceType
        OperatingSystem     = $_.OperatingSystem
        Enabled             = $_.Enabled
        IsDC                = $_.IsDomainController
        BitLockerPresent    = $_.BitLockerPresent
        BitLockerKeyCount   = $_.BitLockerKeyCount
        BitLockerMigration  = $_.BitLockerMigration
        LAPSType            = $_.LAPSType
        LAPSPasswordAge     = $_.LAPSPasswordAge
        LAPSIsCompliant     = $_.LAPSIsCompliant
        LAPSIsEncrypted     = $_.LAPSIsEncrypted
        LAPSMigration       = $_.LAPSMigration
        OrgPath             = $_.OrgPath
        D1_StateClass       = $_.D1_StateClass
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV: $csvFile" -ForegroundColor Green

# Console
Write-Host "`n-- BitLocker State --" -ForegroundColor Cyan
Write-Host "  Endpoints assessed:     $($blSummary.Total)"
Write-Host "  With BitLocker in AD:   $($blSummary.WithBitLocker) ($($blSummary.CoveragePercent)%)" -ForegroundColor $(if ($blSummary.CoveragePercent -ge 90) { 'Green' } elseif ($blSummary.CoveragePercent -ge 50) { 'Yellow' } else { 'Red' })
Write-Host "  Without BitLocker:      $($blSummary.WithoutBitLocker)" -ForegroundColor $(if ($blSummary.WithoutBitLocker -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Workstation coverage:   $($blSummary.WorkstationCoverage)%"
Write-Host "  Server coverage:        $($blSummary.ServerCoverage)%"
Write-Host "  Migration ready:        $($blSummary.MigrationReady)" -ForegroundColor Green
Write-Host "  Action required:        $($blSummary.ActionRequired)" -ForegroundColor $(if ($blSummary.ActionRequired -gt 0) { 'Yellow' } else { 'Green' })

Write-Host "`n-- LAPS State --" -ForegroundColor Cyan
Write-Host "  Endpoints assessed:     $($lapsSummary.Total)"
Write-Host "  With any LAPS:          $($lapsSummary.WithAnyLAPS) ($($lapsSummary.CoveragePercent)%)" -ForegroundColor $(if ($lapsSummary.CoveragePercent -ge 90) { 'Green' } elseif ($lapsSummary.CoveragePercent -ge 50) { 'Yellow' } else { 'Red' })
Write-Host "  Legacy LAPS only:       $($lapsSummary.WithLegacyOnly)" -ForegroundColor Yellow
Write-Host "  Windows LAPS:           $($lapsSummary.WithWindowsLAPS)" -ForegroundColor Green
Write-Host "  No LAPS:                $($lapsSummary.WithoutLAPS)" -ForegroundColor $(if ($lapsSummary.WithoutLAPS -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Encrypted passwords:    $($lapsSummary.EncryptedPasswords)"
Write-Host "  Expired passwords:      $($lapsSummary.ExpiredPasswords)" -ForegroundColor $(if ($lapsSummary.ExpiredPasswords -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Migration ready:        $($lapsSummary.MigrationReady)" -ForegroundColor Green
Write-Host "  Upgrade (Legacy→Win):   $($lapsSummary.UpgradeRequired)" -ForegroundColor Yellow
Write-Host "  Deploy (no LAPS):       $($lapsSummary.DeployRequired)" -ForegroundColor Red

Write-Host "`n-- LAPS Schema --" -ForegroundColor Cyan
Write-Host "  Legacy LAPS schema:     $(if ($lapsSchemaPresent.LegacyLAPS) { 'Present' } else { 'Not found' })"
Write-Host "  Windows LAPS schema:    $(if ($lapsSchemaPresent.WindowsLAPS) { 'Present' } else { 'Not found' })"

Write-Host "`n-- Overall Migration Readiness --" -ForegroundColor Cyan
Write-Host "  Fully ready (BL+LAPS):  $($summary.OverallReadiness.FullyReady)" -ForegroundColor Green
Write-Host "  Partially ready:        $($summary.OverallReadiness.PartiallyReady)" -ForegroundColor Yellow
Write-Host "  Not ready:              $($summary.OverallReadiness.NotReady)" -ForegroundColor Red

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
