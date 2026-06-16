#Requires -Version 5.1
<#
.SYNOPSIS
    Report Intune managed-device enrollment and compliance posture (read-only).

.DESCRIPTION
    Enumerates managed devices via Microsoft Graph and exports enrollment type,
    compliance state, OS version, encryption, and last sync. Read-only (L1 —
    Observe). Use to baseline the fleet before and after enrollment waves.

.EXAMPLE
    .\Get-IntuneEnrollmentStatus.ps1 -OutputPath .\intune-status.csv
#>
[CmdletBinding()]
param(
    [string]$OutputPath = '.\intune-enrollment-status.csv',
    [string]$TenantId,
    [string]$OrgPath   # informational only on a read-only report
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

Connect-ModernizationGraph -ScopeSet DeviceRead -TenantId $TenantId

$devices = Get-MgDeviceManagementManagedDevice -All | Select-Object `
    DeviceName, OperatingSystem, OsVersion, ComplianceState, EnrollmentType,
    ManagementAgent, IsEncrypted, LastSyncDateTime

$devices | Sort-Object ComplianceState | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "Exported $($devices.Count) managed devices to $OutputPath"

# roll-up
$devices | Group-Object ComplianceState | Sort-Object Count -Descending |
    Select-Object @{N='ComplianceState';E={$_.Name}}, Count | Format-Table -AutoSize
