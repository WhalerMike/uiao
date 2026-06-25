#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Applications, Microsoft.Graph.Groups
<#
.SYNOPSIS
    Assign a security group to an Enterprise Application role (the A2
    "Application Access" task), with naming-convention validation and a
    nested-group safety check.

.DESCRIPTION
    Implements Doc 1 §8.1. PRECONDITIONS this script enforces / surfaces:
      - Governance provenance: a SAM/ServiceNow approval reference is REQUIRED
        (-ApprovalRef). The Cloud Services Team only executes approved work.
      - Naming convention (Doc 3 §7.2):  APP-<AppShort>-<Role>-T<tier>
      - Nested-group check: Entra does NOT honor nested group membership for
        Enterprise App assignment (Doc 1 §7.4). If the group contains other
        groups as members, those users will NOT get access — the script warns
        and (by default) refuses to proceed.

.PARAMETER AppDisplayName  Enterprise Application (service principal) display name.
.PARAMETER GroupName       Security group to assign (must match naming convention).
.PARAMETER AppRoleName     App role to grant. Omit for default access (no app role).
.PARAMETER ApprovalRef     SAM access-request id or ServiceNow RITM number. REQUIRED.
.EXAMPLE
    .\Add-AppAccessGroup.ps1 -AppDisplayName 'Payroll' -GroupName 'APP-PAYROLL-USERS-T1' -ApprovalRef 'RITM0045821' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$AppDisplayName,
    [Parameter(Mandatory)][string]$GroupName,
    [string]$AppRoleName,
    [Parameter(Mandatory)][string]$ApprovalRef,
    [switch]$AllowNestedGroups,
    [string]$TenantId
)

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force
Connect-HelpDeskGraph -ScopeSet GroupWrite -TenantId $TenantId

# 0. Naming convention -------------------------------------------------------
$namePattern = '^APP-[A-Z0-9]+-[A-Z]+-T[123]$'
if ($GroupName -notmatch $namePattern) {
    Write-HelpDeskLog -Level WARN -Message "Group name '$GroupName' does not match convention $namePattern (Doc 3 §7.2). Rename before production use."
}

# 1. Resolve objects ---------------------------------------------------------
$sp = Get-MgServicePrincipal -Filter "displayName eq '$AppDisplayName'" -ErrorAction Stop | Select-Object -First 1
if (-not $sp) { throw "Enterprise Application not found: $AppDisplayName" }
$group = Get-MgGroup -Filter "displayName eq '$GroupName'" -ErrorAction Stop | Select-Object -First 1
if (-not $group) { throw "Group not found: $GroupName" }

# 2. Nested-group safety check ----------------------------------------------
$members = Get-MgGroupMember -GroupId $group.Id -All
$nested  = @($members | Where-Object { $_.AdditionalProperties['@odata.type'] -eq '#microsoft.graph.group' })
if ($nested.Count -gt 0) {
    $names = ($nested | ForEach-Object { $_.AdditionalProperties.displayName }) -join ', '
    Write-HelpDeskLog -Level WARN -Message "Group '$GroupName' contains $($nested.Count) NESTED group(s): $names. Entra will NOT grant app access to their members."
    if (-not $AllowNestedGroups) {
        throw "Refusing to assign a group with nested members (use -AllowNestedGroups to override). Flatten to direct user members first."
    }
}

# 3. Resolve app role id -----------------------------------------------------
$appRoleId = '00000000-0000-0000-0000-000000000000'   # default access (no app role)
if ($AppRoleName) {
    $role = $sp.AppRoles | Where-Object { $_.DisplayName -eq $AppRoleName -or $_.Value -eq $AppRoleName }
    if (-not $role) { throw "App role '$AppRoleName' not found on $AppDisplayName" }
    $appRoleId = $role.Id
}
$roleLabel = if ($AppRoleName) { $AppRoleName } else { 'default' }   # PS 5.1-safe (no ?? )

# 4. Assign ------------------------------------------------------------------
 $existingAssignment = Get-MgServicePrincipalAppRoleAssignedTo -ServicePrincipalId $sp.Id -All -ErrorAction SilentlyContinue |
    Where-Object { $_.PrincipalId -eq $group.Id -and $_.AppRoleId -eq $appRoleId } |
    Select-Object -First 1
if ($existingAssignment) {
    Write-HelpDeskLog -Level INFO -Message "Skipped assignment: $GroupName already has role '$roleLabel' on $AppDisplayName."
    return
}

if ($PSCmdlet.ShouldProcess("$GroupName -> $AppDisplayName ($roleLabel)", "Assign (ref $ApprovalRef)")) {
    New-MgServicePrincipalAppRoleAssignedTo -ServicePrincipalId $sp.Id `
        -PrincipalId $group.Id -ResourceId $sp.Id -AppRoleId $appRoleId | Out-Null
    Write-HelpDeskLog -Level ACTION -Message "ASSIGNED $GroupName -> $AppDisplayName role '$roleLabel' | approval=$ApprovalRef | operator=$((Get-MgContext).Account)"
    Write-HelpDeskLog -Level INFO -Message "Record this in the ServiceNow work notes: group Object ID $($group.Id), app $($sp.AppId), approval $ApprovalRef."
}
