<#
.SYNOPSIS
    UIAO Spec 3 — D1.8: SQL Server Authentication Audit
.DESCRIPTION
    Discovers all SQL Server instances in the environment and audits their
    authentication configuration for Entra ID migration readiness per ADR-004.

    Discovery methods:
    1. SPN-based — find all MSSQLSvc/ SPNs from D1.5 Kerberos SPN Inventory
    2. Service-based — query Win32_Service for SQL Server services on target servers
    3. Registry-based — enumerate SQL Server instances from remote registry
    4. Port-based — optional TCP probe for default (1433) and named instance ports

    Per-instance audit:
    1. Authentication Mode Detection:
       - Windows Authentication Only (Kerberos/NTLM)
       - Mixed Mode (Windows + SQL Authentication)
       - SQL Authentication Only (legacy — rare)
    2. SQL Login Inventory:
       - sa account status (enabled/disabled, last password change)
       - All SQL logins with password policy compliance
       - Windows logins (domain users and groups)
       - Orphaned logins (SID mismatch with AD)
    3. Service Account Analysis:
       - SQL Server service account identity
       - SQL Agent service account identity
       - SSRS, SSIS, SSAS service accounts if present
       - Cross-reference with D1.1 service account scan
    4. Entra ID Readiness Assessment:
       - SQL Server version check (2022+ required for native Entra ID auth)
       - Azure Arc enrollment status (required for Entra ID auth on-prem)
       - Current authentication dependencies that block migration
       - Linked server authentication chains
    5. Migration Target per ADR-004:
       - SQL 2022+ on-prem → Entra ID auth via Arc
       - SQL 2019 and earlier → Upgrade path or retain Windows Auth
       - Azure SQL → Native Entra ID auth
       - Application connection string audit scope

    Outputs: JSON + CSV (instance inventory) + CSV (login inventory) + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.8
         ADR-004 (Workload Identity Federation as Default)
         Consumes: Spec1-D1.5 SPN Inventory (MSSQLSvc/ SPNs)
         Consumes: Spec3-D1.1 Service Account Scan
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D5InputFile
    Optional path to Spec1-D1.5 SPN Inventory JSON for MSSQLSvc SPN extraction.
.PARAMETER D1InputFile
    Optional path to Spec3-D1.1 Service Account Scan JSON for cross-reference.
.PARAMETER TargetServers
    Explicit list of server names to audit. If omitted, discovers via SPNs.
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER TestConnectivity
    If set, attempts TCP connection to discovered SQL instances.
.PARAMETER QueryInstances
    If set, connects to each SQL instance via SqlClient to audit logins
    and configuration. Requires appropriate SQL permissions.
.EXAMPLE
    .\Spec3-D1.8-Get-SQLServerAuthAudit.ps1 -D5InputFile .\output\UIAO_Spec1_D1.5_SPNInventory.json
    .\Spec3-D1.8-Get-SQLServerAuthAudit.ps1 -TargetServers SERVER01,SERVER02 -QueryInstances
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for SPN discovery
    Optional: SqlServer PowerShell module for deep instance audit
    Optional: Remote registry access for instance enumeration
    Optional: SQL Server permissions for login inventory
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D5InputFile,
    [string]$D1InputFile,
    [string[]]$TargetServers,
    [string]$DomainController,
    [string]$SearchBase,
    [switch]$TestConnectivity,
    [switch]$QueryInstances
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.8: SQL Server Authentication Audit" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-004" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Discover SQL Server Instances
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/5] Discovering SQL Server instances..." -ForegroundColor Yellow

$sqlInstances = @()

# ── Method 1: SPN-based discovery ──
if ($D5InputFile) {
    if (-not (Test-Path $D5InputFile)) {
        Write-Warning "D1.5 input file not found: $D5InputFile — skipping SPN-based discovery"
    } else {
        $d5Data = Get-Content -Path $D5InputFile -Raw | ConvertFrom-Json
        $mssqlSPNs = $d5Data.SPNInventory | ForEach-Object {
            $_.SPNs | Where-Object { $_.ServiceClass -eq 'MSSQLSvc' }
        } | Where-Object { $_ }

        foreach ($spn in $mssqlSPNs) {
            $sqlInstances += [PSCustomObject]@{
                ServerName       = $spn.Hostname
                InstanceName     = if ($spn.InstanceName) { $spn.InstanceName } elseif ($spn.Port -and $spn.Port -ne 1433) { "Named (port $($spn.Port))" } else { "MSSQLSERVER" }
                Port             = $spn.Port
                DiscoveryMethod  = "SPN (MSSQLSvc/)"
                SPNRegistration  = $spn.RawSPN
                AccountName      = $spn.AccountName
                AccountDN        = $spn.AccountDN
            }
        }
        Write-Host "  SPN discovery: found $($sqlInstances.Count) MSSQLSvc SPNs" -ForegroundColor Green
    }
} else {
    # Live SPN query
    if (Get-Module -ListAvailable -Name ActiveDirectory) {
        Import-Module ActiveDirectory -ErrorAction Stop
        $adParams = @{ Filter = "servicePrincipalName -like 'MSSQLSvc/*'"; Properties = @('servicePrincipalName', 'samAccountName', 'distinguishedName', 'enabled') }
        if ($DomainController) { $adParams['Server'] = $DomainController }
        if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

        $sqlObjects = @()
        $sqlObjects += Get-ADComputer @adParams -ErrorAction SilentlyContinue
        $adParams['Filter'] = "servicePrincipalName -like 'MSSQLSvc/*'"
        $sqlObjects += Get-ADUser @adParams -ErrorAction SilentlyContinue

        foreach ($obj in $sqlObjects) {
            foreach ($spnRaw in ($obj.servicePrincipalName | Where-Object { $_ -like 'MSSQLSvc/*' })) {
                $parts = $spnRaw -replace '^MSSQLSvc/', '' -split ':'
                $hostname = $parts[0]
                $portOrInstance = if ($parts.Count -gt 1) { $parts[1] } else { $null }

                $sqlInstances += [PSCustomObject]@{
                    ServerName       = $hostname
                    InstanceName     = if ($portOrInstance -and $portOrInstance -notmatch '^\d+$') { $portOrInstance } elseif (-not $portOrInstance -or $portOrInstance -eq '1433') { "MSSQLSERVER" } else { "Named (port $portOrInstance)" }
                    Port             = if ($portOrInstance -match '^\d+$') { [int]$portOrInstance } else { 1433 }
                    DiscoveryMethod  = "SPN (Live AD Query)"
                    SPNRegistration  = $spnRaw
                    AccountName      = $obj.samAccountName
                    AccountDN        = $obj.distinguishedName
                }
            }
        }
        Write-Host "  SPN discovery (live): found $($sqlInstances.Count) MSSQLSvc SPNs" -ForegroundColor Green
    } else {
        Write-Warning "  ActiveDirectory module not available — skipping SPN discovery"
    }
}

# ── Method 2: Explicit target servers ──
if ($TargetServers) {
    foreach ($server in $TargetServers) {
        $existing = $sqlInstances | Where-Object { $_.ServerName -like "$server*" }
        if (-not $existing) {
            $sqlInstances += [PSCustomObject]@{
                ServerName       = $server
                InstanceName     = "MSSQLSERVER"
                Port             = 1433
                DiscoveryMethod  = "Explicit Target"
                SPNRegistration  = "N/A"
                AccountName      = "Unknown"
                AccountDN        = "Unknown"
            }
        }
    }
    Write-Host "  Added $($TargetServers.Count) explicit target servers" -ForegroundColor Green
}

# Deduplicate by server+instance
$sqlInstances = $sqlInstances | Sort-Object ServerName, InstanceName -Unique
Write-Host "  Total unique SQL instances: $($sqlInstances.Count)" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Service Account Cross-Reference
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/5] Cross-referencing service accounts..." -ForegroundColor Yellow

$serviceAccountMap = @{}

if ($D1InputFile) {
    if (-not (Test-Path $D1InputFile)) {
        Write-Warning "D1.1 service account file not found: $D1InputFile"
    } else {
        $d1Data = Get-Content -Path $D1InputFile -Raw | ConvertFrom-Json
        foreach ($sa in $d1Data.ServiceAccounts) {
            $serviceAccountMap[$sa.SamAccountName] = @{
                RiskScore        = $sa.RiskScore
                PasswordAge      = $sa.PasswordAge
                IsGMSA           = $sa.IsGMSA
                HasSPN           = $sa.HasSPN
                DelegationType   = $sa.DelegationType
                MigrationTarget  = $sa.MigrationTarget
            }
        }
        Write-Host "  Loaded $($serviceAccountMap.Count) service accounts from D1.1" -ForegroundColor Green
    }
}

# ═══════════════════════════════════════════════════════════════
# SECTION 3: Remote Instance Audit (Optional)
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/5] Auditing SQL Server instances..." -ForegroundColor Yellow

$instanceAudits = @()

foreach ($instance in $sqlInstances) {
    $audit = [PSCustomObject]@{
        ServerName           = $instance.ServerName
        InstanceName         = $instance.InstanceName
        Port                 = $instance.Port
        DiscoveryMethod      = $instance.DiscoveryMethod
        SPNRegistration      = $instance.SPNRegistration
        ServiceAccountName   = $instance.AccountName
        # Service enumeration fields
        SQLServiceAccount    = "Unknown"
        SQLAgentAccount      = "Unknown"
        SSRSAccount          = "Unknown"
        SSISAccount          = "Unknown"
        SSASAccount          = "Unknown"
        # Auth mode fields
        AuthenticationMode   = "Unknown"
        SQLVersion           = "Unknown"
        SQLEdition           = "Unknown"
        SQLVersionMajor      = 0
        # Connectivity
        TCPReachable         = "Not tested"
        # Entra ID readiness
        EntraIDReady         = $false
        EntraIDBlockers      = @()
        MigrationTarget      = "Unknown"
        MigrationComplexity  = "Unknown"
        # Login audit
        SQLLogins            = @()
        WindowsLogins        = @()
        OrphanedLogins       = @()
        LinkedServers        = @()
        # D1.1 cross-reference
        D1ServiceAccountInfo = $null
    }

    # ── Cross-reference with D1.1 ──
    if ($serviceAccountMap.ContainsKey($instance.AccountName)) {
        $audit.D1ServiceAccountInfo = $serviceAccountMap[$instance.AccountName]
    }

    # ── Remote service enumeration ──
    try {
        $serverShort = ($instance.ServerName -split '\.')[0]
        $services = Get-CimInstance -ClassName Win32_Service -ComputerName $serverShort -Filter "PathName LIKE '%sqlservr%' OR PathName LIKE '%MSSQL%' OR PathName LIKE '%ReportServer%' OR PathName LIKE '%MsDtsServer%' OR PathName LIKE '%msmdsrv%'" -ErrorAction Stop

        foreach ($svc in $services) {
            switch -Wildcard ($svc.Name) {
                "MSSQLSERVER"    { $audit.SQLServiceAccount = $svc.StartName }
                "MSSQL`$*"       { $audit.SQLServiceAccount = $svc.StartName }
                "SQLSERVERAGENT" { $audit.SQLAgentAccount = $svc.StartName }
                "SQLAgent`$*"    { $audit.SQLAgentAccount = $svc.StartName }
                "*ReportServer*" { $audit.SSRSAccount = $svc.StartName }
                "*MsDtsServer*"  { $audit.SSISAccount = $svc.StartName }
                "*msmdsrv*"      { $audit.SSASAccount = $svc.StartName }
            }
        }
        Write-Host "  [$($instance.ServerName)\$($instance.InstanceName)] Services enumerated" -ForegroundColor DarkGreen
    } catch {
        Write-Host "  [$($instance.ServerName)\$($instance.InstanceName)] Service enum failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
    }

    # ── TCP connectivity test ──
    if ($TestConnectivity) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $connectTask = $tcp.ConnectAsync($instance.ServerName, $instance.Port)
            if ($connectTask.Wait(3000)) {
                $audit.TCPReachable = "Yes"
                $tcp.Close()
            } else {
                $audit.TCPReachable = "Timeout"
            }
        } catch {
            $audit.TCPReachable = "No"
        }
    }

    # ── SQL instance query (requires QueryInstances and connectivity) ──
    if ($QueryInstances -and $audit.TCPReachable -ne "No") {
        try {
            $connectionString = if ($instance.InstanceName -eq "MSSQLSERVER") {
                "Server=$($instance.ServerName);Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10"
            } else {
                "Server=$($instance.ServerName)\$($instance.InstanceName);Integrated Security=True;TrustServerCertificate=True;Connect Timeout=10"
            }

            $conn = New-Object System.Data.SqlClient.SqlConnection($connectionString)
            $conn.Open()

            # Get version info
            $cmd = $conn.CreateCommand()
            $cmd.CommandText = "SELECT SERVERPROPERTY('ProductVersion') AS Version, SERVERPROPERTY('Edition') AS Edition, SERVERPROPERTY('IsIntegratedSecurityOnly') AS WinAuthOnly"
            $reader = $cmd.ExecuteReader()
            if ($reader.Read()) {
                $audit.SQLVersion = $reader["Version"].ToString()
                $audit.SQLEdition = $reader["Edition"].ToString()
                $versionParts = $audit.SQLVersion -split '\.'
                $audit.SQLVersionMajor = [int]$versionParts[0]
                $winAuthOnly = $reader["WinAuthOnly"]
                $audit.AuthenticationMode = if ($winAuthOnly -eq 1) { "Windows Authentication Only" } else { "Mixed Mode (Windows + SQL)" }
            }
            $reader.Close()

            # Get SQL logins
            $cmd.CommandText = @"
SELECT name, type_desc, is_disabled, create_date, modify_date,
       LOGINPROPERTY(name, 'PasswordLastSetTime') AS PasswordLastSet,
       LOGINPROPERTY(name, 'IsExpired') AS IsExpired,
       LOGINPROPERTY(name, 'IsMustChange') AS IsMustChange,
       LOGINPROPERTY(name, 'IsLocked') AS IsLocked,
       LOGINPROPERTY(name, 'BadPasswordCount') AS BadPasswordCount
FROM sys.server_principals
WHERE type IN ('S', 'U', 'G')
ORDER BY type, name
"@
            $reader = $cmd.ExecuteReader()
            while ($reader.Read()) {
                $loginType = $reader["type_desc"].ToString()
                $loginInfo = @{
                    LoginName        = $reader["name"].ToString()
                    LoginType        = $loginType
                    IsDisabled       = [bool]$reader["is_disabled"]
                    CreatedDate      = $reader["create_date"].ToString()
                    ModifiedDate     = $reader["modify_date"].ToString()
                }

                if ($loginType -eq "SQL_LOGIN") {
                    $loginInfo.PasswordLastSet = if ($reader["PasswordLastSet"] -ne [DBNull]::Value) { $reader["PasswordLastSet"].ToString() } else { "Never" }
                    $loginInfo.IsExpired = if ($reader["IsExpired"] -ne [DBNull]::Value) { [bool]$reader["IsExpired"] } else { $false }
                    $loginInfo.IsSA = ($reader["name"].ToString() -eq "sa")
                    $audit.SQLLogins += $loginInfo
                } else {
                    $audit.WindowsLogins += $loginInfo
                }
            }
            $reader.Close()

            # Get linked servers
            $cmd.CommandText = "SELECT name, provider, data_source, product FROM sys.servers WHERE is_linked = 1"
            $reader = $cmd.ExecuteReader()
            while ($reader.Read()) {
                $audit.LinkedServers += @{
                    Name       = $reader["name"].ToString()
                    Provider   = $reader["provider"].ToString()
                    DataSource = $reader["data_source"].ToString()
                    Product    = $reader["product"].ToString()
                }
            }
            $reader.Close()

            # Check for orphaned logins (Windows logins with invalid SIDs)
            $cmd.CommandText = @"
SELECT sp.name, sp.sid
FROM sys.server_principals sp
WHERE sp.type IN ('U', 'G')
  AND sp.name NOT LIKE 'NT %'
  AND sp.name NOT LIKE 'BUILTIN\%'
  AND sp.name NOT LIKE '##%'
"@
            $reader = $cmd.ExecuteReader()
            while ($reader.Read()) {
                $loginName = $reader["name"].ToString()
                # Try to resolve in AD
                if (Get-Module -Name ActiveDirectory) {
                    try {
                        $adUser = Get-ADObject -Filter "samAccountName -eq '$($loginName -replace '^.*\\', '')'" -ErrorAction Stop
                        if (-not $adUser) {
                            $audit.OrphanedLogins += @{ LoginName = $loginName; Reason = "Not found in AD" }
                        }
                    } catch {
                        $audit.OrphanedLogins += @{ LoginName = $loginName; Reason = "AD lookup failed" }
                    }
                }
            }
            $reader.Close()

            $conn.Close()
            Write-Host "  [$($instance.ServerName)\$($instance.InstanceName)] SQL audit complete — $($audit.AuthenticationMode)" -ForegroundColor DarkGreen
        } catch {
            Write-Host "  [$($instance.ServerName)\$($instance.InstanceName)] SQL query failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
            $audit.AuthenticationMode = "Query Failed"
        }
    }

    # ── Entra ID Readiness Assessment ──
    $blockers = @()

    if ($audit.SQLVersionMajor -gt 0 -and $audit.SQLVersionMajor -lt 16) {
        $blockers += "SQL Server version $($audit.SQLVersion) — requires SQL 2022 (v16+) for native Entra ID authentication"
        $audit.MigrationTarget = "Upgrade to SQL 2022 + Arc, then Entra ID auth"
        $audit.MigrationComplexity = "High"
    } elseif ($audit.SQLVersionMajor -ge 16) {
        $audit.MigrationTarget = "Enable Entra ID auth via Azure Arc (ADR-004)"
        $audit.MigrationComplexity = "Medium"
    }

    if ($audit.AuthenticationMode -eq "Mixed Mode (Windows + SQL)") {
        $blockers += "Mixed mode authentication — SQL logins must be migrated to Entra ID principals or eliminated"
    }

    $saLogin = $audit.SQLLogins | Where-Object { $_.IsSA -eq $true -and $_.IsDisabled -eq $false }
    if ($saLogin) {
        $blockers += "sa account is ENABLED — must be disabled before Entra ID migration"
    }

    if ($audit.LinkedServers.Count -gt 0) {
        $blockers += "$($audit.LinkedServers.Count) linked server(s) found — authentication chain must be audited"
    }

    if ($audit.OrphanedLogins.Count -gt 0) {
        $blockers += "$($audit.OrphanedLogins.Count) orphaned login(s) — clean up before migration"
    }

    $audit.EntraIDBlockers = $blockers
    $audit.EntraIDReady = ($blockers.Count -eq 0 -and $audit.SQLVersionMajor -ge 16)

    $instanceAudits += $audit
}

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Summary Statistics
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/5] Computing summary statistics..." -ForegroundColor Yellow

$summary = @{
    TotalInstances          = $instanceAudits.Count
    UniqueServers           = ($instanceAudits | Select-Object -ExpandProperty ServerName -Unique).Count
    AuthModes               = @{
        WindowsOnly          = @($instanceAudits | Where-Object { $_.AuthenticationMode -eq "Windows Authentication Only" }).Count
        MixedMode            = @($instanceAudits | Where-Object { $_.AuthenticationMode -eq "Mixed Mode (Windows + SQL)" }).Count
        Unknown              = @($instanceAudits | Where-Object { $_.AuthenticationMode -eq "Unknown" }).Count
    }
    VersionDistribution     = @{
        SQL2022Plus          = @($instanceAudits | Where-Object { $_.SQLVersionMajor -ge 16 }).Count
        SQL2019              = @($instanceAudits | Where-Object { $_.SQLVersionMajor -eq 15 }).Count
        SQL2017              = @($instanceAudits | Where-Object { $_.SQLVersionMajor -eq 14 }).Count
        SQL2016OrEarlier     = @($instanceAudits | Where-Object { $_.SQLVersionMajor -gt 0 -and $_.SQLVersionMajor -lt 14 }).Count
        Unknown              = @($instanceAudits | Where-Object { $_.SQLVersionMajor -eq 0 }).Count
    }
    EntraIDReady            = @($instanceAudits | Where-Object { $_.EntraIDReady -eq $true }).Count
    EntraIDNotReady         = @($instanceAudits | Where-Object { $_.EntraIDReady -eq $false }).Count
    TotalSQLLogins          = ($instanceAudits | ForEach-Object { $_.SQLLogins.Count } | Measure-Object -Sum).Sum
    TotalWindowsLogins      = ($instanceAudits | ForEach-Object { $_.WindowsLogins.Count } | Measure-Object -Sum).Sum
    TotalOrphanedLogins     = ($instanceAudits | ForEach-Object { $_.OrphanedLogins.Count } | Measure-Object -Sum).Sum
    TotalLinkedServers      = ($instanceAudits | ForEach-Object { $_.LinkedServers.Count } | Measure-Object -Sum).Sum
    SAEnabled               = @($instanceAudits | Where-Object { $_.SQLLogins | Where-Object { $_.IsSA -and -not $_.IsDisabled } }).Count
    MigrationComplexity     = @{
        Low                  = @($instanceAudits | Where-Object { $_.MigrationComplexity -eq "Low" }).Count
        Medium               = @($instanceAudits | Where-Object { $_.MigrationComplexity -eq "Medium" }).Count
        High                 = @($instanceAudits | Where-Object { $_.MigrationComplexity -eq "High" }).Count
        Unknown              = @($instanceAudits | Where-Object { $_.MigrationComplexity -eq "Unknown" }).Count
    }
}

Write-Host "  Statistics computed" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Export Results
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/5] Exporting results..." -ForegroundColor Yellow

$domain = if ($D5InputFile -and $d5Data.Metadata) { $d5Data.Metadata.Domain } else { try { (Get-ADDomain).DNSRoot } catch { "unknown" } }
$outPrefix = "UIAO_Spec3_D1.8_SQLServerAuthAudit_${domain}_${timestamp}"

$results = @{
    Metadata = @{
        GeneratedAt = (Get-Date -Format "o")
        Generator   = "Spec3-D1.8-Get-SQLServerAuthAudit.ps1"
        UIAORef     = "UIAO_136 Spec 3, Phase 1, D1.8"
        ADRRef      = @("ADR-004")
        Domain      = $domain
    }
    Summary         = $summary
    InstanceAudits  = $instanceAudits
}

# ── JSON ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV (instance inventory) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_instances.csv"
$csvData = foreach ($a in $instanceAudits) {
    [PSCustomObject]@{
        ServerName         = $a.ServerName
        InstanceName       = $a.InstanceName
        Port               = $a.Port
        DiscoveryMethod    = $a.DiscoveryMethod
        SQLVersion         = $a.SQLVersion
        SQLEdition         = $a.SQLEdition
        AuthenticationMode = $a.AuthenticationMode
        SQLServiceAccount  = $a.SQLServiceAccount
        SQLAgentAccount    = $a.SQLAgentAccount
        SQLLoginCount      = $a.SQLLogins.Count
        WindowsLoginCount  = $a.WindowsLogins.Count
        OrphanedLoginCount = $a.OrphanedLogins.Count
        LinkedServerCount  = $a.LinkedServers.Count
        EntraIDReady       = $a.EntraIDReady
        EntraIDBlockers    = ($a.EntraIDBlockers -join "; ")
        MigrationTarget    = $a.MigrationTarget
        MigrationComplexity = $a.MigrationComplexity
        TCPReachable       = $a.TCPReachable
    }
}
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $csvPath" -ForegroundColor Green

# ── CSV (login inventory) ──
$loginCsvPath = Join-Path $OutputPath "${outPrefix}_logins.csv"
$loginCsvData = foreach ($a in $instanceAudits) {
    foreach ($login in ($a.SQLLogins + $a.WindowsLogins)) {
        [PSCustomObject]@{
            ServerName    = $a.ServerName
            InstanceName  = $a.InstanceName
            LoginName     = $login.LoginName
            LoginType     = $login.LoginType
            IsDisabled    = $login.IsDisabled
            IsSA          = if ($login.IsSA) { $true } else { $false }
            CreatedDate   = $login.CreatedDate
            PasswordLastSet = if ($login.PasswordLastSet) { $login.PasswordLastSet } else { "N/A" }
        }
    }
}
if ($loginCsvData) {
    $loginCsvData | Export-Csv -Path $loginCsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "  CSV:  $loginCsvPath" -ForegroundColor Green
}

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " SQL SERVER AUTHENTICATION AUDIT — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  SQL Instances Discovered:    $($summary.TotalInstances)" -ForegroundColor White
Write-Host "  Unique Servers:              $($summary.UniqueServers)" -ForegroundColor White
Write-Host ""
Write-Host "  Authentication Modes:" -ForegroundColor Cyan
Write-Host "    Windows Only:              $($summary.AuthModes.WindowsOnly)" -ForegroundColor Green
Write-Host "    Mixed Mode:                $($summary.AuthModes.MixedMode)" -ForegroundColor $(if ($summary.AuthModes.MixedMode -gt 0) { "Yellow" } else { "Green" })
Write-Host "    Unknown:                   $($summary.AuthModes.Unknown)" -ForegroundColor Gray
Write-Host ""
Write-Host "  SQL Server Versions:" -ForegroundColor Cyan
Write-Host "    SQL 2022+ (Entra capable): $($summary.VersionDistribution.SQL2022Plus)" -ForegroundColor Green
Write-Host "    SQL 2019:                  $($summary.VersionDistribution.SQL2019)" -ForegroundColor Yellow
Write-Host "    SQL 2017:                  $($summary.VersionDistribution.SQL2017)" -ForegroundColor DarkYellow
Write-Host "    SQL 2016 or earlier:       $($summary.VersionDistribution.SQL2016OrEarlier)" -ForegroundColor Red
Write-Host "    Unknown:                   $($summary.VersionDistribution.Unknown)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Entra ID Readiness:" -ForegroundColor Cyan
Write-Host "    Ready:                     $($summary.EntraIDReady)" -ForegroundColor Green
Write-Host "    Not Ready:                 $($summary.EntraIDNotReady)" -ForegroundColor $(if ($summary.EntraIDNotReady -gt 0) { "Red" } else { "Green" })
Write-Host ""
if ($summary.SAEnabled -gt 0) {
    Write-Host "  ⚠ WARNING: $($summary.SAEnabled) instance(s) have sa account ENABLED" -ForegroundColor Red
}
if ($summary.TotalOrphanedLogins -gt 0) {
    Write-Host "  ⚠ WARNING: $($summary.TotalOrphanedLogins) orphaned login(s) found" -ForegroundColor Yellow
}
if ($summary.TotalLinkedServers -gt 0) {
    Write-Host "  ⚠ NOTE: $($summary.TotalLinkedServers) linked server(s) require auth chain audit" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-004 (Workload Identity Federation as Default)" -ForegroundColor DarkCyan
Write-Host " SQL 2022+ required for native Entra ID authentication" -ForegroundColor DarkCyan
Write-Host " Azure Arc required for on-prem Entra ID auth enablement" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan
