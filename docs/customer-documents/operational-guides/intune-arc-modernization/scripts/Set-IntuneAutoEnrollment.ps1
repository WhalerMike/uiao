#Requires -Version 5.1
#Requires -Modules GroupPolicy
<#
.SYNOPSIS
    Create and link the GPO that auto-enrolls Hybrid Azure AD-joined Windows
    devices into Microsoft Intune.

.DESCRIPTION
    Creates the MDM auto-enrollment GPO (AutoEnrollMDM=1, UseAADCredentialType=1)
    and links it to the workstation OU. -WhatIf previews the GPO create + link.

    Canon: ADR-071 / ADR-080 — Intune-first asset onboarding. Hybrid AADJ +
    auto-enrollment is the lowest-friction path for an existing domain-joined
    fleet (no reimage, no user action). This is the INTERIM bridge; the target
    is cloud-native Intune management.

.EXAMPLE
    .\Set-IntuneAutoEnrollment.ps1 -TargetOU 'OU=Workstations,DC=agency,DC=gov' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory)][string]$TargetOU,                      # CONFIGURE: workstation OU DN
    [string]$GpoName = 'INTUNE-AutoEnrollment-Workstations',
    [string]$OrgPath,
    [string]$ApprovalRef
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force
Import-Module GroupPolicy

if (-not (Assert-GovernanceApproval -Operation 'Intune auto-enrollment GPO' -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) { return }

$mdmKey = 'HKLM\SOFTWARE\Policies\Microsoft\Windows\CurrentVersion\MDM'

if ($PSCmdlet.ShouldProcess($GpoName, 'Create MDM auto-enrollment GPO')) {
    $gpo = Get-GPO -Name $GpoName -ErrorAction SilentlyContinue
    if (-not $gpo) {
        $gpo = New-GPO -Name $GpoName -Comment 'Configures MDM auto-enrollment for Hybrid AADJ devices'
    }
    Set-GPRegistryValue -Name $GpoName -Key $mdmKey -ValueName 'AutoEnrollMDM'        -Type DWord -Value 1 | Out-Null
    Set-GPRegistryValue -Name $GpoName -Key $mdmKey -ValueName 'UseAADCredentialType' -Type DWord -Value 1 | Out-Null
    Write-ModernizationLog -Level ACTION -Message "GPO '$GpoName' configured (AutoEnrollMDM=1, UseAADCredentialType=1)."
}

if ($PSCmdlet.ShouldProcess($TargetOU, "Link GPO '$GpoName'")) {
    New-GPLink -Name $GpoName -Target $TargetOU -LinkEnabled Yes -Enforced No -ErrorAction SilentlyContinue | Out-Null
    Write-ModernizationLog -Level ACTION -Message "Linked '$GpoName' to $TargetOU. Verify on a client with: dsregcmd /status"
}
