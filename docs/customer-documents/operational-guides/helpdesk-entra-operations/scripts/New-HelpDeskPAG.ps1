#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Groups, Microsoft.Graph.Identity.Governance
<#
.SYNOPSIS
    Stand up the Help Desk Privileged Access Group (PAG): a role-assignable
    security group that HOLDS the operational Entra roles, with technicians
    added as PIM-ELIGIBLE members (no standing privilege).

.DESCRIPTION
    Implements Doc 1 §3-4. The model:
      - Roles are assigned to the GROUP, never to individual technicians. The
        v1.6 defaults are the least-privileged roles for Help Desk work:
          Helpdesk Administrator        password resets, refresh-token revocation
                                        (Password Administrator is narrower still)
          Authentication Administrator  authentication methods, MFA re-registration,
                                        Temporary Access Pass for members
          Help Desk Enterprise App Assignment
                                        custom role holding only
                                        microsoft.directory/servicePrincipals/appRoleAssignedTo/update
                                        (create it with -CreateAppAssignmentRole)
      - Application Administrator is NOT a Help Desk role: it can grant consent
        and create enterprise apps. Hybrid Identity Administrator is NOT a Help
        Desk role either: it cannot write onPremisesImmutableId, and ImmutableID
        repair belongs to Identity Engineering. Both stay with Identity
        Engineering, eligible only, behind PIM approval. The script refuses them.
      - Technicians are ELIGIBLE members of the group via PIM for Groups; they
        activate (JIT) to inherit the roles for a bounded session.
      - Members and owners of a role-assignable group can be reset only by
        Privileged Authentication Administrators and Global Administrators, so
        one technician cannot reset another and inherit their access.

    Scope: by default roles are assigned tenant-wide ('/'). To scope them to an
    administrative unit, pass -DirectoryScopeId '/administrativeUnits/<id>'
    (Helpdesk, Password and Authentication Administrator support AU scope; an
    AU-scoped role acts only on members who hold no admin role). The custom
    app-assignment role holds a service-principal permission and can't take AU
    scope, so it is always assigned tenant-wide ('/'). For one role
    per group and scope - the pattern the Responsibilities Guide recommends -
    run the script once per group with a single -Roles value.

    This script performs the structural setup it can do safely and idempotently:
      0. Optionally create the custom app-assignment role (-CreateAppAssignmentRole).
      1. Create the role-assignable security group (requires Entra ID P1; the
         PIM activation in step 3 requires P2 / Entra ID Governance).
      2. Assign the required directory roles to the group (active assignment to
         the group object).
      3. Add each technician as an ELIGIBLE member (PIM for Groups).

    The PIM ACTIVATION POLICY (Tier 2: 8h ceiling, Conditional Access authentication context on activation,
    justification and ticket number required, 180-day eligibility) is
    documented in the guide and should be applied
    via the portal or the role-management-policy cmdlets, then verified — those
    policy-rule writes are fiddly and tenant-specific, so they are intentionally
    NOT blindly scripted here.

.PARAMETER GroupName       Display name for the PAG. Default: Entra-HelpDesk-Operators
.PARAMETER TechnicianUpns  UPNs of the 3 Cloud Services Team members to make eligible.
.PARAMETER Roles           Directory roles (built-in or custom, by display name) to assign to the group.
.PARAMETER DirectoryScopeId  '/' (tenant) or '/administrativeUnits/<id>'.
.PARAMETER CreateAppAssignmentRole  Create the custom app-assignment role if it does not exist.
.EXAMPLE
    .\New-HelpDeskPAG.ps1 -TechnicianUpns 'a@agency.gov','b@agency.gov','c@agency.gov' -CreateAppAssignmentRole -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [string]$GroupName = 'Entra-HelpDesk-Operators',
    [Parameter(Mandatory)][string[]]$TechnicianUpns,
    [string[]]$Roles = @('Helpdesk Administrator', 'Authentication Administrator', 'Help Desk Enterprise App Assignment'),
    [string]$DirectoryScopeId = '/',
    [switch]$CreateAppAssignmentRole,
    [int]$EligibilityMonths = 6,
    [string]$TenantId
)

# Module sits in ..\lib\ in the kit zip and beside the scripts in the repo.
$modulePath = @((Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1'), (Join-Path $PSScriptRoot 'HelpDeskEntra.psm1')) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
Import-Module $modulePath -Force

$blocked = @('Application Administrator', 'Cloud Application Administrator', 'Hybrid Identity Administrator',
             'Global Administrator', 'Privileged Authentication Administrator', 'Privileged Role Administrator')
$bad = @($Roles | Where-Object { $_ -in $blocked })
if ($bad.Count) {
    throw "Refusing to put $($bad -join ', ') in the Help Desk PAG. These roles belong to Identity Engineering or Tier 0, not the Help Desk."
}

Connect-HelpDeskGraph -ScopeSet PimGroups -TenantId $TenantId

# 0. Custom enterprise-app assignment role ------------------------------------
$appRoleName = Get-AppAssignmentRoleName
if ($CreateAppAssignmentRole -and ($Roles -contains $appRoleName)) {
    $existingDef = Get-MgRoleManagementDirectoryRoleDefinition -Filter "displayName eq '$appRoleName'" -ErrorAction SilentlyContinue
    if ($existingDef) {
        Write-HelpDeskLog -Level INFO -Message "Custom role already exists: $appRoleName"
    } elseif ($PSCmdlet.ShouldProcess($appRoleName, 'Create custom directory role (appRoleAssignedTo/update only)')) {
        New-MgRoleManagementDirectoryRoleDefinition -DisplayName $appRoleName `
            -Description 'Help Desk: assign and remove users and groups on enterprise apps. No consent, credential or app-configuration rights.' `
            -IsEnabled:$true `
            -RolePermissions @(@{ AllowedResourceActions = @('microsoft.directory/servicePrincipals/appRoleAssignedTo/update') }) | Out-Null
        Write-HelpDeskLog -Level ACTION -Message "Created custom role: $appRoleName (each assignee needs Entra ID P1)"
    }
}

# 1. Create (or find) the role-assignable group --------------------------------
$group = Get-MgGroup -Filter "displayName eq '$GroupName'" -ErrorAction SilentlyContinue
if (-not $group) {
    if ($PSCmdlet.ShouldProcess($GroupName, 'Create role-assignable security group')) {
        $group = New-MgGroup -DisplayName $GroupName `
            -Description 'Help Desk / Cloud Services PAG — holds operational Entra roles; members are PIM-eligible only.' `
            -MailEnabled:$false -SecurityEnabled:$true -IsAssignableToRole:$true `
            -MailNickname ($GroupName -replace '[^a-zA-Z0-9]','')
        Write-HelpDeskLog -Level ACTION -Message "Created PAG '$GroupName' ($($group.Id))"
    }
} else {
    Write-HelpDeskLog -Level INFO -Message "PAG already exists: $GroupName ($($group.Id))"
}

# 2. Assign directory roles to the GROUP --------------------------------------
foreach ($roleName in $Roles) {
    $roleDef = Get-MgRoleManagementDirectoryRoleDefinition -Filter "displayName eq '$roleName'"
    if (-not $roleDef) { Write-HelpDeskLog -Level ERROR -Message "Role not found: $roleName"; continue }

    # Custom roles with only service-principal permissions can't be scoped to an AU.
    $scope = $DirectoryScopeId
    if ($roleName -eq $appRoleName -and $scope -ne '/') {
        Write-HelpDeskLog -Level WARN -Message "$roleName can't take administrative-unit scope; assigning it tenant-wide ('/')."
        $scope = '/'
    }

    $existing = Get-MgRoleManagementDirectoryRoleAssignment -Filter "principalId eq '$($group.Id)' and roleDefinitionId eq '$($roleDef.Id)'" -ErrorAction SilentlyContinue |
        Where-Object { $_.DirectoryScopeId -eq $scope }
    if ($existing) { Write-HelpDeskLog -Level INFO -Message "Role already on group: $roleName"; continue }

    if ($PSCmdlet.ShouldProcess("$roleName -> $GroupName", 'Assign directory role to PAG')) {
        New-MgRoleManagementDirectoryRoleAssignment -PrincipalId $group.Id `
            -RoleDefinitionId $roleDef.Id -DirectoryScopeId $scope | Out-Null
        Write-HelpDeskLog -Level ACTION -Message "Assigned role to PAG: $roleName (scope $scope)"
    }
}

# 3. Add technicians as PIM-ELIGIBLE members ----------------------------------
foreach ($upn in $TechnicianUpns) {
    $user = Get-MgUser -UserId $upn -ErrorAction SilentlyContinue
    if (-not $user) { Write-HelpDeskLog -Level ERROR -Message "User not found: $upn"; continue }

    $alreadyEligible = Get-MgIdentityGovernancePrivilegedAccessGroupEligibilityScheduleInstance -All -ErrorAction SilentlyContinue `
        | Where-Object { $_.GroupId -eq $group.Id -and $_.PrincipalId -eq $user.Id -and $_.AccessId -eq 'member' } `
        | Select-Object -First 1
    if ($alreadyEligible) {
        Write-HelpDeskLog -Level INFO -Message "User already eligible in PAG: $upn"
        continue
    }

    if ($PSCmdlet.ShouldProcess($upn, "Make eligible member of $GroupName (PIM for Groups)")) {
        $params = @{
            accessId      = 'member'
            principalId   = $user.Id
            groupId       = $group.Id
            action        = 'adminAssign'
            scheduleInfo  = @{
                startDateTime = (Get-Date).ToString('o')
                expiration    = @{ type = 'afterDuration'; duration = "P$($EligibilityMonths * 30)D" }
            }
            justification = 'Cloud Services Team — eligible Help Desk operator (180-day eligibility, quarterly review).'
        }
        New-MgIdentityGovernancePrivilegedAccessGroupEligibilityScheduleRequest -BodyParameter $params | Out-Null
        Write-HelpDeskLog -Level ACTION -Message "Eligible member added: $upn"
    }
}

Write-HelpDeskLog -Level INFO -Message @"
PAG structural setup complete. REMAINING (apply + verify in portal or via
Update-MgPolicyRoleManagementPolicyRule on the group's member policy):
  - Max activation duration : 8-hour ceiling (Tier 2); shortening it is tenant-wide per role
  - Activation sign-in       : Conditional Access authentication context with a
                               phishing-resistant authentication strength (PIM's own
                               MFA option doesn't set the method)
  - Justification + ticket   : required (ServiceNow RITM number). PIM does not validate the
                               number, so correlate activations to tickets in the SIEM.
  - Approval to activate     : per your risk acceptance; the task's approval lives in the ticket
                               (if used: manager/owner, NOT a Cloud Services peer)
  - Eligibility expiry       : 180 days, with quarterly membership review
"@
