#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Applications
<#
.SYNOPSIS
    Build the Enterprise Application inventory that every governance step
    depends on: owner status, granted permissions, and an auto-assigned risk
    tier. Flags orphaned apps (no owner) and apps holding critical application
    permissions.

.DESCRIPTION
    Implements the prerequisite "inventory + ownership + risk" step shared by
    all three source documents (Doc 3 risk tiers; Doc 2 Step 1-2 inventory &
    owner assignment). Read-only — it changes nothing in the tenant.

    Risk tiering (from Doc 3 §4 / §8.3 risk table), as this script computes it:
      Tier 1  - holds ANY critical permission (application permission, or a
                delegated scope with the same name), OR has no owner
                (orphaned -> auto-Tier 1).
      Tier 2  - holds a high-risk permission (application or delegated).
      Tier 3  - minimal scopes only.
    "Externally published" (Doc 3) is NOT detected here: Graph exposes no single
    flag for it. Raise those apps to Tier 1 by hand from the Application Registry.

    Ownership: an app counts as owned when its service principal OR, for apps
    registered in this tenant, its application object has at least one owner.
    Owners on the application object (App registrations) are the usual place
    they are recorded; reading only service-principal owners would mark most
    tenant-registered apps orphaned.

.PARAMETER OutputPath
    CSV path for the inventory. Defaults to .\app-inventory.csv

.EXAMPLE
    .\Get-EnterpriseAppInventory.ps1 -OutputPath .\app-inventory.csv
#>
[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'app-inventory.csv'),
    [switch]$IncludeMicrosoftFirstParty,
    [string]$TenantId
)

# Module sits in ..\lib\ in the kit zip and beside the scripts in the repo.
$modulePath = @((Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1'), (Join-Path $PSScriptRoot 'HelpDeskEntra.psm1')) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
Import-Module $modulePath -Force
Connect-HelpDeskGraph -ScopeSet InventoryRead -TenantId $TenantId

$critical = Get-CriticalPermissionList
$high     = Get-HighRiskPermissionList

# Build an appRoleId -> permission-name map for every resource an app might
# hold application permissions against (Graph, Exchange Online, SharePoint...).
Write-HelpDeskLog -Level INFO -Message 'Building resource permission map (appRole id -> value)...'
$resourceMap = @{}   # key: "<resourceSpId>:<appRoleId>" -> permission value
$resourceSpCache = @{}
function Get-PermissionName {
    param($ResourceId, $AppRoleId)
    $key = "$ResourceId`:$AppRoleId"
    if ($resourceMap.ContainsKey($key)) { return $resourceMap[$key] }
    if (-not $resourceSpCache.ContainsKey($ResourceId)) {
        $resourceSpCache[$ResourceId] = Get-MgServicePrincipal -ServicePrincipalId $ResourceId -Property 'appRoles,displayName' -ErrorAction SilentlyContinue
    }
    $rsp = $resourceSpCache[$ResourceId]
    $name = ($rsp.AppRoles | Where-Object Id -eq $AppRoleId).Value
    $resourceMap[$key] = $name
    return $name
}

Write-HelpDeskLog -Level INFO -Message 'Enumerating service principals...'
# Microsoft first-party apps are owned by either of Microsoft's tenants.
$microsoftOwnerTenants = @(
    'f8cdef31-a31e-4b4a-93e4-5f571e91255a',   # Microsoft Services
    '72f988bf-86f1-41af-91ab-2d7cd011db47'    # Microsoft corporate tenant
)
$sps = Get-MgServicePrincipal -All -Property 'id,appId,displayName,servicePrincipalType,tags,appOwnerOrganizationId,accountEnabled' |
       Where-Object {
           $IncludeMicrosoftFirstParty -or
           $_.AppOwnerOrganizationId -notin $microsoftOwnerTenants
       }
$tenantId = (Get-MgContext).TenantId

$inventory = foreach ($sp in $sps) {
    # Owners: the service principal's, plus the application object's when the
    # app is registered in this tenant.
    $owners = @(Get-MgServicePrincipalOwner -ServicePrincipalId $sp.Id -All -ErrorAction SilentlyContinue)
    if ($sp.AppOwnerOrganizationId -eq $tenantId) {
        $app = Get-MgApplication -Filter "appId eq '$($sp.AppId)'" -Property 'id' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($app) { $owners += @(Get-MgApplicationOwner -ApplicationId $app.Id -All -ErrorAction SilentlyContinue) }
    }
    $owners    = @($owners | Where-Object { $_ } | Sort-Object Id -Unique)
    $ownerUpns = @($owners | ForEach-Object { $_.AdditionalProperties.userPrincipalName }) | Where-Object { $null -ne $_ }
    $isOrphan  = ($owners.Count -eq 0)

    # Application permissions this SP HOLDS (appRoleAssignments granted to it).
    $appPerms = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id -ErrorAction SilentlyContinue
    $grantedPermNames = foreach ($a in $appPerms) { Get-PermissionName -ResourceId $a.ResourceId -AppRoleId $a.AppRoleId }
    $grantedPermNames = @($grantedPermNames | Where-Object { $_ })

    # Delegated grants (oauth2), tiered on the same lists as application permissions.
    $delegated = Get-MgServicePrincipalOauth2PermissionGrant -ServicePrincipalId $sp.Id -All -ErrorAction SilentlyContinue
    $delegatedScopes = @($delegated | ForEach-Object { ($_.Scope -split ' ') } | Where-Object { $_ } | Select-Object -Unique)
    $allPerms = @($grantedPermNames) + @($delegatedScopes)

    # Risk tiering
    $hasCritical = @($allPerms | Where-Object { $_ -in $critical }).Count -gt 0
    $hasHigh     = @($allPerms | Where-Object { $_ -in $high }).Count -gt 0
    $tier = if ($isOrphan -or $hasCritical) { 'Tier1' } elseif ($hasHigh) { 'Tier2' } else { 'Tier3' }

    if ($isOrphan)  { Write-HelpDeskLog -Level WARN   -Message "ORPHAN (auto-Tier1): $($sp.DisplayName) [$($sp.AppId)]" }
    if ($hasCritical) { Write-HelpDeskLog -Level WARN -Message "CRITICAL perms: $($sp.DisplayName) -> $((@($allPerms | Where-Object {$_ -in $critical} | Select-Object -Unique)) -join ', ')" }

    [pscustomobject]@{
        DisplayName     = $sp.DisplayName
        AppId           = $sp.AppId
        ObjectId        = $sp.Id
        Type            = $sp.ServicePrincipalType
        Enabled         = $sp.AccountEnabled
        OwnerCount      = $owners.Count
        Owners          = ($ownerUpns -join '; ')
        Orphaned        = $isOrphan
        RiskTier        = $tier
        AppPermissions  = ($grantedPermNames -join '; ')
        CriticalPerms   = (@($allPerms | Where-Object { $_ -in $critical } | Select-Object -Unique) -join '; ')
        DelegatedScopes = ($delegatedScopes -join '; ')
    }
}

$inventory | Sort-Object RiskTier, DisplayName | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8

# Summary
$byTier   = $inventory | Group-Object RiskTier | Select-Object Name, Count
$orphans  = @($inventory | Where-Object Orphaned)
Write-HelpDeskLog -Level INFO -Message "Inventory written: $OutputPath  (total $($inventory.Count))"
$byTier | Format-Table -AutoSize
Write-HelpDeskLog -Level INFO -Message "Orphaned applications (need an owner before access can be granted): $($orphans.Count)"
