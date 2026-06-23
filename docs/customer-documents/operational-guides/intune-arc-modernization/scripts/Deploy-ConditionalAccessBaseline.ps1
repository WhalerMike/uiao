#Requires -Version 5.1
<#
.SYNOPSIS
    Deploy the core Conditional Access baseline policy set (report-only by default).

.DESCRIPTION
    Creates the core CA policies (block legacy auth, require MFA, require
    compliant device, require MFA for admins, require MFA for Azure management)
    in **report-only** state so impact can be measured before enforcement.
    -WhatIf previews each create. Promotion to 'enabled' is a separate, gated
    decision — never flip straight to enforce.

    Canon: ADR-092 — CA changes are gated actuation (L3); on the governed path a
    write requires -ApprovalRef. CA is the cloud-auth enforcement layer; it does
    NOT block on-prem NTLM (that is Set-NtlmRestriction at the LSA layer).

.EXAMPLE
    .\Deploy-ConditionalAccessBaseline.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [ValidateSet('enabledForReportingButNotEnforced','disabled')]
    [string]$State = 'enabledForReportingButNotEnforced',
    [string]$BreakGlassGroupId,   # CONFIGURE: exclude your break-glass accounts group
    [string]$TenantId,
    [string]$OrgPath,
    [string]$ApprovalRef
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

Connect-ModernizationGraph -ScopeSet CaWrite -TenantId $TenantId
if (-not (Assert-GovernanceApproval -Operation 'Conditional Access baseline' -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) { return }

$exclude = if ($BreakGlassGroupId) { @($BreakGlassGroupId) } else { @() }
if (-not $BreakGlassGroupId) {
    Write-ModernizationLog -Level WARN -Message 'No -BreakGlassGroupId supplied. Configure a break-glass exclusion before enforcing, or you can lock yourself out.'
}

# Each policy as report-only; promotion to enforce is a separate gated step.
$policies = @(
    @{ Name = 'CA01 - Block legacy authentication'
       Body = @{ conditions = @{ clientAppTypes = @('exchangeActiveSync','other'); applications = @{ includeApplications = @('All') }; users = @{ includeUsers = @('All'); excludeGroups = $exclude } }
                 grantControls = @{ operator = 'OR'; builtInControls = @('block') } } }
    @{ Name = 'CA02 - Require MFA for all users'
       Body = @{ conditions = @{ clientAppTypes = @('all'); applications = @{ includeApplications = @('All') }; users = @{ includeUsers = @('All'); excludeGroups = $exclude } }
                 grantControls = @{ operator = 'OR'; builtInControls = @('mfa') } } }
    @{ Name = 'CA03 - Require compliant device'
       Body = @{ conditions = @{ clientAppTypes = @('all'); applications = @{ includeApplications = @('All') }; users = @{ includeUsers = @('All'); excludeGroups = $exclude } }
                 grantControls = @{ operator = 'OR'; builtInControls = @('compliantDevice','domainJoinedDevice') } } }
    @{ Name = 'CA04 - Require MFA for Azure management'
       Body = @{ conditions = @{ clientAppTypes = @('all'); applications = @{ includeApplications = @('797f4846-ba00-4fd7-ba43-dac1f8f63013') }; users = @{ includeUsers = @('All'); excludeGroups = $exclude } }
                 grantControls = @{ operator = 'OR'; builtInControls = @('mfa') } } }
)

Write-ModernizationLog -Level INFO -Message 'Loading existing Conditional Access policies for idempotent deployment checks...'
$existingByName = @{}
Get-MgIdentityConditionalAccessPolicy -All -Property 'id,displayName,state' | ForEach-Object {
    if ($_.DisplayName) { $existingByName[$_.DisplayName] = $_ }
}

foreach ($p in $policies) {
    $existing = $existingByName[$p.Name]
    if ($existing) {
        if ($existing.State -ne $State) {
            if ($PSCmdlet.ShouldProcess($p.Name, "Update existing CA policy state to $State")) {
                Update-MgIdentityConditionalAccessPolicy -ConditionalAccessPolicyId $existing.Id -BodyParameter @{ state = $State } | Out-Null
                Write-ModernizationLog -Level ACTION -Message "Updated existing '$($p.Name)' to state $State"
            }
        } else {
            Write-ModernizationLog -Level INFO -Message "Skipped '$($p.Name)' (already exists with state $State)"
        }
        continue
    }

    if ($PSCmdlet.ShouldProcess($p.Name, "Create CA policy (state=$State)")) {
        $params = @{ displayName = $p.Name; state = $State } + $p.Body
        New-MgIdentityConditionalAccessPolicy -BodyParameter $params | Out-Null
        Write-ModernizationLog -Level ACTION -Message "Created '$($p.Name)' as $State"
    }
}
Write-ModernizationLog -Level INFO -Message 'Baseline created report-only. Measure impact, then promote to enforce as a separate gated change.'
