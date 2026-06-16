#Requires -Version 5.1
<#
.SYNOPSIS
    Survey an existing estate and PROPOSE OrgPath assignments (advisory, read-only).

.DESCRIPTION
    The retrofit "derive OrgPath" helper (L2 — Advise). Reads structure the estate
    already has — Arc/Azure resource tags on onboarded servers, and the OU each
    workstation enrolled from — and proposes an OrgPath for each object, with a
    confidence flag so low-confidence rows can be reviewed first.

    It does NOT write anything. Stamping a proposal onto live objects is the
    existing gated (L3) write — re-run the relevant script with `-OrgPath` once
    you have reviewed and accepted the proposal. The derivation rules live in
    `ConvertTo-OrgPathProposal` in the shared module; tune them per agency.

    SOURCES (use any combination):
      -ArcResourceGroup  survey Arc servers' tags          (needs Az + Connect)
      -WorkstationOU     survey AD computer objects' OU     (needs ActiveDirectory)
      -DeviceCsv         survey a Get-IntuneEnrollmentStatus export (offline)

.EXAMPLE
    # Propose from Arc server tags
    .\Get-OrgPathSurvey.ps1 -SubscriptionId $sub -ArcResourceGroup rg-arc-servers -OutputPath .\orgpath-proposal.csv

.EXAMPLE
    # Propose from an AD workstation OU
    .\Get-OrgPathSurvey.ps1 -WorkstationOU 'OU=Workstations,DC=agency,DC=gov' -OutputPath .\orgpath-proposal.csv
#>
[CmdletBinding()]
param(
    [string]$SubscriptionId,
    [string]$ArcResourceGroup,
    [string]$WorkstationOU,
    [string]$DeviceCsv,
    [string]$Root = '/Agency',                 # CONFIGURE: organization root segment
    [string]$OutputPath = '.\orgpath-proposal.csv'
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

if (-not ($ArcResourceGroup -or $WorkstationOU -or $DeviceCsv)) {
    throw 'Supply at least one source: -ArcResourceGroup, -WorkstationOU, or -DeviceCsv.'
}

$proposals = New-Object System.Collections.Generic.List[object]

# --- servers, from Arc resource tags ---
if ($ArcResourceGroup) {
    if (-not $SubscriptionId) { throw '-ArcResourceGroup requires -SubscriptionId.' }
    Connect-ModernizationAzure -SubscriptionId $SubscriptionId
    foreach ($m in (Get-AzConnectedMachine -ResourceGroupName $ArcResourceGroup -ErrorAction SilentlyContinue)) {
        $tags = @{}; if ($m.Tag) { $m.Tag.GetEnumerator() | ForEach-Object { $tags[$_.Key] = $_.Value } }
        $p = ConvertTo-OrgPathProposal -Tags $tags -Root $Root
        $proposals.Add([pscustomobject]@{ Object = $m.Name; Kind = 'Server'; Proposed = $p.Proposed; Owner = $p.Owner; Confidence = $p.Confidence; Basis = $p.Basis })
    }
}

# --- workstations, from AD OU ---
if ($WorkstationOU) {
    Import-Module ActiveDirectory
    foreach ($c in (Get-ADComputer -SearchBase $WorkstationOU -Filter * -ErrorAction SilentlyContinue)) {
        $p = ConvertTo-OrgPathProposal -OuDn $c.DistinguishedName -Root $Root
        $proposals.Add([pscustomobject]@{ Object = $c.Name; Kind = 'Workstation'; Proposed = $p.Proposed; Owner = $p.Owner; Confidence = $p.Confidence; Basis = $p.Basis })
    }
}

# --- workstations, offline from a posture export ---
if ($DeviceCsv) {
    foreach ($row in (Import-Csv $DeviceCsv)) {
        $ou = $row.OU; if (-not $ou) { continue }
        $p = ConvertTo-OrgPathProposal -OuDn $ou -Root $Root
        $proposals.Add([pscustomobject]@{ Object = $row.DeviceName; Kind = 'Workstation'; Proposed = $p.Proposed; Owner = $p.Owner; Confidence = $p.Confidence; Basis = $p.Basis })
    }
}

$proposals | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "OrgPath survey: $($proposals.Count) proposals -> $OutputPath (advisory — review before stamping with -OrgPath)"

$low = ($proposals | Where-Object Confidence -eq 'Low').Count
if ($low) { Write-ModernizationLog -Level WARN -Message "$low proposal(s) are LOW confidence — review these before accepting." }
$proposals | Group-Object Proposed | Sort-Object Count -Descending |
    Select-Object @{N='ProposedOrgPath';E={$_.Name}}, Count | Format-Table -AutoSize
