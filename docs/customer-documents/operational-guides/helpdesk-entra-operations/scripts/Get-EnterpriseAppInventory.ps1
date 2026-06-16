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

    Risk tiering (from Doc 3 §4 / §8.3 risk table):
      Tier 1  - holds ANY critical application permission, OR has no owner
                (orphaned -> auto-Tier 1), OR is externally published.
      Tier 2  - holds a high-risk delegated/app permission.
      Tier 3  - minimal scopes only.

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

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force
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
$sps = Get-MgServicePrincipal -All -Property 'id,appId,displayName,servicePrincipalType,tags,appOwnerOrganizationId,accountEnabled' |
       Where-Object {
           $IncludeMicrosoftFirstParty -or
           $_.AppOwnerOrganizationId -ne 'f8cdef31-a31e-4b4a-93e4-5f571e91255a'  # Microsoft's tenant id (first-party)
       }

$inventory = foreach ($sp in $sps) {
    # Owners
    $owners = Get-MgServicePrincipalOwner -ServicePrincipalId $sp.Id -ErrorAction SilentlyContinue
    $ownerUpns = @($owners | ForEach-Object { $_.AdditionalProperties.userPrincipalName }) -ne $null
    $isOrphan  = ($owners.Count -eq 0)

    # Application permissions this SP HOLDS (appRoleAssignments granted to it).
    $appPerms = Get-MgServicePrincipalAppRoleAssignment -ServicePrincipalId $sp.Id -ErrorAction SilentlyContinue
    $grantedPermNames = foreach ($a in $appPerms) { Get-PermissionName -ResourceId $a.ResourceId -AppRoleId $a.AppRoleId }
    $grantedPermNames = @($grantedPermNames | Where-Object { $_ })

    # Delegated grants (oauth2) - informational for risk.
    $delegated = Get-MgServicePrincipalOauth2PermissionGrant -ServicePrincipalId $sp.Id -ErrorAction SilentlyContinue
    $delegatedScopes = @($delegated | ForEach-Object { ($_.Scope -split ' ') } | Where-Object { $_ } | Select-Object -Unique)

    # Risk tiering
    $hasCritical = @($grantedPermNames | Where-Object { $_ -in $critical }).Count -gt 0
    $hasHigh     = @($grantedPermNames | Where-Object { $_ -in $high }).Count -gt 0
    $tier = if ($isOrphan -or $hasCritical) { 'Tier1' } elseif ($hasHigh) { 'Tier2' } else { 'Tier3' }

    if ($isOrphan)  { Write-HelpDeskLog -Level WARN   -Message "ORPHAN (auto-Tier1): $($sp.DisplayName) [$($sp.AppId)]" }
    if ($hasCritical) { Write-HelpDeskLog -Level WARN -Message "CRITICAL perms: $($sp.DisplayName) -> $((@($grantedPermNames | Where-Object {$_ -in $critical})) -join ', ')" }

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
        CriticalPerms   = (@($grantedPermNames | Where-Object { $_ -in $critical }) -join '; ')
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
