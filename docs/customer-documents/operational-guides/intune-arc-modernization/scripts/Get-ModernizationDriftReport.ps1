#Requires -Version 5.1
<#
.SYNOPSIS
    Cross-domain modernization drift roll-up (read-only).

.DESCRIPTION
    Reads the per-domain artifact CSVs produced by the other scripts
    (Arc, Intune, NTLM, SPN, SQL, CA) from a folder and produces a single
    status roll-up: which domains have evidence, how fresh it is, and the
    headline pass/attention counts. Read-only (L1 — Observe).

    Canon: ADR-040 / ADR-092 — the substrate's whole-estate observe step. On the
    governed path this is what feeds the OrgPath-scoped compliance view; on the
    manual path it is your weekly status page.

.EXAMPLE
    .\Get-ModernizationDriftReport.ps1 -ArtifactPath .\artifacts -OutputPath .\modernization-status.csv
#>
[CmdletBinding()]
param(
    [string]$ArtifactPath = '.',
    [string]$OutputPath   = '.\modernization-status.csv'
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

# Map each domain to the artifact glob the other scripts emit.
$domainArtifacts = @(
    @{ Domain='Endpoint posture'; Glob='intune-enrollment-status*.csv'; PassField='ComplianceState'; PassValue='compliant' }
    @{ Domain='NTLM elimination'; Glob='ntlm-audit*.csv';              PassField=$null;            PassValue=$null }
    @{ Domain='SPN hygiene';      Glob='spn-inventory*.csv';           PassField=$null;            PassValue=$null }
    @{ Domain='SQL hardening';    Glob='sql-hardening*.csv';           PassField='HardeningPass';  PassValue='True' }
)

$rows = foreach ($d in $domainArtifacts) {
    $file = Get-ChildItem -Path $ArtifactPath -Filter $d.Glob -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $file) {
        [pscustomobject]@{ Domain=$d.Domain; Evidence='MISSING'; Rows=0; AgeDays='n/a'; Pass='n/a'; Attention='n/a' }
        continue
    }
    $data = Import-Csv $file.FullName
    $ageDays = [math]::Round(((Get-Date) - $file.LastWriteTime).TotalDays, 1)
    $pass = $att = 'n/a'
    if ($d.PassField) {
        $pass = ($data | Where-Object { "$($_.$($d.PassField))" -ieq $d.PassValue }).Count
        $att  = $data.Count - $pass
    }
    [pscustomobject]@{ Domain=$d.Domain; Evidence=$file.Name; Rows=$data.Count; AgeDays=$ageDays; Pass=$pass; Attention=$att }
}

$rows | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "Modernization status roll-up -> $OutputPath"
$rows | Format-Table -AutoSize
