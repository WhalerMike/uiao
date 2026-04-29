<#
.SYNOPSIS
    UIAO Spec 3 — D1.9: LDAP Bind Account Inventory
.DESCRIPTION
    Discovers all accounts performing LDAP binds against Active Directory —
    the hidden dependency layer that must be eliminated before AD decommission.

    LDAP bind accounts are applications, middleware, and scripts that authenticate
    to AD using simple LDAP binds (port 389/636) rather than Kerberos. These are
    invisible to SPN-based discovery and represent a critical migration blocker.

    Discovery methods:
    1. AD Audit Log Analysis — Event IDs 4624 (logon type 8 = NetworkCleartext),
       2889 (LDAP unsigned bind), 2887 (LDAP signing statistics)
    2. Account Attribute Heuristics — accounts with characteristics suggesting
       LDAP bind usage:
       - Password never expires + no SPN (non-Kerberos service account)
       - Description/name patterns (ldap, bind, svc, app, connector)
       - Accounts in service account OUs with no computer object association
    3. Network Flow Analysis — optional netflow/firewall log parsing for
       connections to DC ports 389, 636, 3268, 3269
    4. DC Debug Logging — optional LDAP field engineering diagnostics
    5. Cross-reference with D1.1 Service Account Scan for enrichment

    Per-account output:
    - Account identity and attributes
    - Bind type classification (Simple, SASL, Anonymous)
    - Authentication security (Plaintext LDAP / LDAPS / LDAP+Signing)
    - Source IP/application (if audit logs available)
    - LDAP query patterns (if diagnostic logging enabled)
    - Migration target per ADR-003/ADR-004:
      * Graph API (for directory queries)
      * SCIM provisioning (for identity sync)
      * Entra ID Service Principal (for app authentication)
      * Managed Identity (for Azure-hosted workloads)
    - Risk classification (Critical / High / Medium / Low)

    Outputs: JSON + CSV (account inventory) + CSV (remediation plan) + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.9
         ADR-003 (API-Driven Inbound Provisioning)
         ADR-004 (Workload Identity Federation as Default)
         Consumes: Spec3-D1.1 Service Account Scan
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC for event log queries. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER D1InputFile
    Optional path to Spec3-D1.1 Service Account Scan JSON for cross-reference.
.PARAMETER EventLogHours
    Hours of event log history to analyze. Default: 168 (7 days).
.PARAMETER IncludeDCLogs
    If set, queries Security event logs on all DCs for LDAP bind events.
.PARAMETER FirewallLogPath
    Optional path to firewall/netflow logs (CSV) for network-based discovery.
.EXAMPLE
    .\Spec3-D1.9-Get-LDAPBindAccountInventory.ps1 -IncludeDCLogs
    .\Spec3-D1.9-Get-LDAPBindAccountInventory.ps1 -D1InputFile .\output\D1.1.json -EventLogHours 720
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    Optional: Remote event log access on Domain Controllers
    Optional: Firewall/netflow log exports
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$SearchBase,
    [string]$D1InputFile,
    [int]$EventLogHours = 168,
    [switch]$IncludeDCLogs,
    [string]$FirewallLogPath
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.9: LDAP Bind Account Inventory" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-003 / ADR-004" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Prerequisites ──
if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT."
    return
}
Import-Module ActiveDirectory -ErrorAction Stop

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
$domain = (Get-ADDomain @adParams).DNSRoot

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Heuristic-Based LDAP Bind Account Discovery
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/5] Discovering potential LDAP bind accounts (heuristic)..." -ForegroundColor Yellow

$ldapAccounts = @()

# Pattern 1: Password never expires + no SPN (strong indicator of LDAP bind)
$queryParams = @{
    Filter     = "PasswordNeverExpires -eq `$true -and servicePrincipalName -notlike '*' -and Enabled -eq `$true"
    Properties = @('samAccountName', 'distinguishedName', 'displayName', 'description',
                   'whenCreated', 'whenChanged', 'lastLogonTimestamp', 'pwdLastSet',
                   'passwordNeverExpires', 'memberOf', 'servicePrincipalName',
                   'userAccountControl', 'adminCount', 'logonCount')
}
if ($SearchBase) { $queryParams['SearchBase'] = $SearchBase }
if ($DomainController) { $queryParams['Server'] = $DomainController }

$pneNoSPN = Get-ADUser @queryParams

foreach ($acct in $pneNoSPN) {
    $lastLogon = if ($acct.lastLogonTimestamp) {
        [DateTime]::FromFileTime($acct.lastLogonTimestamp)
    } else { $null }

    $pwdLastSet = if ($acct.pwdLastSet -and $acct.pwdLastSet -ne 0) {
        [DateTime]::FromFileTime($acct.pwdLastSet)
    } else { $null }

    $passwordAge = if ($pwdLastSet) { ((Get-Date) - $pwdLastSet).Days } else { -1 }
    $daysSinceLogon = if ($lastLogon) { ((Get-Date) - $lastLogon).Days } else { -1 }

    # Compute confidence score
    $confidence = 50  # Base: PNE + no SPN is moderately suspicious

    # Boost confidence based on naming patterns
    $namePatterns = @('ldap', 'bind', 'svc', 'service', 'app', 'connector',
                      'sync', 'integration', 'api', 'middleware', 'provision',
                      'scan', 'monitor', 'backup', 'agent', 'query')
    $nameLC = ($acct.samAccountName + " " + $acct.description).ToLower()
    foreach ($pat in $namePatterns) {
        if ($nameLC -match $pat) { $confidence += 10; break }
    }

    # OU-based boost (service account OUs)
    $ouPatterns = @('Service', 'svc', 'Application', 'NonHuman', 'System')
    foreach ($pat in $ouPatterns) {
        if ($acct.distinguishedName -match "OU=$pat") { $confidence += 15; break }
    }

    # Old password boost (service accounts tend to have ancient passwords)
    if ($passwordAge -gt 365) { $confidence += 10 }
    if ($passwordAge -gt 730) { $confidence += 10 }

    # Active usage boost
    if ($daysSinceLogon -ge 0 -and $daysSinceLogon -le 7) { $confidence += 15 }
    elseif ($daysSinceLogon -ge 0 -and $daysSinceLogon -le 30) { $confidence += 10 }

    # Admin account penalty (probably not LDAP bind)
    if ($acct.adminCount -eq 1) { $confidence -= 20 }

    $confidence = [Math]::Min(100, [Math]::Max(0, $confidence))

    # Classify risk
    $risk = if ($confidence -ge 80) { "Critical" }
            elseif ($confidence -ge 60) { "High" }
            elseif ($confidence -ge 40) { "Medium" }
            else { "Low" }

    $ldapAccounts += [PSCustomObject]@{
        SamAccountName       = $acct.samAccountName
        DistinguishedName    = $acct.distinguishedName
        DisplayName          = $acct.displayName
        Description          = $acct.description
        Enabled              = $true
        PasswordNeverExpires = $true
        HasSPN               = $false
        WhenCreated          = $acct.whenCreated
        LastLogon            = if ($lastLogon) { $lastLogon.ToString("yyyy-MM-dd HH:mm:ss") } else { "Never" }
        DaysSinceLogon       = $daysSinceLogon
        PasswordLastSet      = if ($pwdLastSet) { $pwdLastSet.ToString("yyyy-MM-dd HH:mm:ss") } else { "Never" }
        PasswordAgeDays      = $passwordAge
        LogonCount           = $acct.logonCount
        AdminCount           = $acct.adminCount
        MemberOfCount        = @($acct.memberOf).Count
        DiscoveryMethod      = "Heuristic (PNE + No SPN)"
        LDAPBindConfidence   = $confidence
        RiskClassification   = $risk
        BindType             = "Unknown (heuristic)"
        BindSecurity         = "Unknown (requires event log)"
        SourceApplication    = "Unknown (requires event log or documentation)"
        MigrationTarget      = "TBD — requires application owner identification"
        RemediationPriority  = 0
    }
}

Write-Host "  Found $($ldapAccounts.Count) potential LDAP bind accounts (heuristic)" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Event Log Analysis (Optional)
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/5] Analyzing DC event logs..." -ForegroundColor Yellow

$eventLogResults = @()

if ($IncludeDCLogs) {
    $dcs = @()
    if ($DomainController) {
        $dcs += $DomainController
    } else {
        try {
            $dcs = (Get-ADDomainController -Filter * @adParams).HostName
        } catch {
            Write-Warning "  Could not enumerate DCs: $_"
        }
    }

    $startTime = (Get-Date).AddHours(-$EventLogHours)

    foreach ($dc in $dcs) {
        Write-Host "  Scanning DC: $dc" -ForegroundColor DarkGray

        # Event ID 2889 — LDAP unsigned simple binds
        try {
            $events2889 = Get-WinEvent -ComputerName $dc -FilterHashtable @{
                LogName   = 'Directory Service'
                Id        = 2889
                StartTime = $startTime
            } -ErrorAction SilentlyContinue -MaxEvents 1000

            foreach ($evt in $events2889) {
                $eventLogResults += [PSCustomObject]@{
                    DC              = $dc
                    EventId         = 2889
                    EventType       = "LDAP Unsigned Simple Bind"
                    TimeCreated     = $evt.TimeCreated
                    AccountName     = if ($evt.Properties.Count -ge 2) { $evt.Properties[1].Value } else { "Unknown" }
                    SourceIP        = if ($evt.Properties.Count -ge 1) { $evt.Properties[0].Value } else { "Unknown" }
                    BindType        = "Simple (Unsigned)"
                    SecurityRisk    = "High — credentials sent in cleartext or unsigned"
                }
            }
            if ($events2889) {
                Write-Host "    Event 2889 (unsigned binds): $($events2889.Count)" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "    Event 2889 query failed on $dc" -ForegroundColor DarkYellow
        }

        # Event ID 2887 — LDAP signing statistics (summary event)
        try {
            $events2887 = Get-WinEvent -ComputerName $dc -FilterHashtable @{
                LogName   = 'Directory Service'
                Id        = 2887
                StartTime = $startTime
            } -ErrorAction SilentlyContinue -MaxEvents 10

            foreach ($evt in $events2887) {
                $eventLogResults += [PSCustomObject]@{
                    DC              = $dc
                    EventId         = 2887
                    EventType       = "LDAP Signing Statistics"
                    TimeCreated     = $evt.TimeCreated
                    AccountName     = "N/A (summary event)"
                    SourceIP        = "N/A"
                    BindType        = "Summary"
                    SecurityRisk    = "Informational — unsigned bind count summary"
                    Message         = $evt.Message
                }
            }
        } catch {
            Write-Host "    Event 2887 query failed on $dc" -ForegroundColor DarkYellow
        }

        # Event ID 4624 LogonType 8 (NetworkCleartext — LDAP simple bind)
        try {
            $events4624 = Get-WinEvent -ComputerName $dc -FilterXml @"
<QueryList>
  <Query Id="0" Path="Security">
    <Select Path="Security">
      *[System[(EventID=4624) and TimeCreated[timediff(@SystemTime) &lt;= $($EventLogHours * 3600000)]]]
      and *[EventData[Data[@Name='LogonType']='8']]
    </Select>
  </Query>
</QueryList>
"@ -ErrorAction SilentlyContinue -MaxEvents 5000

            # Aggregate by account
            $accountGroups = $events4624 | Group-Object {
                $xml = [xml]$_.ToXml()
                $ns = New-Object Xml.XmlNamespaceManager($xml.NameTable)
                $ns.AddNamespace("e", "http://schemas.microsoft.com/win/2004/08/events/event")
                $xml.SelectSingleNode("//e:Data[@Name='TargetUserName']", $ns).'#text'
            }

            foreach ($group in $accountGroups) {
                $firstEvt = $group.Group[0]
                $xml = [xml]$firstEvt.ToXml()
                $ns = New-Object Xml.XmlNamespaceManager($xml.NameTable)
                $ns.AddNamespace("e", "http://schemas.microsoft.com/win/2004/08/events/event")
                $sourceIP = $xml.SelectSingleNode("//e:Data[@Name='IpAddress']", $ns).'#text'

                $eventLogResults += [PSCustomObject]@{
                    DC              = $dc
                    EventId         = 4624
                    EventType       = "Network Cleartext Logon (LDAP Simple Bind)"
                    TimeCreated     = $firstEvt.TimeCreated
                    AccountName     = $group.Name
                    SourceIP        = $sourceIP
                    BindType        = "Simple (Cleartext)"
                    SecurityRisk    = "Critical — password transmitted in cleartext"
                    BindCount       = $group.Count
                    FirstSeen       = ($group.Group | Sort-Object TimeCreated | Select-Object -First 1).TimeCreated
                    LastSeen        = ($group.Group | Sort-Object TimeCreated -Descending | Select-Object -First 1).TimeCreated
                }
            }

            if ($events4624) {
                Write-Host "    Event 4624/Type8 (cleartext logon): $($events4624.Count) events, $($accountGroups.Count) accounts" -ForegroundColor Yellow
            }
        } catch {
            Write-Host "    Event 4624 query failed on $dc" -ForegroundColor DarkYellow
        }
    }

    Write-Host "  Total LDAP bind events found: $($eventLogResults.Count)" -ForegroundColor $(if ($eventLogResults.Count -gt 0) { "Yellow" } else { "Green" })

    # ── Enrich heuristic accounts with event log data ──
    foreach ($evt in ($eventLogResults | Where-Object { $_.AccountName -and $_.AccountName -ne "N/A (summary event)" -and $_.AccountName -ne "Unknown" })) {
        $match = $ldapAccounts | Where-Object { $_.SamAccountName -eq $evt.AccountName }
        if ($match) {
            $match.DiscoveryMethod = "Confirmed (Event Log + Heuristic)"
            $match.BindType = $evt.BindType
            $match.BindSecurity = $evt.SecurityRisk
            $match.LDAPBindConfidence = [Math]::Min(100, $match.LDAPBindConfidence + 30)
            if ($match.LDAPBindConfidence -ge 80) { $match.RiskClassification = "Critical" }
        } else {
            # New account discovered via event log only
            $ldapAccounts += [PSCustomObject]@{
                SamAccountName       = $evt.AccountName
                DistinguishedName    = "Unknown (event log only)"
                DisplayName          = ""
                Description          = ""
                Enabled              = "Unknown"
                PasswordNeverExpires = "Unknown"
                HasSPN               = "Unknown"
                WhenCreated          = ""
                LastLogon            = $evt.LastSeen
                DaysSinceLogon       = -1
                PasswordLastSet      = ""
                PasswordAgeDays      = -1
                LogonCount           = $evt.BindCount
                AdminCount           = "Unknown"
                MemberOfCount        = -1
                DiscoveryMethod      = "Event Log Only"
                LDAPBindConfidence   = 95
                RiskClassification   = "Critical"
                BindType             = $evt.BindType
                BindSecurity         = $evt.SecurityRisk
                SourceApplication    = "Source IP: $($evt.SourceIP)"
                MigrationTarget      = "TBD"
                RemediationPriority  = 0
            }
        }
    }
} else {
    Write-Host "  Skipped (use -IncludeDCLogs to enable event log analysis)" -ForegroundColor Gray
    Write-Host "  NOTE: Event log analysis dramatically improves accuracy" -ForegroundColor DarkYellow
}

# ═══════════════════════════════════════════════════════════════
# SECTION 3: Cross-Reference with D1.1 Service Account Scan
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/5] Cross-referencing with D1.1 service account scan..." -ForegroundColor Yellow

if ($D1InputFile -and (Test-Path $D1InputFile)) {
    $d1Data = Get-Content -Path $D1InputFile -Raw | ConvertFrom-Json
    $enriched = 0

    foreach ($acct in $ldapAccounts) {
        $d1Match = $d1Data.ServiceAccounts | Where-Object { $_.SamAccountName -eq $acct.SamAccountName }
        if ($d1Match) {
            $acct | Add-Member -NotePropertyName "D1RiskScore" -NotePropertyValue $d1Match.RiskScore -Force
            $acct | Add-Member -NotePropertyName "D1MigrationTarget" -NotePropertyValue $d1Match.MigrationTarget -Force
            $acct | Add-Member -NotePropertyName "D1IsGMSA" -NotePropertyValue $d1Match.IsGMSA -Force
            $enriched++
        }
    }
    Write-Host "  Enriched $enriched accounts from D1.1 data" -ForegroundColor Green
} else {
    Write-Host "  No D1.1 input file — skipping cross-reference" -ForegroundColor Gray
}

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Migration Target Assignment
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/5] Assigning migration targets..." -ForegroundColor Yellow

foreach ($acct in $ldapAccounts) {
    # Assign remediation priority (1 = highest)
    $priority = switch ($acct.RiskClassification) {
        "Critical" { 1 }
        "High"     { 2 }
        "Medium"   { 3 }
        "Low"      { 4 }
        default    { 5 }
    }

    # Boost priority for cleartext binds
    if ($acct.BindSecurity -match "cleartext|unsigned") {
        $priority = [Math]::Max(1, $priority - 1)
    }

    $acct.RemediationPriority = $priority

    # Assign migration target based on pattern analysis
    $nameLC = ($acct.SamAccountName + " " + $acct.Description).ToLower()

    if ($nameLC -match "sync|provision|connector|hr|workday|oracle|scim") {
        $acct.MigrationTarget = "API-Driven Inbound Provisioning (ADR-003) — replace LDAP sync with Graph API /bulkUpload"
    }
    elseif ($nameLC -match "scan|monitor|audit|inventory|discovery") {
        $acct.MigrationTarget = "Managed Identity or Service Principal with Graph API read permissions — replace LDAP queries with Graph"
    }
    elseif ($nameLC -match "backup|veeam|commvault|dpm") {
        $acct.MigrationTarget = "Managed Identity for Azure-hosted backup, or Service Principal for on-prem — reduce to minimum Graph API permissions"
    }
    elseif ($nameLC -match "print|printer") {
        $acct.MigrationTarget = "Universal Print — eliminate LDAP dependency for print management"
    }
    elseif ($nameLC -match "email|smtp|exchange|mail") {
        $acct.MigrationTarget = "Modern Authentication (OAuth 2.0) for Exchange Online — eliminate LDAP address book queries"
    }
    elseif ($nameLC -match "vpn|radius|nps|nac") {
        $acct.MigrationTarget = "Entra ID with RADIUS proxy or certificate-based auth — complex migration, retain temporarily"
    }
    elseif ($acct.MigrationTarget -eq "TBD" -or $acct.MigrationTarget -eq "TBD — requires application owner identification") {
        $acct.MigrationTarget = "Requires investigation — identify application owner, determine if LDAP queries can be replaced with Graph API"
    }
}

$priorityCounts = $ldapAccounts | Group-Object RemediationPriority | Sort-Object Name
foreach ($p in $priorityCounts) {
    Write-Host "  Priority $($p.Name): $($p.Count) accounts" -ForegroundColor $(if ($p.Name -le 2) { "Yellow" } else { "Green" })
}

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Export Results
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/5] Exporting results..." -ForegroundColor Yellow

$outPrefix = "UIAO_Spec3_D1.9_LDAPBindAccountInventory_${domain}_${timestamp}"

$summary = @{
    TotalLDAPBindAccounts     = $ldapAccounts.Count
    ConfirmedByEventLog       = @($ldapAccounts | Where-Object { $_.DiscoveryMethod -match "Event Log" }).Count
    HeuristicOnly             = @($ldapAccounts | Where-Object { $_.DiscoveryMethod -match "Heuristic" -and $_.DiscoveryMethod -notmatch "Event Log" }).Count
    RiskDistribution          = @{
        Critical = @($ldapAccounts | Where-Object { $_.RiskClassification -eq "Critical" }).Count
        High     = @($ldapAccounts | Where-Object { $_.RiskClassification -eq "High" }).Count
        Medium   = @($ldapAccounts | Where-Object { $_.RiskClassification -eq "Medium" }).Count
        Low      = @($ldapAccounts | Where-Object { $_.RiskClassification -eq "Low" }).Count
    }
    CleartextBindsDetected    = @($eventLogResults | Where-Object { $_.BindType -match "Cleartext" }).Count
    UnsignedBindsDetected     = @($eventLogResults | Where-Object { $_.BindType -match "Unsigned" }).Count
    EventLogAnalysis          = $IncludeDCLogs.IsPresent
    EventLogHoursAnalyzed     = if ($IncludeDCLogs) { $EventLogHours } else { 0 }
    DCsScanned                = if ($IncludeDCLogs) { $dcs.Count } else { 0 }
    D1CrossReference          = [bool]$D1InputFile
}

$results = @{
    Metadata = @{
        GeneratedAt = (Get-Date -Format "o")
        Generator   = "Spec3-D1.9-Get-LDAPBindAccountInventory.ps1"
        UIAORef     = "UIAO_136 Spec 3, Phase 1, D1.9"
        ADRRef      = @("ADR-003", "ADR-004")
        Domain      = $domain
    }
    Summary          = $summary
    LDAPBindAccounts = $ldapAccounts
    EventLogResults  = $eventLogResults
}

# ── JSON ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV (account inventory) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_accounts.csv"
$csvData = foreach ($a in $ldapAccounts) {
    [PSCustomObject]@{
        SamAccountName       = $a.SamAccountName
        DisplayName          = $a.DisplayName
        Description          = $a.Description
        Enabled              = $a.Enabled
        PasswordNeverExpires = $a.PasswordNeverExpires
        PasswordAgeDays      = $a.PasswordAgeDays
        DaysSinceLogon       = $a.DaysSinceLogon
        DiscoveryMethod      = $a.DiscoveryMethod
        LDAPBindConfidence   = $a.LDAPBindConfidence
        RiskClassification   = $a.RiskClassification
        BindType             = $a.BindType
        BindSecurity         = $a.BindSecurity
        SourceApplication    = $a.SourceApplication
        MigrationTarget      = $a.MigrationTarget
        RemediationPriority  = $a.RemediationPriority
    }
}
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $csvPath" -ForegroundColor Green

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " LDAP BIND ACCOUNT INVENTORY — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Total LDAP Bind Accounts:    $($summary.TotalLDAPBindAccounts)" -ForegroundColor White
Write-Host "  Confirmed (Event Log):       $($summary.ConfirmedByEventLog)" -ForegroundColor $(if ($summary.ConfirmedByEventLog -gt 0) { "Green" } else { "Gray" })
Write-Host "  Heuristic Only:              $($summary.HeuristicOnly)" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Risk Distribution:" -ForegroundColor Cyan
if ($summary.RiskDistribution.Critical -gt 0) { Write-Host "    CRITICAL: $($summary.RiskDistribution.Critical)" -ForegroundColor Red }
if ($summary.RiskDistribution.High -gt 0) { Write-Host "    HIGH:     $($summary.RiskDistribution.High)" -ForegroundColor Yellow }
if ($summary.RiskDistribution.Medium -gt 0) { Write-Host "    MEDIUM:   $($summary.RiskDistribution.Medium)" -ForegroundColor DarkYellow }
if ($summary.RiskDistribution.Low -gt 0) { Write-Host "    LOW:      $($summary.RiskDistribution.Low)" -ForegroundColor Green }
Write-Host ""
if ($summary.CleartextBindsDetected -gt 0) {
    Write-Host "  ⚠ CRITICAL: $($summary.CleartextBindsDetected) cleartext LDAP binds detected!" -ForegroundColor Red
    Write-Host "    Passwords are being transmitted in plaintext to DCs" -ForegroundColor Red
}
if ($summary.UnsignedBindsDetected -gt 0) {
    Write-Host "  ⚠ WARNING: $($summary.UnsignedBindsDetected) unsigned LDAP binds detected" -ForegroundColor Yellow
}
Write-Host ""
Write-Host "  Migration Strategy:" -ForegroundColor Cyan
Write-Host "    1. Identify application owners for each LDAP bind account" -ForegroundColor White
Write-Host "    2. Replace LDAP queries with Microsoft Graph API calls" -ForegroundColor White
Write-Host "    3. Replace LDAP simple binds with OAuth 2.0 / certificate auth" -ForegroundColor White
Write-Host "    4. Enforce LDAP channel binding and signing as interim control" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-003 (API-Driven Provisioning) / ADR-004 (Workload Identity)" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan
