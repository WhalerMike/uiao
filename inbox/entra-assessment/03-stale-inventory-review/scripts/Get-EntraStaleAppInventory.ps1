<#
.SYNOPSIS
    Inventory stale apps and service principals in an Entra ID tenant.

.DESCRIPTION
    Read-only assessment. Enumerates Applications and ServicePrincipals,
    joins them, correlates with workload sign-in activity, owner counts,
    consent grants (delegated and application), and credential state.
    Emits a per-app CSV + JSON plus a disposition summary.

    See ../README.md "How the scripts work" section "Apps script" for the
    annotated walkthrough.

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER StaleDays
    Days since last sign-in considered stale. Default 180.

.PARAMETER NewAppGraceDays
    Apps younger than this and never-signed-in are flagged INVESTIGATE_NEW
    rather than SAFE_TO_DELETE. Default 30.

.PARAMETER IncludeMicrosoftBuiltIn
    Include first-party Microsoft-published service principals.
    Default off.

.NOTES
    Required Graph scopes:
      Application.Read.All
      Directory.Read.All
      AuditLog.Read.All
      Reports.Read.All
      DelegatedPermissionGrant.Read.All
      AppRoleAssignment.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Applications
      Microsoft.Graph.Identity.DirectoryManagement
      Microsoft.Graph.Authentication

    Connect before running:
      Connect-MgGraph -Scopes Application.Read.All, Directory.Read.All, AuditLog.Read.All, Reports.Read.All, DelegatedPermissionGrant.Read.All, AppRoleAssignment.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $OutputPath,

    [int]    $StaleDays        = 180,
    [int]    $NewAppGraceDays  = 30,
    [switch] $IncludeMicrosoftBuiltIn
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# ----- Setup -----------------------------------------------------------------

function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) {
        throw "Not connected to Microsoft Graph. See script header."
    }
    $required = @(
        'Application.Read.All','Directory.Read.All','AuditLog.Read.All',
        'Reports.Read.All','DelegatedPermissionGrant.Read.All','AppRoleAssignment.Read.All'
    )
    $missing = $required | Where-Object { $_ -notin $ctx.Scopes }
    if ($missing) {
        Write-Warning ("Connected, but missing recommended scopes: {0}. Some columns may be empty." -f ($missing -join ', '))
    }
    return $ctx
}

function New-OutputFolder {
    param([string] $Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
    return (Resolve-Path -LiteralPath $Path).Path
}

function ConvertTo-Days {
    param(
        [Nullable[datetime]] $From,
        [Nullable[datetime]] $To
    )
    if (-not $From -or -not $To) { return $null }
    return [int][math]::Floor((($To.ToUniversalTime() - $From.ToUniversalTime())).TotalDays)
}

function ConvertTo-DatetimeOrNull {
    param([object] $Value)
    if (-not $Value) { return $null }
    if ($Value -is [datetime]) { return $Value.ToUniversalTime() }
    try { return ([datetime]::Parse([string]$Value)).ToUniversalTime() } catch { return $null }
}

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

# ----- Enumerate -------------------------------------------------------------

Write-Host "Enumerating service principals..." -ForegroundColor Cyan
$sps = Get-MgServicePrincipal -All -PageSize 999 -Property @(
    'Id','AppId','DisplayName','PublisherName','ServicePrincipalType',
    'AccountEnabled','Tags','Notes','AppOwnerOrganizationId',
    'PasswordCredentials','KeyCredentials','SignInAudience','CreatedDateTime'
)
Write-Host ("  found {0} service principal(s)" -f $sps.Count)

if (-not $IncludeMicrosoftBuiltIn) {
    # WHY: Microsoft first-party SPs (AppOwnerOrganizationId = Microsoft tenant)
    #      can't be customer-managed; including them just adds noise.
    $msftTenant = 'f8cdef31-a31e-4b4a-93e4-5f571e91255a'
    $before = $sps.Count
    $sps    = $sps | Where-Object { $_.AppOwnerOrganizationId -ne $msftTenant }
    Write-Host ("  filtered out {0} Microsoft-published SP(s)" -f ($before - $sps.Count))
}

Write-Host "Enumerating applications..." -ForegroundColor Cyan
$apps = Get-MgApplication -All -PageSize 999 -Property @(
    'Id','AppId','DisplayName','CreatedDateTime','PasswordCredentials','KeyCredentials','Tags','Notes'
)
Write-Host ("  found {0} application(s) (apps homed in this tenant)" -f $apps.Count)

# Index apps by AppId for SP join
$appByAppId = @{}
foreach ($a in $apps) { if ($a.AppId) { $appByAppId[$a.AppId] = $a } }

# Sign-in activity (Track 1's source, repeated here)
Write-Host "Fetching service principal sign-in activity (beta)..." -ForegroundColor Cyan
$spActivity = @{}
try {
    $uri = 'https://graph.microsoft.com/beta/reports/servicePrincipalSignInActivity?$top=999'
    do {
        $page = Invoke-MgGraphRequest -Method GET -Uri $uri
        foreach ($row in $page['value']) {
            if ($row['appId']) { $spActivity[$row['appId']] = $row }
        }
        $uri = $page['@odata.nextLink']
    } while ($uri)
    Write-Host ("  loaded sign-in activity for {0} SP(s)" -f $spActivity.Count)
}
catch {
    Write-Warning ("Could not load servicePrincipalSignInActivity: {0}" -f $_.Exception.Message)
}

# Consent grants
# WHY: Pulling all delegated permission grants and app-role assignments
#      tenant-wide is far cheaper than per-SP enumeration. Aggregate counts
#      locally afterward.
Write-Host "Enumerating delegated permission grants (oauth2PermissionGrants)..." -ForegroundColor Cyan
$oauth2Grants = @{}
try {
    $uri = 'https://graph.microsoft.com/v1.0/oauth2PermissionGrants?$top=999'
    do {
        $page = Invoke-MgGraphRequest -Method GET -Uri $uri
        foreach ($g in $page['value']) {
            $clientId = $g['clientId']
            if (-not $oauth2Grants.ContainsKey($clientId)) { $oauth2Grants[$clientId] = 0 }
            $oauth2Grants[$clientId]++
        }
        $uri = $page['@odata.nextLink']
    } while ($uri)
    Write-Host ("  found grants for {0} client SP(s)" -f $oauth2Grants.Count)
}
catch {
    Write-Warning ("Could not enumerate oauth2PermissionGrants: {0}" -f $_.Exception.Message)
}

Write-Host "Enumerating app role assignments (per SP)..." -ForegroundColor Cyan
# WHY: appRoleAssignments are stored on the principal (the SP receiving the
#      assignment) — no tenant-wide list endpoint. Per-SP enumeration is
#      required. For large tenants this is the slowest step; reduce by
#      passing -IncludeMicrosoftBuiltIn:$false (default).
$appRoleCounts = @{}
$i = 0
foreach ($sp in $sps) {
    $i++
    if ($i % 100 -eq 0) { Write-Host ("  per-SP grants: {0}/{1}" -f $i, $sps.Count) }
    try {
        $assignments = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id -All -ErrorAction Stop
        $appRoleCounts[$sp.AppId] = @($assignments).Count
    }
    catch {
        $appRoleCounts[$sp.AppId] = 0
    }
}

# ----- Build records ---------------------------------------------------------

Write-Host "Building per-app records..." -ForegroundColor Cyan
$now     = (Get-Date).ToUniversalTime()
$records = New-Object System.Collections.Generic.List[object]

foreach ($sp in $sps) {
    $app = if ($sp.AppId -and $appByAppId.ContainsKey($sp.AppId)) { $appByAppId[$sp.AppId] } else { $null }
    $isMultiTenantHomeElsewhere = ($null -eq $app)

    # Owners (from app reg if present, else from SP)
    $owners = @()
    try {
        if ($app) {
            $owners = @(Get-MgApplicationOwner -ApplicationId $app.Id -All -ErrorAction Stop)
        }
        else {
            $owners = @(Get-MgServicePrincipalOwner -ServicePrincipalId $sp.Id -All -ErrorAction Stop)
        }
    } catch { }
    $ownerCount = $owners.Count

    # Created date — prefer app reg's, fall back to SP's
    $created = $null
    if     ($app -and $app.CreatedDateTime) { $created = $app.CreatedDateTime }
    elseif ($sp.CreatedDateTime)            { $created = $sp.CreatedDateTime }
    $accountAgeDays = ConvertTo-Days -From $created -To $now

    # Sign-in activity
    $spLastSignIn     = $null
    $spLastSignInDays = $null
    $appLastSignIn    = $null
    $appLastSignInDays= $null

    if ($spActivity.ContainsKey($sp.AppId)) {
        $row = $spActivity[$sp.AppId]
        $lsa = $row['lastSignInActivity']
        if ($lsa -and $lsa['lastSignInDateTime']) {
            $spLastSignIn     = ConvertTo-DatetimeOrNull $lsa['lastSignInDateTime']
            $spLastSignInDays = ConvertTo-Days -From $spLastSignIn -To $now
        }
        $aaca = $row['applicationAuthenticationClientSignInActivity']
        if ($aaca -and $aaca['lastSignInDateTime']) {
            $appLastSignIn     = ConvertTo-DatetimeOrNull $aaca['lastSignInDateTime']
            $appLastSignInDays = ConvertTo-Days -From $appLastSignIn -To $now
        }
    }

    # Consent grant counts
    $oauthCount   = if ($oauth2Grants.ContainsKey($sp.Id)) { $oauth2Grants[$sp.Id] } else { 0 }
    $appRoleCount = if ($appRoleCounts.ContainsKey($sp.AppId)) { $appRoleCounts[$sp.AppId] } else { 0 }

    # Credentials (from app reg if present)
    $secrets = if ($app) { @($app.PasswordCredentials) } else { @() }
    $expiredSecrets = @($secrets | Where-Object { $_.EndDateTime -and $_.EndDateTime -le $now }).Count

    # Disposition cascade — see README "Apps" decision tree
    $reasons = New-Object System.Collections.Generic.List[string]
    $disp    = 'INVESTIGATE'

    $tags = if ($app -and $app.Tags) { ($app.Tags -join ' ') } else { '' }
    $notes = if ($app) { $app.Notes } else { '' }
    $carveout = ($tags + ' ' + ($notes ?? '')) -match 'carveout:'

    $hasAnySignIn = ($null -ne $spLastSignInDays) -or ($null -ne $appLastSignInDays)
    $bestLastSignInDays = $null
    if ($null -ne $spLastSignInDays -and $null -ne $appLastSignInDays) {
        $bestLastSignInDays = [math]::Min($spLastSignInDays, $appLastSignInDays)
    }
    elseif ($null -ne $spLastSignInDays)  { $bestLastSignInDays = $spLastSignInDays }
    elseif ($null -ne $appLastSignInDays) { $bestLastSignInDays = $appLastSignInDays }

    if ($isMultiTenantHomeElsewhere) {
        $reasons.Add('app reg not in this tenant — SP only')
        $disp = 'MULTI_TENANT_HOME_ELSEWHERE'
    }
    elseif ($carveout) {
        $reasons.Add('carveout tag/note present')
        $disp = 'KEEP'
    }
    elseif ($null -ne $accountAgeDays -and $accountAgeDays -lt $NewAppGraceDays -and -not $hasAnySignIn) {
        $reasons.Add(("created {0}d ago; no sign-in yet" -f $accountAgeDays))
        $disp = 'INVESTIGATE_NEW'
    }
    elseif ($hasAnySignIn -and $expiredSecrets -gt 0 -and $expiredSecrets -ge @($secrets).Count -and @($secrets).Count -gt 0) {
        $reasons.Add(("recent sign-in; all {0} secrets expired" -f $expiredSecrets))
        $disp = 'INVESTIGATE_EXPIRED_CRED'
    }
    elseif ($hasAnySignIn -and $bestLastSignInDays -le $StaleDays) {
        if ($ownerCount -eq 0) {
            $reasons.Add('recent sign-in; no owners')
            $disp = 'ASSIGN_OWNER'
        }
        else {
            $reasons.Add('recent sign-in; has owners')
            $disp = 'KEEP'
        }
    }
    elseif (-not $hasAnySignIn -or $bestLastSignInDays -gt $StaleDays) {
        if ($ownerCount -gt 0) {
            $reasons.Add(("no sign-in {0}d; has owners" -f ($bestLastSignInDays ?? 'never')))
            $disp = 'NOTIFY_OWNER_STALE'
        }
        elseif ($oauthCount -gt 0 -or $appRoleCount -gt 0) {
            $reasons.Add(("no sign-in {0}d; no owners; consent grants present" -f ($bestLastSignInDays ?? 'never')))
            $disp = 'INVESTIGATE'
        }
        else {
            $reasons.Add(("no sign-in {0}d; no owners; no consent grants" -f ($bestLastSignInDays ?? 'never')))
            $disp = 'SAFE_TO_DELETE'
        }
    }

    $records.Add([pscustomobject]@{
        AppId                       = $sp.AppId
        DisplayName                 = $sp.DisplayName
        SpObjectId                  = $sp.Id
        AppObjectId                 = if ($app) { $app.Id } else { $null }
        IsMultiTenantHomeElsewhere  = $isMultiTenantHomeElsewhere
        ServicePrincipalType        = $sp.ServicePrincipalType
        AccountEnabled              = $sp.AccountEnabled
        OwnerCount                  = $ownerCount
        CreatedDateTime             = if ($created) { $created.ToString('o') } else { $null }
        AccountAgeDays              = $accountAgeDays
        SpLastSignIn                = if ($spLastSignIn)  { $spLastSignIn.ToString('o') }  else { $null }
        SpLastSignInDays            = $spLastSignInDays
        AppLastSignIn               = if ($appLastSignIn) { $appLastSignIn.ToString('o') } else { $null }
        AppLastSignInDays           = $appLastSignInDays
        Oauth2GrantCount            = $oauthCount
        AppRoleAssignmentCount      = $appRoleCount
        SecretCount                 = @($secrets).Count
        ExpiredSecretCount          = $expiredSecrets
        Tags                        = $tags
        Notes                       = $notes
        Disposition                 = $disp
        DispositionReasons          = ($reasons -join '; ')
    }) | Out-Null
}

# ----- Write outputs ---------------------------------------------------------

$csv     = Join-Path $out "stale-apps-$timestamp.csv"
$json    = Join-Path $out "stale-apps-$timestamp.json"
$summary = Join-Path $out "summary-$timestamp.txt"

$records | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
$records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $json -Encoding UTF8

$lines = @(
    "Stale apps inventory"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ""
    ("Service principals examined: {0}" -f $records.Count)
    ""
    "Disposition breakdown:"
)
foreach ($g in ($records | Group-Object Disposition | Sort-Object Count -Descending)) {
    $lines += ("  {0,-32} {1,6}" -f $g.Name, $g.Count)
}
$lines | Set-Content -LiteralPath $summary -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ("  Apps CSV:  {0}" -f $csv)
Write-Host ("  Apps JSON: {0}" -f $json)
Write-Host ("  Summary:   {0}" -f $summary)
Write-Host ""
$lines | Write-Host
