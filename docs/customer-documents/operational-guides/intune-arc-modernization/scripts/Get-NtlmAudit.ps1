#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Audit NTLM authentication on a domain controller (read-only).

.DESCRIPTION
    Parses Security event ID 4776 (NTLM credential validation on the DC) over a
    look-back window and summarizes the top NTLM-authenticating accounts and
    workstations. Read-only (L1 — Observe). Run on each DC (or against forwarded
    events) for a minimum 14–30 day window BEFORE any restriction.

    Canon: ADR-068 — Kerberos / NTLM elimination (Notice 0009 deadline
    2027-04-01). You cannot safely restrict what you have not first baselined.

.EXAMPLE
    .\Get-NtlmAudit.ps1 -DaysBack 30 -OutputPath .\ntlm-audit.csv
#>
[CmdletBinding()]
param(
    [int]$DaysBack = 30,
    [string]$DC = $env:COMPUTERNAME,
    [string]$OutputPath = '.\ntlm-audit.csv'
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

$startTime = (Get-Date).AddDays(-$DaysBack)
Write-ModernizationLog -Level INFO -Message "Querying 4776 (NTLM) on $DC since $startTime"

$filterXml = @"
<QueryList><Query Id="0"><Select Path="Security">
*[System[(EventID=4776) and TimeCreated[@SystemTime&gt;='$($startTime.ToUniversalTime().ToString("o"))']]]
</Select></Query></QueryList>
"@

$events = Get-WinEvent -ComputerName $DC -FilterXml $filterXml -ErrorAction SilentlyContinue
$results = foreach ($event in $events) {
    $data = ([xml]$event.ToXml()).Event.EventData.Data
    [pscustomobject]@{
        TimeCreated     = $event.TimeCreated
        ComputerName    = $DC
        AccountName     = ($data | Where-Object Name -eq 'TargetUserName').'#text'
        WorkstationName = ($data | Where-Object Name -eq 'Workstation').'#text'
        Status          = ($data | Where-Object Name -eq 'Status').'#text'
        PackageName     = 'NTLM'
    }
}

$results | Sort-Object AccountName, WorkstationName -Unique | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "NTLM audit complete: $($results.Count) events. Output: $OutputPath"

Write-Host "`nTop 20 NTLM-authenticating accounts:" -ForegroundColor Cyan
$results | Group-Object AccountName | Sort-Object Count -Descending |
    Select-Object -First 20 Name, Count | Format-Table -AutoSize
