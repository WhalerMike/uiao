#Requires -Version 5.1
<#
.SYNOPSIS
    Onboard a Windows server to Azure Arc (manual or OrgPath-governed path).

.DESCRIPTION
    Creates (or reuses) a least-privilege onboarding service principal, installs
    the Connected Machine Agent, connects the machine to Azure Arc, and validates
    registration. Every state-changing step honors -WhatIf.

    Canon: ADR-002 — Arc-enabled servers run in a NON-domain-joined state with an
    Entra (Azure AD) machine identity; this script onboards the OS/server layer.
    It does NOT domain-unjoin for you — that is a sequenced decision (see the
    guide). Arc is a MANAGEMENT-plane attachment; the server remains the data
    plane (ADR-092).

.PARAMETER OrgPath
    GOVERNED path only. The organizational path the server belongs to. When set,
    the onboarding write is gated through Assert-GovernanceApproval and requires
    -ApprovalRef. Also written as the `OrgPath` Azure tag for addressability.

.PARAMETER ApprovalRef
    The change reference (e.g. RITM/CR number) authorizing a governed write.

.EXAMPLE
    # Manual path — preview, then run
    .\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf

.EXAMPLE
    # Governed path
    .\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus `
        -OrgPath '/Agency/Infrastructure/Servers/Production' -ApprovalRef 'CR0012345'
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][string]$SubscriptionId,   # CONFIGURE
    [Parameter(Mandatory)][string]$ResourceGroup,    # CONFIGURE
    [Parameter(Mandatory)][string]$Location,         # CONFIGURE (e.g. eastus / usgovvirginia)
    [string]$ServicePrincipalName = 'svc-arc-onboarding',
    [string]$OrgPath,
    [string]$ApprovalRef,
    [string]$Cloud = 'AzureCloud'   # AzureUSGovernment for GCC High / DoD
)

# --- locate and import the shared module (works in zip layout or flat) ---
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" `
    -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

Connect-ModernizationAzure -SubscriptionId $SubscriptionId

if (-not (Assert-GovernanceApproval -Operation 'Arc onboarding' -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) {
    return
}

# 1. Resource group
if ($PSCmdlet.ShouldProcess($ResourceGroup, 'Ensure resource group exists')) {
    if (-not (Get-AzResourceGroup -Name $ResourceGroup -ErrorAction SilentlyContinue)) {
        New-AzResourceGroup -Name $ResourceGroup -Location $Location | Out-Null
        Write-ModernizationLog -Level ACTION -Message "Created resource group $ResourceGroup"
    }
}

# 2. Least-privilege onboarding service principal (Connected Machine Onboarding only)
$scope = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup"
if ($PSCmdlet.ShouldProcess($ServicePrincipalName, 'Create Arc onboarding service principal')) {
    $sp = New-AzADServicePrincipal -DisplayName $ServicePrincipalName -Role 'Azure Connected Machine Onboarding' -Scope $scope
    Write-ModernizationLog -Level ACTION -Message "Service principal AppId=$($sp.AppId). Store the secret in Key Vault NOW — it is shown once. Rotate after onboarding."
}

# 3. Install + connect the Connected Machine Agent
$agent = 'C:\Program Files\AzureConnectedMachineAgent\azcmagent.exe'
if (-not (Get-Service -Name 'himds' -ErrorAction SilentlyContinue)) {
    if ($PSCmdlet.ShouldProcess($env:COMPUTERNAME, 'Install Connected Machine Agent')) {
        $installer = Join-Path $env:TEMP 'AzureConnectedMachineAgent.msi'
        Invoke-WebRequest -Uri 'https://aka.ms/AzureConnectedMachineAgent' -OutFile $installer -UseBasicParsing
        Start-Process msiexec.exe -ArgumentList "/i `"$installer`" /qn /l*v `"$env:TEMP\ArcInstall.log`"" -Wait -NoNewWindow
        Write-ModernizationLog -Level ACTION -Message 'Connected Machine Agent installed.'
    }
} else {
    Write-ModernizationLog -Level INFO -Message 'Connected Machine Agent already present.'
}

$tags = if ($OrgPath) { "OrgPath=$OrgPath" } else { $null }
if ($PSCmdlet.ShouldProcess($env:COMPUTERNAME, 'Connect machine to Azure Arc')) {
    $argList = @('connect','--subscription-id', $SubscriptionId, '--resource-group', $ResourceGroup,
                 '--location', $Location, '--cloud', $Cloud)
    if ($tags) { $argList += @('--tags', $tags) }
    & $agent @argList
    if ($LASTEXITCODE -eq 0) {
        Write-ModernizationLog -Level ACTION -Message "Arc onboarding succeeded for $env:COMPUTERNAME"
    } else {
        Write-ModernizationLog -Level ERROR -Message "Arc onboarding FAILED (exit $LASTEXITCODE). See $env:TEMP\ArcInstall.log"
    }
}

# 4. Validate (read-only)
if (Test-Path $agent) { & $agent show }
