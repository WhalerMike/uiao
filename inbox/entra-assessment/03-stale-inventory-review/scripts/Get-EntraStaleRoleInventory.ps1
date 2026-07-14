<#
.SYNOPSIS
    Inventory stale Entra ID directory role assignments and eligibilities.

.DESCRIPTION
    Read-only assessment. Enumerates:
      - Active directory role assignments (/roleManagement/directory/roleAssignments)
      - PIM eligibility instances (/roleManagement/directory/roleEligibilityScheduleInstances)
    Resolves each principal (User / Group / ServicePrincipal) and classifies
    the assignment by principal state, role privilege level, and group
    membership health.

    Does NOT enrich with PIM activation history (audit-log dependent — see
    README "Roles script" walkthrough).

    Safe to re-run. Does NOT modify the tenant.

.PARAMETER OutputPath
    Folder to write reports into. Created if missing.

.PARAMETER HighPrivilegeRoleTemplateIds
    Override the built-in list of role-template IDs considered
    "high-privilege". Used to flag CONVERT_TO_ELIGIBLE suggestions.

.NOTES
    Required Graph scopes:
      RoleManagement.Read.Directory
      Directory.Read.All
      User.Read.All

    Required modules (PowerShell 7+):
      Microsoft.Graph.Identity.Governance
      Microsoft.Graph.Identity.DirectoryManagement
      Microsoft.Graph.Authentication

    Connect before running:
      Connect-MgGraph -Scopes RoleManagement.Read.Directory, Directory.Read.All, User.Read.All
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]   $OutputPath,

    [string[]] $HighPrivilegeRoleTemplateIds
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

# WHY: Hardcoded list of role-template IDs Microsoft documents as
#      "Privileged" in Entra. These are the well-known GUIDs Microsoft uses
#      for built-in roles; verify against current docs before relying on
#      this list for compliance reporting.
$DefaultHighPrivilegeRoleTemplateIds = @(
    '62e90394-69f5-4237-9190-012177145e10',   # Global Administrator
    'e8611ab8-c189-46e8-94e1-60213ab1f814',   # Privileged Role Administrator
    'fe930be7-5e62-47db-91af-98c3a49a38b1',   # User Administrator
    '9b895d92-2cd3-44c7-9d02-a6ac2d5ea5c3',   # Application Administrator
    '158c047a-c907-4556-b7ef-446551a6b5f7',   # Cloud Application Administrator
    '7be44c8a-adaf-4e2a-84d6-ab2649e08a13',   # Privileged Authentication Administrator
    '194ae4cb-b126-40b2-bd5b-6091b380977d',   # Security Administrator
    'b0f54661-2d74-4c50-afa3-1ec803f12efe',   # Billing Administrator
    'b1be1c3e-b65d-4f19-8427-f6fa0d97feb9',   # Conditional Access Administrator
    'fdd7a751-b60b-444a-984c-02652fe8fa1c',   # Groups Administrator
    '729827e3-9c14-49f7-bb1b-9608f156bbb8',   # Helpdesk Administrator
    '966707d0-3269-4727-9be2-8c3a10f19b9d',   # Password Administrator
    '0526716b-113d-4c15-b2c8-68e3c22b9f80',   # Authentication Policy Administrator
    'f28a1f50-f6e7-4571-818b-6a12f2af6b6c',   # SharePoint Administrator
    '29232cdf-9323-42fd-ade2-1d097af3e4de'    # Exchange Administrator
)

if (-not $HighPrivilegeRoleTemplateIds) {
    $HighPrivilegeRoleTemplateIds = $DefaultHighPrivilegeRoleTemplateIds
}

# ----- Setup -----------------------------------------------------------------

function Test-GraphContext {
    $ctx = Get-MgContext
    if (-not $ctx) { throw "Not connected to Microsoft Graph. See script header." }
    $required = @('RoleManagement.Read.Directory','Directory.Read.All','User.Read.All')
    $missing  = $required | Where-Object { $_ -notin $ctx.Scopes }
    if ($missing) {
        Write-Warning ("Connected, but missing recommended scopes: {0}." -f ($missing -join ', '))
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

$ctx       = Test-GraphContext
$out       = New-OutputFolder -Path $OutputPath
$timestamp = (Get-Date).ToString('yyyy-MM-ddTHH-mm-ss')

Write-Host ("Tenant: {0}" -f $ctx.TenantId) -ForegroundColor Cyan
Write-Host ("Output: {0}" -f $out)          -ForegroundColor Cyan

# ----- Role definitions (template IDs -> names) ------------------------------

Write-Host "Loading role definitions..." -ForegroundColor Cyan
$roleDefs = @{}
$page = Invoke-MgGraphRequest -Method GET -Uri 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleDefinitions?$top=999'
foreach ($r in $page['value']) {
    $roleDefs[$r['id']] = @{
        displayName    = $r['displayName']
        templateId     = $r['templateId']
        isHighPrivilege = ($r['templateId'] -in $HighPrivilegeRoleTemplateIds)
    }
}
Write-Host ("  loaded {0} role definitions" -f $roleDefs.Count)

# ----- Principal resolution cache --------------------------------------------

# WHY: Many assignments share principals (a single Group Admin may hold five
#      role assignments). Caching principal lookups by object ID avoids
#      duplicate Graph calls.
$principalCache = @{}

function Resolve-Principal {
    param([string] $Id)
    if (-not $Id) { return $null }
    if ($principalCache.ContainsKey($Id)) { return $principalCache[$Id] }

    # WHY: /directoryObjects/{id} returns the object regardless of type
    #      (User / Group / SP / DeviceCode etc.) and includes @odata.type.
    #      Faster than trying each type-specific endpoint and catching 404s.
    $info = @{
        ObjectId       = $Id
        Type           = 'Unknown'
        DisplayName    = $null
        Upn            = $null
        AccountEnabled = $null
        Resolved       = $false
        MemberCount    = $null
    }
    try {
        $obj = Invoke-MgGraphRequest -Method GET -Uri ("https://graph.microsoft.com/v1.0/directoryObjects/{0}" -f $Id)
        $info.Resolved    = $true
        $info.DisplayName = $obj['displayName']

        switch -Regex ($obj['@odata.type']) {
            'user'             {
                $info.Type           = 'User'
                $info.Upn            = $obj['userPrincipalName']
                $info.AccountEnabled = $obj['accountEnabled']
            }
            'group'            {
                $info.Type = 'Group'
                # Member count — separate call, expensive in large groups but
                # required for REMOVE_GROUP_NO_MEMBERS detection.
                try {
                    $countResp = Invoke-MgGraphRequest -Method GET `
                        -Uri ("https://graph.microsoft.com/v1.0/groups/{0}/members/`$count" -f $Id) `
                        -Headers @{ 'ConsistencyLevel' = 'eventual' }
                    $info.MemberCount = [int]$countResp
                } catch {
                    $info.MemberCount = $null
                }
            }
            'servicePrincipal' {
                $info.Type           = 'ServicePrincipal'
                $info.AccountEnabled = $obj['accountEnabled']
            }
            default { $info.Type = $obj['@odata.type'] }
        }
    }
    catch {
        # Principal can't be resolved — orphan reference
        Write-Verbose ("Could not resolve principal {0}: {1}" -f $Id, $_.Exception.Message)
    }

    $principalCache[$Id] = $info
    return $info
}

# ----- Active role assignments -----------------------------------------------

Write-Host "Enumerating active role assignments..." -ForegroundColor Cyan
$assignments = New-Object System.Collections.Generic.List[object]
$uri = 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleAssignments?$top=999'
do {
    $page = Invoke-MgGraphRequest -Method GET -Uri $uri
    foreach ($a in $page['value']) {
        $assignments.Add(@{
            type            = 'Active'
            roleDefinitionId = $a['roleDefinitionId']
            principalId     = $a['principalId']
            scopeId         = $a['directoryScopeId']
            id              = $a['id']
            startDateTime   = $null
        }) | Out-Null
    }
    $uri = $page['@odata.nextLink']
} while ($uri)
Write-Host ("  found {0} active assignment(s)" -f $assignments.Count)

# ----- Eligibility instances -------------------------------------------------

Write-Host "Enumerating role-eligibility schedule instances..." -ForegroundColor Cyan
try {
    $uri = 'https://graph.microsoft.com/v1.0/roleManagement/directory/roleEligibilityScheduleInstances?$top=999'
    do {
        $page = Invoke-MgGraphRequest -Method GET -Uri $uri
        foreach ($e in $page['value']) {
            $assignments.Add(@{
                type            = 'Eligible'
                roleDefinitionId = $e['roleDefinitionId']
                principalId     = $e['principalId']
                scopeId         = $e['directoryScopeId']
                id              = $e['id']
                startDateTime   = $e['startDateTime']
            }) | Out-Null
        }
        $uri = $page['@odata.nextLink']
    } while ($uri)
    Write-Host ("  total assignments + eligibilities: {0}" -f $assignments.Count)
}
catch {
    Write-Warning ("Could not enumerate eligibility instances (PIM may not be licensed): {0}" -f $_.Exception.Message)
}

# ----- Build records ---------------------------------------------------------

Write-Host "Resolving principals and classifying..." -ForegroundColor Cyan
$records = New-Object System.Collections.Generic.List[object]
$i = 0

foreach ($a in $assignments) {
    $i++
    if ($i % 200 -eq 0) { Write-Host ("  processed {0}/{1}" -f $i, $assignments.Count) }

    $role = $roleDefs[$a.roleDefinitionId]
    $roleName = if ($role) { $role.displayName } else { '<unknown>' }
    $highPriv = if ($role) { $role.isHighPrivilege } else { $false }

    $p = Resolve-Principal -Id $a.principalId

    # Disposition cascade — see README "Roles" decision tree
    $reasons = New-Object System.Collections.Generic.List[string]
    $disp    = 'KEEP'

    if (-not $p.Resolved) {
        $reasons.Add('principal not found in directory')
        $disp = 'REMOVE_DELETED_PRINCIPAL'
    }
    elseif ($p.Type -eq 'User' -and $p.AccountEnabled -eq $false) {
        $reasons.Add('principal user is disabled')
        $disp = 'REMOVE_DISABLED_PRINCIPAL'
    }
    elseif ($p.Type -eq 'Group' -and $null -ne $p.MemberCount -and $p.MemberCount -eq 0) {
        $reasons.Add('role-assignable group has 0 members')
        $disp = 'REMOVE_GROUP_NO_MEMBERS'
    }
    elseif ($a.type -eq 'Active' -and $highPriv -and $p.Type -eq 'User') {
        $reasons.Add('permanent active assignment to high-privilege role')
        $disp = 'CONVERT_TO_ELIGIBLE'
    }
    elseif ($a.type -eq 'Active') {
        $reasons.Add('active assignment, principal healthy')
        $disp = 'KEEP'
    }
    elseif ($a.type -eq 'Eligible') {
        $reasons.Add('PIM eligibility (activation history not enriched)')
        $disp = 'KEEP'
    }

    $records.Add([pscustomobject]@{
        AssignmentType        = $a.type
        AssignmentId          = $a.id
        RoleDefinitionId      = $a.roleDefinitionId
        RoleDisplayName       = $roleName
        IsHighPrivilege       = $highPriv
        PrincipalId           = $a.principalId
        PrincipalType         = $p.Type
        PrincipalResolved     = $p.Resolved
        PrincipalDisplayName  = $p.DisplayName
        PrincipalUpn          = $p.Upn
        PrincipalEnabled      = $p.AccountEnabled
        PrincipalGroupMembers = $p.MemberCount
        Scope                 = $a.scopeId
        StartDateTime         = $a.startDateTime
        Disposition           = $disp
        DispositionReasons    = ($reasons -join '; ')
    }) | Out-Null
}

# ----- Write outputs ---------------------------------------------------------

$csv     = Join-Path $out "stale-roles-$timestamp.csv"
$json    = Join-Path $out "stale-roles-$timestamp.json"
$summary = Join-Path $out "summary-$timestamp.txt"

$records | Export-Csv -LiteralPath $csv -NoTypeInformation -Encoding UTF8
$records | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $json -Encoding UTF8

$lines = @(
    "Stale role assignments inventory"
    ("Tenant:    {0}" -f $ctx.TenantId)
    ("Generated: {0}" -f (Get-Date).ToString('o'))
    ""
    ("Total role assignments + eligibilities: {0}" -f $records.Count)
    ("  high-privilege:  {0}" -f @($records | Where-Object { $_.IsHighPrivilege }).Count)
    ("  active:          {0}" -f @($records | Where-Object { $_.AssignmentType -eq 'Active' }).Count)
    ("  eligible (PIM):  {0}" -f @($records | Where-Object { $_.AssignmentType -eq 'Eligible' }).Count)
    ""
    "Disposition breakdown:"
)
foreach ($g in ($records | Group-Object Disposition | Sort-Object Count -Descending)) {
    $lines += ("  {0,-32} {1,6}" -f $g.Name, $g.Count)
}
$lines | Set-Content -LiteralPath $summary -Encoding UTF8

Write-Host ""
Write-Host "Done." -ForegroundColor Green
Write-Host ("  Roles CSV:  {0}" -f $csv)
Write-Host ("  Roles JSON: {0}" -f $json)
Write-Host ("  Summary:    {0}" -f $summary)
Write-Host ""
$lines | Write-Host
