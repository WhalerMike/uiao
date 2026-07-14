<#
.SYNOPSIS
    Inventory third-party SaaS integrations in an Entra ID tenant and join them
    against FedRAMP Marketplace authorization status.

.DESCRIPTION
    Read-only assessment. Enumerates service principals instantiated from the
    Entra application gallery, records how each is integrated (SSO mode, whether
    a SCIM synchronization job exists), and — when a FedRAMP Marketplace export
    is supplied — reports an authorization match verdict per integration.

    Produces the two evidence artifacts that
    src/uiao/canon/data/control-library/sa/SA-9.yml already declares but does
    not currently produce:
      - entra-id-external-application-registrations
      - fedramp-marketplace-authorization-verifications

    Scope: FedRAMP Moderate + Microsoft GCC Moderate.

    See ../README.md for why this track exists and what the verdicts mean.
    In particular: this script NEVER emits an "unauthorized" verdict. Absence
    of a name match is not evidence of absence of authorization.

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER FedrampMarketplacePath
    Optional CSV export from https://www.fedramp.gov/marketplace/ filtered to
    Authorized at Moderate or High. Without it, every row is NOT_CHECKED and
    only the inventory artifact is meaningful.

.PARAMETER FedrampNameColumn
    Column in the export holding the service offering name. Auto-detected from
    common headers when omitted.

.PARAMETER IncludeMicrosoftBuiltIn
    Include first-party Microsoft-published service principals. Default off —
    M365 is the boundary, not an integration into it.

.NOTES
    Required Graph scopes:
      Application.Read.All
      Directory.Read.All
      Synchronization.Read.All
      DelegatedPermissionGrant.Read.All
      AppRoleAssignment.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Applications
      Microsoft.Graph.Authentication

    Connect before running:
      Connect-MgGraph -Scopes Application.Read.All, Directory.Read.All, Synchronization.Read.All, DelegatedPermissionGrant.Read.All, AppRoleAssignment.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string] $OutputPath,

    [string] $FedrampMarketplacePath,
    [string] $FedrampNameColumn,
    [switch] $IncludeMicrosoftBuiltIn
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# WHY: "Create your own application" instantiates a service principal with this
#      well-known template id. It is NOT a gallery app — it's the custom/
#      non-gallery path — so it must be excluded or every hand-rolled app
#      registration pollutes the SaaS inventory.
#      Verified against the Graph applicationTemplate reference, which names it
#      verbatim: "The application template with ID 8adf8e6e-67b2-4cf2-a259-e3dc5476c621
#      can be used to add a non-gallery app."
#      https://learn.microsoft.com/en-us/graph/api/resources/applicationtemplate
$CustomAppTemplateId = '8adf8e6e-67b2-4cf2-a259-e3dc5476c621'
$MicrosoftTenantId   = 'f8cdef31-a31e-4b4a-93e4-5f571e91255a'

# ----- Setup -----------------------------------------------------------------

function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) {
        throw "Not connected to Microsoft Graph. See script header."
    }
    $required = @(
        'Application.Read.All','Directory.Read.All','Synchronization.Read.All',
        'DelegatedPermissionGrant.Read.All','AppRoleAssignment.Read.All'
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

function ConvertTo-NormalizedName {
    <#
      Lowercase, strip punctuation, collapse whitespace, drop corporate-form
      noise words. Deliberately does NOT strip "government", "gov", "federal"
      or "high" — those are exactly the tokens that distinguish an authorized
      offering from its commercial twin, and collapsing them would manufacture
      false matches.
    #>
    param([string] $Name)
    if (-not $Name) { return '' }
    $n = $Name.ToLowerInvariant()
    $n = $n -replace '[^a-z0-9 ]', ' '
    $n = ($n -split '\s+' | Where-Object { $_ -and $_ -notin @('inc','llc','ltd','corp','corporation','the','a') }) -join ' '
    return $n.Trim()
}

# ----- FedRAMP marketplace export --------------------------------------------

function Import-FedrampExport {
    param([string] $Path, [string] $NameColumn)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw ("FedRAMP export not found: {0}" -f $Path)
    }
    $rows = @(Import-Csv -LiteralPath $Path)
    if (-not $rows -or $rows.Count -eq 0) {
        throw ("FedRAMP export is empty: {0}" -f $Path)
    }

    $headers = $rows[0].PSObject.Properties.Name
    if (-not $NameColumn) {
        # WHY: the marketplace export's header has changed across revisions;
        #      auto-detect rather than pin to one spelling.
        $candidates = @('Cloud Service Offering','CSO','CSO Name','Service Name','Service Offering','Name')
        $NameColumn = $candidates | Where-Object { $_ -in $headers } | Select-Object -First 1
        if (-not $NameColumn) {
            throw ("Could not auto-detect the name column. Headers found: {0}. Pass -FedrampNameColumn." -f ($headers -join ', '))
        }
        Write-Host ("  auto-detected name column: '{0}'" -f $NameColumn)
    }
    elseif ($NameColumn -notin $headers) {
        throw ("Column '{0}' not in export. Headers found: {1}" -f $NameColumn, ($headers -join ', '))
    }

    $index = @{}
    foreach ($r in $rows) {
        $raw = [string]$r.$NameColumn
        if (-not $raw) { continue }
        $norm = ConvertTo-NormalizedName $raw
        if (-not $norm) { continue }
        if (-not $index.ContainsKey($norm)) {
            $index[$norm] = [pscustomobject]@{ Name = $raw; Tokens = @($norm -split ' ') }
        }
    }
    Write-Host ("  indexed {0} distinct offering name(s) from {1} row(s)" -f $index.Count, $rows.Count)
    return $index
}

function Get-FedrampVerdict {
    param([string] $DisplayName, [hashtable] $Index)

    if (-not $Index) {
        return [pscustomobject]@{ Verdict = 'NOT_CHECKED'; MatchedName = $null; Detail = 'no marketplace export supplied' }
    }

    $norm = ConvertTo-NormalizedName $DisplayName
    if (-not $norm) {
        return [pscustomobject]@{ Verdict = 'NO_MATCH_VERIFY_MANUALLY'; MatchedName = $null; Detail = 'empty display name' }
    }

    if ($Index.ContainsKey($norm)) {
        return [pscustomobject]@{ Verdict = 'AUTHORIZED_EXACT'; MatchedName = $Index[$norm].Name; Detail = 'exact normalized match' }
    }

    # WHY: token-subset in EITHER direction. "atlassian cloud" is a subset of
    #      "atlassian cloud for government" and vice-versa is also informative.
    #      Both are reported as VERIFY, never as authorized — the extra tokens
    #      may be precisely the ones that matter.
    $spTokens = @($norm -split ' ')
    foreach ($key in $Index.Keys) {
        $mkTokens = $Index[$key].Tokens
        $spInMk = -not (@($spTokens | Where-Object { $_ -notin $mkTokens }))
        $mkInSp = -not (@($mkTokens | Where-Object { $_ -notin $spTokens }))
        if ($spInMk -or $mkInSp) {
            return [pscustomobject]@{
                Verdict     = 'AUTHORIZED_FUZZY_VERIFY'
                MatchedName = $Index[$key].Name
                Detail      = ("token-subset match against '{0}' — CONFIRM BY HAND" -f $Index[$key].Name)
            }
        }
    }

    return [pscustomobject]@{
        Verdict     = 'NO_MATCH_VERIFY_MANUALLY'
        MatchedName = $null
        Detail      = 'no marketplace name matched — may be unauthorized, may be a naming mismatch'
    }
}

# ----- Main ------------------------------------------------------------------

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

$fedrampIndex = $null
if ($FedrampMarketplacePath) {
    Write-Host "Loading FedRAMP Marketplace export..." -ForegroundColor Cyan
    $fedrampIndex = Import-FedrampExport -Path $FedrampMarketplacePath -NameColumn $FedrampNameColumn
}
else {
    Write-Warning "No -FedrampMarketplacePath supplied. Inventory only; all verdicts will be NOT_CHECKED."
}

Write-Host "Enumerating service principals..." -ForegroundColor Cyan
$sps = Get-MgServicePrincipal -All -PageSize 999 -Property @(
    'Id','AppId','DisplayName','PublisherName','ServicePrincipalType',
    'AccountEnabled','Tags','Notes','AppOwnerOrganizationId',
    'ApplicationTemplateId','PreferredSingleSignOnMode','SignInAudience','CreatedDateTime'
)
Write-Host ("  found {0} service principal(s)" -f $sps.Count)

if (-not $IncludeMicrosoftBuiltIn) {
    $before = $sps.Count
    $sps    = @($sps | Where-Object { $_.AppOwnerOrganizationId -ne $MicrosoftTenantId })
    Write-Host ("  filtered out {0} Microsoft-published SP(s)" -f ($before - $sps.Count))
}

# WHY: applicationTemplateId is the definitive gallery marker — a non-null value
#      that isn't the custom-app template means this SP was instantiated from a
#      gallery template, i.e. it came from the tutorial-list catalog. This is a
#      stronger signal than Track 3's MULTI_TENANT_HOME_ELSEWHERE heuristic.
$gallery = @($sps | Where-Object {
    $_.ApplicationTemplateId -and $_.ApplicationTemplateId -ne $CustomAppTemplateId
})
Write-Host ("  {0} gallery-instantiated SP(s) in scope" -f $gallery.Count) -ForegroundColor Yellow

Write-Host "Enumerating delegated permission grants..." -ForegroundColor Cyan
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
}
catch {
    Write-Warning ("Could not enumerate oauth2PermissionGrants: {0}" -f $_.Exception.Message)
}

Write-Host "Checking synchronization jobs (SCIM provisioning) per gallery SP..." -ForegroundColor Cyan
$records = New-Object System.Collections.Generic.List[object]
$i = 0

foreach ($sp in $gallery) {
    $i++
    if ($i % 25 -eq 0) { Write-Host ("  {0}/{1}" -f $i, $gallery.Count) }

    # SCIM detection: presence of a synchronization job on the SP. 404 is the
    # normal "provisioning was never configured" answer, not an error.
    $hasScim     = $false
    $scimJobIds  = @()
    $scimStatus  = $null
    try {
        $syncUri = ("https://graph.microsoft.com/v1.0/servicePrincipals/{0}/synchronization/jobs" -f $sp.Id)
        $jobs    = Invoke-MgGraphRequest -Method GET -Uri $syncUri -ErrorAction Stop
        $jobList = @($jobs['value'])
        if ($jobList.Count -gt 0) {
            $hasScim    = $true
            $scimJobIds = @($jobList | ForEach-Object { $_['templateId'] })
            $scimStatus = ($jobList | ForEach-Object {
                if ($_.ContainsKey('status') -and $_['status'] -and $_['status'].ContainsKey('code')) { $_['status']['code'] } else { 'unknown' }
            }) -join ','
        }
    }
    catch {
        # 404 / 400 => no synchronization configured. Anything else is worth surfacing.
        if ($_.Exception.Message -notmatch '404|NotFound|400|BadRequest') {
            Write-Verbose ("sync check failed for {0}: {1}" -f $sp.DisplayName, $_.Exception.Message)
        }
    }

    $owners = @()
    try { $owners = @(Get-MgServicePrincipalOwner -ServicePrincipalId $sp.Id -All -ErrorAction Stop) } catch { }

    $ssoMode = if ($sp.PreferredSingleSignOnMode) { $sp.PreferredSingleSignOnMode } else { 'notConfigured' }
    $fedramp = Get-FedrampVerdict -DisplayName $sp.DisplayName -Index $fedrampIndex

    # Risk cell — the pair that decides review order. A SCIM-provisioned app with
    # no marketplace match is standing directory data in an unverified CSO.
    $riskCell =
        if ($hasScim -and $fedramp.Verdict -eq 'NO_MATCH_VERIFY_MANUALLY')      { 'SCIM_UNVERIFIED' }
        elseif ($hasScim -and $fedramp.Verdict -eq 'AUTHORIZED_FUZZY_VERIFY')   { 'SCIM_FUZZY' }
        elseif ($hasScim)                                                        { 'SCIM_MATCHED' }
        elseif ($fedramp.Verdict -eq 'NO_MATCH_VERIFY_MANUALLY')                { 'SSO_UNVERIFIED' }
        else                                                                     { 'SSO_OTHER' }

    # CA-3: an interconnection exists when directory data flows outbound on a
    # standing basis. SCIM is that; SSO alone is not.
    $needsIsa = $hasScim

    $records.Add([pscustomobject]@{
        DisplayName             = $sp.DisplayName
        AppId                   = $sp.AppId
        SpObjectId              = $sp.Id
        PublisherName           = $sp.PublisherName
        ApplicationTemplateId   = $sp.ApplicationTemplateId
        AccountEnabled          = $sp.AccountEnabled
        SsoMode                 = $ssoMode
        HasScimProvisioning     = $hasScim
        ScimJobTemplateIds      = ($scimJobIds -join ';')
        ScimJobStatus           = $scimStatus
        OwnerCount              = $owners.Count
        Oauth2GrantCount        = if ($oauth2Grants.ContainsKey($sp.Id)) { $oauth2Grants[$sp.Id] } else { 0 }
        CreatedDateTime         = if ($sp.CreatedDateTime) { $sp.CreatedDateTime.ToString('o') } else { $null }
        FedrampVerdict          = $fedramp.Verdict
        FedrampMatchedName      = $fedramp.MatchedName
        FedrampDetail           = $fedramp.Detail
        RiskCell                = $riskCell
        RequiresIsaUnderCa3     = $needsIsa
    }) | Out-Null
}

# ----- Write outputs ---------------------------------------------------------

# Artifact 1: entra-id-external-application-registrations (per SA-9.yml)
$invCsv  = Join-Path $out "saas-integrations-$timestamp.csv"
$invJson = Join-Path $out "saas-integrations-$timestamp.json"
$records | Export-Csv -LiteralPath $invCsv -NoTypeInformation -Encoding UTF8
$records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $invJson -Encoding UTF8

# Artifact 2: fedramp-marketplace-authorization-verifications (per SA-9.yml)
$verCsv  = Join-Path $out "fedramp-verification-$timestamp.csv"
$verJson = Join-Path $out "fedramp-verification-$timestamp.json"
$verification = $records | Select-Object DisplayName, AppId, SsoMode, HasScimProvisioning,
                                         FedrampVerdict, FedrampMatchedName, FedrampDetail,
                                         RequiresIsaUnderCa3
$verification | Export-Csv -LiteralPath $verCsv -NoTypeInformation -Encoding UTF8
$verification | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $verJson -Encoding UTF8

$summaryPath = Join-Path $out "summary-$timestamp.txt"
$lines = @(
    "SaaS integration authorization inventory (Track 4 / SA-9)"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ("Marketplace export: {0}" -f ($(if ($FedrampMarketplacePath) { $FedrampMarketplacePath } else { '(none — verdicts NOT_CHECKED)' })))
    ""
    ("Gallery-instantiated integrations: {0}" -f $records.Count)
    ("  with SCIM provisioning:          {0}" -f @($records | Where-Object { $_.HasScimProvisioning }).Count)
    ("  requiring an ISA under CA-3:     {0}" -f @($records | Where-Object { $_.RequiresIsaUnderCa3 }).Count)
    ""
    "FedRAMP verdict breakdown:"
)
foreach ($g in ($records | Group-Object FedrampVerdict | Sort-Object Count -Descending)) {
    $lines += ("  {0,-28} {1,6}" -f $g.Name, $g.Count)
}
$lines += ""
$lines += "Risk cell breakdown (work SCIM_UNVERIFIED first):"
foreach ($g in ($records | Group-Object RiskCell | Sort-Object Count -Descending)) {
    $lines += ("  {0,-28} {1,6}" -f $g.Name, $g.Count)
}
$lines += ""
$lines += "NOTE: no UNAUTHORIZED verdict is emitted. NO_MATCH_VERIFY_MANUALLY means"
$lines += "the name did not match — it is a review queue, not a finding."
$lines | Set-Content -LiteralPath $summaryPath -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ("  Inventory CSV:    {0}" -f $invCsv)
Write-Host ("  Verification CSV: {0}" -f $verCsv)
Write-Host ("  Summary:          {0}" -f $summaryPath)
Write-Host ""
$lines | Write-Host
