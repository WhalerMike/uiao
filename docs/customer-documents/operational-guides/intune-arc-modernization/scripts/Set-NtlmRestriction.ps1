#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Stage NTLM restriction by setting the LSA LmCompatibilityLevel.

.DESCRIPTION
    Sets HKLM\SYSTEM\CurrentControlSet\Control\Lsa\LmCompatibilityLevel to stage
    NTLM hardening. -WhatIf previews the registry write. Enforcement lives at the
    LSA layer (per ADR-068) — NOT in Conditional Access, which only gates cloud
    auth. DO NOT run until Get-NtlmAudit confirms the target level has no
    remaining dependencies and application owners have signed off.

    Canon: ADR-068 — Kerberos / NTLM elimination, staged Audit → Restrict
    NTLMv1 → Block-all. The federal deadline (Notice 0009) is 2027-04-01.

.PARAMETER Level
    LmCompatibilityLevel 0-5. Level 5 = send NTLMv2 only; DC refuses LM & NTLM.
    Run with -ListLevels to print the meanings.

.EXAMPLE
    .\Set-NtlmRestriction.ps1 -Level 5 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [ValidateRange(0,5)][int]$Level = 5,
    [switch]$ListLevels,
    [string]$OrgPath,
    [string]$ApprovalRef
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

if ($ListLevels) {
    (Get-LmCompatibilityLevels).GetEnumerator() | ForEach-Object { '{0} = {1}' -f $_.Key, $_.Value }
    return
}

if (-not (Assert-GovernanceApproval -Operation "NTLM restriction (LmCompatibilityLevel=$Level)" -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) { return }

$lsaPath = 'HKLM:\SYSTEM\CurrentControlSet\Control\Lsa'
$meaning = (Get-LmCompatibilityLevels)[$Level]

if ($PSCmdlet.ShouldProcess($env:COMPUTERNAME, "Set LmCompatibilityLevel = $Level ($meaning)")) {
    Set-ItemProperty -Path $lsaPath -Name 'LmCompatibilityLevel' -Value $Level -Type DWord
    $applied = Get-ItemPropertyValue -Path $lsaPath -Name 'LmCompatibilityLevel'
    Write-ModernizationLog -Level ACTION -Message "LmCompatibilityLevel set to $applied ($meaning). A reboot may be required to fully apply."
}
