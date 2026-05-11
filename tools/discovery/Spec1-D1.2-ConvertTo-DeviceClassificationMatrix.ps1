<#
.SYNOPSIS
    UIAO Spec 1 — D1.2: Device State Classification Matrix
.DESCRIPTION
    Consumes the D1.1 AD Computer Object Inventory JSON and produces:
    1. Classified device matrix (Active / Stale / Abandoned / Infrastructure-Critical)
    2. Migration readiness pre-score per device
    3. OS currency assessment (supported / approaching EOL / unsupported)
    4. CSV export for spreadsheet consumption
    5. JSON export for Quarto dashboard consumption

    Classification Rules:
      Active                — Logged in within 90 days, enabled
      Stale                 — Logged in 90–180 days ago, enabled
      Abandoned             — No logon >180 days, or disabled with no recent logon
      Infrastructure-Critical — Detected as DC, ADFS, PKI, or Exchange by SPN analysis
      Unknown               — No logon timestamp available

    Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.2
         ADR-048 (extensionAttribute1 = OrgPath)
.PARAMETER InputFile
    Path to D1.1 JSON output file.
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.EXAMPLE
    .\Spec1-D1.2-ConvertTo-DeviceClassificationMatrix.ps1 -InputFile .\output\UIAO_Spec1_D1.1_ComputerInventory_contoso.com_20260428-140000.json
.NOTES
    Requires: D1.1 output JSON
    No AD connectivity required — operates on exported data only.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$InputFile,

    [string]$OutputPath = ".\output"
)

$ErrorActionPreference = "Stop"

# ── Validate input ──
if (-not (Test-Path $InputFile)) {
    Write-Error "Input file not found: $InputFile"
    return
}

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 1 — D1.2: Device State Classification Matrix"       -ForegroundColor Cyan
Write-Host "  Input:     $InputFile"                                         -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Load D1.1 data ──
Write-Host "  Loading D1.1 inventory..." -ForegroundColor Yellow
$raw = Get-Content $InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
$computers = $raw.Computers
$domain = $raw.Summary.ExportMetadata.Domain

Write-Host "  Loaded $($computers.Count) computer objects from $domain" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# OS Currency Assessment
# ══════════════════════════════════════════════════════════════

# Windows OS lifecycle data (as of April 2026)
$osLifecycle = @{
    # Workstation OS
    'Windows 11'            = @{ Status = 'Current';    EOL = '2028-10-14'; Note = 'Varies by version' }
    'Windows 10'            = @{ Status = 'EOL';        EOL = '2025-10-14'; Note = 'Extended Security Updates available' }
    'Windows 8.1'           = @{ Status = 'Unsupported'; EOL = '2023-01-10'; Note = 'No security updates' }
    'Windows 8'             = @{ Status = 'Unsupported'; EOL = '2016-01-12'; Note = 'No security updates' }
    'Windows 7'             = @{ Status = 'Unsupported'; EOL = '2020-01-14'; Note = 'No security updates' }

    # Server OS
    'Windows Server 2025'   = @{ Status = 'Current';    EOL = '2035-10-14'; Note = 'Latest server OS' }
    'Windows Server 2022'   = @{ Status = 'Current';    EOL = '2031-10-14'; Note = 'Mainstream support' }
    'Windows Server 2019'   = @{ Status = 'Current';    EOL = '2029-01-09'; Note = 'Mainstream until 2024, extended until 2029' }
    'Windows Server 2016'   = @{ Status = 'Extended';   EOL = '2027-01-12'; Note = 'Extended support only' }
    'Windows Server 2012 R2'= @{ Status = 'ESU';        EOL = '2023-10-10'; Note = 'Extended Security Updates (paid)' }
    'Windows Server 2012'   = @{ Status = 'ESU';        EOL = '2023-10-10'; Note = 'Extended Security Updates (paid)' }
    'Windows Server 2008 R2'= @{ Status = 'Unsupported'; EOL = '2020-01-14'; Note = 'No security updates' }
    'Windows Server 2008'   = @{ Status = 'Unsupported'; EOL = '2020-01-14'; Note = 'No security updates' }
}

function Get-OSCurrency {
    param([string]$OS)
    if (-not $OS) { return @{ Status = 'Unknown'; EOL = $null; Note = 'OS not reported' } }

    foreach ($key in $osLifecycle.Keys) {
        if ($OS -like "*$key*") {
            return $osLifecycle[$key]
        }
    }

    # Linux / other
    if ($OS -match 'Linux|Ubuntu|CentOS|Red Hat|RHEL|SUSE|Debian') {
        return @{ Status = 'Linux'; EOL = $null; Note = 'Check distro-specific lifecycle' }
    }

    return @{ Status = 'Unknown'; EOL = $null; Note = "Unrecognized OS: $OS" }
}

# ══════════════════════════════════════════════════════════════
# Device Type Classification
# ══════════════════════════════════════════════════════════════

function Get-DeviceType {
    param($Computer)
    $os = $Computer.OperatingSystem

    # Infrastructure detection (already flagged by D1.1)
    if ($Computer.IsInfrastructure) {
        return "Infrastructure — $($Computer.InfrastructureRole)"
    }

    if (-not $os) { return "Unknown" }

    if ($os -match 'Server') {
        if ($Computer.SPNCount -gt 5) { return "Server — Application (High SPN)" }
        return "Server — Application"
    }

    if ($os -match 'Windows 11|Windows 10|Windows 8') {
        # Heuristic: workstation vs laptop is hard from AD alone
        # Use OU path hints
        $ou = $Computer.OUPath
        if ($ou -match 'Laptop|Mobile|Portable') { return "Laptop" }
        if ($ou -match 'Kiosk|Shared|Library|Lab') { return "Shared/Kiosk" }
        if ($ou -match 'VDI|Virtual|AVD') { return "Virtual Desktop" }
        return "Workstation"
    }

    if ($os -match 'Linux|Ubuntu|CentOS|Red Hat|RHEL') {
        return "Server — Linux"
    }

    return "Unknown"
}

# ══════════════════════════════════════════════════════════════
# Migration Readiness Pre-Score
# ══════════════════════════════════════════════════════════════

function Get-MigrationReadiness {
    param($Computer, $DeviceType, $OSCurrency)

    $score = 100
    $factors = [System.Collections.Generic.List[string]]::new()
    $blockers = [System.Collections.Generic.List[string]]::new()

    # OS currency
    switch ($OSCurrency.Status) {
        'Current'     { } # No deduction
        'Extended'    { $score -= 10; $factors.Add("OS in extended support only") }
        'EOL'         { $score -= 20; $factors.Add("OS past end of life — ESU or upgrade required before migration") }
        'ESU'         { $score -= 25; $factors.Add("OS requires paid Extended Security Updates") }
        'Unsupported' { $score -= 40; $blockers.Add("OS is unsupported — must upgrade or decommission before migration") }
        'Unknown'     { $score -= 5;  $factors.Add("OS version not reported") }
    }

    # Disabled
    if (-not $Computer.Enabled) {
        $score -= 30
        $factors.Add("Account disabled — candidate for cleanup, not migration")
    }

    # Stale / Abandoned
    if ($Computer.StateClassification -eq 'Abandoned') {
        $score -= 30
        $factors.Add("No logon in >180 days — validate before migrating")
    }
    elseif ($Computer.StateClassification -eq 'Stale') {
        $score -= 15
        $factors.Add("No logon in 90–180 days — confirm still in use")
    }

    # Infrastructure
    if ($Computer.IsInfrastructure) {
        $score -= 20
        $factors.Add("Infrastructure-critical — migrated last per coexistence rules (D2.9)")
    }

    # Delegation
    if ($Computer.Delegation.TrustedForDelegation) {
        $score -= 15
        $blockers.Add("Unconstrained Kerberos delegation — must be resolved before migration")
    }
    if ($Computer.Delegation.AllowedToDelegateTo.Count -gt 0) {
        $score -= 10
        $factors.Add("Constrained delegation configured — delegation chain must be mapped (D1.6)")
    }

    # High SPN count (complex service dependencies)
    if ($Computer.SPNCount -gt 10) {
        $score -= 10
        $factors.Add("High SPN count ($($Computer.SPNCount)) — complex service dependencies")
    }

    # BitLocker not escrowed
    if ($DeviceType -match 'Workstation|Laptop' -and -not $Computer.BitLocker.Present) {
        $score -= 5
        $factors.Add("No BitLocker recovery key in AD — verify encryption state")
    }

    # No LAPS
    if (-not $Computer.LAPS.HasPassword) {
        $score -= 5
        $factors.Add("No LAPS password managed — deploy Windows LAPS pre-migration")
    }

    # OrgPath readiness (ADR-048)
    $orgPathReady = $false
    if ($Computer.extensionAttribute1) {
        $orgPathReady = $true
    }
    else {
        $factors.Add("OrgPath not yet assigned (extensionAttribute1 empty)")
    }

    # Clamp score
    $score = [math]::Max(0, [math]::Min(100, $score))

    # Readiness tier
    # PowerShell switch evaluates ALL matching cases unless break is used,
    # so each tier case must terminate with `; break` to prevent fall-through
    # (e.g., a score of 90 matches `>=80`, `>=60`, AND `>=40` without break).
    $tier = switch ($true) {
        ($blockers.Count -gt 0)  { "Blocked"; break }
        ($score -ge 80)          { "Ready"; break }
        ($score -ge 60)          { "Ready with Remediation"; break }
        ($score -ge 40)          { "Significant Remediation"; break }
        default                  { "Not Ready" }
    }

    return [ordered]@{
        Score        = $score
        Tier         = $tier
        Factors      = @($factors)
        Blockers     = @($blockers)
        OrgPathReady = $orgPathReady
    }
}

# ══════════════════════════════════════════════════════════════
# Migration Target Recommendation
# ══════════════════════════════════════════════════════════════

function Get-MigrationTarget {
    param($DeviceType, $Computer)

    switch -Wildcard ($DeviceType) {
        'Workstation'        { return "Entra ID Join + Intune + Autopilot" }
        'Laptop'             { return "Entra ID Join + Intune + Autopilot" }
        'Shared/Kiosk'       { return "Entra ID Join + Intune Shared Device Mode" }
        'Virtual Desktop'    { return "Entra ID Join + Intune + AVD/W365" }
        'Server*Linux*'      { return "Azure Arc + Entra ID SSH Auth" }
        'Server*'            { return "Azure Arc + Entra ID RDP Auth + RBAC" }
        'Infrastructure*DC*' { return "Retain in AD — decommission last" }
        'Infrastructure*'    { return "Retain in AD during coexistence — plan decommission" }
        default              { return "Manual assessment required" }
    }
}

# ══════════════════════════════════════════════════════════════
# Process all computers
# ══════════════════════════════════════════════════════════════
Write-Host "  Classifying devices..." -ForegroundColor Yellow

$classifiedDevices = [System.Collections.Generic.List[object]]::new()

foreach ($comp in $computers) {
    $deviceType = Get-DeviceType -Computer $comp
    $osCurrency = Get-OSCurrency -OS $comp.OperatingSystem
    $readiness  = Get-MigrationReadiness -Computer $comp -DeviceType $deviceType -OSCurrency $osCurrency
    $migTarget  = Get-MigrationTarget -DeviceType $deviceType -Computer $comp

    $record = [ordered]@{
        # Identity
        Name                    = $comp.Name
        DNSHostName             = $comp.DNSHostName
        ObjectGUID              = $comp.ObjectGUID

        # Classification
        StateClassification     = $comp.StateClassification
        DeviceType              = $deviceType
        IsInfrastructure        = $comp.IsInfrastructure
        InfrastructureRole      = $comp.InfrastructureRole

        # OS Assessment
        OperatingSystem         = $comp.OperatingSystem
        OperatingSystemVersion  = $comp.OperatingSystemVersion
        OSCurrencyStatus        = $osCurrency.Status
        OSEOL                   = $osCurrency.EOL
        OSNote                  = $osCurrency.Note

        # State
        Enabled                 = $comp.Enabled
        DaysSinceLastLogon      = $comp.DaysSinceLastLogon
        OUPath                  = $comp.OUPath

        # Security posture
        SPNCount                = $comp.SPNCount
        HasDelegation           = ($comp.Delegation.TrustedForDelegation -or $comp.Delegation.AllowedToDelegateTo.Count -gt 0)
        HasBitLocker            = $comp.BitLocker.Present
        HasLAPS                 = $comp.LAPS.HasPassword
        LAPSType                = $comp.LAPS.Type

        # OrgPath (ADR-048)
        OrgPath                 = $comp.extensionAttribute1
        OrgPathDepth            = $comp.extensionAttribute2
        OrgPathReady            = $readiness.OrgPathReady

        # Migration assessment
        MigrationTarget         = $migTarget
        ReadinessScore          = $readiness.Score
        ReadinessTier           = $readiness.Tier
        ReadinessFactors        = ($readiness.Factors -join "; ")
        ReadinessBlockers       = ($readiness.Blockers -join "; ")
    }

    $classifiedDevices.Add($record)
}

Write-Host "  Classified $($classifiedDevices.Count) devices" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Summary Statistics
# ══════════════════════════════════════════════════════════════
Write-Host "  Computing summary statistics..." -ForegroundColor Yellow

$stateSummary = [ordered]@{
    Active               = ($classifiedDevices | Where-Object { $_.StateClassification -eq 'Active' }).Count
    Stale                = ($classifiedDevices | Where-Object { $_.StateClassification -eq 'Stale' }).Count
    Abandoned            = ($classifiedDevices | Where-Object { $_.StateClassification -eq 'Abandoned' }).Count
    Unknown              = ($classifiedDevices | Where-Object { $_.StateClassification -eq 'Unknown' }).Count
    InfrastructureCritical = ($classifiedDevices | Where-Object { $_.IsInfrastructure }).Count
}

$typeSummary = $classifiedDevices |
    Group-Object -Property DeviceType |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ DeviceType = $_.Name; Count = $_.Count } }

$osSummary = $classifiedDevices |
    Group-Object -Property OSCurrencyStatus |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Status = $_.Name; Count = $_.Count } }

$readinessSummary = $classifiedDevices |
    Group-Object -Property ReadinessTier |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Tier = $_.Name; Count = $_.Count } }

$migrationTargetSummary = $classifiedDevices |
    Group-Object -Property MigrationTarget |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Target = $_.Name; Count = $_.Count } }

$securityPosture = [ordered]@{
    WithBitLocker    = ($classifiedDevices | Where-Object { $_.HasBitLocker }).Count
    WithoutBitLocker = ($classifiedDevices | Where-Object { -not $_.HasBitLocker -and $_.DeviceType -match 'Workstation|Laptop' }).Count
    WithLAPS         = ($classifiedDevices | Where-Object { $_.HasLAPS }).Count
    WithoutLAPS      = ($classifiedDevices | Where-Object { -not $_.HasLAPS }).Count
    WithDelegation   = ($classifiedDevices | Where-Object { $_.HasDelegation }).Count
    OrgPathAssigned  = ($classifiedDevices | Where-Object { $_.OrgPathReady }).Count
    OrgPathMissing   = ($classifiedDevices | Where-Object { -not $_.OrgPathReady }).Count
}

# Devices requiring action (not Ready)
$actionRequired = [ordered]@{
    CleanupCandidates     = ($classifiedDevices | Where-Object { $_.StateClassification -eq 'Abandoned' -and -not $_.IsInfrastructure }).Count
    OSUpgradeRequired     = ($classifiedDevices | Where-Object { $_.OSCurrencyStatus -in @('Unsupported', 'ESU', 'EOL') }).Count
    DelegationRemediation = ($classifiedDevices | Where-Object { $_.HasDelegation }).Count
    Blocked               = ($classifiedDevices | Where-Object { $_.ReadinessTier -eq 'Blocked' }).Count
}

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        SourceFile       = $InputFile
        SourceDomain     = $domain
        Timestamp        = (Get-Date).ToString("o")
        TotalDevices     = $classifiedDevices.Count
        Script           = "UIAO Spec 1 D1.2 — Device State Classification Matrix"
        Reference        = "UIAO_136, ADR-048"
    }
    StateClassification    = $stateSummary
    DeviceTypes            = @($typeSummary)
    OSCurrency             = @($osSummary)
    MigrationReadiness     = @($readinessSummary)
    MigrationTargets       = @($migrationTargetSummary)
    SecurityPosture        = $securityPosture
    ActionRequired         = $actionRequired
}

# ══════════════════════════════════════════════════════════════
# Output: JSON (for Quarto dashboard)
# ══════════════════════════════════════════════════════════════
$jsonOutput = [ordered]@{
    Summary = $summary
    Devices = @($classifiedDevices)
}

$jsonFile = Join-Path $OutputPath "UIAO_Spec1_D1.2_DeviceClassification_${domain}_${timestamp}.json"
$jsonOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON output: $jsonFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Output: CSV (for spreadsheet)
# ══════════════════════════════════════════════════════════════
$csvFile = Join-Path $OutputPath "UIAO_Spec1_D1.2_DeviceClassification_${domain}_${timestamp}.csv"
$classifiedDevices | ForEach-Object { [PSCustomObject]$_ } | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV output:  $csvFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Console Dashboard
# ══════════════════════════════════════════════════════════════
Write-Host "`n-- Device State Classification --" -ForegroundColor Cyan
Write-Host "  Active (<90 days):        $($stateSummary.Active)" -ForegroundColor Green
Write-Host "  Stale (90–180 days):      $($stateSummary.Stale)" -ForegroundColor Yellow
Write-Host "  Abandoned (>180 days):    $($stateSummary.Abandoned)" -ForegroundColor Red
Write-Host "  Unknown (no timestamp):   $($stateSummary.Unknown)" -ForegroundColor DarkGray
Write-Host "  Infrastructure-Critical:  $($stateSummary.InfrastructureCritical)" -ForegroundColor Magenta

Write-Host "`n-- Device Types --" -ForegroundColor Cyan
foreach ($t in $typeSummary) {
    Write-Host "  $($t.Count.ToString().PadLeft(6))  $($t.DeviceType)"
}

Write-Host "`n-- OS Currency --" -ForegroundColor Cyan
foreach ($o in $osSummary) {
    $color = switch ($o.Status) {
        'Current'     { 'Green' }
        'Extended'    { 'Yellow' }
        'EOL'         { 'Red' }
        'ESU'         { 'Red' }
        'Unsupported' { 'DarkRed' }
        'Linux'       { 'DarkCyan' }
        default       { 'Gray' }
    }
    Write-Host "  $($o.Count.ToString().PadLeft(6))  $($o.Status)" -ForegroundColor $color
}

Write-Host "`n-- Migration Readiness --" -ForegroundColor Cyan
foreach ($r in $readinessSummary) {
    $color = switch ($r.Tier) {
        'Ready'                   { 'Green' }
        'Ready with Remediation'  { 'Yellow' }
        'Significant Remediation' { 'DarkYellow' }
        'Not Ready'               { 'Red' }
        'Blocked'                 { 'DarkRed' }
        default                   { 'Gray' }
    }
    Write-Host "  $($r.Count.ToString().PadLeft(6))  $($r.Tier)" -ForegroundColor $color
}

Write-Host "`n-- Action Required --" -ForegroundColor Cyan
Write-Host "  Cleanup candidates (abandoned):  $($actionRequired.CleanupCandidates)"
Write-Host "  OS upgrade required:             $($actionRequired.OSUpgradeRequired)"
Write-Host "  Delegation remediation:          $($actionRequired.DelegationRemediation)"
Write-Host "  Migration blocked:               $($actionRequired.Blocked)" -ForegroundColor $(if ($actionRequired.Blocked -gt 0) { 'Red' } else { 'Green' })

Write-Host "`n-- OrgPath Readiness (ADR-048) --" -ForegroundColor Cyan
Write-Host "  OrgPath assigned:   $($securityPosture.OrgPathAssigned)"
Write-Host "  OrgPath missing:    $($securityPosture.OrgPathMissing)"

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
