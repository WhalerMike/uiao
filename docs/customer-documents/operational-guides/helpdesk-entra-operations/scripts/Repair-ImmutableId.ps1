#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Users
<#
.SYNOPSIS
    Repair a Hybrid AD -> Entra ID ImmutableID (onPremisesImmutableId) hard
    match (the A3 task). Graph-only — MSOnline / Set-MsolUser is retired and is
    deliberately NOT used.

.DESCRIPTION
    Implements Doc 1 §9.1, with the team's authority model enforced: this is an
    A3 action requiring DUAL approval (Identity Engineering Lead + IGO). The
    script will not run without both approval references, defaults to -WhatIf
    behavior via ShouldProcess, and verifies the current value before writing.

    The ImmutableID links a cloud user object to its on-prem AD object. The
    correct value is the Base64 encoding of the on-prem AD objectGUID:

        $b64 = [Convert]::ToBase64String(([guid]$ObjectGuid).ToByteArray())

    WARNING: For a synced user this is a hard-match repair. Coordinate with the
    Entra Connect / on-prem AD team. An incorrect value can orphan the cloud
    object or create a duplicate. If anything is uncertain, STOP and escalate to
    Identity Engineering (Doc 1 §9.4).

.PARAMETER Upn                 Target user UPN.
.PARAMETER OnPremObjectGuid    On-prem AD objectGUID (GUID form). Converted to Base64.
.PARAMETER ExpectedCurrentValue  Optional: assert the current ImmutableID before changing.
.PARAMETER IdentityEngApprovalRef / IgoApprovalRef  Dual-approval references. BOTH required.
.EXAMPLE
    .\Repair-ImmutableId.ps1 -Upn jdoe@agency.gov -OnPremObjectGuid 'a1b2...' `
        -IdentityEngApprovalRef 'RITM00123-IE' -IgoApprovalRef 'RITM00123-IGO' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact='High')]
param(
    [Parameter(Mandatory)][string]$Upn,
    [Parameter(Mandatory)][guid]$OnPremObjectGuid,
    [string]$ExpectedCurrentValue,
    [Parameter(Mandatory)][string]$IdentityEngApprovalRef,
    [Parameter(Mandatory)][string]$IgoApprovalRef,
    [string]$TenantId
)

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force
Connect-HelpDeskGraph -ScopeSet HybridUserWrite -TenantId $TenantId

$newImmutableId = [Convert]::ToBase64String($OnPremObjectGuid.ToByteArray())
Write-HelpDeskLog -Level INFO -Message "Computed ImmutableID from objectGUID $OnPremObjectGuid => $newImmutableId"

$user = Get-MgUser -UserId $Upn -Property 'id,displayName,onPremisesImmutableId,onPremisesSyncEnabled' -ErrorAction Stop
Write-HelpDeskLog -Level INFO -Message "Target: $($user.DisplayName) | current ImmutableID='$($user.OnPremisesImmutableId)' | syncEnabled=$($user.OnPremisesSyncEnabled)"

if ($user.OnPremisesImmutableId -eq $newImmutableId) {
    Write-HelpDeskLog -Level INFO -Message 'No change needed: onPremisesImmutableId already matches target value.'
    return
}

if ($ExpectedCurrentValue -and $user.OnPremisesImmutableId -ne $ExpectedCurrentValue) {
    throw "Current ImmutableID '$($user.OnPremisesImmutableId)' does not match expected '$ExpectedCurrentValue'. STOP and contact Identity Engineering (Doc 1 §9.4)."
}

$target = "$Upn (ImmutableID '$($user.OnPremisesImmutableId)' -> '$newImmutableId')"
$desc   = "dual-approval IE=$IdentityEngApprovalRef IGO=$IgoApprovalRef"
if ($PSCmdlet.ShouldProcess($target, "Set onPremisesImmutableId [$desc]")) {
    Update-MgUser -UserId $user.Id -OnPremisesImmutableId $newImmutableId
    Write-HelpDeskLog -Level ACTION -Message "SET ImmutableID for $Upn | $desc | operator=$((Get-MgContext).Account)"

    $verify = Get-MgUser -UserId $user.Id -Property 'onPremisesImmutableId'
    if ($verify.OnPremisesImmutableId -eq $newImmutableId) {
        Write-HelpDeskLog -Level INFO -Message 'Verified. Next: coordinate an Entra Connect delta sync on the sync server:  Start-ADSyncSyncCycle -PolicyType Delta  (run ON the Entra Connect server). Confirm a healthy single object, no duplicate.'
    } else {
        Write-HelpDeskLog -Level ERROR -Message 'Post-change verification FAILED — escalate to Identity Engineering immediately.'
    }
}
