#Requires -Version 5.1
#Requires -Modules ActiveDirectory
<#
.SYNOPSIS
    Detect duplicate / orphaned SPNs and (optionally) repair them.

.DESCRIPTION
    Inventories all servicePrincipalName values in the domain, flags duplicates
    (which break Kerberos and silently fall back to NTLM) and SPNs left on
    disabled accounts. With -Remove it strips a named SPN from a named account;
    -WhatIf previews the write. Correct, complete SPNs are a prerequisite for
    NTLM elimination (ADR-068) — Kerberos cannot be enforced without them.

.EXAMPLE
    # Audit only
    .\Repair-Spn.ps1 -OutputPath .\spn-inventory.csv

.EXAMPLE
    # Repair: remove a stale SPN from a disabled account
    .\Repair-Spn.ps1 -Remove -Spn 'HTTP/webapp.agency.gov' -Account 'svc-webapp-old' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [string]$OutputPath = '.\spn-inventory.csv',
    [switch]$Remove,
    [string]$Spn,
    [string]$Account,
    [string]$OrgPath,
    [string]$ApprovalRef
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force
Import-Module ActiveDirectory

# --- inventory (read-only) ---
$all = Get-ADObject -Filter { ServicePrincipalName -like '*' } `
        -Properties SamAccountName, ServicePrincipalName, ObjectClass, Enabled, DistinguishedName |
    ForEach-Object {
        $o = $_
        foreach ($s in $o.ServicePrincipalName) {
            [pscustomobject]@{
                ObjectName = $o.SamAccountName; ObjectClass = $o.ObjectClass
                Enabled    = if ($o.PSObject.Properties.Name -contains 'Enabled') { $o.Enabled } else { 'N/A' }
                SPN = $s; DistinguishedName = $o.DistinguishedName
            }
        }
    }
$all | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "SPN inventory: $($all.Count) entries -> $OutputPath"

# duplicates + SPNs on disabled accounts
$dups = $all | Group-Object SPN | Where-Object Count -gt 1
if ($dups) { Write-ModernizationLog -Level WARN -Message "$($dups.Count) duplicate SPN group(s) found — these break Kerberos." ; $dups | Select-Object Name, Count | Format-Table -AutoSize }
$stale = $all | Where-Object { $_.Enabled -eq $false }
if ($stale) { Write-ModernizationLog -Level WARN -Message "$($stale.Count) SPN(s) on disabled accounts (stale)." }

# --- repair (write) ---
if ($Remove) {
    if (-not ($Spn -and $Account)) { throw '-Remove requires both -Spn and -Account.' }
    if (-not (Assert-GovernanceApproval -Operation "Remove SPN $Spn from $Account" -OrgPath $OrgPath -ApprovalRef $ApprovalRef -ActuationRung 'L3')) { return }
    $acct = Get-ADUser -Identity $Account -Properties ServicePrincipalName
    $keep = $acct.ServicePrincipalName | Where-Object { $_ -ne $Spn }
    if ($PSCmdlet.ShouldProcess("$Account", "Remove SPN '$Spn'")) {
        Set-ADUser -Identity $Account -ServicePrincipalName $keep
        Write-ModernizationLog -Level ACTION -Message "Removed '$Spn' from $Account. Verify: setspn -L $Account"
    }
}
