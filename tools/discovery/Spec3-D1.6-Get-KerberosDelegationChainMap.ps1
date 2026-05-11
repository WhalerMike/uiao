<#
.SYNOPSIS
    UIAO Spec 3 — D1.6: Kerberos Delegation Chain Map
.DESCRIPTION
    Correlates D1.4 (Authentication Protocol Audit) and D1.5 (SPN Inventory)
    outputs to build a complete Kerberos delegation chain graph — the full
    source → intermediary → target service dependency map that must be
    untangled before AD decommission.

    Analysis phases:
    1. Load D1.4 delegation data (KCD, RBCD, unconstrained, protocol transition)
    2. Load D1.5 SPN inventory (all service endpoints with parsed classes)
    3. Cross-reference: for every KCD entry, resolve the target SPN(s) to their
       hosting account and build a directed edge (source → target)
    4. For RBCD entries, build reverse edges (resource → trusted principal)
    5. Identify multi-hop chains (A delegates to B which delegates to C)
    6. Detect circular delegation (A → B → A — security risk)
    7. Identify orphan delegations (delegation to SPNs on disabled/stale accounts)
    8. Map each chain to its migration pathway:
       - KCD → App Proxy with SSO, or direct OIDC/SAML migration
       - RBCD → Managed Identity with RBAC
       - Unconstrained → CRITICAL — must eliminate before migration
       - Protocol transition → evaluate per-chain necessity
    9. Risk classification per chain:
       - Critical: unconstrained delegation, circular chains, admin-touching chains
       - High: multi-hop KCD chains, protocol transition
       - Medium: single-hop KCD to known services (SQL, HTTP, CIFS)
       - Low: KCD to services with direct cloud equivalents

    Outputs: JSON (full graph), CSV (chain inventory), CSV (critical findings),
             Markdown (chain visualization in text format)

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.6
         Feeds: D2.1 (Target State Architecture), D3.1 (Migration Runbook)
         Requires: D1.4 + D1.5 outputs (or can do standalone AD query)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D4InputFile
    Path to D1.4 Authentication Protocol Audit JSON.
.PARAMETER D5InputFile
    Path to D1.5 Kerberos SPN Inventory JSON.
.PARAMETER DomainController
    Target a specific DC for standalone mode. If omitted, uses auto-discovery.
.PARAMETER SearchBase
    Optional AD search base (DN).
.PARAMETER StandaloneMode
    If set, queries AD directly instead of consuming D1.4/D1.5 files.
.EXAMPLE
    .\Spec3-D1.6-Get-KerberosDelegationChainMap.ps1 -D4InputFile .\output\D1.4.json -D5InputFile .\output\D1.5.json
    .\Spec3-D1.6-Get-KerberosDelegationChainMap.ps1 -StandaloneMode
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for standalone mode
    Requires: D1.4 + D1.5 JSON outputs for correlation mode (recommended)
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D4InputFile,
    [string]$D5InputFile,
    [string]$DomainController,
    [string]$SearchBase,
    [switch]$StandaloneMode
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outPrefix = "UIAO_Spec3_D1.6_DelegationChainMap_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 3 — D1.6: Kerberos Delegation Chain Map"            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }
if ($SearchBase) { $adParams['SearchBase'] = $SearchBase }

# ══════════════════════════════════════════════════════════════
# Phase 1: Data Loading
# ══════════════════════════════════════════════════════════════

$delegationRecords = [System.Collections.Generic.List[object]]::new()
$spnIndex = @{}  # SPN string → hosting account info

if (-not $StandaloneMode -and $D4InputFile -and $D5InputFile) {
    # ── Correlation Mode: consume D1.4 + D1.5 ──
    Write-Host "  [1/7] Loading D1.4 + D1.5 data (correlation mode)..." -ForegroundColor Yellow

    if (-not (Test-Path $D4InputFile)) { Write-Error "D1.4 file not found: $D4InputFile"; return }
    if (-not (Test-Path $D5InputFile)) { Write-Error "D1.5 file not found: $D5InputFile"; return }

    $d4Data = Get-Content $D4InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    $d5Data = Get-Content $D5InputFile -Raw -Encoding UTF8 | ConvertFrom-Json

    # Build SPN index from D1.5
    if ($d5Data.SPNInventory) {
        foreach ($spnEntry in $d5Data.SPNInventory) {
            $spnStr = $spnEntry.SPN
            if ($spnStr -and -not $spnIndex.ContainsKey($spnStr)) {
                $spnIndex[$spnStr] = [ordered]@{
                    SPN              = $spnStr
                    ServiceClass     = $spnEntry.ServiceClass
                    Hostname         = $spnEntry.Hostname
                    Port             = $spnEntry.Port
                    HostingAccount   = $spnEntry.AccountName
                    AccountDN        = $spnEntry.DistinguishedName
                    AccountType      = $spnEntry.AccountType
                    Enabled          = $spnEntry.Enabled
                    IsDuplicate      = $spnEntry.IsDuplicate
                    MigrationTarget  = $spnEntry.MigrationTarget
                }
            }
        }
    }
    Write-Host "    SPN index: $($spnIndex.Count) unique SPNs" -ForegroundColor Green

    # Load delegation records from D1.4
    if ($d4Data.DelegationFindings) {
        foreach ($finding in $d4Data.DelegationFindings) {
            $delegationRecords.Add($finding)
        }
    }
    # Fallback: check for per-type arrays
    foreach ($propName in @('UnconstrainedDelegation','KCDDelegation','RBCDDelegation','ProtocolTransition','CertBasedAuth')) {
        if ($d4Data.$propName) {
            foreach ($item in $d4Data.$propName) {
                if ($delegationRecords | Where-Object { $_.ObjectGUID -eq $item.ObjectGUID -and $_.DelegationType -eq $item.DelegationType }) { continue }
                $delegationRecords.Add($item)
            }
        }
    }
    Write-Host "    Delegation records: $($delegationRecords.Count)" -ForegroundColor Green

} else {
    # ── Standalone Mode: query AD directly ──
    Write-Host "  [1/7] Querying AD for delegation data (standalone mode)..." -ForegroundColor Yellow

    if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
        Write-Error "ActiveDirectory module not found. Install RSAT."
        return
    }
    Import-Module ActiveDirectory -ErrorAction Stop

    $domain = (Get-ADDomain @adParams).DNSRoot

    # Get all accounts with delegation
    $compProps = @('Name','SamAccountName','ObjectGUID','DistinguishedName','Enabled',
        'ServicePrincipalName','TrustedForDelegation','TrustedToAuthForDelegation',
        'msDS-AllowedToDelegateTo','msDS-AllowedToActOnBehalfOfOtherIdentity',
        'PrimaryGroupID','AdminCount','userAccountControl')

    $allComputers = @(Get-ADComputer -Filter * -Properties $compProps @adParams)
    $allUsers = @(Get-ADUser -Filter { ServicePrincipalName -like "*" } -Properties $compProps @adParams)

    $allAccounts = $allComputers + $allUsers
    Write-Host "    Scanned $($allComputers.Count) computers + $($allUsers.Count) SPN-bearing users" -ForegroundColor Green

    # Build SPN index
    foreach ($acct in $allAccounts) {
        foreach ($spn in $acct.ServicePrincipalName) {
            if (-not $spnIndex.ContainsKey($spn)) {
                $parsed = $null
                if ($spn -match '^([^/]+)/([^:]+)(?::(\d+))?') {
                    $parsed = @{ ServiceClass = $Matches[1]; Hostname = $Matches[2]; Port = $Matches[3] }
                }
                $spnIndex[$spn] = [ordered]@{
                    SPN            = $spn
                    ServiceClass   = if ($parsed) { $parsed.ServiceClass } else { "Unknown" }
                    Hostname       = if ($parsed) { $parsed.Hostname } else { "Unknown" }
                    Port           = if ($parsed) { $parsed.Port } else { $null }
                    HostingAccount = $acct.SamAccountName
                    AccountDN      = $acct.DistinguishedName
                    AccountType    = if ($acct.ObjectClass -eq 'computer') { 'Computer' } else { 'User' }
                    Enabled        = $acct.Enabled
                    IsDuplicate    = $false
                    MigrationTarget = $null
                }
            }
        }
    }
    Write-Host "    SPN index: $($spnIndex.Count) unique SPNs" -ForegroundColor Green

    # Collect delegation records
    foreach ($acct in $allAccounts) {
        $isDC = ($acct.PrimaryGroupID -eq 516)
        $isAdmin = ($acct.AdminCount -eq 1)

        # Unconstrained delegation (exclude DCs)
        if ($acct.TrustedForDelegation -and -not $isDC) {
            $delegationRecords.Add([ordered]@{
                AccountName     = $acct.SamAccountName
                ObjectGUID      = $acct.ObjectGUID.ToString()
                DN              = $acct.DistinguishedName
                AccountType     = if ($acct.ObjectClass -eq 'computer') { 'Computer' } else { 'User' }
                Enabled         = $acct.Enabled
                IsAdminCount    = $isAdmin
                IsDC            = $isDC
                DelegationType  = "Unconstrained"
                TargetSPNs      = @("ANY — unrestricted")
                ProtocolTransition = $acct.TrustedToAuthForDelegation
            })
        }

        # KCD
        $kcdTargets = $acct.'msDS-AllowedToDelegateTo'
        if ($kcdTargets -and $kcdTargets.Count -gt 0) {
            $delegationRecords.Add([ordered]@{
                AccountName     = $acct.SamAccountName
                ObjectGUID      = $acct.ObjectGUID.ToString()
                DN              = $acct.DistinguishedName
                AccountType     = if ($acct.ObjectClass -eq 'computer') { 'Computer' } else { 'User' }
                Enabled         = $acct.Enabled
                IsAdminCount    = $isAdmin
                IsDC            = $isDC
                DelegationType  = "KCD"
                TargetSPNs      = @($kcdTargets)
                ProtocolTransition = $acct.TrustedToAuthForDelegation
            })
        }

        # RBCD
        $rbcdValue = $acct.'msDS-AllowedToActOnBehalfOfOtherIdentity'
        if ($rbcdValue) {
            try {
                $sd = New-Object System.DirectoryServices.ActiveDirectorySecurity
                $sd.SetSecurityDescriptorBinaryForm($rbcdValue)
                $trustedPrincipals = @($sd.Access | ForEach-Object {
                    try {
                        $_.IdentityReference.Translate([System.Security.Principal.NTAccount]).Value
                    } catch {
                        $_.IdentityReference.Value
                    }
                })
            } catch {
                $trustedPrincipals = @("(parse error)")
            }

            $delegationRecords.Add([ordered]@{
                AccountName     = $acct.SamAccountName
                ObjectGUID      = $acct.ObjectGUID.ToString()
                DN              = $acct.DistinguishedName
                AccountType     = if ($acct.ObjectClass -eq 'computer') { 'Computer' } else { 'User' }
                Enabled         = $acct.Enabled
                IsAdminCount    = $isAdmin
                IsDC            = $isDC
                DelegationType  = "RBCD"
                TrustedPrincipals = $trustedPrincipals
                ProtocolTransition = $false
            })
        }
    }

    # Detect duplicates in SPN index
    $spnHostMap = @{}
    foreach ($spn in $spnIndex.Keys) {
        if (-not $spnHostMap.ContainsKey($spn)) { $spnHostMap[$spn] = @() }
        $spnHostMap[$spn] += $spnIndex[$spn].HostingAccount
    }
    # Mark duplicates via full AD scan
    $allSPNs = @{}
    foreach ($acct in $allAccounts) {
        foreach ($spn in $acct.ServicePrincipalName) {
            if (-not $allSPNs.ContainsKey($spn)) { $allSPNs[$spn] = @() }
            $allSPNs[$spn] += $acct.SamAccountName
        }
    }
    foreach ($spn in $allSPNs.Keys) {
        if ($allSPNs[$spn].Count -gt 1 -and $spnIndex.ContainsKey($spn)) {
            $spnIndex[$spn].IsDuplicate = $true
        }
    }

    Write-Host "    Delegation records: $($delegationRecords.Count)" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════
# Phase 2: Build Directed Edge Graph
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/7] Building delegation edge graph..." -ForegroundColor Yellow

$edges = [System.Collections.Generic.List[object]]::new()
$nodes = @{}  # account name → node info

foreach ($record in $delegationRecords) {
    $sourceAcct = $record.AccountName
    if (-not $nodes.ContainsKey($sourceAcct)) {
        $nodes[$sourceAcct] = [ordered]@{
            Account        = $sourceAcct
            DN             = $record.DN
            AccountType    = $record.AccountType
            Enabled        = $record.Enabled
            IsAdminCount   = $record.IsAdminCount
            IsDC           = $record.IsDC
            DelegationTypes = [System.Collections.Generic.List[string]]::new()
            OutboundEdges  = 0
            InboundEdges   = 0
        }
    }
    if ($record.DelegationType -and $record.DelegationType -notin $nodes[$sourceAcct].DelegationTypes) {
        $nodes[$sourceAcct].DelegationTypes.Add($record.DelegationType)
    }

    switch ($record.DelegationType) {
        "Unconstrained" {
            $edges.Add([ordered]@{
                EdgeID          = "E$($edges.Count + 1)"
                Source          = $sourceAcct
                Target          = "ANY (Unconstrained)"
                DelegationType  = "Unconstrained"
                TargetSPN       = $null
                TargetServiceClass = $null
                TargetHostname  = $null
                TargetAccount   = $null
                TargetEnabled   = $null
                ProtocolTransition = $record.ProtocolTransition
                IsOrphan        = $false
                Risk            = "Critical"
            })
            $nodes[$sourceAcct].OutboundEdges++
        }
        "KCD" {
            foreach ($targetSPN in $record.TargetSPNs) {
                $spnInfo = if ($spnIndex.ContainsKey($targetSPN)) { $spnIndex[$targetSPN] } else { $null }

                $targetAcct = if ($spnInfo) { $spnInfo.HostingAccount } else { $null }
                $isOrphan = if ($spnInfo) { -not $spnInfo.Enabled } else { $true }

                # Ensure target node exists
                if ($targetAcct -and -not $nodes.ContainsKey($targetAcct)) {
                    $nodes[$targetAcct] = [ordered]@{
                        Account        = $targetAcct
                        DN             = if ($spnInfo) { $spnInfo.AccountDN } else { $null }
                        AccountType    = if ($spnInfo) { $spnInfo.AccountType } else { "Unknown" }
                        Enabled        = if ($spnInfo) { $spnInfo.Enabled } else { $null }
                        IsAdminCount   = $false
                        IsDC           = $false
                        DelegationTypes = [System.Collections.Generic.List[string]]::new()
                        OutboundEdges  = 0
                        InboundEdges   = 0
                    }
                }

                $edges.Add([ordered]@{
                    EdgeID          = "E$($edges.Count + 1)"
                    Source          = $sourceAcct
                    Target          = if ($targetAcct) { $targetAcct } else { "UNKNOWN ($targetSPN)" }
                    DelegationType  = "KCD"
                    TargetSPN       = $targetSPN
                    TargetServiceClass = if ($spnInfo) { $spnInfo.ServiceClass } else { $null }
                    TargetHostname  = if ($spnInfo) { $spnInfo.Hostname } else { $null }
                    TargetAccount   = $targetAcct
                    TargetEnabled   = if ($spnInfo) { $spnInfo.Enabled } else { $null }
                    ProtocolTransition = $record.ProtocolTransition
                    IsOrphan        = $isOrphan
                    Risk            = $null  # Calculated later
                })

                $nodes[$sourceAcct].OutboundEdges++
                if ($targetAcct -and $nodes.ContainsKey($targetAcct)) {
                    $nodes[$targetAcct].InboundEdges++
                }
            }
        }
        "RBCD" {
            foreach ($trustedPrincipal in $record.TrustedPrincipals) {
                $trustedName = if ($trustedPrincipal -match '\\(.+)$') { $Matches[1] } else { $trustedPrincipal }

                if (-not $nodes.ContainsKey($trustedName)) {
                    $nodes[$trustedName] = [ordered]@{
                        Account        = $trustedName
                        DN             = $null
                        AccountType    = "Unknown (RBCD trusted)"
                        Enabled        = $null
                        IsAdminCount   = $false
                        IsDC           = $false
                        DelegationTypes = [System.Collections.Generic.List[string]]::new()
                        OutboundEdges  = 0
                        InboundEdges   = 0
                    }
                }

                # RBCD: trusted principal can delegate TO the resource
                $edges.Add([ordered]@{
                    EdgeID          = "E$($edges.Count + 1)"
                    Source          = $trustedName
                    Target          = $sourceAcct
                    DelegationType  = "RBCD"
                    TargetSPN       = $null
                    TargetServiceClass = $null
                    TargetHostname  = $null
                    TargetAccount   = $sourceAcct
                    TargetEnabled   = $record.Enabled
                    ProtocolTransition = $false
                    IsOrphan        = $false
                    Risk            = $null
                })

                $nodes[$trustedName].OutboundEdges++
                $nodes[$sourceAcct].InboundEdges++
            }
        }
    }
}

Write-Host "    Nodes: $($nodes.Count)" -ForegroundColor Green
Write-Host "    Edges: $($edges.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Phase 3: Multi-Hop Chain Detection
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/7] Detecting multi-hop delegation chains..." -ForegroundColor Yellow

$chains = [System.Collections.Generic.List[object]]::new()
$visited = @{}

# Build adjacency list (source → targets)
$adjacency = @{}
foreach ($edge in $edges) {
    if (-not $adjacency.ContainsKey($edge.Source)) { $adjacency[$edge.Source] = @() }
    $adjacency[$edge.Source] += $edge
}

# DFS to find all chains
function Trace-Chain {
    param([string]$Current, [System.Collections.Generic.List[string]]$Path, [System.Collections.Generic.List[object]]$EdgePath)

    if ($adjacency.ContainsKey($Current)) {
        foreach ($edge in $adjacency[$Current]) {
            $nextTarget = $edge.Target
            if ($nextTarget -eq "ANY (Unconstrained)") {
                $chainCopy = [System.Collections.Generic.List[string]]::new($Path)
                $chainCopy.Add("ANY (Unconstrained)")
                $edgeCopy = [System.Collections.Generic.List[object]]::new($EdgePath)
                $edgeCopy.Add($edge)
                $chains.Add([ordered]@{
                    ChainID    = "C$($chains.Count + 1)"
                    Hops       = $chainCopy.Count - 1
                    Path       = @($chainCopy)
                    Edges      = @($edgeCopy | ForEach-Object { $_.EdgeID })
                    HasUnconstrained = $true
                    IsCircular = $false
                })
                continue
            }
            if ($nextTarget -in $Path) {
                # Circular delegation detected
                $chainCopy = [System.Collections.Generic.List[string]]::new($Path)
                $chainCopy.Add($nextTarget)
                $edgeCopy = [System.Collections.Generic.List[object]]::new($EdgePath)
                $edgeCopy.Add($edge)
                $chains.Add([ordered]@{
                    ChainID    = "C$($chains.Count + 1)"
                    Hops       = $chainCopy.Count - 1
                    Path       = @($chainCopy)
                    Edges      = @($edgeCopy | ForEach-Object { $_.EdgeID })
                    HasUnconstrained = $false
                    IsCircular = $true
                })
                continue
            }

            $Path.Add($nextTarget)
            $EdgePath.Add($edge)
            Trace-Chain -Current $nextTarget -Path $Path -EdgePath $EdgePath
            $Path.RemoveAt($Path.Count - 1)
            $EdgePath.RemoveAt($EdgePath.Count - 1)
        }
    } else {
        # Terminal node — record chain if > 1 hop
        if ($Path.Count -gt 2) {
            $chains.Add([ordered]@{
                ChainID    = "C$($chains.Count + 1)"
                Hops       = $Path.Count - 1
                Path       = @($Path)
                Edges      = @($EdgePath | ForEach-Object { $_.EdgeID })
                HasUnconstrained = $false
                IsCircular = $false
            })
        }
    }
}

# Start from each source node
foreach ($sourceNode in $adjacency.Keys) {
    $path = [System.Collections.Generic.List[string]]::new()
    $path.Add($sourceNode)
    $edgePath = [System.Collections.Generic.List[object]]::new()
    Trace-Chain -Current $sourceNode -Path $path -EdgePath $edgePath
}

$multiHopChains = @($chains | Where-Object { $_.Hops -gt 1 })
$circularChains = @($chains | Where-Object { $_.IsCircular })

Write-Host "    Total chains: $($chains.Count)" -ForegroundColor Green
Write-Host "    Multi-hop (>1): $($multiHopChains.Count)" -ForegroundColor $(if ($multiHopChains.Count -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    Circular: $($circularChains.Count)" -ForegroundColor $(if ($circularChains.Count -gt 0) { 'Red' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Phase 4: Risk Classification
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/7] Classifying risk per edge..." -ForegroundColor Yellow

# Service class migration targets
$migrationMap = @{
    'HTTP'          = [ordered]@{ Target = 'Entra Application Proxy or direct OIDC/SAML'; Complexity = 'Medium' }
    'MSSQLSvc'      = [ordered]@{ Target = 'Entra ID Auth for SQL (ADR-004)'; Complexity = 'Medium' }
    'ldap'          = [ordered]@{ Target = 'Retain for DCs; eliminate for apps'; Complexity = 'High' }
    'cifs'          = [ordered]@{ Target = 'Azure Files with Kerberos or SMB-over-QUIC'; Complexity = 'Medium' }
    'TERMSRV'       = [ordered]@{ Target = 'Azure Arc RDP with Entra ID auth'; Complexity = 'Low' }
    'HOST'          = [ordered]@{ Target = 'Evaluate per service; often eliminatable'; Complexity = 'Medium' }
    'RestrictedKrbHost' = [ordered]@{ Target = 'Windows LAPS or Entra ID join'; Complexity = 'Low' }
    'WSMAN'         = [ordered]@{ Target = 'Azure Arc remote management'; Complexity = 'Low' }
    'exchangeMDB'   = [ordered]@{ Target = 'Exchange Online (migration)'; Complexity = 'High' }
    'exchangeRFR'   = [ordered]@{ Target = 'Exchange Online (migration)'; Complexity = 'High' }
    'exchangeAB'    = [ordered]@{ Target = 'Exchange Online (migration)'; Complexity = 'High' }
    'FIMService'    = [ordered]@{ Target = 'Entra ID Governance / Lifecycle Workflows'; Complexity = 'High' }
    'SIP'           = [ordered]@{ Target = 'Teams (migration from Skype)'; Complexity = 'Medium' }
}

foreach ($edge in $edges) {
    if ($edge.Risk) { continue }  # Already classified (unconstrained)

    $risk = "Medium"  # Default

    # Escalation factors
    if ($edge.DelegationType -eq "Unconstrained") { $risk = "Critical" }
    elseif ($edge.ProtocolTransition) { $risk = "High" }
    elseif ($edge.IsOrphan) { $risk = "High" }
    elseif ($edge.DelegationType -eq "KCD") {
        # Check if source or target has AdminCount
        $sourceNode = if ($nodes.ContainsKey($edge.Source)) { $nodes[$edge.Source] } else { $null }
        $targetNode = if ($nodes.ContainsKey($edge.Target)) { $nodes[$edge.Target] } else { $null }
        if (($sourceNode -and $sourceNode.IsAdminCount) -or ($targetNode -and $targetNode.IsAdminCount)) {
            $risk = "Critical"
        } elseif ($edge.TargetServiceClass -and $edge.TargetServiceClass -in @('ldap', 'exchangeMDB', 'FIMService')) {
            $risk = "High"
        } elseif ($edge.TargetServiceClass -and $migrationMap.ContainsKey($edge.TargetServiceClass) -and $migrationMap[$edge.TargetServiceClass].Complexity -eq 'Low') {
            $risk = "Low"
        }
    } elseif ($edge.DelegationType -eq "RBCD") {
        $risk = "Medium"
    }

    # Check for multi-hop escalation
    $inMultiHop = $chains | Where-Object { $_.Hops -gt 1 -and $edge.EdgeID -in $_.Edges }
    if ($inMultiHop) { if ($risk -eq "Medium") { $risk = "High" } }

    $inCircular = $chains | Where-Object { $_.IsCircular -and $edge.EdgeID -in $_.Edges }
    if ($inCircular) { $risk = "Critical" }

    $edge.Risk = $risk

    # Add migration info
    if ($edge.TargetServiceClass -and $migrationMap.ContainsKey($edge.TargetServiceClass)) {
        $edge['MigrationTarget'] = $migrationMap[$edge.TargetServiceClass].Target
        $edge['MigrationComplexity'] = $migrationMap[$edge.TargetServiceClass].Complexity
    } else {
        $edge['MigrationTarget'] = "Per-application assessment required"
        $edge['MigrationComplexity'] = "Unknown"
    }
}

$riskCounts = [ordered]@{
    Critical = ($edges | Where-Object { $_.Risk -eq 'Critical' }).Count
    High     = ($edges | Where-Object { $_.Risk -eq 'High' }).Count
    Medium   = ($edges | Where-Object { $_.Risk -eq 'Medium' }).Count
    Low      = ($edges | Where-Object { $_.Risk -eq 'Low' }).Count
}

Write-Host "    Risk: Critical=$($riskCounts.Critical) High=$($riskCounts.High) Medium=$($riskCounts.Medium) Low=$($riskCounts.Low)" -ForegroundColor $(if ($riskCounts.Critical -gt 0) { 'Red' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Phase 5: Orphan Delegation Detection
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/7] Detecting orphan delegations..." -ForegroundColor Yellow

$orphanEdges = @($edges | Where-Object { $_.IsOrphan })
Write-Host "    Orphan delegations (target disabled/stale): $($orphanEdges.Count)" -ForegroundColor $(if ($orphanEdges.Count -gt 0) { 'Yellow' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Phase 6: Service Class Distribution
# ══════════════════════════════════════════════════════════════
Write-Host "  [6/7] Analyzing service class distribution..." -ForegroundColor Yellow

$serviceClassDist = $edges |
    Where-Object { $_.TargetServiceClass } |
    Group-Object -Property TargetServiceClass |
    Sort-Object Count -Descending |
    ForEach-Object {
        [ordered]@{
            ServiceClass    = $_.Name
            Count           = $_.Count
            MigrationTarget = if ($migrationMap.ContainsKey($_.Name)) { $migrationMap[$_.Name].Target } else { "Per-app assessment" }
            Complexity      = if ($migrationMap.ContainsKey($_.Name)) { $migrationMap[$_.Name].Complexity } else { "Unknown" }
        }
    }

foreach ($sc in $serviceClassDist) {
    Write-Host "    $($sc.ServiceClass.PadRight(20)) x$($sc.Count.ToString().PadLeft(4)) → $($sc.MigrationTarget)" -ForegroundColor DarkGray
}

# ══════════════════════════════════════════════════════════════
# Phase 7: Output
# ══════════════════════════════════════════════════════════════
Write-Host "  [7/7] Generating outputs..." -ForegroundColor Yellow

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Timestamp   = (Get-Date).ToString("o")
        Script      = "UIAO Spec 3 D1.6 — Kerberos Delegation Chain Map"
        Reference   = "UIAO_136"
        Mode        = if ($StandaloneMode) { "Standalone (direct AD)" } else { "Correlation (D1.4 + D1.5)" }
        D4Source    = if ($D4InputFile) { $D4InputFile } else { "Standalone AD query" }
        D5Source    = if ($D5InputFile) { $D5InputFile } else { "Standalone AD query" }
    }
    GraphSummary = [ordered]@{
        TotalNodes          = $nodes.Count
        TotalEdges          = $edges.Count
        DelegationTypes     = [ordered]@{
            Unconstrained       = ($edges | Where-Object { $_.DelegationType -eq 'Unconstrained' }).Count
            KCD                 = ($edges | Where-Object { $_.DelegationType -eq 'KCD' }).Count
            RBCD                = ($edges | Where-Object { $_.DelegationType -eq 'RBCD' }).Count
        }
        RiskDistribution    = $riskCounts
        ChainAnalysis       = [ordered]@{
            TotalChains         = $chains.Count
            MultiHopChains      = $multiHopChains.Count
            CircularChains      = $circularChains.Count
            MaxChainDepth       = if ($chains.Count -gt 0) { ($chains | Measure-Object -Property Hops -Maximum).Maximum } else { 0 }
        }
        OrphanDelegations   = $orphanEdges.Count
        ProtocolTransition  = ($edges | Where-Object { $_.ProtocolTransition }).Count
        ServiceClassDistribution = @($serviceClassDist)
    }
}

# JSON (full graph)
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{
    Summary = $summary
    Nodes   = $nodes.Values | ForEach-Object { $_ }
    Edges   = @($edges)
    Chains  = @($chains)
} | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# CSV — all edges
$csvFile = Join-Path $OutputPath "${outPrefix}_edges.csv"
$edges | ForEach-Object {
    [PSCustomObject]@{
        EdgeID              = $_.EdgeID
        Source              = $_.Source
        Target              = $_.Target
        DelegationType      = $_.DelegationType
        TargetSPN           = $_.TargetSPN
        TargetServiceClass  = $_.TargetServiceClass
        TargetHostname      = $_.TargetHostname
        ProtocolTransition  = $_.ProtocolTransition
        IsOrphan            = $_.IsOrphan
        Risk                = $_.Risk
        MigrationTarget     = $_.MigrationTarget
        MigrationComplexity = $_.MigrationComplexity
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (edges): $csvFile" -ForegroundColor Green

# CSV — critical/high findings only
$critFile = Join-Path $OutputPath "${outPrefix}_critical.csv"
$critEdges = @($edges | Where-Object { $_.Risk -in @('Critical','High') })
if ($critEdges.Count -gt 0) {
    $critEdges | ForEach-Object {
        [PSCustomObject]@{
            EdgeID             = $_.EdgeID
            Risk               = $_.Risk
            Source             = $_.Source
            Target             = $_.Target
            DelegationType     = $_.DelegationType
            TargetSPN          = $_.TargetSPN
            TargetServiceClass = $_.TargetServiceClass
            ProtocolTransition = $_.ProtocolTransition
            IsOrphan           = $_.IsOrphan
            MigrationTarget    = $_.MigrationTarget
        }
    } | Export-Csv -Path $critFile -NoTypeInformation -Encoding utf8NoBOM
    Write-Host "  CSV (critical/high): $critFile" -ForegroundColor Green
} else {
    Write-Host "  CSV (critical/high): none — no critical/high findings" -ForegroundColor Green
}

# Markdown chain visualization
$mdFile = Join-Path $OutputPath "${outPrefix}.md"
$mdLines = [System.Collections.Generic.List[string]]::new()
$mdLines.Add("# UIAO Spec 3 D1.6 — Kerberos Delegation Chain Map")
$mdLines.Add("")
$mdLines.Add("> **Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$mdLines.Add("> **Ref:** UIAO_136 Spec 3, Phase 1, D1.6")
$mdLines.Add("")
$mdLines.Add("---")
$mdLines.Add("")
$mdLines.Add("## Summary")
$mdLines.Add("")
$mdLines.Add("| Metric | Value |")
$mdLines.Add("|--------|-------|")
$mdLines.Add("| Total nodes | $($nodes.Count) |")
$mdLines.Add("| Total edges | $($edges.Count) |")
$mdLines.Add("| Unconstrained delegation | $($summary.GraphSummary.DelegationTypes.Unconstrained) |")
$mdLines.Add("| KCD edges | $($summary.GraphSummary.DelegationTypes.KCD) |")
$mdLines.Add("| RBCD edges | $($summary.GraphSummary.DelegationTypes.RBCD) |")
$mdLines.Add("| Multi-hop chains | $($multiHopChains.Count) |")
$mdLines.Add("| Circular chains | $($circularChains.Count) |")
$mdLines.Add("| Orphan delegations | $($orphanEdges.Count) |")
$mdLines.Add("| Protocol transition | $(($edges | Where-Object { $_.ProtocolTransition }).Count) |")
$mdLines.Add("")
$mdLines.Add("## Risk Distribution")
$mdLines.Add("")
$mdLines.Add("| Risk | Count |")
$mdLines.Add("|------|-------|")
foreach ($r in @('Critical','High','Medium','Low')) {
    $mdLines.Add("| **$r** | $($riskCounts[$r]) |")
}
$mdLines.Add("")

if ($circularChains.Count -gt 0) {
    $mdLines.Add("## ⚠ Circular Delegation Chains")
    $mdLines.Add("")
    foreach ($chain in $circularChains) {
        $mdLines.Add("- **$($chain.ChainID):** $($chain.Path -join ' → ')")
    }
    $mdLines.Add("")
}

if ($multiHopChains.Count -gt 0) {
    $mdLines.Add("## Multi-Hop Chains")
    $mdLines.Add("")
    foreach ($chain in ($multiHopChains | Sort-Object Hops -Descending | Select-Object -First 20)) {
        $mdLines.Add("- **$($chain.ChainID)** ($($chain.Hops) hops): $($chain.Path -join ' → ')")
    }
    $mdLines.Add("")
}

$mdLines.Add("## Service Class Migration Map")
$mdLines.Add("")
$mdLines.Add("| Service Class | Count | Migration Target | Complexity |")
$mdLines.Add("|--------------|-------|-----------------|-----------|")
foreach ($sc in $serviceClassDist) {
    $mdLines.Add("| ``$($sc.ServiceClass)`` | $($sc.Count) | $($sc.MigrationTarget) | $($sc.Complexity) |")
}

($mdLines -join "`n") | Out-File -FilePath $mdFile -Encoding utf8NoBOM
Write-Host "  Markdown: $mdFile" -ForegroundColor Green

# Console summary
Write-Host "`n-- Delegation Graph Summary --" -ForegroundColor Cyan
Write-Host "  Nodes:                  $($nodes.Count)"
Write-Host "  Edges:                  $($edges.Count)"
Write-Host "  Unconstrained:          $($summary.GraphSummary.DelegationTypes.Unconstrained)" -ForegroundColor $(if ($summary.GraphSummary.DelegationTypes.Unconstrained -gt 0) { 'Red' } else { 'Green' })
Write-Host "  KCD:                    $($summary.GraphSummary.DelegationTypes.KCD)"
Write-Host "  RBCD:                   $($summary.GraphSummary.DelegationTypes.RBCD)"

Write-Host "`n-- Chain Analysis --" -ForegroundColor Cyan
Write-Host "  Total chains:           $($chains.Count)"
Write-Host "  Multi-hop:              $($multiHopChains.Count)" -ForegroundColor $(if ($multiHopChains.Count -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Circular (security):    $($circularChains.Count)" -ForegroundColor $(if ($circularChains.Count -gt 0) { 'Red' } else { 'Green' })
Write-Host "  Max depth:              $($summary.GraphSummary.ChainAnalysis.MaxChainDepth)"

Write-Host "`n-- Risk --" -ForegroundColor Cyan
Write-Host "  Critical:               $($riskCounts.Critical)" -ForegroundColor $(if ($riskCounts.Critical -gt 0) { 'Red' } else { 'Green' })
Write-Host "  High:                   $($riskCounts.High)" -ForegroundColor $(if ($riskCounts.High -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  Medium:                 $($riskCounts.Medium)"
Write-Host "  Low:                    $($riskCounts.Low)" -ForegroundColor Green

Write-Host "`n-- Orphans --" -ForegroundColor Cyan
Write-Host "  Orphan delegations:     $($orphanEdges.Count)" -ForegroundColor $(if ($orphanEdges.Count -gt 0) { 'Yellow' } else { 'Green' })

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
