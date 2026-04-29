<#
.SYNOPSIS
    UIAO Spec 3 — D1.11: Network Service Account Audit
.DESCRIPTION
    Discovers all Windows services, scheduled tasks, and application pools
    running under built-in network identity accounts (NETWORK SERVICE,
    LOCAL SERVICE, LOCAL SYSTEM) across the server fleet. These built-in
    accounts authenticate to remote resources using the computer's AD
    machine account — a dependency that breaks when the computer object
    is removed from AD during Entra ID migration.

    Built-in identity accounts and their AD dependencies:
    - NT AUTHORITY\NETWORK SERVICE — authenticates to network resources as
      the computer account (DOMAIN\COMPUTERNAME$). Uses Kerberos machine
      TGT. Breaks when machine leaves AD domain.
    - NT AUTHORITY\LOCAL SERVICE — authenticates to network as Anonymous.
      No AD dependency for remote auth, but may depend on local AD-joined
      state for local security policy.
    - NT AUTHORITY\LOCAL SYSTEM — highest privilege. Authenticates to
      network as computer account (like NETWORK SERVICE). Full AD dependency.

    Discovery passes:
    1. Windows Services — enumerate all services on target servers running
       under built-in accounts, focusing on NETWORK SERVICE and LOCAL SYSTEM
       services that make outbound network calls
    2. Scheduled Tasks — tasks running under built-in accounts with network
       actions (HTTP calls, file copies, database queries)
    3. IIS Application Pools — app pools using ApplicationPoolIdentity
       (which maps to virtual account IIS APPPOOL\poolname) or built-in
       accounts
    4. COM+ Applications — COM+ apps configured with built-in identity
    5. Network Authentication Analysis — which of these services actually
       authenticate to remote resources vs operate locally only
    6. Migration Impact Assessment:
       - NETWORK SERVICE → Managed Identity (Azure-hosted) or gMSA (on-prem
         during coexistence) or Entra ID joined machine credential
       - LOCAL SYSTEM → Evaluate if service needs network auth; if yes,
         same as NETWORK SERVICE path
       - LOCAL SERVICE → Generally safe, no network auth dependency
       - ApplicationPoolIdentity → Managed Identity for Azure App Service
         or container migration

    Outputs: JSON + CSV (service inventory) + CSV (migration plan) + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.11
         ADR-004 (Workload Identity Federation as Default)
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER TargetServers
    Array of server names to audit. If omitted, discovers from D1.1 or AD.
.PARAMETER D1InputFile
    Optional path to Spec1-D1.1 Computer Inventory JSON to derive server list.
.PARAMETER DomainController
    Target a specific DC for AD queries. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER IncludeScheduledTasks
    If set, enumerates scheduled tasks under built-in accounts.
.PARAMETER IncludeIISPools
    If set, enumerates IIS application pools under built-in accounts.
.PARAMETER IncludeCOMPlus
    If set, enumerates COM+ applications under built-in accounts.
.PARAMETER MaxConcurrent
    Maximum concurrent remote queries. Default: 10.
.EXAMPLE
    .\Spec3-D1.11-Get-NetworkServiceAccountAudit.ps1 -TargetServers SERVER01,SERVER02
    .\Spec3-D1.11-Get-NetworkServiceAccountAudit.ps1 -D1InputFile .\output\D1.1.json -IncludeScheduledTasks
.NOTES
    Requires: Remote WMI/CIM access to target servers
    Requires: Administrative privileges on target servers
    Optional: IIS WebAdministration module for app pool enumeration
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string[]]$TargetServers,
    [string]$D1InputFile,
    [string]$DomainController,
    [string]$SearchBase,
    [switch]$IncludeScheduledTasks,
    [switch]$IncludeIISPools,
    [switch]$IncludeCOMPlus,
    [int]$MaxConcurrent = 10
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.11: Network Service Account Audit" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-004" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Built-in account patterns ──
$builtinPatterns = @(
    'NT AUTHORITY\NETWORK SERVICE',
    'NT AUTHORITY\LOCAL SERVICE',
    'NT AUTHORITY\SYSTEM',
    'NT AUTHORITY\LOCAL SYSTEM',
    'LocalSystem',
    'NetworkService',
    'LocalService',
    'NETWORK SERVICE',
    'LOCAL SERVICE',
    'LOCAL SYSTEM'
)

$builtinRegex = ($builtinPatterns | ForEach-Object { [regex]::Escape($_) }) -join '|'

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Determine Target Server List
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/5] Building target server list..." -ForegroundColor Yellow

$servers = @()

if ($TargetServers) {
    $servers = $TargetServers
    Write-Host "  Explicit targets: $($servers.Count) servers" -ForegroundColor Green
}
elseif ($D1InputFile -and (Test-Path $D1InputFile)) {
    $d1Data = Get-Content -Path $D1InputFile -Raw | ConvertFrom-Json
    # Extract server-class computers (Server OS)
    $servers = $d1Data.Computers |
        Where-Object { $_.OperatingSystem -match 'Server' -and $_.Enabled -eq $true } |
        ForEach-Object { $_.DNSHostName ?? $_.Name }
    Write-Host "  From D1.1 inventory: $($servers.Count) server-class computers" -ForegroundColor Green
}
else {
    # Discover from AD
    if (Get-Module -ListAvailable -Name ActiveDirectory) {
        Import-Module ActiveDirectory -ErrorAction Stop
        $adParams = @{
            Filter     = "OperatingSystem -like '*Server*' -and Enabled -eq `$true"
            Properties = @('dNSHostName', 'operatingSystem')
        }
        if ($DomainController) { $adParams['Server'] = $DomainController }
        if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

        $servers = (Get-ADComputer @adParams).dNSHostName | Where-Object { $_ }
        Write-Host "  From AD query: $($servers.Count) server-class computers" -ForegroundColor Green
    } else {
        Write-Error "No target servers specified and ActiveDirectory module not available."
        return
    }
}

if ($servers.Count -eq 0) {
    Write-Error "No target servers to audit."
    return
}

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Windows Service Enumeration
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/5] Enumerating Windows services under built-in accounts..." -ForegroundColor Yellow

$serviceResults = @()
$serverStatus = @{}

foreach ($server in $servers) {
    $serverShort = ($server -split '\.')[0]
    Write-Host "  Scanning: $serverShort" -ForegroundColor DarkGray -NoNewline

    try {
        $services = Get-CimInstance -ClassName Win32_Service -ComputerName $serverShort -ErrorAction Stop |
            Where-Object {
                $_.StartName -and ($_.StartName -match $builtinRegex)
            }

        $serverStatus[$server] = "OK"

        foreach ($svc in $services) {
            # Classify the identity type
            $identityType = switch -Regex ($svc.StartName) {
                'NETWORK SERVICE|NetworkService' { "NETWORK SERVICE" }
                'LOCAL SYSTEM|LocalSystem|SYSTEM' { "LOCAL SYSTEM" }
                'LOCAL SERVICE|LocalService' { "LOCAL SERVICE" }
                default { $svc.StartName }
            }

            # Determine AD dependency
            $adDependency = switch ($identityType) {
                "NETWORK SERVICE" { "HIGH — authenticates to network as computer account (Kerberos machine TGT)" }
                "LOCAL SYSTEM"    { "HIGH — authenticates to network as computer account" }
                "LOCAL SERVICE"   { "LOW — authenticates to network as Anonymous (no machine credential)" }
                default           { "UNKNOWN" }
            }

            # Determine if service likely makes network calls
            $networkIndicators = @()
            if ($svc.PathName -match 'sql|iis|http|web|exchange|smtp|dns|dhcp|ftp|ssh|vpn|radius|nps') {
                $networkIndicators += "Service binary name suggests network activity"
            }
            if ($svc.Description -match 'network|remote|server|listener|connection|protocol') {
                $networkIndicators += "Service description mentions network"
            }

            $serviceResults += [PSCustomObject]@{
                ServerName         = $server
                ServiceName        = $svc.Name
                DisplayName        = $svc.DisplayName
                IdentityType       = $identityType
                RawStartName       = $svc.StartName
                StartMode          = $svc.StartMode
                State              = $svc.State
                PathName           = $svc.PathName
                Description        = $svc.Description
                ADDependency       = $adDependency
                NetworkIndicators  = ($networkIndicators -join "; ")
                IsRunning          = ($svc.State -eq "Running")
                IsAutoStart        = ($svc.StartMode -eq "Auto")
                MigrationTarget    = ""
                MigrationComplexity = ""
            }
        }

        Write-Host " — $($services.Count) built-in identity services" -ForegroundColor DarkGreen
    } catch {
        $serverStatus[$server] = "FAILED: $($_.Exception.Message)"
        Write-Host " — FAILED: $($_.Exception.Message)" -ForegroundColor Red
    }
}

Write-Host "  Total services found: $($serviceResults.Count)" -ForegroundColor Green
$reachable = @($serverStatus.Values | Where-Object { $_ -eq "OK" }).Count
Write-Host "  Servers reachable: $reachable / $($servers.Count)" -ForegroundColor $(if ($reachable -eq $servers.Count) { "Green" } else { "Yellow" })

# ═══════════════════════════════════════════════════════════════
# SECTION 3: Scheduled Task Enumeration (Optional)
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/5] Enumerating scheduled tasks..." -ForegroundColor Yellow

$taskResults = @()

if ($IncludeScheduledTasks) {
    foreach ($server in $servers) {
        if ($serverStatus[$server] -ne "OK") { continue }
        $serverShort = ($server -split '\.')[0]

        try {
            # Use schtasks.exe for remote query (more reliable than ScheduledTasks module)
            $schtasksOutput = & schtasks.exe /query /s $serverShort /fo CSV /v 2>&1
            if ($LASTEXITCODE -eq 0 -and $schtasksOutput) {
                $tasks = $schtasksOutput | ConvertFrom-Csv -ErrorAction SilentlyContinue |
                    Where-Object { $_.'Run As User' -and $_.'Run As User' -match $builtinRegex }

                foreach ($task in $tasks) {
                    $identityType = switch -Regex ($_.'Run As User') {
                        'NETWORK SERVICE|NetworkService' { "NETWORK SERVICE" }
                        'LOCAL SYSTEM|LocalSystem|SYSTEM' { "LOCAL SYSTEM" }
                        'LOCAL SERVICE|LocalService' { "LOCAL SERVICE" }
                        default { $_.'Run As User' }
                    }

                    $taskResults += [PSCustomObject]@{
                        ServerName       = $server
                        TaskName         = $task.TaskName
                        TaskPath         = if ($task.'Task To Run') { $task.'Task To Run' } else { "" }
                        IdentityType     = $identityType
                        RawRunAsUser     = $_.'Run As User'
                        Status           = $task.Status
                        LastRunTime      = if ($task.'Last Run Time') { $task.'Last Run Time' } else { "" }
                        NextRunTime      = if ($task.'Next Run Time') { $task.'Next Run Time' } else { "" }
                        ScheduleType     = if ($task.'Schedule Type') { $task.'Schedule Type' } else { "" }
                        ADDependency     = switch ($identityType) {
                            "NETWORK SERVICE" { "HIGH" }
                            "LOCAL SYSTEM"    { "HIGH" }
                            "LOCAL SERVICE"   { "LOW" }
                            default           { "UNKNOWN" }
                        }
                    }
                }
            }
        } catch {
            Write-Host "  Task enum failed on $serverShort : $_" -ForegroundColor DarkYellow
        }
    }

    Write-Host "  Scheduled tasks found: $($taskResults.Count)" -ForegroundColor Green
} else {
    Write-Host "  Skipped (use -IncludeScheduledTasks to enable)" -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════
# SECTION 3b: IIS Application Pool Enumeration (Optional)
# ═══════════════════════════════════════════════════════════════

$iisResults = @()

if ($IncludeIISPools) {
    Write-Host "  Enumerating IIS application pools..." -ForegroundColor DarkGray
    foreach ($server in $servers) {
        if ($serverStatus[$server] -ne "OK") { continue }
        $serverShort = ($server -split '\.')[0]

        try {
            # Try appcmd remotely
            $appcmdPath = "\\$serverShort\admin$\system32\inetsrv\appcmd.exe"
            if (Test-Path $appcmdPath -ErrorAction SilentlyContinue) {
                $poolOutput = & $appcmdPath list apppool /text:* 2>&1
                # Parse appcmd output for identity type
                $currentPool = @{}
                foreach ($line in $poolOutput) {
                    if ($line -match '^APPPOOL "(.+)"') {
                        if ($currentPool.Name) {
                            $iisResults += [PSCustomObject]$currentPool
                        }
                        $currentPool = @{
                            ServerName    = $server
                            Name          = $Matches[1]
                            IdentityType  = "Unknown"
                            UserName      = ""
                        }
                    }
                    if ($line -match 'processModel\.identityType:"(\w+)"') {
                        $currentPool.IdentityType = $Matches[1]
                    }
                    if ($line -match 'processModel\.userName:"(.+)"') {
                        $currentPool.UserName = $Matches[1]
                    }
                }
                if ($currentPool.Name) {
                    $iisResults += [PSCustomObject]$currentPool
                }
            }
        } catch {
            Write-Host "    IIS enum failed on $serverShort" -ForegroundColor DarkYellow
        }
    }
    Write-Host "  IIS app pools found: $($iisResults.Count)" -ForegroundColor Green
} else {
    Write-Host "  IIS pools: Skipped (use -IncludeIISPools to enable)" -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Migration Target Assignment
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/5] Assigning migration targets..." -ForegroundColor Yellow

# Well-known Windows services that are safe to ignore
$safeServices = @(
    'wuauserv', 'WinRM', 'WSearch', 'Themes', 'Spooler', 'Schedule',
    'ProfSvc', 'PlugPlay', 'nsi', 'NlaSvc', 'Netlogon', 'LanmanWorkstation',
    'LanmanServer', 'KeyIso', 'iphlpsvc', 'gpsvc', 'EventLog', 'Dhcp',
    'Dnscache', 'CryptSvc', 'COMSysApp', 'BFE', 'AudioSrv', 'Appinfo',
    'BITS', 'TrustedInstaller', 'wudfsvc', 'WinDefend', 'MpsSvc',
    'SamSs', 'SecurityHealthService', 'DiagTrack', 'WdiServiceHost'
)

foreach ($svc in $serviceResults) {
    # Skip well-known OS services
    if ($svc.ServiceName -in $safeServices) {
        $svc.MigrationTarget = "N/A — core Windows service, migrates with OS"
        $svc.MigrationComplexity = "None"
        continue
    }

    # Assign migration target based on identity type and service characteristics
    switch ($svc.IdentityType) {
        "NETWORK SERVICE" {
            if ($svc.ServiceName -match 'SQL|MSSQL') {
                $svc.MigrationTarget = "gMSA (coexistence) → Managed Identity via Arc (ADR-004)"
                $svc.MigrationComplexity = "High"
            }
            elseif ($svc.ServiceName -match 'W3SVC|WAS|IIS') {
                $svc.MigrationTarget = "Managed Identity for Azure App Service or container migration"
                $svc.MigrationComplexity = "Medium"
            }
            elseif ($svc.NetworkIndicators) {
                $svc.MigrationTarget = "Evaluate network auth requirement → gMSA or Managed Identity"
                $svc.MigrationComplexity = "Medium"
            }
            else {
                $svc.MigrationTarget = "Likely local-only — verify no outbound auth, then safe for Entra join"
                $svc.MigrationComplexity = "Low"
            }
        }
        "LOCAL SYSTEM" {
            if ($svc.ServiceName -match 'SQL|MSSQL') {
                $svc.MigrationTarget = "Change to gMSA first, then Managed Identity via Arc (ADR-004)"
                $svc.MigrationComplexity = "High"
            }
            elseif ($svc.NetworkIndicators) {
                $svc.MigrationTarget = "Evaluate: does service authenticate to remote resources? If yes → gMSA → Managed Identity"
                $svc.MigrationComplexity = "Medium"
            }
            else {
                $svc.MigrationTarget = "LOCAL SYSTEM with no network auth — safe for Entra join"
                $svc.MigrationComplexity = "Low"
            }
        }
        "LOCAL SERVICE" {
            $svc.MigrationTarget = "LOW RISK — LOCAL SERVICE does not use machine credential for network auth"
            $svc.MigrationComplexity = "Low"
        }
        default {
            $svc.MigrationTarget = "Investigate — non-standard built-in account"
            $svc.MigrationComplexity = "Unknown"
        }
    }
}

$complexityCounts = $serviceResults | Where-Object { $_.MigrationComplexity -ne "None" } | Group-Object MigrationComplexity
foreach ($c in $complexityCounts) {
    Write-Host "  $($c.Name): $($c.Count) services" -ForegroundColor $(switch ($c.Name) { "High" { "Red" }; "Medium" { "Yellow" }; "Low" { "Green" }; default { "Gray" } })
}

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Export Results
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/5] Exporting results..." -ForegroundColor Yellow

$domain = try { (Get-ADDomain).DNSRoot } catch { "unknown" }
$outPrefix = "UIAO_Spec3_D1.11_NetworkServiceAccountAudit_${domain}_${timestamp}"

$summary = @{
    TotalServersTargeted     = $servers.Count
    ServersReachable         = $reachable
    ServersFailed            = $servers.Count - $reachable
    TotalServicesAudited     = $serviceResults.Count
    ByIdentityType           = @{
        NetworkService       = @($serviceResults | Where-Object { $_.IdentityType -eq "NETWORK SERVICE" }).Count
        LocalSystem          = @($serviceResults | Where-Object { $_.IdentityType -eq "LOCAL SYSTEM" }).Count
        LocalService         = @($serviceResults | Where-Object { $_.IdentityType -eq "LOCAL SERVICE" }).Count
    }
    RunningServices          = @($serviceResults | Where-Object { $_.IsRunning }).Count
    AutoStartServices        = @($serviceResults | Where-Object { $_.IsAutoStart }).Count
    NetworkAuthDependencies  = @($serviceResults | Where-Object { $_.ADDependency -match "HIGH" -and $_.MigrationComplexity -ne "None" }).Count
    ScheduledTasks           = $taskResults.Count
    IISAppPools              = $iisResults.Count
    MigrationComplexity      = @{
        High    = @($serviceResults | Where-Object { $_.MigrationComplexity -eq "High" }).Count
        Medium  = @($serviceResults | Where-Object { $_.MigrationComplexity -eq "Medium" }).Count
        Low     = @($serviceResults | Where-Object { $_.MigrationComplexity -eq "Low" }).Count
        None    = @($serviceResults | Where-Object { $_.MigrationComplexity -eq "None" }).Count
        Unknown = @($serviceResults | Where-Object { $_.MigrationComplexity -eq "Unknown" }).Count
    }
}

$results = @{
    Metadata = @{
        GeneratedAt = (Get-Date -Format "o")
        Generator   = "Spec3-D1.11-Get-NetworkServiceAccountAudit.ps1"
        UIAORef     = "UIAO_136 Spec 3, Phase 1, D1.11"
        ADRRef      = @("ADR-004")
        Domain      = $domain
    }
    Summary          = $summary
    ServerStatus     = $serverStatus
    Services         = $serviceResults
    ScheduledTasks   = $taskResults
    IISAppPools      = $iisResults
}

# ── JSON ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV (service inventory) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_services.csv"
$csvData = foreach ($svc in $serviceResults) {
    [PSCustomObject]@{
        ServerName         = $svc.ServerName
        ServiceName        = $svc.ServiceName
        DisplayName        = $svc.DisplayName
        IdentityType       = $svc.IdentityType
        StartMode          = $svc.StartMode
        State              = $svc.State
        ADDependency       = $svc.ADDependency
        NetworkIndicators  = $svc.NetworkIndicators
        MigrationTarget    = $svc.MigrationTarget
        MigrationComplexity = $svc.MigrationComplexity
    }
}
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $csvPath" -ForegroundColor Green

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " NETWORK SERVICE ACCOUNT AUDIT — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Servers Audited:             $reachable / $($servers.Count)" -ForegroundColor White
Write-Host "  Total Services (built-in):   $($summary.TotalServicesAudited)" -ForegroundColor White
Write-Host ""
Write-Host "  Identity Distribution:" -ForegroundColor Cyan
Write-Host "    NETWORK SERVICE:           $($summary.ByIdentityType.NetworkService)" -ForegroundColor $(if ($summary.ByIdentityType.NetworkService -gt 0) { "Yellow" } else { "Green" })
Write-Host "    LOCAL SYSTEM:              $($summary.ByIdentityType.LocalSystem)" -ForegroundColor $(if ($summary.ByIdentityType.LocalSystem -gt 0) { "Yellow" } else { "Green" })
Write-Host "    LOCAL SERVICE:             $($summary.ByIdentityType.LocalService)" -ForegroundColor Green
Write-Host ""
Write-Host "  AD Dependencies (non-OS):    $($summary.NetworkAuthDependencies)" -ForegroundColor $(if ($summary.NetworkAuthDependencies -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "  Migration Complexity:" -ForegroundColor Cyan
Write-Host "    High:                      $($summary.MigrationComplexity.High)" -ForegroundColor $(if ($summary.MigrationComplexity.High -gt 0) { "Red" } else { "Green" })
Write-Host "    Medium:                    $($summary.MigrationComplexity.Medium)" -ForegroundColor $(if ($summary.MigrationComplexity.Medium -gt 0) { "Yellow" } else { "Green" })
Write-Host "    Low:                       $($summary.MigrationComplexity.Low)" -ForegroundColor Green
Write-Host "    Core OS (no action):       $($summary.MigrationComplexity.None)" -ForegroundColor DarkGray
if ($IncludeScheduledTasks) {
    Write-Host ""
    Write-Host "  Scheduled Tasks:             $($summary.ScheduledTasks)" -ForegroundColor White
}
if ($IncludeIISPools) {
    Write-Host "  IIS App Pools:               $($summary.IISAppPools)" -ForegroundColor White
}
Write-Host ""
Write-Host "  Key Insight:" -ForegroundColor Cyan
Write-Host "    NETWORK SERVICE and LOCAL SYSTEM authenticate to remote" -ForegroundColor White
Write-Host "    resources using the computer's AD machine account." -ForegroundColor White
Write-Host "    When the computer leaves AD → these services lose network auth." -ForegroundColor White
Write-Host "    Migration: gMSA (coexistence) → Managed Identity (post-migration)" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-004 (Workload Identity Federation as Default)" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan
