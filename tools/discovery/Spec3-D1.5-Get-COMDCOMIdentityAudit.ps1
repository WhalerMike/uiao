<#
.SYNOPSIS
    UIAO Spec 3 — D1.5: COM+/DCOM Application Identity Audit
.DESCRIPTION
    Scans local and remote servers for COM+ applications and DCOM configurations
    running under domain accounts that must be migrated to workload identities.

    Discovery passes:
    1. COM+ Application Inventory — COMAdmin.COMAdminCatalog enumeration of all
       COM+ applications: name, identity (RunAs account), activation type
       (Server/Library), authentication level, impersonation level, constructor
       strings, role-based security configuration
    2. DCOM Application Inventory — WMI Win32_DCOMApplicationSetting enumeration:
       AppID, identity, authentication level, launch/access permissions (SDDL
       parsing for domain account ACEs), remote activation status
    3. Domain Account Resolution — Cross-reference discovered identities against
       AD to determine: account type (user/service/gMSA), delegation flags,
       SPNs registered, group memberships, AdminCount, password age
    4. Permission Analysis — Parse SDDL launch/access permission strings to
       identify domain accounts with Launch, Activate, or Access rights
    5. D1.1 Cross-Reference — Enrich with service account classification from
       Spec 3 D1.1 scan (risk score, migration target, account type)
    6. Risk Classification — Score each COM+/DCOM application:
       - Critical: runs as domain admin or has unconstrained delegation
       - High: shared credentials across multiple apps, or AdminCount=1
       - Medium: domain user account with password-never-expires
       - Low: gMSA or built-in identity (no migration needed)

    Outputs:
    - JSON with full detail (COM+ apps, DCOM apps, domain accounts, risk)
    - CSV inventory of COM+ applications with migration recommendations
    - CSV inventory of DCOM applications with migration recommendations
    - Color-coded console dashboard

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.5
         Feeds: D2.1 (Workload Identity Mapping), D1.6 (Delegation Chain Map)
         Related: ADR-004 (Workload Identity Federation as default)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER ComputerName
    Target server(s) for remote scanning. If omitted, scans localhost.
    Accepts pipeline input or comma-separated values.
.PARAMETER D1InputFile
    Optional path to D1.1 Service Account Scan JSON for cross-reference.
.PARAMETER Credential
    Optional PSCredential for remote WinRM connections.
.PARAMETER SkipDCOM
    Skip DCOM discovery (COM+ only).
.PARAMETER SkipCOMPlus
    Skip COM+ discovery (DCOM only).
.EXAMPLE
    .\Spec3-D1.5-Get-COMDCOMIdentityAudit.ps1
    .\Spec3-D1.5-Get-COMDCOMIdentityAudit.ps1 -ComputerName SERVER01,SERVER02
    .\Spec3-D1.5-Get-COMDCOMIdentityAudit.ps1 -D1InputFile .\output\ServiceAccountScan.json
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for account resolution
    Requires: WinRM access for remote servers
    Requires: Local admin rights for COM+ catalog access
    COM+ enumeration uses COMAdmin.COMAdminCatalog COM object
    DCOM enumeration uses WMI Win32_DCOMApplicationSetting
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string[]]$ComputerName = @($env:COMPUTERNAME),
    [string]$D1InputFile,
    [PSCredential]$Credential,
    [switch]$SkipDCOM,
    [switch]$SkipCOMPlus
)

$ErrorActionPreference = "Stop"

# ── Prerequisites ──
if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Warning "ActiveDirectory module not found. Account resolution will be limited."
    $hasADModule = $false
} else {
    Import-Module ActiveDirectory -ErrorAction Stop
    $hasADModule = $true
}

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = if ($hasADModule) { (Get-ADDomain).DNSRoot } else { $env:USERDNSDOMAIN }
$outPrefix = "UIAO_Spec3_D1.5_COMDCOMIdentityAudit_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 3 — D1.5: COM+/DCOM Application Identity Audit"     -ForegroundColor Cyan
Write-Host "  Targets:   $($ComputerName -join ', ')"                         -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                             -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                          -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════
# D1.1 Cross-Reference Load
# ══════════════════════════════════════════════════════════════

$d1Data = $null
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  Loading D1.1 cross-reference: $D1InputFile" -ForegroundColor Yellow
    $d1Data = Get-Content $D1InputFile -Raw | ConvertFrom-Json
    $d1Lookup = @{}
    if ($d1Data.ServiceAccounts) {
        foreach ($sa in $d1Data.ServiceAccounts) {
            $key = ($sa.SamAccountName ?? $sa.Name ?? "").ToLower()
            if ($key) { $d1Lookup[$key] = $sa }
        }
    }
    Write-Host "    Loaded $($d1Lookup.Count) service accounts for cross-reference" -ForegroundColor Green
} else {
    $d1Lookup = @{}
}

# ══════════════════════════════════════════════════════════════
# Helper: SDDL Permission Parser
# ══════════════════════════════════════════════════════════════

function ConvertFrom-DCOMPermissionSDDL {
    param([string]$SDDL, [string]$PermissionType)

    if (-not $SDDL) { return @() }

    $results = [System.Collections.Generic.List[object]]::new()

    # Parse DACL ACEs: (AceType;;Rights;;;SID)
    $acePattern = '\(([^)]+)\)'
    $matches2 = [regex]::Matches($SDDL, $acePattern)

    foreach ($m in $matches2) {
        $parts = $m.Groups[1].Value -split ';'
        if ($parts.Count -lt 6) { continue }

        $aceType = $parts[0]
        $rights  = $parts[2]
        $sid     = $parts[5]

        # Map ACE type
        $accessType = switch ($aceType) {
            'A'  { 'Allow' }
            'D'  { 'Deny' }
            default { $aceType }
        }

        # Try to resolve SID to account name
        $accountName = $sid
        try {
            $sidObj = New-Object System.Security.Principal.SecurityIdentifier($sid)
            $accountName = $sidObj.Translate([System.Security.Principal.NTAccount]).Value
        } catch {
            # Keep raw SID
        }

        # Determine if this is a domain account (not BUILTIN, NT AUTHORITY, etc.)
        $isDomainAccount = $false
        if ($accountName -match '^[A-Za-z0-9]+\\' -and
            $accountName -notmatch '^(BUILTIN|NT AUTHORITY|NT SERVICE|IIS APPPOOL)\\') {
            $isDomainAccount = $true
        }

        $results.Add([ordered]@{
            PermissionType = $PermissionType
            AccessType     = $accessType
            Rights         = $rights
            SID            = $sid
            AccountName    = $accountName
            IsDomainAccount = $isDomainAccount
        })
    }

    return $results
}

# ══════════════════════════════════════════════════════════════
# Helper: Resolve Domain Account Details
# ══════════════════════════════════════════════════════════════

$resolvedAccountCache = @{}

function Resolve-DomainAccountDetails {
    param([string]$AccountIdentity)

    if (-not $hasADModule) { return $null }
    if (-not $AccountIdentity) { return $null }

    # Normalize — strip domain prefix if present
    $samName = $AccountIdentity
    if ($samName -match '^[^\\]+\\(.+)$') { $samName = $Matches[1] }
    $cacheKey = $samName.ToLower()

    if ($resolvedAccountCache.ContainsKey($cacheKey)) {
        return $resolvedAccountCache[$cacheKey]
    }

    try {
        $adObj = Get-ADUser -Identity $samName -Properties `
            SamAccountName, UserPrincipalName, Enabled, PasswordNeverExpires,
            PasswordLastSet, LastLogonDate, AdminCount, ServicePrincipalName,
            MemberOf, TrustedForDelegation, TrustedToAuthForDelegation,
            'msDS-AllowedToDelegateTo', 'msDS-AllowedToActOnBehalfOfOtherIdentity',
            Description -ErrorAction Stop

        $result = [ordered]@{
            SamAccountName         = $adObj.SamAccountName
            UPN                    = $adObj.UserPrincipalName
            Enabled                = $adObj.Enabled
            PasswordNeverExpires   = $adObj.PasswordNeverExpires
            PasswordLastSet        = $adObj.PasswordLastSet
            PasswordAgeDays        = if ($adObj.PasswordLastSet) {
                                        [math]::Round(((Get-Date) - $adObj.PasswordLastSet).TotalDays)
                                     } else { -1 }
            LastLogonDate          = $adObj.LastLogonDate
            AdminCount             = $adObj.AdminCount
            SPNCount               = @($adObj.ServicePrincipalName).Count
            SPNs                   = @($adObj.ServicePrincipalName)
            GroupCount             = @($adObj.MemberOf).Count
            UnconstrainedDelegation = $adObj.TrustedForDelegation
            ProtocolTransition     = $adObj.TrustedToAuthForDelegation
            KCDTargetCount         = @($adObj.'msDS-AllowedToDelegateTo').Count
            HasRBCD                = $null -ne $adObj.'msDS-AllowedToActOnBehalfOfOtherIdentity'
            Description            = $adObj.Description
            ObjectType             = 'User'
        }
        $resolvedAccountCache[$cacheKey] = $result
        return $result
    } catch {
        # Try as computer object
        try {
            $adObj = Get-ADComputer -Identity $samName -Properties `
                SamAccountName, Enabled, TrustedForDelegation -ErrorAction Stop
            $result = [ordered]@{
                SamAccountName          = $adObj.SamAccountName
                Enabled                 = $adObj.Enabled
                UnconstrainedDelegation = $adObj.TrustedForDelegation
                ObjectType              = 'Computer'
            }
            $resolvedAccountCache[$cacheKey] = $result
            return $result
        } catch {
            $resolvedAccountCache[$cacheKey] = $null
            return $null
        }
    }
}

# ══════════════════════════════════════════════════════════════
# Helper: Classify Identity Type
# ══════════════════════════════════════════════════════════════

function Get-IdentityClassification {
    param([string]$Identity)

    if (-not $Identity) { return "Unknown" }

    $id = $Identity.Trim()

    switch -Regex ($id) {
        '^(Interactive User|Launching User)$'           { return "Interactive" }
        '^$'                                             { return "Interactive" }
        '^(LocalSystem|Local System|NT AUTHORITY\\SYSTEM|\.\\LocalSystem)$' { return "BuiltIn-System" }
        '^(NT AUTHORITY\\LOCAL SERVICE|LocalService)$'   { return "BuiltIn-LocalService" }
        '^(NT AUTHORITY\\NETWORK SERVICE|NetworkService)$' { return "BuiltIn-NetworkService" }
        '^NT SERVICE\\'                                  { return "BuiltIn-ServiceAccount" }
        '^IIS APPPOOL\\'                                 { return "IIS-AppPool" }
        '^BUILTIN\\'                                     { return "BuiltIn-Group" }
        default {
            if ($id -match '^[A-Za-z0-9]+\\.+\$$') { return "MachineAccount" }
            if ($id -match '^[A-Za-z0-9]+\\') { return "DomainAccount" }
            return "Unknown"
        }
    }
}

# ══════════════════════════════════════════════════════════════
# Helper: Risk Scoring
# ══════════════════════════════════════════════════════════════

function Get-ApplicationRiskScore {
    param(
        [string]$IdentityClass,
        $AccountDetails,
        $D1Record,
        [bool]$IsSharedCredential
    )

    # Built-in identities — no migration needed
    if ($IdentityClass -match '^(BuiltIn|Interactive|IIS-AppPool|MachineAccount)') {
        return [ordered]@{
            Level      = "Low"
            Score      = 1
            Factors    = @("Uses built-in identity — no migration needed")
            MigrationTarget = "None — retain current identity"
        }
    }

    $factors = [System.Collections.Generic.List[string]]::new()
    $score = 3  # Base score for domain accounts

    # Check D1.1 data first
    if ($D1Record) {
        if ($D1Record.RiskLevel -eq 'Critical') { $score += 4; $factors.Add("D1.1 Critical risk") }
        elseif ($D1Record.RiskLevel -eq 'High') { $score += 3; $factors.Add("D1.1 High risk") }
    }

    if ($AccountDetails) {
        if ($AccountDetails.AdminCount -eq 1) {
            $score += 3; $factors.Add("AdminCount=1 (privileged)")
        }
        if ($AccountDetails.UnconstrainedDelegation) {
            $score += 4; $factors.Add("Unconstrained delegation")
        }
        if ($AccountDetails.ProtocolTransition) {
            $score += 2; $factors.Add("Protocol transition enabled")
        }
        if ($AccountDetails.PasswordNeverExpires) {
            $score += 1; $factors.Add("Password never expires")
        }
        if ($AccountDetails.PasswordAgeDays -gt 365) {
            $score += 1; $factors.Add("Password age > 365 days ($($AccountDetails.PasswordAgeDays)d)")
        }
        if ($AccountDetails.KCDTargetCount -gt 0) {
            $score += 1; $factors.Add("KCD configured ($($AccountDetails.KCDTargetCount) targets)")
        }
    }

    if ($IsSharedCredential) {
        $score += 2; $factors.Add("Shared credential across multiple applications")
    }

    # Determine level and migration target
    $level = switch {
        ($score -ge 8) { "Critical" }
        ($score -ge 5) { "High" }
        ($score -ge 3) { "Medium" }
        default        { "Low" }
    }

    $migrationTarget = switch ($level) {
        "Critical" { "Managed Identity (immediate) — eliminate domain admin dependency per ADR-004" }
        "High"     { "Managed Identity or Workload Identity Federation — isolate credentials" }
        "Medium"   { "Workload Identity Federation or certificate-based auth" }
        "Low"      { "Workload Identity Federation (standard migration)" }
    }

    return [ordered]@{
        Level           = $level
        Score           = $score
        Factors         = @($factors)
        MigrationTarget = $migrationTarget
    }
}

# ══════════════════════════════════════════════════════════════
# Pass 1: COM+ Application Discovery
# ══════════════════════════════════════════════════════════════

$allCOMPlusApps = [System.Collections.Generic.List[object]]::new()
$comPlusErrors  = [System.Collections.Generic.List[string]]::new()

if (-not $SkipCOMPlus) {
    Write-Host "  Pass 1: COM+ Application Discovery" -ForegroundColor Yellow

    foreach ($server in $ComputerName) {
        $isLocal = ($server -eq $env:COMPUTERNAME -or $server -eq 'localhost' -or $server -eq '.')
        Write-Host "    Scanning: $server $(if ($isLocal) { '(local)' })" -ForegroundColor Gray

        $scriptBlock = {
            try {
                $catalog = New-Object -ComObject COMAdmin.COMAdminCatalog
                $apps = $catalog.GetCollection("Applications")
                $apps.Populate()

                $results = @()
                foreach ($app in $apps) {
                    $appName    = $app.Value("Name")
                    $appId      = $app.Value("ID")
                    $identity   = $app.Value("Identity")
                    $activation = if ($app.Value("Activation") -eq 1) { "Server" } else { "Library" }
                    $authLevel  = $app.Value("Authentication")
                    $impLevel   = $app.Value("ImpersonationLevel")
                    $roleBased  = $app.Value("ApplicationAccessChecksEnabled")
                    $secEnabled = $app.Value("AccessChecksLevel")

                    # Get components
                    $components = $catalog.GetCollection("Components", $app.Key)
                    $components.Populate()
                    $componentList = @()
                    foreach ($comp in $components) {
                        $componentList += [ordered]@{
                            Name        = $comp.Value("ProgID")
                            CLSID       = $comp.Value("CLSID")
                            Constructor = try { $comp.Value("ConstructorString") } catch { "" }
                            Transaction = $comp.Value("Transaction")
                        }
                    }

                    $results += [ordered]@{
                        Name                = $appName
                        AppID               = $appId
                        Identity            = $identity
                        ActivationType      = $activation
                        AuthenticationLevel = $authLevel
                        ImpersonationLevel  = $impLevel
                        RoleBasedSecurity   = $roleBased
                        SecurityCheckLevel  = $secEnabled
                        ComponentCount      = $componentList.Count
                        Components          = $componentList
                    }
                }
                return $results
            } catch {
                return @{ Error = $_.Exception.Message }
            }
        }

        try {
            $comApps = $null
            if ($isLocal) {
                $comApps = & $scriptBlock
            } else {
                $sessionParams = @{ ComputerName = $server }
                if ($Credential) { $sessionParams['Credential'] = $Credential }
                $session = New-PSSession @sessionParams
                try {
                    $comApps = Invoke-Command -Session $session -ScriptBlock $scriptBlock
                } finally {
                    Remove-PSSession $session -ErrorAction SilentlyContinue
                }
            }

            if ($comApps -is [hashtable] -and $comApps.Error) {
                $comPlusErrors.Add("$server : $($comApps.Error)")
                Write-Host "      Error: $($comApps.Error)" -ForegroundColor Red
                continue
            }

            foreach ($app in $comApps) {
                $identityClass = Get-IdentityClassification -Identity $app.Identity
                $allCOMPlusApps.Add([ordered]@{
                    Server            = $server
                    ApplicationName   = $app.Name
                    AppID             = $app.AppID
                    Identity          = $app.Identity
                    IdentityClass     = $identityClass
                    ActivationType    = $app.ActivationType
                    AuthLevel         = $app.AuthenticationLevel
                    ImpersonationLevel = $app.ImpersonationLevel
                    RoleBasedSecurity = $app.RoleBasedSecurity
                    ComponentCount    = $app.ComponentCount
                    Components        = $app.Components
                })
            }

            $domainCount = @($comApps | Where-Object {
                (Get-IdentityClassification -Identity $_.Identity) -eq 'DomainAccount'
            }).Count
            Write-Host "      Found $($comApps.Count) COM+ apps ($domainCount with domain accounts)" -ForegroundColor Green

        } catch {
            $comPlusErrors.Add("$server : $($_.Exception.Message)")
            Write-Host "      Connection failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host "    Total COM+ applications: $($allCOMPlusApps.Count)" -ForegroundColor White
}

# ══════════════════════════════════════════════════════════════
# Pass 2: DCOM Application Discovery
# ══════════════════════════════════════════════════════════════

$allDCOMApps   = [System.Collections.Generic.List[object]]::new()
$dcomErrors    = [System.Collections.Generic.List[string]]::new()

if (-not $SkipDCOM) {
    Write-Host "`n  Pass 2: DCOM Application Discovery" -ForegroundColor Yellow

    foreach ($server in $ComputerName) {
        $isLocal = ($server -eq $env:COMPUTERNAME -or $server -eq 'localhost' -or $server -eq '.')
        Write-Host "    Scanning: $server $(if ($isLocal) { '(local)' })" -ForegroundColor Gray

        try {
            $wmiParams = @{ Class = 'Win32_DCOMApplicationSetting'; Namespace = 'root\cimv2' }
            if (-not $isLocal) {
                $wmiParams['ComputerName'] = $server
                if ($Credential) { $wmiParams['Credential'] = $Credential }
            }

            $dcomApps = Get-CimInstance @wmiParams -ErrorAction Stop

            foreach ($dcom in $dcomApps) {
                $appId = $dcom.AppID
                $appName = $dcom.Caption ?? "(No Caption)"
                $authLevel = $dcom.AuthenticationLevel
                $runAs = $dcom.RunAsUser

                # Get DCOM permissions from registry (launch + access)
                $launchPerms = @()
                $accessPerms = @()

                $regBlock = {
                    param($AppId)
                    $result = @{ Launch = $null; Access = $null }
                    try {
                        $regPath = "HKLM:\SOFTWARE\Classes\AppID\$AppId"
                        if (Test-Path $regPath) {
                            $launchPerm = (Get-ItemProperty $regPath -Name 'LaunchPermission' -ErrorAction SilentlyContinue).LaunchPermission
                            $accessPerm = (Get-ItemProperty $regPath -Name 'AccessPermission' -ErrorAction SilentlyContinue).AccessPermission
                            if ($launchPerm) {
                                $sd = New-Object System.Security.AccessControl.RawSecurityDescriptor($launchPerm, 0)
                                $result.Launch = $sd.GetSddlForm('All')
                            }
                            if ($accessPerm) {
                                $sd = New-Object System.Security.AccessControl.RawSecurityDescriptor($accessPerm, 0)
                                $result.Access = $sd.GetSddlForm('All')
                            }
                        }
                    } catch {}
                    return $result
                }

                $permData = $null
                try {
                    if ($isLocal) {
                        $permData = & $regBlock -AppId $appId
                    } else {
                        $sessionParams = @{ ComputerName = $server }
                        if ($Credential) { $sessionParams['Credential'] = $Credential }
                        $permData = Invoke-Command -ComputerName $server -ScriptBlock $regBlock `
                            -ArgumentList $appId @(if ($Credential) { @{Credential = $Credential} } else { @{} })
                    }
                } catch {}

                if ($permData) {
                    if ($permData.Launch) {
                        $launchPerms = ConvertFrom-DCOMPermissionSDDL -SDDL $permData.Launch -PermissionType "Launch"
                    }
                    if ($permData.Access) {
                        $accessPerms = ConvertFrom-DCOMPermissionSDDL -SDDL $permData.Access -PermissionType "Access"
                    }
                }

                $identityClass = if ($runAs) {
                    Get-IdentityClassification -Identity $runAs
                } else {
                    "Interactive"
                }

                $domainPerms = @($launchPerms + $accessPerms | Where-Object { $_.IsDomainAccount })

                $allDCOMApps.Add([ordered]@{
                    Server              = $server
                    ApplicationName     = $appName
                    AppID               = $appId
                    RunAsUser           = $runAs
                    IdentityClass       = $identityClass
                    AuthenticationLevel = $authLevel
                    LaunchPermissions   = @($launchPerms)
                    AccessPermissions   = @($accessPerms)
                    DomainPermissionCount = $domainPerms.Count
                })
            }

            $domainRunAs = @($dcomApps | Where-Object {
                $_.RunAsUser -and (Get-IdentityClassification -Identity $_.RunAsUser) -eq 'DomainAccount'
            }).Count
            Write-Host "      Found $($dcomApps.Count) DCOM apps ($domainRunAs with domain RunAs)" -ForegroundColor Green

        } catch {
            $dcomErrors.Add("$server : $($_.Exception.Message)")
            Write-Host "      Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host "    Total DCOM applications: $($allDCOMApps.Count)" -ForegroundColor White
}

# ══════════════════════════════════════════════════════════════
# Pass 3: Domain Account Resolution
# ══════════════════════════════════════════════════════════════

Write-Host "`n  Pass 3: Domain Account Resolution" -ForegroundColor Yellow

# Collect unique domain accounts from COM+ and DCOM
$domainAccountIdentities = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase)

foreach ($app in $allCOMPlusApps) {
    if ($app.IdentityClass -eq 'DomainAccount' -and $app.Identity) {
        $domainAccountIdentities.Add($app.Identity) | Out-Null
    }
}
foreach ($app in $allDCOMApps) {
    if ($app.IdentityClass -eq 'DomainAccount' -and $app.RunAsUser) {
        $domainAccountIdentities.Add($app.RunAsUser) | Out-Null
    }
}

Write-Host "    Unique domain accounts found: $($domainAccountIdentities.Count)"

$resolvedAccounts = [ordered]@{}
foreach ($acct in $domainAccountIdentities) {
    $details = Resolve-DomainAccountDetails -AccountIdentity $acct
    $resolvedAccounts[$acct] = $details
    if ($details) {
        Write-Host "      Resolved: $acct -> $($details.ObjectType)" -ForegroundColor Gray
    } else {
        Write-Host "      Unresolved: $acct" -ForegroundColor DarkYellow
    }
}

# ══════════════════════════════════════════════════════════════
# Pass 4: Shared Credential Detection
# ══════════════════════════════════════════════════════════════

Write-Host "`n  Pass 4: Shared Credential Detection" -ForegroundColor Yellow

$credentialUsage = @{}
foreach ($app in $allCOMPlusApps) {
    if ($app.IdentityClass -eq 'DomainAccount' -and $app.Identity) {
        $key = $app.Identity.ToLower()
        if (-not $credentialUsage[$key]) { $credentialUsage[$key] = @() }
        $credentialUsage[$key] += [ordered]@{
            Type   = "COM+"
            Server = $app.Server
            App    = $app.ApplicationName
        }
    }
}
foreach ($app in $allDCOMApps) {
    if ($app.IdentityClass -eq 'DomainAccount' -and $app.RunAsUser) {
        $key = $app.RunAsUser.ToLower()
        if (-not $credentialUsage[$key]) { $credentialUsage[$key] = @() }
        $credentialUsage[$key] += [ordered]@{
            Type   = "DCOM"
            Server = $app.Server
            App    = $app.ApplicationName
        }
    }
}

$sharedCredentials = @($credentialUsage.GetEnumerator() | Where-Object { $_.Value.Count -gt 1 })
Write-Host "    Shared credentials (>1 app): $($sharedCredentials.Count)"

# ══════════════════════════════════════════════════════════════
# Pass 5: Risk Classification
# ══════════════════════════════════════════════════════════════

Write-Host "`n  Pass 5: Risk Classification" -ForegroundColor Yellow

# Enrich COM+ apps with risk
foreach ($app in $allCOMPlusApps) {
    $acctDetails = if ($app.Identity) { $resolvedAccounts[$app.Identity] } else { $null }
    $d1Record = if ($app.Identity) {
        $sam = $app.Identity
        if ($sam -match '^[^\\]+\\(.+)$') { $sam = $Matches[1] }
        $d1Lookup[$sam.ToLower()]
    } else { $null }
    $isShared = if ($app.Identity) {
        $key = $app.Identity.ToLower()
        $credentialUsage.ContainsKey($key) -and $credentialUsage[$key].Count -gt 1
    } else { $false }

    $risk = Get-ApplicationRiskScore -IdentityClass $app.IdentityClass `
        -AccountDetails $acctDetails -D1Record $d1Record -IsSharedCredential $isShared

    $app['RiskLevel']       = $risk.Level
    $app['RiskScore']       = $risk.Score
    $app['RiskFactors']     = $risk.Factors
    $app['MigrationTarget'] = $risk.MigrationTarget
    $app['AccountDetails']  = $acctDetails
    $app['D1CrossRef']      = if ($d1Record) { $true } else { $false }
}

# Enrich DCOM apps with risk
foreach ($app in $allDCOMApps) {
    $acctDetails = if ($app.RunAsUser) { $resolvedAccounts[$app.RunAsUser] } else { $null }
    $d1Record = if ($app.RunAsUser) {
        $sam = $app.RunAsUser
        if ($sam -match '^[^\\]+\\(.+)$') { $sam = $Matches[1] }
        $d1Lookup[$sam.ToLower()]
    } else { $null }
    $isShared = if ($app.RunAsUser) {
        $key = $app.RunAsUser.ToLower()
        $credentialUsage.ContainsKey($key) -and $credentialUsage[$key].Count -gt 1
    } else { $false }

    $risk = Get-ApplicationRiskScore -IdentityClass $app.IdentityClass `
        -AccountDetails $acctDetails -D1Record $d1Record -IsSharedCredential $isShared

    $app['RiskLevel']       = $risk.Level
    $app['RiskScore']       = $risk.Score
    $app['RiskFactors']     = $risk.Factors
    $app['MigrationTarget'] = $risk.MigrationTarget
    $app['AccountDetails']  = $acctDetails
    $app['D1CrossRef']      = if ($d1Record) { $true } else { $false }
}

# ══════════════════════════════════════════════════════════════
# Summary Statistics
# ══════════════════════════════════════════════════════════════

$comDomainApps  = @($allCOMPlusApps | Where-Object { $_.IdentityClass -eq 'DomainAccount' })
$dcomDomainApps = @($allDCOMApps    | Where-Object { $_.IdentityClass -eq 'DomainAccount' })

$comRiskDist  = @($comDomainApps  | Group-Object { $_.RiskLevel })
$dcomRiskDist = @($dcomDomainApps | Group-Object { $_.RiskLevel })

$allDomainApps = @($comDomainApps) + @($dcomDomainApps)
$overallRisk  = @($allDomainApps | Group-Object { $_.RiskLevel })

$summary = [ordered]@{
    COMPlus = [ordered]@{
        TotalApplications   = $allCOMPlusApps.Count
        DomainAccountApps   = $comDomainApps.Count
        BuiltInIdentityApps = @($allCOMPlusApps | Where-Object { $_.IdentityClass -match '^BuiltIn' }).Count
        InteractiveApps     = @($allCOMPlusApps | Where-Object { $_.IdentityClass -eq 'Interactive' }).Count
        RiskDistribution    = [ordered]@{}
    }
    DCOM = [ordered]@{
        TotalApplications   = $allDCOMApps.Count
        DomainRunAsApps     = $dcomDomainApps.Count
        BuiltInIdentityApps = @($allDCOMApps | Where-Object { $_.IdentityClass -match '^BuiltIn' }).Count
        InteractiveApps     = @($allDCOMApps | Where-Object { $_.IdentityClass -eq 'Interactive' }).Count
        DomainPermissionApps = @($allDCOMApps | Where-Object { $_.DomainPermissionCount -gt 0 }).Count
        RiskDistribution    = [ordered]@{}
    }
    Overall = [ordered]@{
        TotalDomainAccountApps = $allDomainApps.Count
        UniqueCredentials      = $domainAccountIdentities.Count
        SharedCredentials      = $sharedCredentials.Count
        ServersScanned         = $ComputerName.Count
        RiskDistribution       = [ordered]@{}
    }
}

foreach ($g in $comRiskDist)  { $summary.COMPlus.RiskDistribution[$g.Name] = $g.Count }
foreach ($g in $dcomRiskDist) { $summary.DCOM.RiskDistribution[$g.Name] = $g.Count }
foreach ($g in $overallRisk)  { $summary.Overall.RiskDistribution[$g.Name] = $g.Count }

# ══════════════════════════════════════════════════════════════
# Output Files
# ══════════════════════════════════════════════════════════════

# JSON — full detail
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
$jsonOutput = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain        = $domain
        Timestamp     = (Get-Date).ToString("o")
        ServersScanned = $ComputerName
        Script        = "UIAO Spec 3 D1.5 — COM+/DCOM Application Identity Audit"
        Reference     = "UIAO_136, ADR-004"
        D1InputFile   = $D1InputFile
    }
    Summary           = $summary
    COMPlusApplications = @($allCOMPlusApps)
    DCOMApplications    = @($allDCOMApps)
    ResolvedAccounts    = $resolvedAccounts
    SharedCredentials   = @($sharedCredentials | ForEach-Object {
        [ordered]@{
            Account  = $_.Key
            UsageCount = $_.Value.Count
            Usage    = $_.Value
        }
    })
    Errors = [ordered]@{
        COMPlus = @($comPlusErrors)
        DCOM    = @($dcomErrors)
    }
}

$jsonOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# CSV — COM+ inventory
$comCSV = Join-Path $OutputPath "${outPrefix}_COMPlus.csv"
$comDomainApps | ForEach-Object {
    [PSCustomObject]@{
        Server          = $_.Server
        ApplicationName = $_.ApplicationName
        AppID           = $_.AppID
        Identity        = $_.Identity
        ActivationType  = $_.ActivationType
        ComponentCount  = $_.ComponentCount
        RiskLevel       = $_.RiskLevel
        RiskScore       = $_.RiskScore
        RiskFactors     = ($_.RiskFactors -join '; ')
        MigrationTarget = $_.MigrationTarget
        D1CrossRef      = $_.D1CrossRef
    }
} | Export-Csv -Path $comCSV -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (COM+): $comCSV" -ForegroundColor Green

# CSV — DCOM inventory
$dcomCSV = Join-Path $OutputPath "${outPrefix}_DCOM.csv"
$dcomDomainApps | ForEach-Object {
    [PSCustomObject]@{
        Server              = $_.Server
        ApplicationName     = $_.ApplicationName
        AppID               = $_.AppID
        RunAsUser           = $_.RunAsUser
        AuthenticationLevel = $_.AuthenticationLevel
        DomainPermissions   = $_.DomainPermissionCount
        RiskLevel           = $_.RiskLevel
        RiskScore           = $_.RiskScore
        RiskFactors         = ($_.RiskFactors -join '; ')
        MigrationTarget     = $_.MigrationTarget
        D1CrossRef          = $_.D1CrossRef
    }
} | Export-Csv -Path $dcomCSV -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV (DCOM): $dcomCSV" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Console Dashboard
# ══════════════════════════════════════════════════════════════

Write-Host "`n-- COM+/DCOM Identity Audit Summary --" -ForegroundColor Cyan
Write-Host "  Servers Scanned:         $($ComputerName.Count)"

if (-not $SkipCOMPlus) {
    Write-Host "`n  COM+ Applications:" -ForegroundColor White
    Write-Host "    Total:                 $($allCOMPlusApps.Count)"
    Write-Host "    Domain Account:        $($comDomainApps.Count)" -ForegroundColor $(if ($comDomainApps.Count -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "    Built-In Identity:     $($summary.COMPlus.BuiltInIdentityApps)"
    Write-Host "    Interactive User:      $($summary.COMPlus.InteractiveApps)"
    if ($comRiskDist.Count -gt 0) {
        Write-Host "    Risk Distribution:" -ForegroundColor White
        foreach ($g in ($comRiskDist | Sort-Object Name)) {
            $color = switch ($g.Name) {
                'Critical' { 'Red' }
                'High'     { 'DarkYellow' }
                'Medium'   { 'Yellow' }
                'Low'      { 'Green' }
                default    { 'Gray' }
            }
            Write-Host "      $($g.Name): $($g.Count)" -ForegroundColor $color
        }
    }
}

if (-not $SkipDCOM) {
    Write-Host "`n  DCOM Applications:" -ForegroundColor White
    Write-Host "    Total:                 $($allDCOMApps.Count)"
    Write-Host "    Domain RunAs:          $($dcomDomainApps.Count)" -ForegroundColor $(if ($dcomDomainApps.Count -gt 0) { 'Yellow' } else { 'Green' })
    Write-Host "    Domain Permissions:    $($summary.DCOM.DomainPermissionApps)"
    Write-Host "    Built-In Identity:     $($summary.DCOM.BuiltInIdentityApps)"
    Write-Host "    Interactive User:      $($summary.DCOM.InteractiveApps)"
    if ($dcomRiskDist.Count -gt 0) {
        Write-Host "    Risk Distribution:" -ForegroundColor White
        foreach ($g in ($dcomRiskDist | Sort-Object Name)) {
            $color = switch ($g.Name) {
                'Critical' { 'Red' }
                'High'     { 'DarkYellow' }
                'Medium'   { 'Yellow' }
                'Low'      { 'Green' }
                default    { 'Gray' }
            }
            Write-Host "      $($g.Name): $($g.Count)" -ForegroundColor $color
        }
    }
}

Write-Host "`n  Credential Analysis:" -ForegroundColor White
Write-Host "    Unique Domain Accounts: $($domainAccountIdentities.Count)"
Write-Host "    Shared Credentials:     $($sharedCredentials.Count)" -ForegroundColor $(if ($sharedCredentials.Count -gt 0) { 'Yellow' } else { 'Green' })

if ($sharedCredentials.Count -gt 0) {
    Write-Host "`n  Shared Credential Details:" -ForegroundColor DarkYellow
    foreach ($shared in $sharedCredentials) {
        Write-Host "    $($shared.Key) -> $($shared.Value.Count) apps:" -ForegroundColor Yellow
        foreach ($usage in $shared.Value) {
            Write-Host "      [$($usage.Type)] $($usage.Server): $($usage.App)" -ForegroundColor Gray
        }
    }
}

if ($overallRisk.Count -gt 0) {
    Write-Host "`n  Overall Risk (domain accounts only):" -ForegroundColor White
    foreach ($g in ($overallRisk | Sort-Object Name)) {
        $color = switch ($g.Name) {
            'Critical' { 'Red' }
            'High'     { 'DarkYellow' }
            'Medium'   { 'Yellow' }
            'Low'      { 'Green' }
            default    { 'Gray' }
        }
        Write-Host "    $($g.Name): $($g.Count)" -ForegroundColor $color
    }
}

if ($comPlusErrors.Count -gt 0 -or $dcomErrors.Count -gt 0) {
    Write-Host "`n  Errors:" -ForegroundColor Red
    foreach ($e in $comPlusErrors) { Write-Host "    [COM+] $e" -ForegroundColor Red }
    foreach ($e in $dcomErrors)    { Write-Host "    [DCOM] $e" -ForegroundColor Red }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
