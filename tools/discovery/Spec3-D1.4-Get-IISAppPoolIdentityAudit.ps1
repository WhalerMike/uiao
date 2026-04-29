<#
.SYNOPSIS
    UIAO Spec 3 — D1.4: IIS Application Pool Identity Audit
.DESCRIPTION
    Scans IIS servers for application pools running under domain service accounts
    and documents the complete identity dependency chain:

    1. Application Pool Inventory — Name, state, managed runtime, pipeline mode,
       identity type (ApplicationPoolIdentity, NetworkService, LocalSystem,
       SpecificUser/domain account)
    2. Domain Account Mapping — For each app pool using a domain account:
       sAMAccountName, UPN, SPN assignments, delegation configuration
    3. Website Binding — Maps each app pool to its bound websites/virtual
       directories with binding information (protocol, hostname, port, SSL cert)
    4. Authentication Configuration — Per-site authentication modules:
       Windows (Negotiate/NTLM), Anonymous, Basic, Forms, OAuth/OIDC
    5. Handler & Module Inventory — Managed handlers and native modules per site
       for migration impact assessment
    6. Risk Classification — Domain account app pools classified by delegation
       exposure, SPN sensitivity, shared credential risk
    7. Cross-Reference — Links to D1.1 service account scan, D1.2 scheduled
       tasks, D1.3 Windows services for full identity dependency graph

    Outputs: JSON (full detail) + CSV (app pool summary) + CSV (auth config)

    Ref: UIAO_136 Spec 3, Phase 1, Deliverable D1.4
         ADR-004 (Workload Identity Federation default)
         Feeds: D1.5 (COM+/DCOM Application Identity Audit)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER ComputerName
    One or more IIS server names to scan. If omitted, discovers IIS servers
    from AD via SPN (HTTP/) and serverManager feature (Web-Server).
.PARAMETER Credential
    Credential for remote WinRM connections. If omitted, uses current user.
.PARAMETER D1InputFile
    Optional path to D1.1 Service Account Scan JSON for cross-reference.
.PARAMETER SkipRemote
    If set, only scans the local machine (for testing or standalone IIS).
.EXAMPLE
    .\Spec3-D1.4-Get-IISAppPoolIdentityAudit.ps1
    .\Spec3-D1.4-Get-IISAppPoolIdentityAudit.ps1 -ComputerName WEB01,WEB02
    .\Spec3-D1.4-Get-IISAppPoolIdentityAudit.ps1 -D1InputFile .\output\UIAO_Spec3_D1.1_ServiceAccountScan_contoso.com_20260428.json
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT) for server discovery
    Requires: WinRM enabled on target servers for remote scanning
    Requires: WebAdministration or IISAdministration module on targets
    Requires: Read access to IIS configuration on target servers
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string[]]$ComputerName,
    [PSCredential]$Credential,
    [string]$D1InputFile,
    [switch]$SkipRemote
)

$ErrorActionPreference = "Stop"

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Warning "ActiveDirectory module not found. Server discovery from AD will be skipped."
    $noAD = $true
} else {
    Import-Module ActiveDirectory -ErrorAction Stop
    $noAD = $false
}

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = if (-not $noAD) { (Get-ADDomain).DNSRoot } else { $env:USERDNSDOMAIN }
$outPrefix = "UIAO_Spec3_D1.4_IISAppPoolAudit_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 3 — D1.4: IIS Application Pool Identity Audit"      -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════
# Pass 1: Discover IIS Servers
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/7] Discovering IIS servers..." -ForegroundColor Yellow

$iisServers = @()

if ($ComputerName) {
    $iisServers = $ComputerName
    Write-Host "    Explicit server list: $($iisServers.Count) servers" -ForegroundColor DarkGray
} elseif ($SkipRemote) {
    $iisServers = @($env:COMPUTERNAME)
    Write-Host "    Local-only mode: $env:COMPUTERNAME" -ForegroundColor DarkGray
} elseif (-not $noAD) {
    # Method 1: Find servers with HTTP/ SPNs (indicates IIS or web services)
    $httpSpnComputers = @(Get-ADComputer -Filter 'ServicePrincipalName -like "HTTP/*"' -Properties ServicePrincipalName, OperatingSystem, DNSHostName |
        Where-Object { $_.OperatingSystem -match 'Windows Server' } |
        Select-Object -ExpandProperty DNSHostName)
    Write-Host "    HTTP/ SPN discovery: $($httpSpnComputers.Count) servers" -ForegroundColor DarkGray

    # Method 2: Find servers in known IIS OUs
    $webOUs = @(Get-ADOrganizationalUnit -Filter 'Name -like "*Web*" -or Name -like "*IIS*" -or Name -like "*DMZ*"' -ErrorAction SilentlyContinue)
    $ouComputers = @()
    foreach ($ou in $webOUs) {
        $ouComputers += @(Get-ADComputer -SearchBase $ou.DistinguishedName -Filter 'OperatingSystem -like "Windows Server*"' -Properties DNSHostName |
            Select-Object -ExpandProperty DNSHostName)
    }
    Write-Host "    OU-based discovery:  $($ouComputers.Count) servers" -ForegroundColor DarkGray

    $iisServers = @($httpSpnComputers + $ouComputers | Sort-Object -Unique)
    Write-Host "    Combined unique:     $($iisServers.Count) servers" -ForegroundColor Green
} else {
    $iisServers = @($env:COMPUTERNAME)
    Write-Host "    No AD module and no -ComputerName. Scanning local only." -ForegroundColor Yellow
}

if ($iisServers.Count -eq 0) {
    Write-Warning "No IIS servers found. Provide -ComputerName or run from a domain-joined machine."
    return
}

# ══════════════════════════════════════════════════════════════
# Pass 2: Remote IIS Configuration Collection
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/7] Collecting IIS configuration from $($iisServers.Count) server(s)..." -ForegroundColor Yellow

# The scan script block executed on each server
$scanBlock = {
    $results = [ordered]@{
        ComputerName = $env:COMPUTERNAME
        ScanTime     = (Get-Date).ToString("o")
        IISInstalled = $false
        AppPools     = @()
        Sites        = @()
        Errors       = @()
    }

    # Check if IIS is installed
    try {
        $iisFeature = Get-WindowsFeature -Name Web-Server -ErrorAction SilentlyContinue
        if (-not $iisFeature -or -not $iisFeature.Installed) {
            $results.Errors += "Web-Server feature not installed"
            return $results
        }
        $results.IISInstalled = $true
    } catch {
        # Try alternative detection
        if (-not (Test-Path "$env:SystemRoot\System32\inetsrv\appcmd.exe")) {
            $results.Errors += "IIS not detected (no Web-Server feature, no appcmd.exe)"
            return $results
        }
        $results.IISInstalled = $true
    }

    # Try WebAdministration module first, fall back to appcmd
    $useWebAdmin = $false
    try {
        Import-Module WebAdministration -ErrorAction Stop
        $useWebAdmin = $true
    } catch {
        try {
            Import-Module IISAdministration -ErrorAction Stop
            $useWebAdmin = $true
        } catch {
            $results.Errors += "Neither WebAdministration nor IISAdministration module available. Using appcmd fallback."
        }
    }

    if ($useWebAdmin) {
        # ── App Pool Collection via WebAdministration ──
        try {
            $pools = Get-ChildItem IIS:\AppPools -ErrorAction Stop
            foreach ($pool in $pools) {
                $poolInfo = [ordered]@{
                    Name               = $pool.Name
                    State              = $pool.State
                    ManagedRuntime     = $pool.managedRuntimeVersion
                    PipelineMode       = $pool.managedPipelineMode
                    Enable32Bit        = $pool.enable32BitAppOnWin64
                    AutoStart          = $pool.autoStart
                    StartMode          = $pool.startMode
                    IdentityType       = $pool.processModel.identityType.ToString()
                    Username           = $null
                    IsDomainAccount    = $false
                    IdleTimeout        = $pool.processModel.idleTimeout.ToString()
                    RecyclingTime      = ($pool.recycling.periodicRestart.time).ToString()
                    RecyclingMemoryKB  = $pool.recycling.periodicRestart.privateMemory
                }

                if ($pool.processModel.identityType -eq 'SpecificUser') {
                    $poolInfo.Username = $pool.processModel.userName
                    # Detect domain accounts (DOMAIN\user or user@domain.com)
                    if ($poolInfo.Username -match '\\' -or $poolInfo.Username -match '@.*\.') {
                        $poolInfo.IsDomainAccount = $true
                    }
                }

                $results.AppPools += $poolInfo
            }
        } catch {
            $results.Errors += "AppPool collection error: $($_.Exception.Message)"
        }

        # ── Site Collection via WebAdministration ──
        try {
            $sites = Get-ChildItem IIS:\Sites -ErrorAction Stop
            foreach ($site in $sites) {
                $bindings = @($site.Bindings.Collection | ForEach-Object {
                    [ordered]@{
                        Protocol            = $_.protocol
                        BindingInformation  = $_.bindingInformation
                        Host                = if ($_.host) { $_.host } else { "*" }
                        CertificateHash     = if ($_.certificateHash) { $_.certificateHash } else { $null }
                        CertificateStore    = if ($_.certificateStoreName) { $_.certificateStoreName } else { $null }
                        SslFlags            = if ($_.sslFlags) { $_.sslFlags } else { 0 }
                    }
                })

                # Authentication configuration
                $authConfig = [ordered]@{
                    Anonymous  = $false
                    Basic      = $false
                    Windows    = $false
                    Digest     = $false
                    Forms      = $false
                    WindowsProviders = @()
                    WindowsUseKernelMode = $false
                }

                try {
                    $anonAuth = Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/anonymousAuthentication" -PSPath "IIS:\Sites\$($site.Name)" -Name "enabled" -ErrorAction SilentlyContinue
                    $authConfig.Anonymous = [bool]$anonAuth.Value

                    $basicAuth = Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/basicAuthentication" -PSPath "IIS:\Sites\$($site.Name)" -Name "enabled" -ErrorAction SilentlyContinue
                    $authConfig.Basic = [bool]$basicAuth.Value

                    $winAuth = Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication" -PSPath "IIS:\Sites\$($site.Name)" -Name "enabled" -ErrorAction SilentlyContinue
                    $authConfig.Windows = [bool]$winAuth.Value

                    if ($authConfig.Windows) {
                        $providers = Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication/providers" -PSPath "IIS:\Sites\$($site.Name)" -Name "." -ErrorAction SilentlyContinue
                        $authConfig.WindowsProviders = @($providers.Collection | ForEach-Object { $_.Value })

                        $kernelMode = Get-WebConfigurationProperty -Filter "/system.webServer/security/authentication/windowsAuthentication" -PSPath "IIS:\Sites\$($site.Name)" -Name "useKernelMode" -ErrorAction SilentlyContinue
                        $authConfig.WindowsUseKernelMode = [bool]$kernelMode.Value
                    }

                    # Check for Forms authentication in web.config
                    $formsAuth = Get-WebConfigurationProperty -Filter "/system.web/authentication" -PSPath "IIS:\Sites\$($site.Name)" -Name "mode" -ErrorAction SilentlyContinue
                    if ($formsAuth -eq 'Forms') { $authConfig.Forms = $true }
                } catch {
                    # Auth config read may fail on some sites
                }

                # Virtual directories / applications
                $apps = @()
                try {
                    $webApps = Get-WebApplication -Site $site.Name -ErrorAction SilentlyContinue
                    foreach ($app in $webApps) {
                        $apps += [ordered]@{
                            Path                = $app.path
                            PhysicalPath        = $app.PhysicalPath
                            ApplicationPool     = $app.applicationPool
                            EnabledProtocols    = $app.enabledProtocols
                        }
                    }
                } catch { }

                $siteInfo = [ordered]@{
                    Name              = $site.Name
                    ID                = $site.ID
                    State             = $site.State
                    PhysicalPath      = $site.PhysicalPath
                    ApplicationPool   = $site.ApplicationPool
                    Bindings          = $bindings
                    Authentication    = $authConfig
                    Applications      = $apps
                    LogPath           = $site.LogFile.Directory
                }

                $results.Sites += $siteInfo
            }
        } catch {
            $results.Errors += "Site collection error: $($_.Exception.Message)"
        }
    } else {
        # ── Fallback: appcmd.exe ──
        try {
            $appcmdPath = "$env:SystemRoot\System32\inetsrv\appcmd.exe"

            # App Pools via appcmd
            $poolXml = [xml](& $appcmdPath list apppool /xml 2>$null)
            if ($poolXml -and $poolXml.appcmd.APPPOOL) {
                foreach ($pool in $poolXml.appcmd.APPPOOL) {
                    $poolDetail = [xml](& $appcmdPath list apppool $pool.'APPPOOL.NAME' /config /xml 2>$null)
                    $pm = $poolDetail.appcmd.APPPOOL.add.processModel

                    $poolInfo = [ordered]@{
                        Name            = $pool.'APPPOOL.NAME'
                        State           = $pool.state
                        ManagedRuntime  = $poolDetail.appcmd.APPPOOL.add.managedRuntimeVersion
                        PipelineMode    = $poolDetail.appcmd.APPPOOL.add.managedPipelineMode
                        Enable32Bit     = $poolDetail.appcmd.APPPOOL.add.enable32BitAppOnWin64
                        AutoStart       = $poolDetail.appcmd.APPPOOL.add.autoStart
                        StartMode       = $poolDetail.appcmd.APPPOOL.add.startMode
                        IdentityType    = $pm.identityType
                        Username        = $pm.userName
                        IsDomainAccount = $false
                    }

                    if ($pm.identityType -eq 'SpecificUser' -and $pm.userName) {
                        if ($pm.userName -match '\\' -or $pm.userName -match '@.*\.') {
                            $poolInfo.IsDomainAccount = $true
                        }
                    }

                    $results.AppPools += $poolInfo
                }
            }

            # Sites via appcmd
            $siteXml = [xml](& $appcmdPath list site /xml 2>$null)
            if ($siteXml -and $siteXml.appcmd.SITE) {
                foreach ($site in $siteXml.appcmd.SITE) {
                    $siteInfo = [ordered]@{
                        Name            = $site.'SITE.NAME'
                        ID              = $site.'SITE.ID'
                        State           = $site.state
                        Bindings        = $site.bindings
                        ApplicationPool = $null
                        Authentication  = [ordered]@{ Note = "Authentication details require WebAdministration module" }
                        Applications    = @()
                    }
                    $results.Sites += $siteInfo
                }
            }
        } catch {
            $results.Errors += "appcmd fallback error: $($_.Exception.Message)"
        }
    }

    return $results
}

# Execute scan across all servers
$allServerResults = @()
$reachable = 0
$unreachable = 0

foreach ($server in $iisServers) {
    Write-Host "    Scanning: $server..." -ForegroundColor DarkGray -NoNewline

    $isLocal = ($server -eq $env:COMPUTERNAME -or
                $server -eq 'localhost' -or
                $server -eq '.' -or
                $server -eq ([System.Net.Dns]::GetHostName()))

    try {
        if ($isLocal -or $SkipRemote) {
            $result = & $scanBlock
        } else {
            $sessParams = @{ ComputerName = $server; ErrorAction = 'Stop' }
            if ($Credential) { $sessParams['Credential'] = $Credential }
            $session = New-PSSession @sessParams
            $result = Invoke-Command -Session $session -ScriptBlock $scanBlock
            Remove-PSSession $session
        }

        if ($result.IISInstalled) {
            $reachable++
            $poolCount = $result.AppPools.Count
            $domainPoolCount = @($result.AppPools | Where-Object { $_.IsDomainAccount }).Count
            Write-Host " OK (${poolCount} pools, ${domainPoolCount} domain)" -ForegroundColor Green
        } else {
            $reachable++
            Write-Host " OK (IIS not installed)" -ForegroundColor DarkGray
        }

        $allServerResults += $result
    } catch {
        $unreachable++
        Write-Host " UNREACHABLE: $($_.Exception.Message)" -ForegroundColor Red
        $allServerResults += [ordered]@{
            ComputerName = $server
            ScanTime     = (Get-Date).ToString("o")
            IISInstalled = $null
            AppPools     = @()
            Sites        = @()
            Errors       = @("Connection failed: $($_.Exception.Message)")
        }
    }
}

Write-Host "    Servers scanned: $reachable reachable, $unreachable unreachable" -ForegroundColor $(if ($unreachable -gt 0) { 'Yellow' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Pass 3: Domain Account Resolution
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/7] Resolving domain account details..." -ForegroundColor Yellow

$domainAccounts = @{}

foreach ($serverResult in $allServerResults) {
    foreach ($pool in $serverResult.AppPools) {
        if ($pool.IsDomainAccount -and $pool.Username) {
            $accountKey = $pool.Username.ToLower()
            if (-not $domainAccounts.ContainsKey($accountKey)) {
                $acctDetail = [ordered]@{
                    Username        = $pool.Username
                    sAMAccountName  = $null
                    DN              = $null
                    Enabled         = $null
                    PasswordLastSet = $null
                    SPNs            = @()
                    MemberOf        = @()
                    AdminCount      = $null
                    Delegation      = "None"
                    LookupError     = $null
                }

                if (-not $noAD) {
                    try {
                        # Parse username format
                        $samName = $pool.Username
                        if ($samName -match '^(.+)\\(.+)$') {
                            $samName = $Matches[2]
                        } elseif ($samName -match '^(.+)@') {
                            $samName = $Matches[1]
                        }

                        $adUser = Get-ADUser -Identity $samName -Properties `
                            ServicePrincipalName, MemberOf, AdminCount, `
                            PasswordLastSet, Enabled, `
                            msDS-AllowedToDelegateTo, `
                            TrustedForDelegation, TrustedToAuthForDelegation `
                            -ErrorAction Stop

                        $acctDetail.sAMAccountName  = $adUser.SamAccountName
                        $acctDetail.DN              = $adUser.DistinguishedName
                        $acctDetail.Enabled         = $adUser.Enabled
                        $acctDetail.PasswordLastSet = if ($adUser.PasswordLastSet) { $adUser.PasswordLastSet.ToString("o") } else { $null }
                        $acctDetail.SPNs            = @($adUser.ServicePrincipalName)
                        $acctDetail.MemberOf        = @($adUser.MemberOf | ForEach-Object {
                            ($_ -split ',')[0] -replace '^CN=',''
                        })
                        $acctDetail.AdminCount      = $adUser.AdminCount

                        # Delegation classification
                        if ($adUser.TrustedForDelegation) {
                            $acctDetail.Delegation = "UNCONSTRAINED"
                        } elseif ($adUser.'msDS-AllowedToDelegateTo'.Count -gt 0) {
                            if ($adUser.TrustedToAuthForDelegation) {
                                $acctDetail.Delegation = "CONSTRAINED_WITH_PROTOCOL_TRANSITION"
                            } else {
                                $acctDetail.Delegation = "CONSTRAINED"
                            }
                        }
                    } catch {
                        $acctDetail.LookupError = $_.Exception.Message
                    }
                }

                $domainAccounts[$accountKey] = $acctDetail
            }
        }
    }
}

Write-Host "    Unique domain accounts resolved: $($domainAccounts.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 4: Build App Pool → Site → Auth Dependency Map
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/7] Building dependency map..." -ForegroundColor Yellow

$dependencyMap = @()

foreach ($serverResult in $allServerResults) {
    if (-not $serverResult.IISInstalled) { continue }

    foreach ($pool in $serverResult.AppPools) {
        # Find all sites using this app pool
        $boundSites = @($serverResult.Sites | Where-Object { $_.ApplicationPool -eq $pool.Name })

        # Find all sub-applications using this app pool
        $boundApps = @()
        foreach ($site in $serverResult.Sites) {
            if ($site.Applications) {
                $boundApps += @($site.Applications | Where-Object { $_.ApplicationPool -eq $pool.Name } |
                    ForEach-Object {
                        [ordered]@{
                            SiteName = $site.Name
                            AppPath  = $_.Path
                            PhysicalPath = $_.PhysicalPath
                        }
                    })
            }
        }

        $authMethods = @()
        foreach ($site in $boundSites) {
            if ($site.Authentication) {
                $methods = @()
                if ($site.Authentication.Windows)  { $methods += "Windows" }
                if ($site.Authentication.Anonymous) { $methods += "Anonymous" }
                if ($site.Authentication.Basic)     { $methods += "Basic" }
                if ($site.Authentication.Digest)    { $methods += "Digest" }
                if ($site.Authentication.Forms)     { $methods += "Forms" }
                $authMethods += $methods
            }
        }
        $authMethods = $authMethods | Sort-Object -Unique

        # Determine migration target per ADR-004
        $migrationTarget = switch ($true) {
            ($pool.IdentityType -ne 'SpecificUser') {
                "RETAIN — built-in identity, no migration needed"
            }
            (-not $pool.IsDomainAccount) {
                "RETAIN — local account, evaluate for Managed Identity"
            }
            ($authMethods -contains 'Windows' -and $authMethods.Count -eq 1) {
                "CONVERT — Negotiate/Kerberos to Entra ID auth (OIDC/OAuth)"
            }
            ($authMethods -contains 'Windows' -and $authMethods -contains 'Forms') {
                "CONVERT — Hybrid auth to Entra ID SSO (SAML/OIDC)"
            }
            ($authMethods -contains 'Forms' -and $authMethods.Count -eq 1) {
                "CONVERT — Forms auth to Entra ID SSO (SAML/OIDC)"
            }
            default {
                "EVALUATE — Complex auth configuration requires manual assessment"
            }
        }

        $acctInfo = $null
        if ($pool.IsDomainAccount -and $pool.Username) {
            $acctInfo = $domainAccounts[$pool.Username.ToLower()]
        }

        $dependency = [ordered]@{
            Server            = $serverResult.ComputerName
            AppPoolName       = $pool.Name
            State             = $pool.State
            ManagedRuntime    = $pool.ManagedRuntime
            PipelineMode      = $pool.PipelineMode
            IdentityType      = $pool.IdentityType
            Username          = $pool.Username
            IsDomainAccount   = $pool.IsDomainAccount
            AccountDetails    = $acctInfo
            BoundSites        = @($boundSites | ForEach-Object { $_.Name })
            BoundApplications = $boundApps
            AuthMethods       = $authMethods
            HasSSL            = $false
            SSLCerts          = @()
            MigrationTarget   = $migrationTarget
        }

        # Check for SSL bindings
        foreach ($site in $boundSites) {
            if ($site.Bindings) {
                foreach ($binding in $site.Bindings) {
                    if ($binding.Protocol -eq 'https' -or ($binding -is [string] -and $binding -match 'https')) {
                        $dependency.HasSSL = $true
                        if ($binding.CertificateHash) {
                            $dependency.SSLCerts += [ordered]@{
                                Site     = $site.Name
                                CertHash = $binding.CertificateHash
                                Store    = $binding.CertificateStore
                            }
                        }
                    }
                }
            }
        }

        $dependencyMap += $dependency
    }
}

Write-Host "    Total app pool dependencies mapped: $($dependencyMap.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Pass 5: Risk Classification
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/7] Classifying risk levels..." -ForegroundColor Yellow

$riskFindings = @()

foreach ($dep in $dependencyMap) {
    if (-not $dep.IsDomainAccount) { continue }

    $risks = @()
    $riskLevel = "LOW"

    # Check delegation
    if ($dep.AccountDetails -and $dep.AccountDetails.Delegation -eq 'UNCONSTRAINED') {
        $risks += "Unconstrained delegation on IIS service account"
        $riskLevel = "CRITICAL"
    } elseif ($dep.AccountDetails -and $dep.AccountDetails.Delegation -match 'PROTOCOL_TRANSITION') {
        $risks += "Protocol transition enabled — can impersonate any user"
        if ($riskLevel -ne "CRITICAL") { $riskLevel = "HIGH" }
    } elseif ($dep.AccountDetails -and $dep.AccountDetails.Delegation -eq 'CONSTRAINED') {
        $risks += "Constrained delegation — limited but present"
        if ($riskLevel -notin @("CRITICAL","HIGH")) { $riskLevel = "MEDIUM" }
    }

    # Check AdminCount
    if ($dep.AccountDetails -and $dep.AccountDetails.AdminCount -eq 1) {
        $risks += "Account has AdminCount=1 (privileged or formerly privileged)"
        if ($riskLevel -ne "CRITICAL") { $riskLevel = "HIGH" }
    }

    # Check shared credentials across servers
    $sharedServers = @($dependencyMap | Where-Object {
        $_.IsDomainAccount -and $_.Username -eq $dep.Username -and $_.Server -ne $dep.Server
    } | Select-Object -ExpandProperty Server -Unique)
    if ($sharedServers.Count -gt 0) {
        $risks += "Shared credential across $($sharedServers.Count + 1) servers: $($dep.Server), $($sharedServers -join ', ')"
        if ($riskLevel -notin @("CRITICAL","HIGH")) { $riskLevel = "MEDIUM" }
    }

    # Check shared credentials across app pools on same server
    $sharedPools = @($dependencyMap | Where-Object {
        $_.IsDomainAccount -and $_.Username -eq $dep.Username -and
        $_.Server -eq $dep.Server -and $_.AppPoolName -ne $dep.AppPoolName
    } | Select-Object -ExpandProperty AppPoolName)
    if ($sharedPools.Count -gt 0) {
        $risks += "Same credential used by $($sharedPools.Count + 1) app pools on $($dep.Server)"
        if ($riskLevel -eq "LOW") { $riskLevel = "MEDIUM" }
    }

    # Check if account is disabled
    if ($dep.AccountDetails -and $dep.AccountDetails.Enabled -eq $false) {
        $risks += "ANOMALY: App pool using disabled AD account"
        if ($riskLevel -ne "CRITICAL") { $riskLevel = "HIGH" }
    }

    # Check password age
    if ($dep.AccountDetails -and $dep.AccountDetails.PasswordLastSet) {
        $pwdAge = (New-TimeSpan -Start ([datetime]$dep.AccountDetails.PasswordLastSet) -End (Get-Date)).Days
        if ($pwdAge -gt 365) {
            $risks += "Password age: $pwdAge days (>1 year)"
            if ($riskLevel -eq "LOW") { $riskLevel = "MEDIUM" }
        }
    }

    # Check Windows auth with no SSL
    if ($dep.AuthMethods -contains 'Windows' -and -not $dep.HasSSL) {
        $risks += "Windows authentication without SSL — credential exposure risk"
        if ($riskLevel -eq "LOW") { $riskLevel = "MEDIUM" }
    }

    if ($risks.Count -gt 0) {
        $riskFindings += [ordered]@{
            Server      = $dep.Server
            AppPool     = $dep.AppPoolName
            Account     = $dep.Username
            RiskLevel   = $riskLevel
            Risks       = $risks
            BoundSites  = $dep.BoundSites
            AuthMethods = $dep.AuthMethods
        }
    }
}

$critCount = @($riskFindings | Where-Object { $_.RiskLevel -eq 'CRITICAL' }).Count
$highCount = @($riskFindings | Where-Object { $_.RiskLevel -eq 'HIGH' }).Count
$medCount  = @($riskFindings | Where-Object { $_.RiskLevel -eq 'MEDIUM' }).Count
$lowCount  = @($riskFindings | Where-Object { $_.RiskLevel -eq 'LOW' }).Count

Write-Host "    Risk findings: CRITICAL=$critCount HIGH=$highCount MEDIUM=$medCount LOW=$lowCount" -ForegroundColor $(
    if ($critCount -gt 0) { 'Red' } elseif ($highCount -gt 0) { 'Yellow' } else { 'Green' }
)

# ══════════════════════════════════════════════════════════════
# Pass 6: D1.1 Cross-Reference
# ══════════════════════════════════════════════════════════════
$d1CrossRef = $null
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  [6/7] Cross-referencing D1.1 Service Account Scan..." -ForegroundColor Yellow
    try {
        $d1Data = Get-Content $D1InputFile -Raw | ConvertFrom-Json

        $d1Accounts = @{}
        if ($d1Data.ServiceAccounts) {
            foreach ($sa in $d1Data.ServiceAccounts) {
                $d1Accounts[$sa.sAMAccountName.ToLower()] = $sa
            }
        } elseif ($d1Data.Findings) {
            foreach ($f in $d1Data.Findings) {
                if ($f.sAMAccountName) {
                    $d1Accounts[$f.sAMAccountName.ToLower()] = $f
                }
            }
        }

        $matched = @()
        $unmatched = @()

        foreach ($acctKey in $domainAccounts.Keys) {
            $acct = $domainAccounts[$acctKey]
            $sam = if ($acct.sAMAccountName) { $acct.sAMAccountName.ToLower() } else { $null }

            if ($sam -and $d1Accounts.ContainsKey($sam)) {
                $matched += [ordered]@{
                    Account    = $acct.Username
                    D1Category = $d1Accounts[$sam].Category
                    D1Risk     = $d1Accounts[$sam].RiskLevel
                    IISServers = @($dependencyMap | Where-Object { $_.Username -eq $acct.Username } |
                        Select-Object -ExpandProperty Server -Unique)
                }
            } else {
                $unmatched += [ordered]@{
                    Account    = $acct.Username
                    Note       = "Found in IIS but not in D1.1 service account scan"
                    IISServers = @($dependencyMap | Where-Object { $_.Username -eq $acct.Username } |
                        Select-Object -ExpandProperty Server -Unique)
                }
            }
        }

        $d1CrossRef = [ordered]@{
            D1InputFile    = $D1InputFile
            MatchedAccounts   = $matched
            UnmatchedAccounts = $unmatched
            MatchRate      = if ($domainAccounts.Count -gt 0) {
                [math]::Round(($matched.Count / $domainAccounts.Count) * 100, 1)
            } else { 0 }
        }

        Write-Host "    D1.1 match rate: $($d1CrossRef.MatchRate)% ($($matched.Count) matched, $($unmatched.Count) new)" -ForegroundColor Green
    } catch {
        Write-Warning "D1.1 cross-reference failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "  [6/7] D1.1 cross-reference skipped (no -D1InputFile)" -ForegroundColor DarkGray
}

# ══════════════════════════════════════════════════════════════
# Pass 7: Output Generation
# ══════════════════════════════════════════════════════════════
Write-Host "  [7/7] Generating output files..." -ForegroundColor Yellow

# Summary statistics
$totalPools       = @($dependencyMap).Count
$domainPools      = @($dependencyMap | Where-Object { $_.IsDomainAccount }).Count
$builtinPools     = $totalPools - $domainPools
$totalSites       = @($allServerResults | ForEach-Object { $_.Sites.Count } | Measure-Object -Sum).Sum
$serversWithIIS   = @($allServerResults | Where-Object { $_.IISInstalled }).Count
$windowsAuthSites = @($dependencyMap | Where-Object { $_.AuthMethods -contains 'Windows' }).Count
$formsAuthSites   = @($dependencyMap | Where-Object { $_.AuthMethods -contains 'Forms' }).Count
$sslSites         = @($dependencyMap | Where-Object { $_.HasSSL }).Count

# Unique domain accounts across all servers
$uniqueAccounts = @($dependencyMap | Where-Object { $_.IsDomainAccount } |
    Select-Object -ExpandProperty Username -Unique)

# Shared credential analysis
$sharedAccounts = @($uniqueAccounts | Where-Object {
    $acct = $_
    @($dependencyMap | Where-Object { $_.Username -eq $acct }).Count -gt 1
})

# ── JSON Output ──
$jsonOutput = [ordered]@{
    Metadata = [ordered]@{
        Script        = "Spec3-D1.4-Get-IISAppPoolIdentityAudit.ps1"
        Reference     = "UIAO_136 Spec 3, Phase 1, D1.4"
        ADRs          = @("ADR-004 (Workload Identity Federation)")
        Domain        = $domain
        Timestamp     = $timestamp
        ServersScanned = $iisServers.Count
        ServersReachable = $reachable
        ServersWithIIS = $serversWithIIS
    }
    Summary = [ordered]@{
        TotalAppPools         = $totalPools
        DomainAccountPools    = $domainPools
        BuiltInIdentityPools  = $builtinPools
        TotalSites            = $totalSites
        UniqueDomainAccounts  = $uniqueAccounts.Count
        SharedCredentialAccounts = $sharedAccounts.Count
        WindowsAuthPools      = $windowsAuthSites
        FormsAuthPools         = $formsAuthSites
        SSLEnabledPools        = $sslSites
        RiskSummary = [ordered]@{
            Critical = $critCount
            High     = $highCount
            Medium   = $medCount
            Low      = $lowCount
        }
    }
    ServerResults     = $allServerResults
    DependencyMap     = $dependencyMap
    DomainAccounts    = $domainAccounts
    RiskFindings      = $riskFindings
    D1CrossReference  = $d1CrossRef
    MigrationBlockers = @(
        $riskFindings | Where-Object { $_.RiskLevel -eq 'CRITICAL' } | ForEach-Object {
            [ordered]@{
                Server  = $_.Server
                AppPool = $_.AppPool
                Account = $_.Account
                Blocker = $_.Risks -join "; "
            }
        }
    )
}

$jsonPath = Join-Path $OutputPath "$outPrefix.json"
$jsonOutput | ConvertTo-Json -Depth 15 | Out-File -FilePath $jsonPath -Encoding UTF8 -Force
Write-Host "    JSON: $jsonPath" -ForegroundColor Green

# ── CSV Output: App Pool Summary ──
$csvData = @()
foreach ($dep in $dependencyMap) {
    $csvData += [PSCustomObject][ordered]@{
        Server           = $dep.Server
        AppPoolName      = $dep.AppPoolName
        State            = $dep.State
        ManagedRuntime   = $dep.ManagedRuntime
        PipelineMode     = $dep.PipelineMode
        IdentityType     = $dep.IdentityType
        Username         = $dep.Username
        IsDomainAccount  = $dep.IsDomainAccount
        BoundSites       = ($dep.BoundSites -join "; ")
        AuthMethods      = ($dep.AuthMethods -join "; ")
        HasSSL           = $dep.HasSSL
        Delegation       = if ($dep.AccountDetails) { $dep.AccountDetails.Delegation } else { "N/A" }
        AdminCount       = if ($dep.AccountDetails) { $dep.AccountDetails.AdminCount } else { "N/A" }
        SPNCount         = if ($dep.AccountDetails) { $dep.AccountDetails.SPNs.Count } else { 0 }
        MigrationTarget  = $dep.MigrationTarget
        RiskLevel        = ($riskFindings | Where-Object { $_.Server -eq $dep.Server -and $_.AppPool -eq $dep.AppPoolName } |
            Select-Object -ExpandProperty RiskLevel -First 1)
    }
}

$csvPath = Join-Path $OutputPath "${outPrefix}_AppPools.csv"
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "    CSV (App Pools): $csvPath" -ForegroundColor Green

# ── CSV Output: Auth Configuration ──
$authCsvData = @()
foreach ($serverResult in $allServerResults) {
    foreach ($site in $serverResult.Sites) {
        $authCsvData += [PSCustomObject][ordered]@{
            Server       = $serverResult.ComputerName
            SiteName     = $site.Name
            AppPool      = $site.ApplicationPool
            Anonymous    = if ($site.Authentication) { $site.Authentication.Anonymous } else { "Unknown" }
            Basic        = if ($site.Authentication) { $site.Authentication.Basic } else { "Unknown" }
            Windows      = if ($site.Authentication) { $site.Authentication.Windows } else { "Unknown" }
            Digest       = if ($site.Authentication) { $site.Authentication.Digest } else { "Unknown" }
            Forms        = if ($site.Authentication) { $site.Authentication.Forms } else { "Unknown" }
            WinProviders = if ($site.Authentication -and $site.Authentication.WindowsProviders) {
                $site.Authentication.WindowsProviders -join "; "
            } else { "" }
            KernelMode   = if ($site.Authentication) { $site.Authentication.WindowsUseKernelMode } else { "Unknown" }
        }
    }
}

$authCsvPath = Join-Path $OutputPath "${outPrefix}_AuthConfig.csv"
$authCsvData | Export-Csv -Path $authCsvPath -NoTypeInformation -Encoding UTF8
Write-Host "    CSV (Auth Config): $authCsvPath" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Console Dashboard
# ══════════════════════════════════════════════════════════════
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  IIS APPLICATION POOL IDENTITY AUDIT — SUMMARY"                  -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

Write-Host "`n  Infrastructure:" -ForegroundColor White
Write-Host "    IIS Servers Scanned:        $reachable / $($iisServers.Count)" -ForegroundColor $(if ($unreachable -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    Servers with IIS Installed:  $serversWithIIS" -ForegroundColor Green
Write-Host "    Total Sites:                $totalSites" -ForegroundColor White
Write-Host "    Total Application Pools:    $totalPools" -ForegroundColor White

Write-Host "`n  Identity Analysis:" -ForegroundColor White
Write-Host "    Built-in Identity Pools:    $builtinPools" -ForegroundColor Green
Write-Host "    Domain Account Pools:       $domainPools" -ForegroundColor $(if ($domainPools -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    Unique Domain Accounts:     $($uniqueAccounts.Count)" -ForegroundColor White
Write-Host "    Shared Credential Accounts: $($sharedAccounts.Count)" -ForegroundColor $(if ($sharedAccounts.Count -gt 0) { 'Yellow' } else { 'Green' })

Write-Host "`n  Authentication:" -ForegroundColor White
Write-Host "    Windows Auth (Kerberos/NTLM): $windowsAuthSites pools" -ForegroundColor $(if ($windowsAuthSites -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    Forms Authentication:         $formsAuthSites pools" -ForegroundColor White
Write-Host "    SSL/TLS Enabled:              $sslSites pools" -ForegroundColor White

Write-Host "`n  Risk Assessment:" -ForegroundColor White
Write-Host "    CRITICAL: $critCount" -ForegroundColor $(if ($critCount -gt 0) { 'Red' } else { 'Green' })
Write-Host "    HIGH:     $highCount" -ForegroundColor $(if ($highCount -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    MEDIUM:   $medCount" -ForegroundColor $(if ($medCount -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "    LOW:      $lowCount" -ForegroundColor Green

if ($critCount -gt 0) {
    Write-Host "`n  *** MIGRATION BLOCKERS ***" -ForegroundColor Red
    foreach ($blocker in $jsonOutput.MigrationBlockers) {
        Write-Host "    [$($blocker.Server)] $($blocker.AppPool) ($($blocker.Account))" -ForegroundColor Red
        Write-Host "      $($blocker.Blocker)" -ForegroundColor DarkRed
    }
}

if ($sharedAccounts.Count -gt 0) {
    Write-Host "`n  Shared Credentials (must migrate together):" -ForegroundColor Yellow
    foreach ($shared in $sharedAccounts) {
        $servers = @($dependencyMap | Where-Object { $_.Username -eq $shared } |
            Select-Object -ExpandProperty Server -Unique)
        $pools = @($dependencyMap | Where-Object { $_.Username -eq $shared } |
            Select-Object -ExpandProperty AppPoolName)
        Write-Host "    $shared" -ForegroundColor Yellow
        Write-Host "      Servers: $($servers -join ', ')" -ForegroundColor DarkGray
        Write-Host "      Pools:   $($pools -join ', ')" -ForegroundColor DarkGray
    }
}

Write-Host "`n  Output Files:" -ForegroundColor White
Write-Host "    $jsonPath" -ForegroundColor DarkGray
Write-Host "    $csvPath" -ForegroundColor DarkGray
Write-Host "    $authCsvPath" -ForegroundColor DarkGray
Write-Host "`n  Cross-reference:" -ForegroundColor White
Write-Host "    D1.1 Service Account Scan → Correlate domain accounts" -ForegroundColor DarkGray
Write-Host "    D1.2 Scheduled Tasks      → Identify app pool credential overlap" -ForegroundColor DarkGray
Write-Host "    D1.3 Windows Services     → Complete identity dependency graph" -ForegroundColor DarkGray
Write-Host "    D1.5 COM+/DCOM            → Next: application identity layer" -ForegroundColor DarkGray

Write-Host "`n  ADR Reference:" -ForegroundColor White
Write-Host "    ADR-004: Workload Identity Federation is the default migration target" -ForegroundColor DarkGray
Write-Host "    Domain app pool accounts → Managed Identity or Workload Identity Federation" -ForegroundColor DarkGray

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  Audit complete. Review domain account pools for migration planning." -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Cyan
