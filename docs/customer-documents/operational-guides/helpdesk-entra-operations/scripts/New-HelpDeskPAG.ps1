#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Groups, Microsoft.Graph.Identity.Governance
<#
.SYNOPSIS
    Stand up the Help Desk Privileged Access Group (PAG): a role-assignable
    security group that HOLDS the operational Entra roles, with technicians
    added as PIM-ELIGIBLE members (no standing privilege).

.DESCRIPTION
    Implements Doc 1 §3-4. The model:
      - Roles (Application Administrator, Hybrid Identity Administrator) are
        assigned to the GROUP, never to individual technicians.
      - Technicians are ELIGIBLE members of the group via PIM for Groups; they
        activate (JIT) to inherit the roles for a bounded session.

    This script performs the structural setup it can do safely and idempotently:
      1. Create the role-assignable security group (requires Entra ID P1; the
         PIM activation in step 3 requires P2 / Entra ID Governance).
      2. Assign the required directory roles to the group (active assignment to
         the group object).
      3. Add each technician as an ELIGIBLE member (PIM for Groups).

    The PIM ACTIVATION POLICY (max 4h, MFA-on-activation, approval required,
    justification required) is documented in the guide and should be applied
    via the portal or the role-management-policy cmdlets, then verified — those
    policy-rule writes are fiddly and tenant-specific, so they are intentionally
    NOT blindly scripted here.

.PARAMETER GroupName       Display name for the PAG. Default: Entra-HelpDesk-Operators
.PARAMETER TechnicianUpns  UPNs of the 3 Cloud Services Team members to make eligible.
.PARAMETER Roles           Directory roles to assign to the group.
.EXAMPLE
    .\New-HelpDeskPAG.ps1 -TechnicianUpns 'a@agency.gov','b@agency.gov','c@agency.gov' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [string]$GroupName = 'Entra-HelpDesk-Operators',
    [Parameter(Mandatory)][string[]]$TechnicianUpns,
    [string[]]$Roles = @('Application Administrator','Hybrid Identity Administrator'),
    [int]$EligibilityMonths = 12,
    [string]$TenantId
)

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force
Connect-HelpDeskGraph -ScopeSet PimGroups -TenantId $TenantId

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

    $existing = Get-MgRoleManagementDirectoryRoleAssignment -Filter "principalId eq '$($group.Id)' and roleDefinitionId eq '$($roleDef.Id)'" -ErrorAction SilentlyContinue
    if ($existing) { Write-HelpDeskLog -Level INFO -Message "Role already on group: $roleName"; continue }

    if ($PSCmdlet.ShouldProcess("$roleName -> $GroupName", 'Assign directory role to PAG')) {
        New-MgRoleManagementDirectoryRoleAssignment -PrincipalId $group.Id `
            -RoleDefinitionId $roleDef.Id -DirectoryScopeId '/' | Out-Null
        Write-HelpDeskLog -Level ACTION -Message "Assigned role to PAG: $roleName"
    }
}

# 3. Add technicians as PIM-ELIGIBLE members ----------------------------------
foreach ($upn in $TechnicianUpns) {
    $user = Get-MgUser -UserId $upn -ErrorAction SilentlyContinue
    if (-not $user) { Write-HelpDeskLog -Level ERROR -Message "User not found: $upn"; continue }

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
            justification = 'Cloud Services Team — eligible Help Desk operator (annual recert).'
        }
        New-MgIdentityGovernancePrivilegedAccessGroupEligibilityScheduleRequest -BodyParameter $params | Out-Null
        Write-HelpDeskLog -Level ACTION -Message "Eligible member added: $upn"
    }
}

Write-HelpDeskLog -Level INFO -Message @"
PAG structural setup complete. REMAINING (apply + verify in portal or via
Update-MgPolicyRoleManagementPolicyRule on the group's member policy):
  - Max activation duration : 4 hours (App Admin / Hybrid Identity Admin)
  - MFA on activation       : required (phishing-resistant)
  - Approval to activate     : required (manager/owner per your model — NOT a Cloud Services peer)
  - Justification            : required (must contain the ServiceNow RITM number)
"@
