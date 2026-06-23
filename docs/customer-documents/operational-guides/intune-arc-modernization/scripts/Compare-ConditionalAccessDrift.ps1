#Requires -Version 5.1
<#
.SYNOPSIS
    Compare live Conditional Access policies against a saved JSON baseline (read-only).

.DESCRIPTION
    Exports the current CA policy set and diffs it against a committed baseline,
    reporting Added / Removed / Changed policies. Read-only (L1 — Observe); this
    is the CA facet of the drift loop. With no -BaselinePath it writes the
    current set as a new baseline.

    Canon: ADR-040 (OrgTree Drift Detection Engine — Snapshot, Compare, Classify)
    / ADR-092 (the substrate observes actual vs desired and classifies drift).

.EXAMPLE
    # First run: capture a baseline
    .\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\ca-baseline.json

    # Later: diff live against the baseline
    .\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\ca-baseline.json
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$BaselinePath,
    [string]$TenantId
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

Connect-ModernizationGraph -ScopeSet CaRead -TenantId $TenantId

function Get-ObjectSha256 {
    param([Parameter(Mandatory)]$InputObject)
    $json = $InputObject | ConvertTo-Json -Depth 10 -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($bytes)
    } finally {
        $sha.Dispose()
    }
    return ([System.BitConverter]::ToString($hashBytes) -replace '-', '').ToLowerInvariant()
}

$live = Get-MgIdentityConditionalAccessPolicy -All |
    Select-Object Id, DisplayName, State,
        @{N='Hash';E={ Get-ObjectSha256 -InputObject $_ }}

if (-not (Test-Path $BaselinePath)) {
    $live | ConvertTo-Json -Depth 6 | Set-Content -Path $BaselinePath -Encoding UTF8
    Write-ModernizationLog -Level INFO -Message "No baseline existed — wrote current $($live.Count) policies to $BaselinePath"
    return
}

$baseline = Get-Content $BaselinePath -Raw | ConvertFrom-Json
$baseById = @{}; $baseline | ForEach-Object { $baseById[$_.Id] = $_ }
$liveById = @{}; $live     | ForEach-Object { $liveById[$_.Id] = $_ }

$added   = $live     | Where-Object { -not $baseById.ContainsKey($_.Id) }
$removed = $baseline | Where-Object { -not $liveById.ContainsKey($_.Id) }
$changed = $live | Where-Object { $baseById.ContainsKey($_.Id) -and $baseById[$_.Id].Hash -ne $_.Hash }

Write-ModernizationLog -Level $(if ($added -or $removed -or $changed) { 'WARN' } else { 'INFO' }) `
    -Message "CA drift — Added:$($added.Count) Removed:$($removed.Count) Changed:$($changed.Count)"
if ($added)   { Write-Host "`nADDED:";   $added   | Select-Object DisplayName, State | Format-Table -AutoSize }
if ($removed) { Write-Host "`nREMOVED:"; $removed | Select-Object DisplayName, State | Format-Table -AutoSize }
if ($changed) { Write-Host "`nCHANGED:"; $changed | Select-Object DisplayName, State | Format-Table -AutoSize }
