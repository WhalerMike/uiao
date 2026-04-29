<#
.SYNOPSIS
    UIAO Spec 3 — D1.7: SPN Collision Report
.DESCRIPTION
    Analyzes the Spec 1 D1.5 Kerberos SPN Inventory output to identify SPN
    collisions (duplicate SPNs registered to multiple accounts) that will cause
    Kerberos authentication failures during or after AD-to-Entra ID migration.

    Analysis passes:
    1. Duplicate SPN Detection — exact-match duplicates across all accounts
    2. Case-Insensitive Collision — SPNs that differ only by case (Kerberos is
       case-insensitive for service class and hostname)
    3. Port-Variant Collision — same service/host with and without explicit port
       (HTTP/server vs HTTP/server:443)
    4. Alias Collision — SPNs pointing to same host via CNAME/alias vs FQDN
       (requires DNS resolution — optional)
    5. Orphan SPN on Disabled Accounts — SPNs registered to disabled or stale
       accounts that shadow active registrations
    6. Cross-Object-Type Collision — same SPN on both computer object AND user
       object (service account)
    7. Forest-Wide Duplicate Check — if multi-domain, checks for cross-domain
       SPN collisions within the forest

    Per-collision output:
    - Collision type and severity (Critical / High / Medium / Low)
    - All accounts holding the duplicate SPN
    - Account status (enabled/disabled, last logon, object type)
    - Service class and target host
    - Remediation recommendation per ADR-004:
      * Remove orphan SPN from disabled account
      * Consolidate to single registration
      * Migrate to Workload Identity (Managed Identity / App Registration)
      * Retain for infrastructure services (DCs, ADFS)

    Outputs: JSON + CSV (collision inventory) + CSV (remediation plan) + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.7
         ADR-004 (Workload Identity Federation as Default)
         Consumes: Spec1-D1.5 SPN Inventory JSON
         Feeds: D2.1 (Target State Architecture), D2.3 (Migration Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D5InputFile
    Path to Spec1-D1.5 Kerberos SPN Inventory JSON. If omitted, performs
    live AD query for SPNs (requires AD connectivity).
.PARAMETER DomainController
    Target a specific DC for live query. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN) for live query.
.PARAMETER ResolveDNS
    If set, performs DNS resolution to detect alias collisions.
.PARAMETER IncludeForestWide
    If set, queries all domains in the forest for cross-domain collisions.
.EXAMPLE
    .\Spec3-D1.7-Get-SPNCollisionReport.ps1 -D5InputFile .\output\UIAO_Spec1_D1.5_SPNInventory_contoso.com_20260428.json
    .\Spec3-D1.7-Get-SPNCollisionReport.ps1 -ResolveDNS -IncludeForestWide
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for live query mode
    Requires: D1.5 JSON for enriched analysis mode
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D5InputFile,
    [string]$DomainController,
    [string]$SearchBase,
    [switch]$ResolveDNS,
    [switch]$IncludeForestWide
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.7: SPN Collision Report" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-004" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Load or Query SPN Data
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/6] Loading SPN data..." -ForegroundColor Yellow

$spnRecords = @()

if ($D5InputFile) {
    # ── Consume D1.5 output ──
    if (-not (Test-Path $D5InputFile)) {
        Write-Error "D1.5 input file not found: $D5InputFile"
        return
    }
    $d5Data = Get-Content -Path $D5InputFile -Raw | ConvertFrom-Json
    Write-Host "  Loaded D1.5 data: $($d5Data.Summary.TotalSPNs) SPNs from $($d5Data.Summary.TotalObjects) objects" -ForegroundColor Green

    # Extract SPN records from D1.5 format
    foreach ($obj in $d5Data.SPNInventory) {
        foreach ($spn in $obj.SPNs) {
            $spnRecords += [PSCustomObject]@{
                SPN              = $spn.RawSPN
                ServiceClass     = $spn.ServiceClass
                Hostname         = $spn.Hostname
                Port             = $spn.Port
                InstanceName     = $spn.InstanceName
                AccountName      = $obj.SamAccountName
                AccountDN        = $obj.DistinguishedName
                ObjectType       = $obj.ObjectClass
                Enabled          = $obj.Enabled
                LastLogon        = $obj.LastLogonTimestamp
                Domain           = $obj.Domain
                Source           = "D1.5 Import"
            }
        }
    }
} else {
    # ── Live AD query ──
    if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
        Write-Error "ActiveDirectory module not found. Install RSAT or provide -D5InputFile."
        return
    }
    Import-Module ActiveDirectory -ErrorAction Stop

    $adParams = @{
        Filter     = "servicePrincipalName -like '*'"
        Properties = @('servicePrincipalName', 'samAccountName', 'distinguishedName',
                       'objectClass', 'enabled', 'lastLogonTimestamp', 'userAccountControl',
                       'pwdLastSet', 'description')
    }
    if ($DomainController) { $adParams['Server'] = $DomainController }
    if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

    $domain = (Get-ADDomain).DNSRoot

    Write-Host "  Querying AD for objects with SPNs..." -ForegroundColor DarkYellow

    # Query both computer and user objects
    $adObjects = @()
    $adObjects += Get-ADComputer @adParams
    $adParams['Filter'] = "servicePrincipalName -like '*'"
    $adObjects += Get-ADUser @adParams

    Write-Host "  Found $($adObjects.Count) objects with SPNs" -ForegroundColor Green

    foreach ($obj in $adObjects) {
        $objectType = if ($obj.objectClass -contains 'computer') { 'computer' } else { 'user' }
        $isEnabled = if ($null -ne $obj.Enabled) { $obj.Enabled } else { $true }
        $lastLogon = if ($obj.lastLogonTimestamp) {
            [DateTime]::FromFileTime($obj.lastLogonTimestamp).ToString("yyyy-MM-dd")
        } else { "Never" }

        foreach ($spnRaw in $obj.servicePrincipalName) {
            $parsed = Parse-SPN $spnRaw
            $spnRecords += [PSCustomObject]@{
                SPN              = $spnRaw
                ServiceClass     = $parsed.ServiceClass
                Hostname         = $parsed.Hostname
                Port             = $parsed.Port
                InstanceName     = $parsed.InstanceName
                AccountName      = $obj.samAccountName
                AccountDN        = $obj.distinguishedName
                ObjectType       = $objectType
                Enabled          = $isEnabled
                LastLogon        = $lastLogon
                Domain           = $domain
                Source           = "Live AD Query"
            }
        }
    }

    # ── Forest-wide check ──
    if ($IncludeForestWide) {
        Write-Host "  Performing forest-wide SPN check..." -ForegroundColor DarkYellow
        try {
            $forest = Get-ADForest
            foreach ($childDomain in $forest.Domains) {
                if ($childDomain -eq $domain) { continue }
                Write-Host "    Scanning domain: $childDomain" -ForegroundColor DarkGray
                try {
                    $childDC = (Get-ADDomainController -DomainName $childDomain -Discover).HostName[0]
                    $childObjects = @()
                    $childObjects += Get-ADComputer -Filter "servicePrincipalName -like '*'" -Properties servicePrincipalName, samAccountName, distinguishedName, objectClass, enabled, lastLogonTimestamp -Server $childDC
                    $childObjects += Get-ADUser -Filter "servicePrincipalName -like '*'" -Properties servicePrincipalName, samAccountName, distinguishedName, objectClass, enabled, lastLogonTimestamp -Server $childDC

                    foreach ($obj in $childObjects) {
                        $objectType = if ($obj.objectClass -contains 'computer') { 'computer' } else { 'user' }
                        foreach ($spnRaw in $obj.servicePrincipalName) {
                            $parsed = Parse-SPN $spnRaw
                            $spnRecords += [PSCustomObject]@{
                                SPN              = $spnRaw
                                ServiceClass     = $parsed.ServiceClass
                                Hostname         = $parsed.Hostname
                                Port             = $parsed.Port
                                InstanceName     = $parsed.InstanceName
                                AccountName      = $obj.samAccountName
                                AccountDN        = $obj.distinguishedName
                                ObjectType       = $objectType
                                Enabled          = $obj.Enabled
                                LastLogon        = if ($obj.lastLogonTimestamp) { [DateTime]::FromFileTime($obj.lastLogonTimestamp).ToString("yyyy-MM-dd") } else { "Never" }
                                Domain           = $childDomain
                                Source           = "Forest-Wide Query"
                            }
                        }
                    }
                    Write-Host "    Found $($childObjects.Count) objects in $childDomain" -ForegroundColor DarkGreen
                } catch {
                    Write-Warning "    Could not query domain $childDomain : $_"
                }
            }
        } catch {
            Write-Warning "  Forest-wide check failed: $_"
        }
    }
}

Write-Host "  Total SPN records to analyze: $($spnRecords.Count)" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# HELPER: SPN Parser
# ═══════════════════════════════════════════════════════════════

function Parse-SPN {
    param([string]$RawSPN)

    $result = @{
        ServiceClass = ""
        Hostname     = ""
        Port         = $null
        InstanceName = $null
    }

    # SPN format: serviceclass/hostname[:port][/instancename]
    $parts = $RawSPN -split '/', 3
    if ($parts.Count -ge 1) { $result.ServiceClass = $parts[0] }
    if ($parts.Count -ge 2) {
        $hostPart = $parts[1]
        if ($hostPart -match '^(.+):(\d+)$') {
            $result.Hostname = $Matches[1]
            $result.Port = [int]$Matches[2]
        } else {
            $result.Hostname = $hostPart
        }
    }
    if ($parts.Count -ge 3) { $result.InstanceName = $parts[2] }

    return $result
}

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Exact Duplicate Detection
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/6] Detecting exact SPN duplicates..." -ForegroundColor Yellow

$collisions = @()

# Pass 1: Exact match (case-sensitive)
$spnGroups = $spnRecords | Group-Object -Property SPN | Where-Object { $_.Count -gt 1 }

foreach ($group in $spnGroups) {
    $accounts = $group.Group | ForEach-Object {
        @{
            AccountName = $_.AccountName
            AccountDN   = $_.AccountDN
            ObjectType  = $_.ObjectType
            Enabled     = $_.Enabled
            LastLogon   = $_.LastLogon
            Domain      = $_.Domain
        }
    }

    # Determine severity
    $enabledCount = ($group.Group | Where-Object { $_.Enabled -eq $true }).Count
    $severity = if ($enabledCount -gt 1) { "Critical" }
                elseif ($enabledCount -eq 1) { "High" }
                else { "Medium" }

    $collisions += [PSCustomObject]@{
        CollisionType    = "ExactDuplicate"
        SPN              = $group.Name
        ServiceClass     = $group.Group[0].ServiceClass
        Hostname         = $group.Group[0].Hostname
        DuplicateCount   = $group.Count
        EnabledAccounts  = $enabledCount
        Severity         = $severity
        Accounts         = $accounts
        Remediation      = Get-SPNRemediation -Type "ExactDuplicate" -Severity $severity -ServiceClass $group.Group[0].ServiceClass -Accounts $group.Group
    }
}

Write-Host "  Found $($spnGroups.Count) exact duplicate SPNs" -ForegroundColor $(if ($spnGroups.Count -gt 0) { "Red" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 3: Case-Insensitive Collision Detection
# ═══════════════════════════════════════════════════════════════

Write-Host "[3/6] Detecting case-insensitive collisions..." -ForegroundColor Yellow

# Kerberos is case-insensitive for service class and hostname
$ciGroups = $spnRecords | Group-Object -Property { $_.SPN.ToLower() } | Where-Object { $_.Count -gt 1 }

# Filter out exact duplicates (already caught)
$ciOnly = foreach ($group in $ciGroups) {
    $uniqueSPNs = $group.Group | Select-Object -ExpandProperty SPN -Unique
    if ($uniqueSPNs.Count -gt 1) {
        $group
    }
}

foreach ($group in $ciOnly) {
    $accounts = $group.Group | ForEach-Object {
        @{
            AccountName = $_.AccountName
            AccountDN   = $_.AccountDN
            ObjectType  = $_.ObjectType
            Enabled     = $_.Enabled
            LastLogon   = $_.LastLogon
            SPN         = $_.SPN
        }
    }

    $collisions += [PSCustomObject]@{
        CollisionType    = "CaseInsensitive"
        SPN              = ($group.Group | Select-Object -ExpandProperty SPN -Unique) -join " | "
        ServiceClass     = $group.Group[0].ServiceClass
        Hostname         = $group.Group[0].Hostname
        DuplicateCount   = $group.Count
        EnabledAccounts  = ($group.Group | Where-Object { $_.Enabled -eq $true }).Count
        Severity         = "High"
        Accounts         = $accounts
        Remediation      = "Standardize SPN casing. Kerberos is case-insensitive — mixed casing indicates registration inconsistency. Consolidate to lowercase service class per RFC 4120."
    }
}

$ciCount = @($ciOnly).Count
Write-Host "  Found $ciCount case-insensitive collisions" -ForegroundColor $(if ($ciCount -gt 0) { "Yellow" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Port-Variant Collision Detection
# ═══════════════════════════════════════════════════════════════

Write-Host "[4/6] Detecting port-variant collisions..." -ForegroundColor Yellow

# Group by ServiceClass + Hostname (ignoring port)
$portGroups = $spnRecords | Group-Object -Property { "$($_.ServiceClass.ToLower())/$($_.Hostname.ToLower())" } |
    Where-Object { $_.Count -gt 1 }

$portCollisions = foreach ($group in $portGroups) {
    $ports = $group.Group | Select-Object -ExpandProperty Port -Unique
    $hasNoPort = $ports -contains $null
    $hasPort = ($ports | Where-Object { $null -ne $_ }).Count -gt 0

    if ($hasNoPort -and $hasPort) {
        $group
    }
}

foreach ($group in $portCollisions) {
    $accounts = $group.Group | ForEach-Object {
        @{
            AccountName = $_.AccountName
            SPN         = $_.SPN
            Port        = $_.Port
            ObjectType  = $_.ObjectType
            Enabled     = $_.Enabled
        }
    }

    $collisions += [PSCustomObject]@{
        CollisionType    = "PortVariant"
        SPN              = ($group.Group | Select-Object -ExpandProperty SPN -Unique) -join " | "
        ServiceClass     = $group.Group[0].ServiceClass
        Hostname         = $group.Group[0].Hostname
        DuplicateCount   = $group.Count
        EnabledAccounts  = ($group.Group | Where-Object { $_.Enabled -eq $true }).Count
        Severity         = "Medium"
        Accounts         = $accounts
        Remediation      = "Review port-variant SPNs. HTTP/server and HTTP/server:443 may cause ambiguous Kerberos ticket requests. Standardize to explicit port or portless form based on application requirements."
    }
}

$pvCount = @($portCollisions).Count
Write-Host "  Found $pvCount port-variant collisions" -ForegroundColor $(if ($pvCount -gt 0) { "Yellow" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Cross-Object-Type Collision Detection
# ═══════════════════════════════════════════════════════════════

Write-Host "[5/6] Detecting cross-object-type collisions..." -ForegroundColor Yellow

$crossTypeGroups = $spnRecords | Group-Object -Property { $_.SPN.ToLower() } |
    Where-Object {
        $types = $_.Group | Select-Object -ExpandProperty ObjectType -Unique
        $types.Count -gt 1
    }

foreach ($group in $crossTypeGroups) {
    # Skip if already captured as exact duplicate
    $alreadyCaptured = $collisions | Where-Object { $_.SPN -eq $group.Group[0].SPN -and $_.CollisionType -eq "ExactDuplicate" }
    if ($alreadyCaptured) { continue }

    $accounts = $group.Group | ForEach-Object {
        @{
            AccountName = $_.AccountName
            AccountDN   = $_.AccountDN
            ObjectType  = $_.ObjectType
            Enabled     = $_.Enabled
            LastLogon   = $_.LastLogon
            SPN         = $_.SPN
        }
    }

    $collisions += [PSCustomObject]@{
        CollisionType    = "CrossObjectType"
        SPN              = $group.Group[0].SPN
        ServiceClass     = $group.Group[0].ServiceClass
        Hostname         = $group.Group[0].Hostname
        DuplicateCount   = $group.Count
        EnabledAccounts  = ($group.Group | Where-Object { $_.Enabled -eq $true }).Count
        Severity         = "Critical"
        Accounts         = $accounts
        Remediation      = "CRITICAL: Same SPN registered on both computer and user objects. Kerberos ticket encryption key will be ambiguous. Remove SPN from user/service account and use computer identity, OR migrate service to Managed Identity per ADR-004."
    }
}

$ctCount = @($crossTypeGroups).Count
Write-Host "  Found $ctCount cross-object-type collisions" -ForegroundColor $(if ($ctCount -gt 0) { "Red" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 5b: DNS Alias Collision Detection (Optional)
# ═══════════════════════════════════════════════════════════════

if ($ResolveDNS) {
    Write-Host "[5b/6] Performing DNS alias collision detection..." -ForegroundColor Yellow

    # Build hostname → IP mapping
    $hostnameMap = @{}
    $uniqueHosts = $spnRecords | Select-Object -ExpandProperty Hostname -Unique

    $resolved = 0
    $failed = 0
    foreach ($host in $uniqueHosts) {
        try {
            $dns = [System.Net.Dns]::GetHostAddresses($host)
            $ipList = ($dns | ForEach-Object { $_.IPAddressToString }) -join ","
            $hostnameMap[$host.ToLower()] = $ipList
            $resolved++
        } catch {
            $hostnameMap[$host.ToLower()] = "UNRESOLVED"
            $failed++
        }
    }

    Write-Host "  DNS resolved: $resolved, failed: $failed of $($uniqueHosts.Count) unique hosts" -ForegroundColor DarkGreen

    # Find SPNs pointing to same IP but different hostnames
    $ipGroups = $spnRecords | Where-Object {
        $hostnameMap[$_.Hostname.ToLower()] -and $hostnameMap[$_.Hostname.ToLower()] -ne "UNRESOLVED"
    } | Group-Object -Property { "$($_.ServiceClass.ToLower())/$($hostnameMap[$_.Hostname.ToLower()])" } |
        Where-Object {
            $hostnames = $_.Group | Select-Object -ExpandProperty Hostname -Unique
            $hostnames.Count -gt 1
        }

    foreach ($group in $ipGroups) {
        $hostnames = ($group.Group | Select-Object -ExpandProperty Hostname -Unique) -join ", "
        $accounts = $group.Group | ForEach-Object {
            @{
                AccountName = $_.AccountName
                SPN         = $_.SPN
                Hostname    = $_.Hostname
                ResolvedIP  = $hostnameMap[$_.Hostname.ToLower()]
            }
        }

        $collisions += [PSCustomObject]@{
            CollisionType    = "DNSAlias"
            SPN              = "$($group.Group[0].ServiceClass)/ → [$hostnames]"
            ServiceClass     = $group.Group[0].ServiceClass
            Hostname         = $hostnames
            DuplicateCount   = $group.Count
            EnabledAccounts  = ($group.Group | Where-Object { $_.Enabled -eq $true }).Count
            Severity         = "Medium"
            Accounts         = $accounts
            Remediation      = "Multiple hostnames ($hostnames) resolve to same IP. Kerberos may request ticket for wrong SPN. Consolidate to single canonical hostname or ensure each SPN is on the correct account."
        }
    }

    $aliasCount = @($ipGroups).Count
    Write-Host "  Found $aliasCount DNS alias collisions" -ForegroundColor $(if ($aliasCount -gt 0) { "Yellow" } else { "Green" })
}

# ═══════════════════════════════════════════════════════════════
# SECTION 6: Remediation Recommendations
# ═══════════════════════════════════════════════════════════════

function Get-SPNRemediation {
    param(
        [string]$Type,
        [string]$Severity,
        [string]$ServiceClass,
        $Accounts
    )

    $disabledAccounts = @($Accounts | Where-Object { $_.Enabled -eq $false })
    $enabledAccounts = @($Accounts | Where-Object { $_.Enabled -eq $true })

    $remediation = @()

    # If one account is disabled, remove SPN from disabled account
    if ($disabledAccounts.Count -gt 0 -and $enabledAccounts.Count -gt 0) {
        foreach ($da in $disabledAccounts) {
            $remediation += "Remove SPN from disabled account '$($da.AccountName)' — orphan registration shadowing active service"
        }
    }

    # Service-class specific guidance
    switch -Wildcard ($ServiceClass.ToLower()) {
        "http" {
            $remediation += "HTTP SPN: Consider migrating web application to Entra Application Proxy or direct OIDC/SAML — eliminates Kerberos SPN dependency entirely (ADR-004)"
        }
        "mssqlsvc" {
            $remediation += "MSSQLSvc SPN: Migrate SQL Server to Entra ID authentication (SQL 2022+ required). Use Managed Identity for application connections (ADR-004)"
        }
        "cifs" {
            $remediation += "CIFS SPN: Evaluate migration to Azure Files with Kerberos authentication or eliminate file share dependency"
        }
        "ldap" {
            if ($enabledAccounts | Where-Object { $_.AccountName -match 'DC\$|dc\$' }) {
                $remediation += "LDAP SPN on Domain Controller: Retain during coexistence — required for AD operations. Decommission with DC retirement"
            } else {
                $remediation += "LDAP SPN on non-DC: Investigate application LDAP dependency. Migrate to Graph API or SCIM (ADR-003)"
            }
        }
        "host" {
            $remediation += "HOST SPN: Standard computer identity SPN. If duplicate, likely stale computer object — verify and clean up"
        }
        default {
            $remediation += "Custom SPN ($ServiceClass): Requires per-application assessment. Target: Managed Identity or App Registration per ADR-004"
        }
    }

    # If multiple enabled accounts have same SPN — critical
    if ($enabledAccounts.Count -gt 1) {
        $remediation += "CRITICAL: $($enabledAccounts.Count) enabled accounts hold this SPN. Kerberos will use unpredictable encryption key. Immediate remediation required before migration"
    }

    return ($remediation -join "; ")
}

# ═══════════════════════════════════════════════════════════════
# OUTPUT: Assemble and Export
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[6/6] Exporting collision report..." -ForegroundColor Yellow

$domainLabel = if ($D5InputFile -and $d5Data.Metadata) { $d5Data.Metadata.Domain } else { $domain }
$outPrefix = "UIAO_Spec3_D1.7_SPNCollisionReport_${domainLabel}_${timestamp}"

# ── Summary statistics ──
$summary = @{
    TotalSPNRecords        = $spnRecords.Count
    UniqueSPNs             = ($spnRecords | Select-Object -ExpandProperty SPN -Unique).Count
    TotalCollisions        = $collisions.Count
    CriticalCollisions     = @($collisions | Where-Object { $_.Severity -eq "Critical" }).Count
    HighCollisions         = @($collisions | Where-Object { $_.Severity -eq "High" }).Count
    MediumCollisions       = @($collisions | Where-Object { $_.Severity -eq "Medium" }).Count
    LowCollisions          = @($collisions | Where-Object { $_.Severity -eq "Low" }).Count
    CollisionsByType       = @{
        ExactDuplicate   = @($collisions | Where-Object { $_.CollisionType -eq "ExactDuplicate" }).Count
        CaseInsensitive  = @($collisions | Where-Object { $_.CollisionType -eq "CaseInsensitive" }).Count
        PortVariant      = @($collisions | Where-Object { $_.CollisionType -eq "PortVariant" }).Count
        CrossObjectType  = @($collisions | Where-Object { $_.CollisionType -eq "CrossObjectType" }).Count
        DNSAlias         = @($collisions | Where-Object { $_.CollisionType -eq "DNSAlias" }).Count
    }
    DataSource             = if ($D5InputFile) { "D1.5 Import: $D5InputFile" } else { "Live AD Query" }
    DNSResolution          = $ResolveDNS.IsPresent
    ForestWide             = $IncludeForestWide.IsPresent
}

$results = @{
    Metadata = @{
        GeneratedAt = (Get-Date -Format "o")
        Generator   = "Spec3-D1.7-Get-SPNCollisionReport.ps1"
        UIAORef     = "UIAO_136 Spec 3, Phase 1, D1.7"
        ADRRef      = @("ADR-004")
        Domain      = $domainLabel
    }
    Summary    = $summary
    Collisions = $collisions
}

# ── JSON export ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV export (collision inventory) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_collisions.csv"
$csvData = foreach ($c in $collisions) {
    $accountNames = ($c.Accounts | ForEach-Object { $_.AccountName }) -join "; "
    [PSCustomObject]@{
        CollisionType   = $c.CollisionType
        SPN             = $c.SPN
        ServiceClass    = $c.ServiceClass
        Hostname        = $c.Hostname
        DuplicateCount  = $c.DuplicateCount
        EnabledAccounts = $c.EnabledAccounts
        Severity        = $c.Severity
        AccountNames    = $accountNames
        Remediation     = $c.Remediation
    }
}
if ($csvData) {
    $csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
    Write-Host "  CSV:  $csvPath" -ForegroundColor Green
} else {
    Write-Host "  CSV:  No collisions — clean SPN state!" -ForegroundColor Green
}

# ── CSV export (remediation plan) ──
$remCsvPath = Join-Path $OutputPath "${outPrefix}_remediation.csv"
$remData = foreach ($c in $collisions) {
    foreach ($acct in $c.Accounts) {
        [PSCustomObject]@{
            SPN             = $c.SPN
            Severity        = $c.Severity
            CollisionType   = $c.CollisionType
            AccountName     = $acct.AccountName
            ObjectType      = $acct.ObjectType
            Enabled         = $acct.Enabled
            LastLogon       = $acct.LastLogon
            Action          = if ($acct.Enabled -eq $false) { "REMOVE SPN (disabled account)" }
                              elseif ($c.CollisionType -eq "CrossObjectType" -and $acct.ObjectType -eq "user") { "MIGRATE to Managed Identity (ADR-004)" }
                              else { "INVESTIGATE — determine canonical SPN owner" }
            Remediation     = $c.Remediation
        }
    }
}
if ($remData) {
    $remData | Export-Csv -Path $remCsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "  CSV:  $remCsvPath" -ForegroundColor Green
}

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " SPN COLLISION REPORT — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Total SPN Records Analyzed:  $($summary.TotalSPNRecords)" -ForegroundColor White
Write-Host "  Unique SPNs:                 $($summary.UniqueSPNs)" -ForegroundColor White
Write-Host ""

if ($summary.TotalCollisions -eq 0) {
    Write-Host "  ✓ NO COLLISIONS DETECTED — Clean SPN state" -ForegroundColor Green
} else {
    Write-Host "  ⚠ COLLISIONS DETECTED:      $($summary.TotalCollisions)" -ForegroundColor Red
    Write-Host ""

    if ($summary.CriticalCollisions -gt 0) {
        Write-Host "    CRITICAL:  $($summary.CriticalCollisions)" -ForegroundColor Red
    }
    if ($summary.HighCollisions -gt 0) {
        Write-Host "    HIGH:      $($summary.HighCollisions)" -ForegroundColor Yellow
    }
    if ($summary.MediumCollisions -gt 0) {
        Write-Host "    MEDIUM:    $($summary.MediumCollisions)" -ForegroundColor DarkYellow
    }
    if ($summary.LowCollisions -gt 0) {
        Write-Host "    LOW:       $($summary.LowCollisions)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "  By Type:" -ForegroundColor White
    foreach ($type in $summary.CollisionsByType.GetEnumerator()) {
        if ($type.Value -gt 0) {
            $color = switch ($type.Key) {
                "ExactDuplicate"  { "Red" }
                "CrossObjectType" { "Red" }
                "CaseInsensitive" { "Yellow" }
                "PortVariant"     { "DarkYellow" }
                "DNSAlias"        { "DarkYellow" }
                default           { "White" }
            }
            Write-Host "    $($type.Key): $($type.Value)" -ForegroundColor $color
        }
    }

    # Top 5 critical collisions
    $topCritical = $collisions | Where-Object { $_.Severity -eq "Critical" } | Select-Object -First 5
    if ($topCritical) {
        Write-Host ""
        Write-Host "  Top Critical Collisions:" -ForegroundColor Red
        foreach ($c in $topCritical) {
            $acctList = ($c.Accounts | ForEach-Object { $_.AccountName }) -join ", "
            Write-Host "    [$($c.CollisionType)] $($c.SPN)" -ForegroundColor Red
            Write-Host "      Accounts: $acctList" -ForegroundColor DarkRed
        }
    }
}

Write-Host ""
Write-Host "  Migration Impact:" -ForegroundColor Cyan
Write-Host "    Critical collisions MUST be resolved before AD decommission" -ForegroundColor White
Write-Host "    High collisions should be resolved during Phase 2 planning" -ForegroundColor White
Write-Host "    Medium/Low collisions can be addressed during migration waves" -ForegroundColor White
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-004 (Workload Identity Federation as Default)" -ForegroundColor DarkCyan
Write-Host " Feeds: D2.1 (Target State Architecture)" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan
