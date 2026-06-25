#Requires -Version 5.1
<#
.SYNOPSIS
    Assign the Windows security baseline (Guest Configuration) and enable
    Defender for Servers on Arc-enabled servers.

.DESCRIPTION
    Applies the Microsoft security-baseline policy initiative to the Arc scope
    and enables Defender for Servers Plan 2. -WhatIf previews both writes.

    Canon: ADR-002 (server/OS layer) + ADR-092 (gated actuation, L3). Policy is
    the control plane expressing desired state; Guest Configuration reconciles
    the data plane toward it.

.EXAMPLE
    .\Set-ArcPolicyBaseline.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][string]$SubscriptionId,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$Location,
    # CONFIGURE: Windows security baseline Guest Configuration initiative id.
    [string]$PolicySetDefinitionId = '/providers/Microsoft.Authorization/policySetDefinitions/b35b83a6-a5e7-4c68-87b0-5765b84b9e0f',
    [string]$OrgPath,
    [string]$ApprovalRef
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

Connect-ModernizationAzure -SubscriptionId $SubscriptionId
if (-not (Assert-GovernanceApproval -Operation 'Arc policy baseline' -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) { return }

$scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
$assignmentName = 'arc-win-security-baseline'
$existingAssignment = Get-AzPolicyAssignment -Name $assignmentName -Scope $scope -ErrorAction SilentlyContinue

if ($existingAssignment) {
    Write-ModernizationLog -Level INFO -Message "Policy assignment '$assignmentName' already exists at $scope."
} elseif ($PSCmdlet.ShouldProcess($scope, 'Assign Windows security baseline initiative')) {
    New-AzPolicyAssignment -Name $assignmentName `
        -DisplayName 'Windows Security Baseline - Arc Servers' `
        -Scope $scope `
        -PolicySetDefinition (Get-AzPolicySetDefinition -Id $PolicySetDefinitionId) `
        -IdentityType SystemAssigned -Location $Location | Out-Null
    Write-ModernizationLog -Level ACTION -Message 'Security baseline initiative assigned. Compliance eval may take ~30 min.'
}

$pricing = Get-AzSecurityPricing -Name 'VirtualMachines' -ErrorAction SilentlyContinue
if ($pricing -and $pricing.PricingTier -eq 'Standard' -and $pricing.SubPlan -eq 'P2') {
    Write-ModernizationLog -Level INFO -Message 'Defender for Servers Plan 2 is already enabled on the subscription.'
} elseif ($PSCmdlet.ShouldProcess($SubscriptionId, 'Enable Defender for Servers Plan 2')) {
    Set-AzSecurityPricing -Name 'VirtualMachines' -PricingTier 'Standard' -SubPlan 'P2'
    Write-ModernizationLog -Level ACTION -Message 'Defender for Servers Plan 2 enabled on the subscription.'
}
