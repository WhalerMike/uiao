#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Users, Microsoft.Graph.Identity.Governance
<#
.SYNOPSIS
    IDENTITY ENGINEERING ONLY - not a Help Desk script. Prepare a CLOUD-ONLY
    Entra ID user to be hard-matched by an on-premises AD account, by setting
    onPremisesImmutableId (the A3 task). Graph-only; MSOnline / Set-MsolUser is
    retired and is deliberately NOT used.

.DESCRIPTION
    v1.6 narrows this script to the one case where a cloud-side write is the
    right fix. ImmutableID repair moved from the Help Desk to Identity
    Engineering: the Help Desk detects and escalates; Identity Engineering
    decides where the fix belongs and executes it under DUAL approval (Identity
    Engineering Lead + IGO).

    Where the fix belongs (Microsoft, "Configure Microsoft Entra Connect for an
    existing tenant"):
      - Hard match and soft match are evaluated only when a NEW object arrives
        from AD; editing an existing object so it matches produces an error.
      - For a duplicate-object conflict, the documented fix is on the AD side:
        set the on-premises user's mS-DS-ConsistencyGuid to the cloud user's
        ImmutableID, then let the next sync make the hard match. That is an AD
        change, not this script.
      - From July 1, 2026, Entra ID blocks a hard match when the target cloud
        account already has onPremisesObjectIdentifier set, or holds or is
        eligible for a privileged role. Keep hard matching blocked unless you
        are taking over cloud-only accounts, and re-block it afterwards.

    So the script REFUSES, before any write:
      - a synced user (onPremisesSyncEnabled = true): fix it in AD instead;
      - a user that already has onPremisesObjectIdentifier: the platform would
        block the match;
      - a user holding or eligible for any directory role.

    Run it as a role that can update onPremisesImmutableId for the target
    (Authentication, User or Privileged Authentication Administrator, or Global
    Administrator, per Microsoft's sensitive-actions table). Hybrid Identity
    Administrator CANNOT write this property.

    The value is the Base64 form of the source anchor your Entra Connect
    configuration uses - mS-DS-ConsistencyGuid by default, or objectGUID:

        $b64 = [Convert]::ToBase64String(([guid]$ObjectGuid).ToByteArray())

    Confirm which attribute is the anchor before running, and take the value
    from the approved ticket, never by working it out yourself.

.PARAMETER Upn                 Target cloud-only user UPN.
.PARAMETER SourceAnchorGuid    The on-prem source anchor (mS-DS-ConsistencyGuid
                               or objectGUID) in GUID form. Converted to Base64.
.PARAMETER ExpectedCurrentValue  Optional: assert the current ImmutableID before changing.
.PARAMETER IdentityEngApprovalRef / IgoApprovalRef  Dual-approval references. BOTH required.
.EXAMPLE
    .\Repair-ImmutableId.ps1 -Upn jdoe@agency.gov -SourceAnchorGuid 'a1b2...' `
        -IdentityEngApprovalRef 'RITM00123-IE' -IgoApprovalRef 'RITM00123-IGO' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$Upn,
    [Parameter(Mandatory)][Alias('OnPremObjectGuid')][guid]$SourceAnchorGuid,
    [string]$ExpectedCurrentValue,
    [Parameter(Mandatory)][string]$IdentityEngApprovalRef,
    [Parameter(Mandatory)][string]$IgoApprovalRef,
    [string]$TenantId
)

# Module sits in ..\lib\ in the kit zip and beside the scripts in the repo.
$modulePath = @((Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1'), (Join-Path $PSScriptRoot 'HelpDeskEntra.psm1')) |
    Where-Object { Test-Path $_ } | Select-Object -First 1
Import-Module $modulePath -Force
Connect-HelpDeskGraph -ScopeSet ImmutableIdWrite -TenantId $TenantId

$newImmutableId = [Convert]::ToBase64String($SourceAnchorGuid.ToByteArray())
Write-HelpDeskLog -Level INFO -Message "Computed ImmutableID from source anchor $SourceAnchorGuid => $newImmutableId"

$user = Get-MgUser -UserId $Upn -Property 'id,displayName,onPremisesImmutableId,onPremisesSyncEnabled' -ErrorAction Stop
# onPremisesObjectIdentifier is exposed on the Graph beta endpoint only.
$onPremObjectId = $null
try {
    $onPremObjectId = (Invoke-MgGraphRequest -Method GET -Uri "https://graph.microsoft.com/beta/users/$($user.Id)?`$select=onPremisesObjectIdentifier" -ErrorAction Stop).onPremisesObjectIdentifier
} catch {
    Write-HelpDeskLog -Level WARN -Message "Could not read onPremisesObjectIdentifier (beta): $($_.Exception.Message). Check it by hand before proceeding."
}
Write-HelpDeskLog -Level INFO -Message "Target: $($user.DisplayName) | current ImmutableID='$($user.OnPremisesImmutableId)' | syncEnabled=$($user.OnPremisesSyncEnabled)"

# Refusals ---------------------------------------------------------------------
if ($user.OnPremisesSyncEnabled) {
    throw "REFUSED: $Upn is synchronized from AD (onPremisesSyncEnabled = true). Fix it at the source: set the on-premises user's mS-DS-ConsistencyGuid to the intended ImmutableID and let Entra Connect sync. Do not edit the cloud object."
}
if ($onPremObjectId) {
    throw "REFUSED: $Upn already has onPremisesObjectIdentifier set; since July 1, 2026 Entra ID blocks a hard match to this account. Escalate to the identity engineering lead."
}
$active   = @(Get-MgRoleManagementDirectoryRoleAssignment -Filter "principalId eq '$($user.Id)'" -All -ErrorAction Stop)
$eligible = @(Get-MgRoleManagementDirectoryRoleEligibilitySchedule -Filter "principalId eq '$($user.Id)'" -All -ErrorAction Stop)
if ($active.Count -or $eligible.Count) {
    throw "REFUSED: $Upn holds $($active.Count) active and $($eligible.Count) eligible directory role assignment(s). Entra ID blocks a hard match to a privileged account; remove the roles under change control first or choose another path."
}

if ($user.OnPremisesImmutableId -eq $newImmutableId) {
    Write-HelpDeskLog -Level INFO -Message 'No change needed: onPremisesImmutableId already matches target value.'
    return
}

if ($ExpectedCurrentValue -and $user.OnPremisesImmutableId -ne $ExpectedCurrentValue) {
    throw "Current ImmutableID '$($user.OnPremisesImmutableId)' does not match expected '$ExpectedCurrentValue'. STOP and contact the identity engineering lead."
}

$target = "$Upn (ImmutableID '$($user.OnPremisesImmutableId)' -> '$newImmutableId')"
$desc   = "dual-approval IE=$IdentityEngApprovalRef IGO=$IgoApprovalRef"
if ($PSCmdlet.ShouldProcess($target, "Set onPremisesImmutableId [$desc]")) {
    Update-MgUser -UserId $user.Id -OnPremisesImmutableId $newImmutableId
    Write-HelpDeskLog -Level ACTION -Message "SET ImmutableID for $Upn | $desc | operator=$((Get-MgContext).Account)"

    $verify = Get-MgUser -UserId $user.Id -Property 'onPremisesImmutableId'
    if ($verify.OnPremisesImmutableId -eq $newImmutableId) {
        Write-HelpDeskLog -Level INFO -Message 'Verified. Next: confirm hard matching is allowed for this takeover, run a delta sync ON the Entra Connect server (Start-ADSyncSyncCycle -PolicyType Delta), confirm one healthy object with no duplicate, then re-block hard matching.'
    } else {
        Write-HelpDeskLog -Level ERROR -Message 'Post-change verification FAILED. Escalate to the identity engineering lead immediately.'
    }
}
