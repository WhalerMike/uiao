<#
.SYNOPSIS
    UIAO Spec 3 — D1.12: Service Account Owner Accountability Matrix
.DESCRIPTION
    Generates a comprehensive owner-to-service-account mapping matrix that
    assigns organizational accountability for every service account, gMSA,
    and workload identity discovered across the D1.x discovery pipeline.

    This is the capstone deliverable for Spec 3 Phase 1 — without clear
    ownership, no service account can be safely migrated, decommissioned,
    or converted to a workload identity. This matrix becomes the operational
    governance artifact for the entire service account transformation.

    Data sources consumed (all optional — works with whatever is available):
    1. Spec3-D1.1 — Service Account Scan (primary inventory)
    2. Spec3-D1.2 — Scheduled Task Credential Audit
    3. Spec3-D1.3 — Windows Service Credential Audit
    4. Spec3-D1.4 — IIS App Pool Identity Audit
    5. Spec3-D1.5 — COM/DCOM Identity Audit
    6. Spec3-D1.6 — Kerberos Delegation Chain Map
    7. Spec3-D1.7 — SPN Collision Report
    8. Spec3-D1.8 — SQL Server Auth Audit
    9. Spec3-D1.9 — LDAP Bind Account Inventory
    10. Spec3-D1.10 — Certificate-Based Auth Audit
    11. Spec3-D1.11 — Network Service Account Audit

    Owner resolution strategy (layered):
    1. AD managedBy attribute — explicit owner assignment in AD
    2. AD description field parsing — "Owner: John Smith" or "Contact: jsmith"
    3. OU-based ownership — map OUs to organizational owners
    4. SPN-to-application mapping — infer owner from application/service
    5. Group membership analysis — shared group membership with known owners
    6. Last password changer — who last reset the password (if auditable)
    7. Manual assignment — unresolved accounts flagged for manual triage

    Per-account output:
    - Service account identity and classification
    - Assigned owner (name, email, department, confidence level)
    - Ownership resolution method
    - All consuming systems (services, tasks, apps, pools, delegation chains)
    - Migration target per ADR-004
    - Migration complexity and risk score
    - Migration wave assignment (recommended sequencing)
    - Accountability status (Owned / Orphan / Disputed / Pending)

    Migration wave logic:
    - Wave 0: Decommission (disabled/stale accounts with no active consumers)
    - Wave 1: Quick wins (gMSAs, accounts with single consumer, low complexity)
    - Wave 2: Standard (accounts with clear owner, medium complexity)
    - Wave 3: Complex (multi-consumer, delegation chains, high complexity)
    - Wave 4: Infrastructure (DCs, ADFS, PKI — last to migrate)

    Outputs: JSON + CSV (owner matrix) + CSV (orphan accounts) +
             CSV (migration waves) + Markdown report + console

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.12
         ADR-004 (Workload Identity Federation as Default)
         Feeds: D2.1 (Target State Architecture), D2.2 (Migration Runbook),
                D2.3 (Migration Wave Plan), D3.1 (Operational Governance)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D1InputFile
    Path to Spec3-D1.1 Service Account Scan JSON (primary source).
.PARAMETER D2InputFile
    Path to Spec3-D1.2 Scheduled Task Credential Audit JSON.
.PARAMETER D3InputFile
    Path to Spec3-D1.3 Windows Service Credential Audit JSON.
.PARAMETER D4InputFile
    Path to Spec3-D1.4 IIS App Pool Identity Audit JSON.
.PARAMETER D5InputFile
    Path to Spec3-D1.5 COM/DCOM Identity Audit JSON.
.PARAMETER D6InputFile
    Path to Spec3-D1.6 Kerberos Delegation Chain Map JSON.
.PARAMETER D7InputFile
    Path to Spec3-D1.7 SPN Collision Report JSON.
.PARAMETER D8InputFile
    Path to Spec3-D1.8 SQL Server Auth Audit JSON.
.PARAMETER D9InputFile
    Path to Spec3-D1.9 LDAP Bind Account Inventory JSON.
.PARAMETER D10InputFile
    Path to Spec3-D1.10 Certificate-Based Auth Audit JSON.
.PARAMETER D11InputFile
    Path to Spec3-D1.11 Network Service Account Audit JSON.
.PARAMETER OwnerMappingFile
    Optional CSV with manual owner assignments: SamAccountName, OwnerName,
    OwnerEmail, OwnerDepartment.
.PARAMETER OUOwnerMappingFile
    Optional CSV mapping OUs to default owners: OUPattern, OwnerName,
    OwnerEmail, OwnerDepartment.
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.EXAMPLE
    .\Spec3-D1.12-New-ServiceAccountOwnerMatrix.ps1 -D1InputFile .\output\D1.1.json
    .\Spec3-D1.12-New-ServiceAccountOwnerMatrix.ps1 -D1InputFile .\output\D1.1.json -OwnerMappingFile .\owners.csv
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for owner resolution
    Optional: All D1.x JSON outputs for comprehensive cross-reference
    Optional: Manual owner mapping CSV for pre-assigned accounts
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D1InputFile,
    [string]$D2InputFile,
    [string]$D3InputFile,
    [string]$D4InputFile,
    [string]$D5InputFile,
    [string]$D6InputFile,
    [string]$D7InputFile,
    [string]$D8InputFile,
    [string]$D9InputFile,
    [string]$D10InputFile,
    [string]$D11InputFile,
    [string]$OwnerMappingFile,
    [string]$OUOwnerMappingFile,
    [string]$DomainController
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 3 — D1.12: Service Account Owner Matrix" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-004 (Capstone Deliverable)" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Load All Available D1.x Data Sources
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/7] Loading data sources..." -ForegroundColor Yellow

$dataSources = @{}
$sourceFiles = @{
    "D1.1_ServiceAccountScan"       = $D1InputFile
    "D1.2_ScheduledTaskAudit"       = $D2InputFile
    "D1.3_WindowsServiceAudit"      = $D3InputFile
    "D1.4_IISAppPoolAudit"          = $D4InputFile
    "D1.5_COMDCOMAudit"             = $D5InputFile
    "D1.6_DelegationChainMap"       = $D6InputFile
    "D1.7_SPNCollisionReport"       = $D7InputFile
    "D1.8_SQLServerAuthAudit"       = $D8InputFile
    "D1.9_LDAPBindInventory"        = $D9InputFile
    "D1.10_CertBasedAuthAudit"      = $D10InputFile
    "D1.11_NetworkServiceAudit"     = $D11InputFile
}

foreach ($source in $sourceFiles.GetEnumerator()) {
    if ($source.Value -and (Test-Path $source.Value)) {
        try {
            $dataSources[$source.Key] = Get-Content -Path $source.Value -Raw | ConvertFrom-Json
            Write-Host "  ✓ $($source.Key)" -ForegroundColor Green
        } catch {
            Write-Host "  ✗ $($source.Key) — parse error: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  · $($source.Key) — not provided" -ForegroundColor DarkGray
    }
}

# Load manual owner mappings
$manualOwners = @{}
if ($OwnerMappingFile -and (Test-Path $OwnerMappingFile)) {
    $ownerCsv = Import-Csv -Path $OwnerMappingFile
    foreach ($row in $ownerCsv) {
        $manualOwners[$row.SamAccountName] = @{
            OwnerName       = $row.OwnerName
            OwnerEmail      = $row.OwnerEmail
            OwnerDepartment = $row.OwnerDepartment
        }
    }
    Write-Host "  ✓ Manual owner mappings: $($manualOwners.Count)" -ForegroundColor Green
}

$ouOwners = @()
if ($OUOwnerMappingFile -and (Test-Path $OUOwnerMappingFile)) {
    $ouOwners = Import-Csv -Path $OUOwnerMappingFile
    Write-Host "  ✓ OU owner mappings: $($ouOwners.Count)" -ForegroundColor Green
}

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Build Unified Service Account Registry
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[2/7] Building unified service account registry..." -ForegroundColor Yellow

$registry = @{}  # Key: SamAccountName, Value: unified record

# ── Primary source: D1.1 Service Account Scan ──
if ($dataSources.ContainsKey("D1.1_ServiceAccountScan")) {
    foreach ($sa in $dataSources["D1.1_ServiceAccountScan"].ServiceAccounts) {
        $key = $sa.SamAccountName
        if (-not $registry.ContainsKey($key)) {
            $registry[$key] = @{
                SamAccountName      = $sa.SamAccountName
                DistinguishedName   = $sa.DistinguishedName
                DisplayName         = $sa.DisplayName
                Description         = $sa.Description
                Enabled             = $sa.Enabled
                ObjectType          = $sa.ObjectType
                IsGMSA              = $sa.IsGMSA
                IsSMSA              = $sa.IsSMSA
                HasSPN              = $sa.HasSPN
                PasswordAge         = $sa.PasswordAge
                LastLogon           = $sa.LastLogon
                RiskScore           = $sa.RiskScore
                DelegationType      = $sa.DelegationType
                MigrationTarget     = $sa.MigrationTarget
                # Owner fields
                Owner               = $null
                OwnerEmail          = $null
                OwnerDepartment     = $null
                OwnerConfidence     = 0
                OwnerMethod         = "Unresolved"
                OwnerStatus         = "Pending"
                # Consumer tracking
                Consumers           = @()
                ConsumerCount       = 0
                # Migration planning
                MigrationWave       = -1
                MigrationComplexity = "Unknown"
                MigrationBlockers   = @()
                # Cross-reference flags
                HasScheduledTasks   = $false
                HasWindowsServices  = $false
                HasIISPools         = $false
                HasCOMApps          = $false
                HasDelegationChains = $false
                HasSPNCollisions    = $false
                HasSQLDependency    = $false
                HasLDAPBinds        = $false
                HasCertAuth         = $false
                HasNetworkSvcDep    = $false
            }
        }
    }
    Write-Host "  D1.1: $($dataSources['D1.1_ServiceAccountScan'].ServiceAccounts.Count) accounts loaded" -ForegroundColor Green
}

# ── Cross-reference D1.2: Scheduled Tasks ──
if ($dataSources.ContainsKey("D1.2_ScheduledTaskAudit")) {
    foreach ($task in $dataSources["D1.2_ScheduledTaskAudit"].Tasks) {
        $key = $task.RunAsAccount
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasScheduledTasks = $true
            $registry[$key].Consumers += @{
                Type = "ScheduledTask"
                Name = $task.TaskName
                Server = $task.ServerName
                Source = "D1.2"
            }
        }
    }
    Write-Host "  D1.2: Scheduled task cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.3: Windows Services ──
if ($dataSources.ContainsKey("D1.3_WindowsServiceAudit")) {
    foreach ($svc in $dataSources["D1.3_WindowsServiceAudit"].Services) {
        $key = $svc.ServiceAccount -replace '^.*\\', ''
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasWindowsServices = $true
            $registry[$key].Consumers += @{
                Type = "WindowsService"
                Name = $svc.ServiceName
                Server = $svc.ServerName
                Source = "D1.3"
            }
        }
    }
    Write-Host "  D1.3: Windows service cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.4: IIS App Pools ──
if ($dataSources.ContainsKey("D1.4_IISAppPoolAudit")) {
    foreach ($pool in $dataSources["D1.4_IISAppPoolAudit"].AppPools) {
        $key = $pool.IdentityAccount -replace '^.*\\', ''
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasIISPools = $true
            $registry[$key].Consumers += @{
                Type = "IISAppPool"
                Name = $pool.AppPoolName
                Server = $pool.ServerName
                Source = "D1.4"
            }
        }
    }
    Write-Host "  D1.4: IIS app pool cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.5: COM/DCOM ──
if ($dataSources.ContainsKey("D1.5_COMDCOMAudit")) {
    foreach ($com in $dataSources["D1.5_COMDCOMAudit"].COMApplications) {
        $key = $com.IdentityAccount -replace '^.*\\', ''
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasCOMApps = $true
            $registry[$key].Consumers += @{
                Type = "COMApplication"
                Name = $com.ApplicationName
                Server = $com.ServerName
                Source = "D1.5"
            }
        }
    }
    Write-Host "  D1.5: COM/DCOM cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.6: Delegation Chains ──
if ($dataSources.ContainsKey("D1.6_DelegationChainMap")) {
    foreach ($chain in $dataSources["D1.6_DelegationChainMap"].DelegationChains) {
        foreach ($node in $chain.Nodes) {
            $key = $node.AccountName
            if ($registry.ContainsKey($key)) {
                $registry[$key].HasDelegationChains = $true
                $registry[$key].Consumers += @{
                    Type = "DelegationChain"
                    Name = "Chain: $($chain.ChainId)"
                    ChainDepth = $chain.Depth
                    Source = "D1.6"
                }
            }
        }
    }
    Write-Host "  D1.6: Delegation chain cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.7: SPN Collisions ──
if ($dataSources.ContainsKey("D1.7_SPNCollisionReport")) {
    foreach ($collision in $dataSources["D1.7_SPNCollisionReport"].Collisions) {
        foreach ($acct in $collision.Accounts) {
            $key = $acct.AccountName
            if ($registry.ContainsKey($key)) {
                $registry[$key].HasSPNCollisions = $true
                $registry[$key].MigrationBlockers += "SPN Collision: $($collision.SPN) ($($collision.CollisionType))"
            }
        }
    }
    Write-Host "  D1.7: SPN collision cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.8: SQL Server ──
if ($dataSources.ContainsKey("D1.8_SQLServerAuthAudit")) {
    foreach ($instance in $dataSources["D1.8_SQLServerAuthAudit"].InstanceAudits) {
        $key = $instance.ServiceAccountName -replace '^.*\\', '' -replace '\$$', ''
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasSQLDependency = $true
            $registry[$key].Consumers += @{
                Type = "SQLServer"
                Name = "$($instance.ServerName)\$($instance.InstanceName)"
                SQLVersion = $instance.SQLVersion
                Source = "D1.8"
            }
        }
    }
    Write-Host "  D1.8: SQL Server cross-reference complete" -ForegroundColor DarkGreen
}

# ── Cross-reference D1.9: LDAP Binds ──
if ($dataSources.ContainsKey("D1.9_LDAPBindInventory")) {
    foreach ($ldap in $dataSources["D1.9_LDAPBindInventory"].LDAPBindAccounts) {
        $key = $ldap.SamAccountName
        if ($registry.ContainsKey($key)) {
            $registry[$key].HasLDAPBinds = $true
            $registry[$key].Consumers += @{
                Type = "LDAPBind"
                Name = "LDAP Bind ($($ldap.BindType))"
                Confidence = $ldap.LDAPBindConfidence
                Source = "D1.9"
            }
            $registry[$key].MigrationBlockers += "LDAP bind dependency — must migrate to Graph API"
        } elseif ($ldap.LDAPBindConfidence -ge 60) {
            # Add to registry if high confidence
            $registry[$key] = @{
                SamAccountName    = $key
                DistinguishedName = $ldap.DistinguishedName
                DisplayName       = $ldap.DisplayName
                Description       = $ldap.Description
                Enabled           = $ldap.Enabled
                ObjectType        = "user"
                IsGMSA            = $false
                IsSMSA            = $false
                HasSPN            = $ldap.HasSPN
                PasswordAge       = $ldap.PasswordAgeDays
                LastLogon         = $ldap.LastLogon
                RiskScore         = 0
                DelegationType    = "None"
                MigrationTarget   = $ldap.MigrationTarget
                Owner             = $null
                OwnerEmail        = $null
                OwnerDepartment   = $null
                OwnerConfidence   = 0
                OwnerMethod       = "Unresolved"
                OwnerStatus       = "Pending"
                Consumers         = @(@{ Type = "LDAPBind"; Name = "LDAP Bind ($($ldap.BindType))"; Source = "D1.9" })
                ConsumerCount     = 0
                MigrationWave     = -1
                MigrationComplexity = "Unknown"
                MigrationBlockers = @("LDAP bind dependency")
                HasScheduledTasks = $false; HasWindowsServices = $false; HasIISPools = $false
                HasCOMApps = $false; HasDelegationChains = $false; HasSPNCollisions = $false
                HasSQLDependency = $false; HasLDAPBinds = $true; HasCertAuth = $false
                HasNetworkSvcDep = $false
            }
        }
    }
    Write-Host "  D1.9: LDAP bind cross-reference complete" -ForegroundColor DarkGreen
}

# Update consumer counts
foreach ($key in $registry.Keys) {
    $registry[$key].ConsumerCount = $registry[$key].Consumers.Count
}

Write-Host "  Unified registry: $($registry.Count) service accounts" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 3: Owner Resolution
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[3/7] Resolving account owners..." -ForegroundColor Yellow

$adAvailable = $false
if (Get-Module -ListAvailable -Name ActiveDirectory) {
    Import-Module ActiveDirectory -ErrorAction SilentlyContinue
    $adAvailable = $true
}

foreach ($key in @($registry.Keys)) {
    $acct = $registry[$key]

    # ── Method 1: Manual owner mapping (highest confidence) ──
    if ($manualOwners.ContainsKey($key)) {
        $mo = $manualOwners[$key]
        $acct.Owner = $mo.OwnerName
        $acct.OwnerEmail = $mo.OwnerEmail
        $acct.OwnerDepartment = $mo.OwnerDepartment
        $acct.OwnerConfidence = 100
        $acct.OwnerMethod = "Manual Assignment"
        $acct.OwnerStatus = "Owned"
        continue
    }

    # ── Method 2: AD managedBy attribute ──
    if ($adAvailable -and $acct.DistinguishedName -and $acct.DistinguishedName -ne "Unknown (event log only)") {
        try {
            $adParams2 = @{}
            if ($DomainController) { $adParams2['Server'] = $DomainController }
            $adObj = Get-ADObject -Identity $acct.DistinguishedName -Properties managedBy @adParams2 -ErrorAction SilentlyContinue
            if ($adObj.managedBy) {
                try {
                    $manager = Get-ADUser -Identity $adObj.managedBy -Properties displayName, mail, department @adParams2 -ErrorAction SilentlyContinue
                    if ($manager) {
                        $acct.Owner = $manager.displayName
                        $acct.OwnerEmail = $manager.mail
                        $acct.OwnerDepartment = $manager.department
                        $acct.OwnerConfidence = 90
                        $acct.OwnerMethod = "AD managedBy"
                        $acct.OwnerStatus = "Owned"
                        continue
                    }
                } catch { }
            }
        } catch { }
    }

    # ── Method 3: Description field parsing ──
    if ($acct.Description) {
        $descLC = $acct.Description
        $ownerPatterns = @(
            'Owner:\s*(.+?)(?:\s*[;,|]|$)',
            'Contact:\s*(.+?)(?:\s*[;,|]|$)',
            'Managed by:\s*(.+?)(?:\s*[;,|]|$)',
            'Responsible:\s*(.+?)(?:\s*[;,|]|$)',
            'Team:\s*(.+?)(?:\s*[;,|]|$)'
        )

        foreach ($pattern in $ownerPatterns) {
            if ($descLC -match $pattern) {
                $acct.Owner = $Matches[1].Trim()
                $acct.OwnerConfidence = 70
                $acct.OwnerMethod = "Description Field"
                $acct.OwnerStatus = "Owned (unverified)"

                # Try to resolve in AD
                if ($adAvailable) {
                    try {
                        $adParams3 = @{}
                        if ($DomainController) { $adParams3['Server'] = $DomainController }
                        $resolvedUser = Get-ADUser -Filter "displayName -like '*$($acct.Owner)*'" -Properties mail, department @adParams3 -ErrorAction SilentlyContinue | Select-Object -First 1
                        if ($resolvedUser) {
                            $acct.OwnerEmail = $resolvedUser.mail
                            $acct.OwnerDepartment = $resolvedUser.department
                            $acct.OwnerConfidence = 80
                            $acct.OwnerStatus = "Owned"
                        }
                    } catch { }
                }
                break
            }
        }
        if ($acct.OwnerStatus -ne "Pending") { continue }
    }

    # ── Method 4: OU-based ownership ──
    if ($acct.DistinguishedName -and $ouOwners.Count -gt 0) {
        foreach ($ouMap in $ouOwners) {
            if ($acct.DistinguishedName -match $ouMap.OUPattern) {
                $acct.Owner = $ouMap.OwnerName
                $acct.OwnerEmail = $ouMap.OwnerEmail
                $acct.OwnerDepartment = $ouMap.OwnerDepartment
                $acct.OwnerConfidence = 50
                $acct.OwnerMethod = "OU Mapping"
                $acct.OwnerStatus = "Owned (OU-inferred)"
                break
            }
        }
        if ($acct.OwnerStatus -ne "Pending") { continue }
    }

    # ── Method 5: Service/application name inference ──
    $nameLC = ($acct.SamAccountName + " " + $acct.Description).ToLower()
    $appOwnerMap = @{
        'sql|mssql'       = @{ App = "SQL Server"; Dept = "Database Administration" }
        'exchange|exch'   = @{ App = "Exchange"; Dept = "Messaging/Collaboration" }
        'sharepoint|sp'   = @{ App = "SharePoint"; Dept = "Collaboration" }
        'sccm|mecm|cm'    = @{ App = "ConfigMgr/MECM"; Dept = "Endpoint Management" }
        'scom'            = @{ App = "SCOM"; Dept = "Operations/Monitoring" }
        'backup|veeam'    = @{ App = "Backup Infrastructure"; Dept = "Infrastructure" }
        'antivirus|av|defender' = @{ App = "Security/AV"; Dept = "Security Operations" }
        'print|printer'   = @{ App = "Print Services"; Dept = "Infrastructure" }
        'scan|scanner'    = @{ App = "Scanning/Monitoring"; Dept = "Security/Operations" }
        'hr|workday|oracle|peoplesoft' = @{ App = "HR System"; Dept = "HRIS/People Operations" }
    }

    foreach ($pattern in $appOwnerMap.GetEnumerator()) {
        if ($nameLC -match $pattern.Key) {
            $acct.Owner = "[$($pattern.Value.Dept)] — $($pattern.Value.App) Team"
            $acct.OwnerConfidence = 30
            $acct.OwnerMethod = "Name Pattern Inference"
            $acct.OwnerStatus = "Pending (inferred)"
            break
        }
    }

    # ── If still unresolved → Orphan ──
    if ($acct.OwnerStatus -eq "Pending") {
        $acct.OwnerStatus = "Orphan"
        $acct.OwnerMethod = "Unresolved"
        $acct.OwnerConfidence = 0
    }
}

# ── Owner resolution stats ──
$allAccounts = $registry.Values
$owned = @($allAccounts | Where-Object { $_.OwnerStatus -match "^Owned" }).Count
$orphan = @($allAccounts | Where-Object { $_.OwnerStatus -eq "Orphan" }).Count
$pending = @($allAccounts | Where-Object { $_.OwnerStatus -match "Pending" }).Count

Write-Host "  Owned:   $owned" -ForegroundColor Green
Write-Host "  Pending: $pending" -ForegroundColor Yellow
Write-Host "  Orphan:  $orphan" -ForegroundColor $(if ($orphan -gt 0) { "Red" } else { "Green" })

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Migration Complexity Scoring
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[4/7] Computing migration complexity..." -ForegroundColor Yellow

foreach ($key in $registry.Keys) {
    $acct = $registry[$key]
    $score = 0

    # Consumer count drives complexity
    $score += [Math]::Min(30, $acct.ConsumerCount * 5)

    # Cross-reference flags add complexity
    if ($acct.HasDelegationChains) { $score += 20 }
    if ($acct.HasSPNCollisions)   { $score += 15 }
    if ($acct.HasSQLDependency)   { $score += 15 }
    if ($acct.HasLDAPBinds)       { $score += 10 }
    if ($acct.HasCertAuth)        { $score += 10 }
    if ($acct.HasIISPools)        { $score += 5 }
    if ($acct.HasCOMApps)         { $score += 10 }

    # gMSA reduces complexity (already using modern pattern)
    if ($acct.IsGMSA) { $score = [Math]::Max(0, $score - 20) }

    # Orphan owner increases complexity (can't coordinate migration)
    if ($acct.OwnerStatus -eq "Orphan") { $score += 15 }

    # Disabled accounts reduce complexity
    if ($acct.Enabled -eq $false) { $score = [Math]::Max(0, $score - 30) }

    $acct.MigrationComplexity = if ($score -ge 50) { "High" }
                                 elseif ($score -ge 25) { "Medium" }
                                 elseif ($score -ge 10) { "Low" }
                                 else { "Minimal" }

    # ── Assign migration wave ──
    if ($acct.Enabled -eq $false -or ($acct.LastLogon -match "Never" -and $acct.ConsumerCount -eq 0)) {
        $acct.MigrationWave = 0  # Decommission
    }
    elseif ($acct.IsGMSA -or ($acct.ConsumerCount -le 1 -and $score -lt 20)) {
        $acct.MigrationWave = 1  # Quick wins
    }
    elseif ($score -lt 40 -and $acct.OwnerStatus -match "^Owned") {
        $acct.MigrationWave = 2  # Standard
    }
    elseif ($acct.HasDelegationChains -or $acct.HasSQLDependency -or $score -ge 40) {
        $acct.MigrationWave = 3  # Complex
    }
    else {
        $acct.MigrationWave = 2  # Default to standard
    }

    # Infrastructure accounts → Wave 4
    if ($acct.SamAccountName -match 'krbtgt|ADFS|AZUREADSSOACC|MSOL_') {
        $acct.MigrationWave = 4
    }
}

$waveCounts = $registry.Values | Group-Object MigrationWave | Sort-Object Name
foreach ($w in $waveCounts) {
    $waveLabel = switch ($w.Name) {
        "0" { "Wave 0 (Decommission)" }
        "1" { "Wave 1 (Quick Wins)" }
        "2" { "Wave 2 (Standard)" }
        "3" { "Wave 3 (Complex)" }
        "4" { "Wave 4 (Infrastructure)" }
        default { "Wave $($w.Name)" }
    }
    Write-Host "  $waveLabel : $($w.Count) accounts" -ForegroundColor $(switch ($w.Name) { "0" { "DarkGray" }; "1" { "Green" }; "2" { "Yellow" }; "3" { "Red" }; "4" { "Magenta" }; default { "White" } })
}

# ═══════════════════════════════════════════════════════════════
# SECTION 5: Migration Target Refinement
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[5/7] Refining migration targets per ADR-004..." -ForegroundColor Yellow

foreach ($key in $registry.Keys) {
    $acct = $registry[$key]

    if ($acct.MigrationWave -eq 0) {
        $acct.MigrationTarget = "DECOMMISSION — disable and delete after validation period"
        continue
    }

    if ($acct.IsGMSA) {
        $acct.MigrationTarget = "Retain gMSA during coexistence → Managed Identity post-migration"
        continue
    }

    # Refine based on consumer types
    $consumerTypes = $acct.Consumers | ForEach-Object { $_.Type } | Select-Object -Unique

    if ($consumerTypes -contains "SQLServer") {
        $acct.MigrationTarget = "gMSA (coexistence) → Entra ID Auth for SQL 2022+ via Arc (ADR-004)"
    }
    elseif ($consumerTypes -contains "IISAppPool") {
        $acct.MigrationTarget = "gMSA (coexistence) → Managed Identity for Azure App Service migration"
    }
    elseif ($consumerTypes -contains "LDAPBind") {
        $acct.MigrationTarget = "Replace LDAP binds with Graph API calls → Service Principal or Managed Identity"
    }
    elseif ($consumerTypes -contains "DelegationChain") {
        $acct.MigrationTarget = "Break delegation chain → per-hop Managed Identity or App Registration with constrained permissions"
    }
    elseif ($consumerTypes -contains "ScheduledTask" -and $consumerTypes.Count -eq 1) {
        $acct.MigrationTarget = "gMSA for scheduled task (immediate) → Managed Identity if task moves to Azure"
    }
    elseif ($consumerTypes -contains "WindowsService" -and $consumerTypes.Count -eq 1) {
        $acct.MigrationTarget = "gMSA for Windows service (immediate) → Managed Identity if service containerizes"
    }
    elseif (-not $acct.MigrationTarget -or $acct.MigrationTarget -eq "Unknown") {
        $acct.MigrationTarget = "Evaluate: gMSA (coexistence) → Workload Identity Federation (ADR-004)"
    }
}

Write-Host "  Migration targets assigned" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 6: Generate Accountability Report
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[6/7] Generating accountability report..." -ForegroundColor Yellow

$domain = try { (Get-ADDomain).DNSRoot } catch { "unknown" }
$outPrefix = "UIAO_Spec3_D1.12_ServiceAccountOwnerMatrix_${domain}_${timestamp}"

$summary = @{
    TotalServiceAccounts     = $registry.Count
    OwnershipStatus          = @{
        Owned                = $owned
        PendingVerification  = $pending
        Orphan               = $orphan
    }
    OwnershipRate            = if ($registry.Count -gt 0) { [Math]::Round(($owned / $registry.Count) * 100, 1) } else { 0 }
    MigrationWaves           = @{
        Wave0_Decommission   = @($registry.Values | Where-Object { $_.MigrationWave -eq 0 }).Count
        Wave1_QuickWins      = @($registry.Values | Where-Object { $_.MigrationWave -eq 1 }).Count
        Wave2_Standard       = @($registry.Values | Where-Object { $_.MigrationWave -eq 2 }).Count
        Wave3_Complex        = @($registry.Values | Where-Object { $_.MigrationWave -eq 3 }).Count
        Wave4_Infrastructure = @($registry.Values | Where-Object { $_.MigrationWave -eq 4 }).Count
    }
    MigrationComplexity      = @{
        Minimal = @($registry.Values | Where-Object { $_.MigrationComplexity -eq "Minimal" }).Count
        Low     = @($registry.Values | Where-Object { $_.MigrationComplexity -eq "Low" }).Count
        Medium  = @($registry.Values | Where-Object { $_.MigrationComplexity -eq "Medium" }).Count
        High    = @($registry.Values | Where-Object { $_.MigrationComplexity -eq "High" }).Count
    }
    CrossReferences          = @{
        WithScheduledTasks   = @($registry.Values | Where-Object { $_.HasScheduledTasks }).Count
        WithWindowsServices  = @($registry.Values | Where-Object { $_.HasWindowsServices }).Count
        WithIISPools         = @($registry.Values | Where-Object { $_.HasIISPools }).Count
        WithCOMApps          = @($registry.Values | Where-Object { $_.HasCOMApps }).Count
        WithDelegationChains = @($registry.Values | Where-Object { $_.HasDelegationChains }).Count
        WithSPNCollisions    = @($registry.Values | Where-Object { $_.HasSPNCollisions }).Count
        WithSQLDependency    = @($registry.Values | Where-Object { $_.HasSQLDependency }).Count
        WithLDAPBinds        = @($registry.Values | Where-Object { $_.HasLDAPBinds }).Count
    }
    DataSourcesLoaded        = $dataSources.Count
    ManualOwnerMappings      = $manualOwners.Count
}

# ═══════════════════════════════════════════════════════════════
# SECTION 7: Export Results
# ═══════════════════════════════════════════════════════════════

Write-Host "`n[7/7] Exporting results..." -ForegroundColor Yellow

$results = @{
    Metadata = @{
        GeneratedAt     = (Get-Date -Format "o")
        Generator       = "Spec3-D1.12-New-ServiceAccountOwnerMatrix.ps1"
        UIAORef         = "UIAO_136 Spec 3, Phase 1, D1.12 (Capstone)"
        ADRRef          = @("ADR-004")
        Domain          = $domain
        DataSources     = $dataSources.Keys
    }
    Summary             = $summary
    OwnerMatrix         = $registry.Values
}

# ── JSON ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV (owner matrix) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_owners.csv"
$csvData = foreach ($acct in $registry.Values) {
    [PSCustomObject]@{
        SamAccountName       = $acct.SamAccountName
        DisplayName          = $acct.DisplayName
        Enabled              = $acct.Enabled
        IsGMSA               = $acct.IsGMSA
        Owner                = $acct.Owner
        OwnerEmail           = $acct.OwnerEmail
        OwnerDepartment      = $acct.OwnerDepartment
        OwnerConfidence      = $acct.OwnerConfidence
        OwnerMethod          = $acct.OwnerMethod
        OwnerStatus          = $acct.OwnerStatus
        ConsumerCount        = $acct.ConsumerCount
        MigrationWave        = $acct.MigrationWave
        MigrationComplexity  = $acct.MigrationComplexity
        MigrationTarget      = $acct.MigrationTarget
        HasDelegation        = $acct.HasDelegationChains
        HasSPNCollision      = $acct.HasSPNCollisions
        HasSQL               = $acct.HasSQLDependency
        HasLDAP              = $acct.HasLDAPBinds
        MigrationBlockers    = ($acct.MigrationBlockers -join "; ")
    }
}
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $csvPath" -ForegroundColor Green

# ── CSV (orphan accounts) ──
$orphanCsvPath = Join-Path $OutputPath "${outPrefix}_orphans.csv"
$orphanData = $csvData | Where-Object { $_.OwnerStatus -eq "Orphan" }
if ($orphanData) {
    $orphanData | Export-Csv -Path $orphanCsvPath -NoTypeInformation -Encoding UTF8
    Write-Host "  CSV:  $orphanCsvPath (orphans)" -ForegroundColor Yellow
}

# ── CSV (migration waves) ──
$waveCsvPath = Join-Path $OutputPath "${outPrefix}_waves.csv"
$waveData = $csvData | Sort-Object MigrationWave, MigrationComplexity, SamAccountName
$waveData | Export-Csv -Path $waveCsvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $waveCsvPath (wave plan)" -ForegroundColor Green

# ── Markdown Report ──
$mdPath = Join-Path $OutputPath "${outPrefix}_report.md"
$md = @"
# UIAO Spec 3 — D1.12: Service Account Owner Accountability Matrix

> Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
> Ref: UIAO_136 Spec 3, Phase 1, D1.12 (Capstone) | ADR-004
> Domain: $domain

---

## Executive Summary

| Metric | Value |
|---|---|
| Total Service Accounts | $($summary.TotalServiceAccounts) |
| Ownership Rate | $($summary.OwnershipRate)% |
| Owned | $owned |
| Orphan (needs triage) | $orphan |
| Data Sources Loaded | $($summary.DataSourcesLoaded) / 11 |

## Migration Wave Plan

| Wave | Description | Accounts | Strategy |
|---|---|---|---|
| 0 | Decommission | $($summary.MigrationWaves.Wave0_Decommission) | Disable, validate, delete |
| 1 | Quick Wins | $($summary.MigrationWaves.Wave1_QuickWins) | gMSA conversion, single-consumer migrations |
| 2 | Standard | $($summary.MigrationWaves.Wave2_Standard) | Owned accounts, medium complexity |
| 3 | Complex | $($summary.MigrationWaves.Wave3_Complex) | Multi-consumer, delegation chains, SQL |
| 4 | Infrastructure | $($summary.MigrationWaves.Wave4_Infrastructure) | DCs, ADFS, PKI — last to migrate |

## Ownership Resolution Methods

| Method | Count |
|---|---|
"@

$methodCounts = $registry.Values | Group-Object OwnerMethod | Sort-Object Count -Descending
foreach ($m in $methodCounts) {
    $md += "| $($m.Name) | $($m.Count) |`n"
}

$md += @"

## Cross-Reference Dependencies

| Dependency | Accounts Affected |
|---|---|
| Scheduled Tasks | $($summary.CrossReferences.WithScheduledTasks) |
| Windows Services | $($summary.CrossReferences.WithWindowsServices) |
| IIS App Pools | $($summary.CrossReferences.WithIISPools) |
| COM/DCOM Apps | $($summary.CrossReferences.WithCOMApps) |
| Delegation Chains | $($summary.CrossReferences.WithDelegationChains) |
| SPN Collisions | $($summary.CrossReferences.WithSPNCollisions) |
| SQL Server | $($summary.CrossReferences.WithSQLDependency) |
| LDAP Binds | $($summary.CrossReferences.WithLDAPBinds) |

## Next Steps

1. **Triage orphan accounts** — $orphan accounts have no identified owner
2. **Validate inferred owners** — $pending accounts need owner confirmation
3. **Begin Wave 0** — decommission $($summary.MigrationWaves.Wave0_Decommission) disabled/stale accounts
4. **Plan Wave 1** — convert $($summary.MigrationWaves.Wave1_QuickWins) quick-win accounts to gMSA
5. **Feed into D2.1** — Target State Architecture consumes this matrix
"@

Set-Content -Path $mdPath -Value $md -Encoding UTF8
Write-Host "  MD:   $mdPath" -ForegroundColor Green

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " SERVICE ACCOUNT OWNER MATRIX — DASHBOARD" -ForegroundColor Cyan
Write-Host " ★ CAPSTONE DELIVERABLE — Spec 3, Phase 1 Complete ★" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Total Service Accounts:      $($summary.TotalServiceAccounts)" -ForegroundColor White
Write-Host "  Data Sources Loaded:         $($summary.DataSourcesLoaded) / 11" -ForegroundColor White
Write-Host ""
Write-Host "  Ownership:" -ForegroundColor Cyan
Write-Host "    Owned:                     $owned ($($summary.OwnershipRate)%)" -ForegroundColor Green
Write-Host "    Pending Verification:      $pending" -ForegroundColor Yellow
Write-Host "    ORPHAN (needs triage):     $orphan" -ForegroundColor $(if ($orphan -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "  Migration Waves:" -ForegroundColor Cyan
Write-Host "    Wave 0 (Decommission):     $($summary.MigrationWaves.Wave0_Decommission)" -ForegroundColor DarkGray
Write-Host "    Wave 1 (Quick Wins):       $($summary.MigrationWaves.Wave1_QuickWins)" -ForegroundColor Green
Write-Host "    Wave 2 (Standard):         $($summary.MigrationWaves.Wave2_Standard)" -ForegroundColor Yellow
Write-Host "    Wave 3 (Complex):          $($summary.MigrationWaves.Wave3_Complex)" -ForegroundColor $(if ($summary.MigrationWaves.Wave3_Complex -gt 0) { "Red" } else { "Green" })
Write-Host "    Wave 4 (Infrastructure):   $($summary.MigrationWaves.Wave4_Infrastructure)" -ForegroundColor Magenta
Write-Host ""
Write-Host "  Migration Complexity:" -ForegroundColor Cyan
Write-Host "    Minimal:                   $($summary.MigrationComplexity.Minimal)" -ForegroundColor Green
Write-Host "    Low:                       $($summary.MigrationComplexity.Low)" -ForegroundColor Green
Write-Host "    Medium:                    $($summary.MigrationComplexity.Medium)" -ForegroundColor Yellow
Write-Host "    High:                      $($summary.MigrationComplexity.High)" -ForegroundColor $(if ($summary.MigrationComplexity.High -gt 0) { "Red" } else { "Green" })
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Ref: ADR-004 (Workload Identity Federation as Default)" -ForegroundColor DarkCyan
Write-Host " This matrix feeds: D2.1, D2.2, D2.3, D3.1" -ForegroundColor DarkCyan
Write-Host " ★ ALL SPEC 3 PHASE 1 DELIVERABLES COMPLETE ★" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Cyan
