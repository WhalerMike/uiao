<#
.SYNOPSIS
    UIAO AD Adapter — Forest Archaeological Survey
    Canon reference: Appendix F Phase 1 (Discovery)
    Emits structured JSON consumed by survey.py::_run_powershell_survey()

.DESCRIPTION
    Read-only enumeration of an AD forest. Requires RSAT ActiveDirectory module
    or domain-joined execution context.

    Enumerates:
      - Forest / tree / trust topology (forest mode, every domain, DCs, FSMO
        holders, inter-site links, and trust relationships) — captured FIRST,
        because OrgPath is the DN-encoded org spine and a distinguishedName has
        no meaning until the forest root, the constituent trees, and the trust
        boundaries that join them are known.
      - All OUs with GPO linkage and ManagedBy status
      - All user objects with key governance attributes
      - All objects with SPNs (service accounts)
      - All computer objects
      - All Sites and Services site objects

    Outputs a single JSON object to stdout.

.PARAMETER Server
    Domain controller FQDN or IP.

.PARAMETER BaseDN
    Forest root distinguished name, e.g. DC=corp,DC=contoso,DC=com

.PARAMETER OutputJson
    Switch. If set, outputs JSON to stdout. Otherwise outputs human-readable table.

.PARAMETER IncludeComputers
    Switch. Include computer object enumeration (may be slow on large forests).

.EXAMPLE
    .\Invoke-ADSurvey.ps1 -Server dc01.corp.contoso.com -BaseDN "DC=corp,DC=contoso,DC=com" -OutputJson
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Server,

    [Parameter(Mandatory = $true)]
    [string]$BaseDN,

    [switch]$OutputJson,

    [switch]$IncludeComputers
)

$ErrorActionPreference = "Stop"
Import-Module ActiveDirectory -ErrorAction Stop

# ----------------------------------------------------------------
# Helper: age in days from a FileTime or DateTime (handles AD's
# never-logged-in sentinel value 0 / 9223372036854775807)
# ----------------------------------------------------------------
function Get-AgeDays {
    [Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSUseSingularNouns', '', Justification = '''Days'' is a unit, not a plural noun.')]
    param([object]$Value)
    if ($null -eq $Value) { return -1 }
    if ($Value -is [datetime]) {
        return [int]([datetime]::UtcNow - $Value.ToUniversalTime()).TotalDays
    }
    if ($Value -is [int64] -or $Value -is [long]) {
        if ($Value -le 0 -or $Value -eq [Int64]::MaxValue) { return -1 }
        try {
            $dt = [datetime]::FromFileTimeUtc($Value)
            return [int]([datetime]::UtcNow - $dt).TotalDays
        } catch { return -1 }
    }
    return -1
}

# ----------------------------------------------------------------
# Forest / Tree / Trust Topology — Phase 1 baseline (run FIRST)
#
# Promoted from UIAOADAssessment.psm1::Export-UIAOForestTopology (inbox module)
# into this canonical Appendix F Phase 1 adapter. OrgPath is the DN-encoded org
# spine; a distinguishedName only has meaning once the forest root, the
# constituent domains (trees), and the trust boundaries joining them are known.
# So topology is established here, before the OU walk below.
#
# Wrapped in try/catch so the survey degrades gracefully (empty $Forest) on
# hosts without forest-wide reachability — same pattern as the GPO block.
# ----------------------------------------------------------------
Write-Verbose "Discovering forest / tree / trust topology..."
$Forest = $null
try {
    $adForest   = Get-ADForest -Server $Server
    $rootDomain = Get-ADDomain -Server $adForest.RootDomain

    # FSMO role holders (forest-wide + root-domain)
    $fsmo = [PSCustomObject]@{
        schemaMaster         = $adForest.SchemaMaster
        domainNamingMaster   = $adForest.DomainNamingMaster
        pdcEmulator          = $rootDomain.PDCEmulator
        ridMaster            = $rootDomain.RIDMaster
        infrastructureMaster = $rootDomain.InfrastructureMaster
    }

    # Each tree / domain in the forest
    $DomainList = @()
    foreach ($domName in $adForest.Domains) {
        try {
            $dom = Get-ADDomain -Server $domName
            $DomainList += [PSCustomObject]@{
                name                 = $dom.DNSRoot
                netbiosName          = $dom.NetBIOSName
                domainMode           = $dom.DomainMode.ToString()
                distinguishedName    = $dom.DistinguishedName
                pdcEmulator          = $dom.PDCEmulator
                ridMaster            = $dom.RIDMaster
                infrastructureMaster = $dom.InfrastructureMaster
                isForestRoot         = ($dom.DNSRoot -eq $adForest.RootDomain)
            }
        } catch {
            Write-Warning "Could not query domain $domName : $_"
        }
    }

    # Domain controllers across the forest
    $DCList = @()
    foreach ($dc in (Get-ADDomainController -Server $Server -Filter *)) {
        $DCList += [PSCustomObject]@{
            name            = $dc.Name
            domain          = $dc.Domain
            site            = $dc.Site
            ipv4Address     = $dc.IPv4Address
            operatingSystem = $dc.OperatingSystem
            osVersion       = $dc.OperatingSystemVersion
            isGlobalCatalog = $dc.IsGlobalCatalog
            isReadOnly      = $dc.IsReadOnly
            fsmoRoles       = ($dc.OperationMasterRoles -join "; ")
        }
    }

    # Inter-site replication links (topology spine for multi-tree forests)
    $SiteLinkList = @()
    foreach ($sl in (Get-ADReplicationSiteLink -Server $Server -Filter * `
                -Properties Cost, ReplicationFrequencyInMinutes)) {
        $SiteLinkList += [PSCustomObject]@{
            name                        = $sl.Name
            cost                        = $sl.Cost
            replicationFrequencyMinutes = $sl.ReplicationFrequencyInMinutes
            sites                       = ($sl.SitesIncluded -join "; ")
        }
    }

    # Trust relationships — tree-internal (intra-forest) + cross-forest/external
    $TrustList = @()
    try {
        foreach ($t in (Get-ADTrust -Server $Server -Filter * -Properties *)) {
            $TrustList += [PSCustomObject]@{
                name                    = $t.Name
                source                  = $t.Source
                target                  = $t.Target
                direction               = $t.Direction.ToString()
                trustType               = $t.TrustType.ToString()
                intraForest             = $t.IntraForest
                forestTransitive        = $t.ForestTransitive
                selectiveAuthentication = $t.SelectiveAuthentication
                sidFilteringForestAware = $t.SIDFilteringForestAware
                sidFilteringQuarantined = $t.SIDFilteringQuarantined
                # A cross-boundary trust with SID filtering NOT quarantined is a
                # SID-history privilege-escalation path UIAO surfaces before
                # migration. Informational here; see survey.py note re: a future
                # registered GOV code if this should become a blocking finding.
                sidFilteringRisk        = ((-not $t.IntraForest) -and (-not $t.SIDFilteringQuarantined))
            }
        }
    } catch {
        Write-Warning "Trust enumeration skipped: $_"
    }

    $Forest = [PSCustomObject]@{
        name              = $adForest.Name
        forestMode        = $adForest.ForestMode.ToString()
        rootDomain        = $adForest.RootDomain
        domainCount       = $adForest.Domains.Count
        globalCatalogs    = @($adForest.GlobalCatalogs)
        fsmoRoles         = $fsmo
        domains           = $DomainList
        domainControllers = $DCList
        siteLinks         = $SiteLinkList
        trusts            = $TrustList
    }
    Write-Verbose ("Forest: {0} | domains: {1} | DCs: {2} | trusts: {3}" -f `
        $adForest.Name, $DomainList.Count, $DCList.Count, $TrustList.Count)
} catch {
    Write-Warning "Forest topology discovery failed (need RSAT AD module + forest reachability): $_"
}

# ----------------------------------------------------------------
# OU Enumeration
# ----------------------------------------------------------------
Write-Verbose "Enumerating OUs..."
$OUs = Get-ADOrganizationalUnit -Server $Server `
    -Filter * `
    -Properties DistinguishedName, Name, gPLink, ManagedBy, WhenCreated `
    -SearchBase $BaseDN

$OUList = @()
foreach ($OU in $OUs) {
    $OUList += [PSCustomObject]@{
        distinguishedName    = $OU.DistinguishedName
        name                 = $OU.Name
        hasGpo               = (-not [string]::IsNullOrEmpty($OU.gPLink))
        hasDelegationOwner   = (-not [string]::IsNullOrEmpty($OU.ManagedBy))
        whenCreated          = $OU.WhenCreated
        # Age as a proxy for 2003-era topology (anything > 15 years old)
        ageYears             = [int]([datetime]::UtcNow - $OU.WhenCreated).TotalDays / 365
    }
}
Write-Verbose "OUs found: $($OUList.Count)"

# ----------------------------------------------------------------
# User Enumeration — Appendix F Phase 1 PowerShell block
# ----------------------------------------------------------------
Write-Verbose "Enumerating users..."
$Users = Get-ADUser -Server $Server `
    -Filter { Enabled -eq $true } `
    -Properties DistinguishedName, SamAccountName, EmployeeID, `
                Department, Manager, JobTitle, `
                LastLogonDate, PasswordLastSet, `
                extensionAttribute1, extensionAttribute2, `
                extensionAttribute3, extensionAttribute4 `
    -SearchBase $BaseDN

$UserList = @()
foreach ($User in $Users) {
    $UserList += [PSCustomObject]@{
        distinguishedName   = $User.DistinguishedName
        samAccountName      = $User.SamAccountName
        employeeId          = $User.EmployeeID
        department          = $User.Department
        jobTitle            = $User.JobTitle
        hasManager          = ($null -ne $User.Manager)
        lastLogonDays       = (Get-AgeDays -Value $User.LastLogonDate)
        passwordAgeDays     = (Get-AgeDays -Value $User.PasswordLastSet)
        # Current extensionAttributes — shows what Entra Connect already syncs
        existingOrgPath     = $User.extensionAttribute1
        existingRegion      = $User.extensionAttribute2
        existingLifecycle   = $User.extensionAttribute3
        existingMigStatus   = $User.extensionAttribute4
    }
}
Write-Verbose "Users found: $($UserList.Count)"

# ----------------------------------------------------------------
# Service Account Enumeration (objects with SPNs)
# ----------------------------------------------------------------
Write-Verbose "Enumerating service accounts (SPN holders)..."
$SAObjects = Get-ADUser -Server $Server `
    -Filter { ServicePrincipalName -like "*" } `
    -Properties DistinguishedName, SamAccountName, `
                ServicePrincipalName, PasswordLastSet, `
                LastLogonDate, TrustedForDelegation, `
                "msDS-AllowedToDelegateTo", `
                UserAccountControl `
    -SearchBase $BaseDN

$SAList = @()
foreach ($SA in $SAObjects) {
    # Delegation type
    $delegation = "none"
    if ($SA.TrustedForDelegation) {
        $delegation = "unconstrained"
    } elseif ($SA."msDS-AllowedToDelegateTo") {
        $delegation = "constrained"
    }

    $SAList += [PSCustomObject]@{
        distinguishedName   = $SA.DistinguishedName
        samAccountName      = $SA.SamAccountName
        spns                = ($SA.ServicePrincipalName -join "|")
        spnCount            = $SA.ServicePrincipalName.Count
        passwordAgeDays     = (Get-AgeDays -Value $SA.PasswordLastSet)
        lastLogonDays       = (Get-AgeDays -Value $SA.LastLogonDate)
        delegationType      = $delegation
        # ADCS heuristic — HTTP/certsrv or HOST/CA*
        adcsSuspect         = (
            ($SA.ServicePrincipalName -join " ") -match "certsrv|host/ca|certificateservices"
        )
    }
}
Write-Verbose "Service accounts (SPN holders): $($SAList.Count)"

# ----------------------------------------------------------------
# Computer Objects (optional — large forests may be slow)
# ----------------------------------------------------------------
$ComputerList = @()
if ($IncludeComputers) {
    Write-Verbose "Enumerating computer objects..."
    $Computers = Get-ADComputer -Server $Server `
        -Filter * `
        -Properties DistinguishedName, Name, OperatingSystem, `
                    LastLogonDate, Enabled `
        -SearchBase $BaseDN

    foreach ($Comp in $Computers) {
        $ComputerList += [PSCustomObject]@{
            distinguishedName = $Comp.DistinguishedName
            name              = $Comp.Name
            operatingSystem   = $Comp.OperatingSystem
            lastLogonDays     = (Get-AgeDays -Value $Comp.LastLogonDate)
            enabled           = $Comp.Enabled
            stale             = ((Get-AgeDays -Value $Comp.LastLogonDate) -gt 90)
        }
    }
    Write-Verbose "Computer objects: $($ComputerList.Count)"
}

# ----------------------------------------------------------------
# Sites and Services
# ----------------------------------------------------------------
Write-Verbose "Enumerating Sites and Services..."
$Sites = Get-ADReplicationSite -Server $Server -Filter * -Properties Name, WhenCreated

$SiteList = @()
foreach ($Site in $Sites) {
    # Check subnet associations — stale sites have none
    $Subnets = Get-ADReplicationSubnet -Server $Server `
        -Filter { Site -eq $Site.DistinguishedName } -ErrorAction SilentlyContinue
    $SiteList += [PSCustomObject]@{
        name          = $Site.Name
        whenCreated   = $Site.WhenCreated
        ageYears      = [int]([datetime]::UtcNow - $Site.WhenCreated).TotalDays / 365
        subnetCount   = ($Subnets | Measure-Object).Count
        likelyStale   = (($Subnets | Measure-Object).Count -eq 0)
    }
}
Write-Verbose "Sites: $($SiteList.Count)"

# ----------------------------------------------------------------
# GPO Inventory — Appendix F Phase 1
# ----------------------------------------------------------------
Write-Verbose "Enumerating GPOs..."
try {
    Import-Module GroupPolicy -ErrorAction Stop
    $GPOs = Get-GPO -All -Server $Server -Domain ($BaseDN -replace "DC=","" -replace ",",".")
    $GPOList = @()
    foreach ($GPO in $GPOs) {
        $GPOList += [PSCustomObject]@{
            displayName         = $GPO.DisplayName
            id                  = $GPO.Id
            modificationTime    = $GPO.ModificationTime
            daysSinceModified   = (Get-AgeDays -Value $GPO.ModificationTime)
            gpoStatus           = $GPO.GpoStatus
            # A GPO not modified in > 5 years is a strong candidate for archaeology
            likelyStale         = ((Get-AgeDays -Value $GPO.ModificationTime) -gt 1825)
        }
    }
    Write-Verbose "GPOs: $($GPOList.Count)"
} catch {
    Write-Warning "GroupPolicy module unavailable; GPO enumeration skipped: $_"
    $GPOList = @()
}

# ----------------------------------------------------------------
# Assemble output
# ----------------------------------------------------------------
# Forest-derived summary counts (null-safe: $Forest is $null when topology
# discovery was unreachable).
$forestDomainCount = if ($Forest) { $Forest.domainCount } else { 0 }
$forestDcCount     = if ($Forest) { @($Forest.domainControllers).Count } else { 0 }
$forestSiteLinks   = if ($Forest) { @($Forest.siteLinks).Count } else { 0 }
$forestTrustCount  = if ($Forest) { @($Forest.trusts).Count } else { 0 }
$forestRiskyTrusts = if ($Forest) { @($Forest.trusts | Where-Object { $_.sidFilteringRisk }).Count } else { 0 }

$Output = [PSCustomObject]@{
    forestRoot      = $BaseDN
    surveyTimestamp = [datetime]::UtcNow.ToString("o")
    forest          = $Forest
    ous             = $OUList
    users           = $UserList
    serviceAccounts = $SAList
    computers       = $ComputerList
    sites           = $SiteList
    gpos            = $GPOList
    summary         = [PSCustomObject]@{
        domainCount              = $forestDomainCount
        dcCount                  = $forestDcCount
        siteLinkCount            = $forestSiteLinks
        trustCount               = $forestTrustCount
        riskyTrustCount          = $forestRiskyTrusts
        ouCount                  = $OUList.Count
        userCount                = $UserList.Count
        serviceAccountCount      = $SAList.Count
        adcsSuspectCount         = ($SAList | Where-Object { $_.adcsSuspect }).Count
        unconstrainedDelegCount  = ($SAList | Where-Object { $_.delegationType -eq "unconstrained" }).Count
        computerCount            = $ComputerList.Count
        staleComputerCount       = ($ComputerList | Where-Object { $_.stale }).Count
        siteCount                = $SiteList.Count
        staleSiteCount           = ($SiteList | Where-Object { $_.likelyStale }).Count
        gpoCount                 = $GPOList.Count
        staleGpoCount            = ($GPOList | Where-Object { $_.likelyStale }).Count
        usersWithExistingOrgPath = ($UserList | Where-Object { -not [string]::IsNullOrEmpty($_.existingOrgPath) }).Count
    }
}

if ($OutputJson) {
    $Output | ConvertTo-Json -Depth 6 -Compress:$false
} else {
    # Human-readable summary
    Write-Host "`n=== UIAO AD Forest Survey Summary ===" -ForegroundColor Cyan
    Write-Host "Forest:          $BaseDN"
    if ($Forest) {
        Write-Host "Forest name:     $($Forest.name) (mode $($Forest.forestMode))"
        Write-Host "Domains/Trees:   $forestDomainCount"
        Write-Host "Domain Ctrls:    $forestDcCount"
        Write-Host "Site Links:      $forestSiteLinks"
        Write-Host "Trusts:          $forestTrustCount ($forestRiskyTrusts SID-filtering risk)"
    } else {
        Write-Host "Forest topology: (unavailable — see warnings above)" -ForegroundColor Yellow
    }
    Write-Host "OUs:             $($OUList.Count)"
    Write-Host "Users:           $($UserList.Count)"
    Write-Host "Service Accts:   $($SAList.Count) ($($Output.summary.adcsSuspectCount) ADCS-suspect)"
    Write-Host "Unconstrained:   $($Output.summary.unconstrainedDelegCount) delegation accounts"
    Write-Host "Computer Objs:   $($ComputerList.Count) ($($Output.summary.staleComputerCount) stale)"
    Write-Host "Sites:           $($SiteList.Count) ($($Output.summary.staleSiteCount) stale/no-subnet)"
    Write-Host "GPOs:            $($GPOList.Count) ($($Output.summary.staleGpoCount) not modified 5+ years)"
    Write-Host "Existing OrgPath: $($Output.summary.usersWithExistingOrgPath) users already have extensionAttribute1"
    Write-Host "`nRun with -OutputJson for machine-readable output consumed by survey.py"
}
