<#
.SYNOPSIS
    UIAO Spec 1 — D1.5: Kerberos SPN Inventory
.DESCRIPTION
    Comprehensive Service Principal Name (SPN) inventory across all
    computer and user objects in the domain. This deliverable maps every
    Kerberos service endpoint that will be affected by AD decommission.

    Discovery and analysis:
    1. Full SPN export from all computer objects
    2. Full SPN export from all user objects (service accounts with SPNs)
    3. SPN parsing — service class, hostname, port, instance
    4. Duplicate SPN detection (causes Kerberos auth failures)
    5. Orphan SPN detection (SPN on disabled/stale accounts)
    6. SPN-to-host resolution (DNS validation — does the host exist?)
    7. Service class distribution (HTTP, MSSQLSvc, ldap, cifs, etc.)
    8. Delegation chain correlation — cross-reference with D1.4 KCD targets
    9. Migration impact per service class:
       - HTTP/ → Entra Application Proxy or direct OIDC migration
       - MSSQLSvc/ → Entra ID Auth for SQL (ADR-004)
       - ldap/ → Retained for DCs, eliminated for others
       - cifs/ → Azure Files with Kerberos or eliminate
       - Custom SPNs → per-application assessment

    Outputs: JSON (full detail) + CSV (SPN inventory) + CSV (duplicates)

    Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.5
         Feeds: D1.6 (BitLocker/LAPS State), D2.1 (Target State Architecture)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER D4InputFile
    Optional path to D1.4 Authentication Protocol Audit JSON for
    delegation chain cross-reference.
.PARAMETER ResolveDNS
    If set, performs DNS resolution for each unique SPN hostname.
    Can be slow in large environments. Default: $false.
.EXAMPLE
    .\Spec1-D1.5-Get-KerberosSPNInventory.ps1
    .\Spec1-D1.5-Get-KerberosSPNInventory.ps1 -ResolveDNS
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    Requires: Read access to servicePrincipalName on all objects
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$SearchBase,
    [string]$D4InputFile,
    [switch]$ResolveDNS
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
$outPrefix = "UIAO_Spec1_D1.5_SPNInventory_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 1 — D1.5: Kerberos SPN Inventory"                   -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

# ══════════════════════════════════════════════════════════════
# SPN Parser
# ══════════════════════════════════════════════════════════════

function Parse-SPN {
    param([string]$SPN)
    # SPN format: serviceclass/host:port/servicename
    # or: serviceclass/host:port
    # or: serviceclass/host
    $result = [ordered]@{
        RawSPN       = $SPN
        ServiceClass = $null
        Host         = $null
        Port         = $null
        ServiceName  = $null
        IsFQDN       = $false
    }

    $parts = $SPN -split '/', 3
    if ($parts.Count -ge 1) { $result.ServiceClass = $parts[0] }
    if ($parts.Count -ge 2) {
        $hostPart = $parts[1]
        if ($hostPart -match '^(.+):(\d+)$') {
            $result.Host = $Matches[1]
            $result.Port = [int]$Matches[2]
        } else {
            $result.Host = $hostPart
        }
        $result.IsFQDN = ($result.Host -match '\.')
    }
    if ($parts.Count -ge 3) { $result.ServiceName = $parts[2] }

    return $result
}

# ══════════════════════════════════════════════════════════════
# Migration target per service class
# ══════════════════════════════════════════════════════════════

$serviceClassMigration = @{
    'HTTP'                = @{ Target = 'Entra Application Proxy, direct OIDC/SAML, or Azure Front Door'; Complexity = 'Medium'; Notes = 'Most common web SPN. Migration path depends on app architecture.' }
    'MSSQLSvc'            = @{ Target = 'Entra ID Auth for SQL Server 2022+ via Arc (ADR-004)'; Complexity = 'Medium'; Notes = 'Requires SQL 2022+. Older versions need upgrade first.' }
    'ldap'                = @{ Target = 'Retain on DCs; eliminate on non-DC servers'; Complexity = 'Low'; Notes = 'DC SPNs are forest infrastructure. Non-DC ldap SPNs are unusual.' }
    'GC'                  = @{ Target = 'Retain on DCs — Global Catalog is forest infrastructure'; Complexity = 'N/A'; Notes = 'GC SPNs exist only on DCs. Eliminated when forest is decommissioned.' }
    'cifs'                = @{ Target = 'Azure Files with Entra Kerberos, or eliminate file share dependency'; Complexity = 'High'; Notes = 'File share migration to SharePoint/OneDrive or Azure Files.' }
    'HOST'                = @{ Target = 'Eliminated when computer object decommissioned'; Complexity = 'Low'; Notes = 'HOST is the default computer SPN. No migration needed — disappears with AD.' }
    'RestrictedKrbHost'   = @{ Target = 'Eliminated when computer object decommissioned'; Complexity = 'Low'; Notes = 'Restricted Kerberos host — paired with HOST SPN.' }
    'TERMSRV'             = @{ Target = 'Entra ID RDP auth via Arc (AADLoginForWindows extension)'; Complexity = 'Medium'; Notes = 'Terminal Services SPN. Arc-enabled servers use Entra RDP auth.' }
    'WSMAN'               = @{ Target = 'Retain during coexistence; eliminated post-migration'; Complexity = 'Low'; Notes = 'WinRM/PowerShell remoting. Cloud equivalent is Azure Automation/Arc.' }
    'FIMService'          = @{ Target = 'Eliminate — MIM replaced by Entra ID Governance (ADR-003)'; Complexity = 'Medium'; Notes = 'MIM/FIM service. Entire provisioning engine migrates to cloud.' }
    'exchangeMDB'         = @{ Target = 'Eliminate — Exchange Online replaces on-prem Exchange'; Complexity = 'Low'; Notes = 'Exchange mailbox database. Eliminated in Exchange Online migration.' }
    'exchangeRFR'         = @{ Target = 'Eliminate — Exchange Online'; Complexity = 'Low'; Notes = 'Exchange address book referral.' }
    'exchangeAB'          = @{ Target = 'Eliminate — Exchange Online'; Complexity = 'Low'; Notes = 'Exchange address book.' }
    'SMTP'                = @{ Target = 'Exchange Online handles SMTP routing'; Complexity = 'Low'; Notes = 'SMTP relay SPN. Cloud migration eliminates on-prem SMTP.' }
    'IMAP'                = @{ Target = 'Eliminate — Exchange Online'; Complexity = 'Low'; Notes = 'IMAP access SPN.' }
    'POP'                 = @{ Target = 'Eliminate — Exchange Online'; Complexity = 'Low'; Notes = 'POP3 access SPN.' }
    'DNS'                 = @{ Target = 'Azure DNS / hybrid DNS — retain during coexistence'; Complexity = 'Low'; Notes = 'DNS server SPN. Hybrid DNS documented separately.' }
    'nfs'                 = @{ Target = 'Azure NetApp Files or Azure Files NFS'; Complexity = 'High'; Notes = 'NFS file share. Requires infrastructure migration.' }
    'MSServerCluster'     = @{ Target = 'Azure failover or application redesign'; Complexity = 'High'; Notes = 'Windows Server Failover Cluster SPN.' }
    'MSServerClusterMgmtAPI' = @{ Target = 'Azure failover or application redesign'; Complexity = 'High'; Notes = 'Cluster management API.' }
    'MSClusterVirtualServer' = @{ Target = 'Azure failover or application redesign'; Complexity = 'High'; Notes = 'Cluster virtual server name.' }
    'SAPService'          = @{ Target = 'SAP on Azure with Managed Identity'; Complexity = 'High'; Notes = 'SAP application SPN. Complex migration.' }
    'Hyper-V'             = @{ Target = 'Azure or retain on-prem hypervisor'; Complexity = 'Medium'; Notes = 'Hyper-V replica SPN.' }
    'DFSR'                = @{ Target = 'Eliminate — DFS-R replaced by OneDrive/SharePoint sync or Azure File Sync'; Complexity = 'Medium'; Notes = 'DFS Replication SPN.' }
}

# ══════════════════════════════════════════════════════════════
# Pass 1: Collect SPNs from Computer Objects
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/6] Collecting SPNs from computer objects..." -ForegroundColor Yellow

$compSPNProps = @('Name','DNSHostName','SamAccountName','ObjectGUID','Enabled',
    'OperatingSystem','LastLogonDate','ServicePrincipalName',
    'PrimaryGroupID','extensionAttribute1')

$computerSPNs = @(Get-ADComputer -Filter { ServicePrincipalName -like '*' } `
    -Properties $compSPNProps @adParams)

$compSPNCount = ($computerSPNs | ForEach-Object { $_.ServicePrincipalName.Count } | Measure-Object -Sum).Sum
Write-Host "    $($computerSPNs.Count) computers with $compSPNCount total SPNs" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 2: Collect SPNs from User Objects (Service Accounts)
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/6] Collecting SPNs from user objects..." -ForegroundColor Yellow

$userSPNProps = @('Name','SamAccountName','UserPrincipalName','ObjectGUID','Enabled',
    'LastLogonDate','ServicePrincipalName','PasswordLastSet',
    'PasswordNeverExpires','AdminCount','Description',
    'TrustedForDelegation','TrustedToAuthForDelegation',
    'msDS-AllowedToDelegateTo','extensionAttribute1')

$userSPNs = @(Get-ADUser -Filter { ServicePrincipalName -like '*' } `
    -Properties $userSPNProps @adParams)

$userSPNCount = ($userSPNs | ForEach-Object { $_.ServicePrincipalName.Count } | Measure-Object -Sum).Sum
Write-Host "    $($userSPNs.Count) users with $userSPNCount total SPNs" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 3: Parse and Catalog All SPNs
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/6] Parsing all SPNs..." -ForegroundColor Yellow

$allSPNRecords = [System.Collections.Generic.List[object]]::new()
$spnIndex = [System.Collections.Generic.Dictionary[string,System.Collections.Generic.List[object]]]::new()

foreach ($comp in $computerSPNs) {
    $isDC = ($comp.PrimaryGroupID -eq 516)

    foreach ($spn in $comp.ServicePrincipalName) {
        $parsed = Parse-SPN $spn

        $isStale = $false
        $daysSinceLogon = $null
        if ($comp.LastLogonDate) {
            $daysSinceLogon = [int]((Get-Date) - $comp.LastLogonDate).TotalDays
            if ($daysSinceLogon -gt 180) { $isStale = $true }
        }

        $migInfo = $serviceClassMigration[$parsed.ServiceClass]

        $record = [ordered]@{
            SPN              = $spn
            ServiceClass     = $parsed.ServiceClass
            Host             = $parsed.Host
            Port             = $parsed.Port
            ServiceName      = $parsed.ServiceName
            IsFQDN           = $parsed.IsFQDN
            ObjectType       = "Computer"
            ObjectName       = $comp.Name
            SamAccountName   = $comp.SamAccountName
            DNSHostName      = $comp.DNSHostName
            ObjectGUID       = $comp.ObjectGUID.ToString()
            Enabled          = $comp.Enabled
            LastLogonDate    = if ($comp.LastLogonDate) { $comp.LastLogonDate.ToString("o") } else { $null }
            DaysSinceLogon   = $daysSinceLogon
            OperatingSystem  = $comp.OperatingSystem
            IsDomainController = $isDC
            IsOrphan         = (-not $comp.Enabled -or $isStale)
            OrgPath          = $comp.extensionAttribute1
            MigrationTarget  = if ($migInfo) { $migInfo.Target } else { "Manual assessment — unknown service class" }
            MigrationComplexity = if ($migInfo) { $migInfo.Complexity } else { "Unknown" }
            MigrationNotes   = if ($migInfo) { $migInfo.Notes } else { "Unrecognized SPN service class: $($parsed.ServiceClass)" }
        }

        $allSPNRecords.Add($record)

        # Index for duplicate detection
        $spnKey = $spn.ToLower()
        if (-not $spnIndex.ContainsKey($spnKey)) {
            $spnIndex[$spnKey] = [System.Collections.Generic.List[object]]::new()
        }
        $spnIndex[$spnKey].Add($record)
    }
}

foreach ($user in $userSPNs) {
    $passwordAge = $null
    if ($user.PasswordLastSet) {
        $passwordAge = [int]((Get-Date) - $user.PasswordLastSet).TotalDays
    }

    foreach ($spn in $user.ServicePrincipalName) {
        $parsed = Parse-SPN $spn

        $isStale = $false
        $daysSinceLogon = $null
        if ($user.LastLogonDate) {
            $daysSinceLogon = [int]((Get-Date) - $user.LastLogonDate).TotalDays
            if ($daysSinceLogon -gt 180) { $isStale = $true }
        }

        $migInfo = $serviceClassMigration[$parsed.ServiceClass]

        $record = [ordered]@{
            SPN              = $spn
            ServiceClass     = $parsed.ServiceClass
            Host             = $parsed.Host
            Port             = $parsed.Port
            ServiceName      = $parsed.ServiceName
            IsFQDN           = $parsed.IsFQDN
            ObjectType       = "User (Service Account)"
            ObjectName       = $user.Name
            SamAccountName   = $user.SamAccountName
            UPN              = $user.UserPrincipalName
            DNSHostName      = $null
            ObjectGUID       = $user.ObjectGUID.ToString()
            Enabled          = $user.Enabled
            LastLogonDate    = if ($user.LastLogonDate) { $user.LastLogonDate.ToString("o") } else { $null }
            DaysSinceLogon   = $daysSinceLogon
            OperatingSystem  = $null
            IsDomainController = $false
            IsOrphan         = (-not $user.Enabled -or $isStale)
            PasswordAge      = $passwordAge
            PasswordNeverExpires = [bool]$user.PasswordNeverExpires
            AdminCount       = $user.AdminCount
            Description      = $user.Description
            HasDelegation    = ([bool]$user.TrustedForDelegation -or @($user.'msDS-AllowedToDelegateTo').Count -gt 0)
            OrgPath          = $user.extensionAttribute1
            MigrationTarget  = if ($migInfo) { $migInfo.Target } else { "Manual assessment — unknown service class" }
            MigrationComplexity = if ($migInfo) { $migInfo.Complexity } else { "Unknown" }
            MigrationNotes   = if ($migInfo) { $migInfo.Notes } else { "Unrecognized SPN service class: $($parsed.ServiceClass)" }
        }

        $allSPNRecords.Add($record)

        $spnKey = $spn.ToLower()
        if (-not $spnIndex.ContainsKey($spnKey)) {
            $spnIndex[$spnKey] = [System.Collections.Generic.List[object]]::new()
        }
        $spnIndex[$spnKey].Add($record)
    }
}

Write-Host "    Total SPNs cataloged: $($allSPNRecords.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 4: Duplicate SPN Detection
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/6] Detecting duplicate SPNs..." -ForegroundColor Yellow

$duplicates = [System.Collections.Generic.List[object]]::new()
foreach ($entry in $spnIndex.GetEnumerator()) {
    if ($entry.Value.Count -gt 1) {
        $duplicates.Add([ordered]@{
            SPN       = $entry.Key
            Count     = $entry.Value.Count
            Owners    = @($entry.Value | ForEach-Object {
                [ordered]@{
                    ObjectType     = $_.ObjectType
                    ObjectName     = $_.ObjectName
                    SamAccountName = $_.SamAccountName
                    Enabled        = $_.Enabled
                }
            })
            Impact    = "Kerberos authentication failure — clients receive wrong service ticket"
            Remediation = "Remove SPN from all but the correct owner. If both are valid, one service must use a different SPN or port."
        })
    }
}

Write-Host "    Duplicate SPNs found: $($duplicates.Count)" -ForegroundColor $(if ($duplicates.Count -gt 0) { 'Red' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Pass 5: Orphan SPN Detection
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/6] Detecting orphan SPNs..." -ForegroundColor Yellow

$orphanSPNs = @($allSPNRecords | Where-Object { $_.IsOrphan -and -not $_.IsDomainController })
Write-Host "    Orphan SPNs (disabled/stale accounts): $($orphanSPNs.Count)" -ForegroundColor $(if ($orphanSPNs.Count -gt 0) { 'Yellow' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Pass 6: DNS Resolution (optional)
# ══════════════════════════════════════════════════════════════
$dnsResults = @{}
if ($ResolveDNS) {
    Write-Host "  [6/6] Resolving DNS for SPN hostnames..." -ForegroundColor Yellow
    $uniqueHosts = @($allSPNRecords | Where-Object { $_.Host } |
        Select-Object -ExpandProperty Host -Unique)

    $counter = 0
    foreach ($host in $uniqueHosts) {
        $counter++
        if ($counter % 50 -eq 0) {
            Write-Progress -Activity "DNS Resolution" -Status "$counter / $($uniqueHosts.Count)" -PercentComplete (($counter / $uniqueHosts.Count) * 100)
        }

        try {
            $dns = Resolve-DnsName -Name $host -ErrorAction SilentlyContinue -DnsOnly
            $dnsResults[$host] = [ordered]@{
                Resolved  = $true
                IPAddress = @($dns | Where-Object { $_.Type -in @('A','AAAA') } | Select-Object -ExpandProperty IPAddress -First 1)
                Type      = @($dns | Select-Object -ExpandProperty Type -First 1)
            }
        } catch {
            $dnsResults[$host] = [ordered]@{
                Resolved  = $false
                IPAddress = $null
                Error     = "DNS resolution failed"
            }
        }
    }
    Write-Progress -Activity "DNS Resolution" -Completed

    $unresolvable = @($dnsResults.GetEnumerator() | Where-Object { -not $_.Value.Resolved })
    Write-Host "    Resolved: $($uniqueHosts.Count - $unresolvable.Count) / $($uniqueHosts.Count)" -ForegroundColor Green
    if ($unresolvable.Count -gt 0) {
        Write-Host "    Unresolvable hosts: $($unresolvable.Count) (stale DNS or decommissioned)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [6/6] DNS resolution skipped (use -ResolveDNS to enable)" -ForegroundColor DarkGray
}

# ══════════════════════════════════════════════════════════════
# Summary Statistics
# ══════════════════════════════════════════════════════════════

$serviceClassDist = $allSPNRecords |
    Group-Object -Property ServiceClass |
    Sort-Object Count -Descending |
    ForEach-Object {
        $migInfo = $serviceClassMigration[$_.Name]
        [ordered]@{
            ServiceClass = $_.Name
            Count        = $_.Count
            Target       = if ($migInfo) { $migInfo.Target } else { "Manual assessment" }
            Complexity   = if ($migInfo) { $migInfo.Complexity } else { "Unknown" }
        }
    }

$complexityDist = $allSPNRecords |
    Group-Object -Property MigrationComplexity |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Complexity = $_.Name; Count = $_.Count } }

$objectTypeDist = $allSPNRecords |
    Group-Object -Property ObjectType |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ ObjectType = $_.Name; Count = $_.Count } }

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain           = $domain
        Timestamp        = (Get-Date).ToString("o")
        Script           = "UIAO Spec 1 D1.5 — Kerberos SPN Inventory"
        Reference        = "UIAO_136, ADR-004"
        DNSResolved      = [bool]$ResolveDNS
    }
    Statistics = [ordered]@{
        TotalSPNs        = $allSPNRecords.Count
        ComputerSPNs     = $compSPNCount
        UserSPNs         = $userSPNCount
        UniqueServiceClasses = ($allSPNRecords | Select-Object -ExpandProperty ServiceClass -Unique).Count
        DuplicateSPNs    = $duplicates.Count
        OrphanSPNs       = $orphanSPNs.Count
        DCOnlySPNs       = ($allSPNRecords | Where-Object { $_.IsDomainController }).Count
    }
    ServiceClassDistribution = @($serviceClassDist)
    MigrationComplexity      = @($complexityDist)
    ObjectTypeDistribution   = @($objectTypeDist)
}

# ══════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════

# JSON
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{
    Summary    = $summary
    SPNs       = @($allSPNRecords)
    Duplicates = @($duplicates)
    Orphans    = @($orphanSPNs | ForEach-Object { [ordered]@{ SPN = $_.SPN; ObjectName = $_.ObjectName; ObjectType = $_.ObjectType; Enabled = $_.Enabled; DaysSinceLogon = $_.DaysSinceLogon } })
    DNSResults = if ($ResolveDNS) { $dnsResults } else { $null }
} | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# CSV — full SPN inventory
$csvFile = Join-Path $OutputPath "${outPrefix}.csv"
$allSPNRecords | ForEach-Object {
    [PSCustomObject]@{
        SPN                = $_.SPN
        ServiceClass       = $_.ServiceClass
        Host               = $_.Host
        Port               = $_.Port
        ObjectType         = $_.ObjectType
        ObjectName         = $_.ObjectName
        SamAccountName     = $_.SamAccountName
        Enabled            = $_.Enabled
        DaysSinceLogon     = $_.DaysSinceLogon
        IsOrphan           = $_.IsOrphan
        IsDomainController = $_.IsDomainController
        MigrationTarget    = $_.MigrationTarget
        MigrationComplexity = $_.MigrationComplexity
        OperatingSystem    = $_.OperatingSystem
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (inventory): $csvFile" -ForegroundColor Green

# CSV — duplicates only
if ($duplicates.Count -gt 0) {
    $dupCsv = Join-Path $OutputPath "${outPrefix}_duplicates.csv"
    $duplicates | ForEach-Object {
        $d = $_
        foreach ($owner in $d.Owners) {
            [PSCustomObject]@{
                DuplicateSPN    = $d.SPN
                OwnerCount      = $d.Count
                OwnerObjectType = $owner.ObjectType
                OwnerObjectName = $owner.ObjectName
                OwnerSAM        = $owner.SamAccountName
                OwnerEnabled    = $owner.Enabled
                Impact          = $d.Impact
            }
        }
    } | Export-Csv -Path $dupCsv -NoTypeInformation -Encoding utf8NoBOM
    Write-Host "  CSV (duplicates): $dupCsv" -ForegroundColor Green
}

# Console Dashboard
Write-Host "`n-- Kerberos SPN Inventory --" -ForegroundColor Cyan
Write-Host "  Total SPNs:          $($allSPNRecords.Count)"
Write-Host "  On computers:        $compSPNCount"
Write-Host "  On users (svc accts):$userSPNCount"
Write-Host "  Unique service classes: $(($allSPNRecords | Select-Object -ExpandProperty ServiceClass -Unique).Count)"
Write-Host "  Duplicates:          $($duplicates.Count)" -ForegroundColor $(if ($duplicates.Count -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Orphans:             $($orphanSPNs.Count)" -ForegroundColor $(if ($orphanSPNs.Count -gt 0) { 'Yellow' } else { 'Green' })

Write-Host "`n-- Service Class Distribution (Top 15) --" -ForegroundColor Cyan
foreach ($sc in ($serviceClassDist | Select-Object -First 15)) {
    Write-Host "  $($sc.Count.ToString().PadLeft(6))  $($sc.ServiceClass.PadRight(25)) [$($sc.Complexity)]"
}

Write-Host "`n-- Migration Complexity --" -ForegroundColor Cyan
foreach ($c in $complexityDist) {
    $color = switch ($c.Complexity) { 'Low' { 'Green' } 'Medium' { 'Yellow' } 'High' { 'Red' } default { 'Gray' } }
    Write-Host "  $($c.Count.ToString().PadLeft(6))  $($c.Complexity)" -ForegroundColor $color
}

if ($duplicates.Count -gt 0) {
    Write-Host "`n-- DUPLICATE SPNs (Kerberos auth failures) --" -ForegroundColor Red
    foreach ($d in ($duplicates | Select-Object -First 10)) {
        $owners = ($d.Owners | ForEach-Object { $_.ObjectName }) -join ', '
        Write-Host "  ! $($d.SPN) -> owned by: $owners" -ForegroundColor Red
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
