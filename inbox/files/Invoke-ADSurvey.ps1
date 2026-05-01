<#
.SYNOPSIS
    UIAO AD Adapter — Forest Archaeological Survey
    Canon reference: Appendix F Phase 1 (Discovery)
    Emits structured JSON consumed by survey.py::_run_powershell_survey()

.DESCRIPTION
    Read-only enumeration of an AD forest. Requires RSAT ActiveDirectory module
    or domain-joined execution context.

    Enumerates:
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
$Output = [PSCustomObject]@{
    forestRoot      = $BaseDN
    surveyTimestamp = [datetime]::UtcNow.ToString("o")
    ous             = $OUList
    users           = $UserList
    serviceAccounts = $SAList
    computers       = $ComputerList
    sites           = $SiteList
    gpos            = $GPOList
    summary         = [PSCustomObject]@{
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
