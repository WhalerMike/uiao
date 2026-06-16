#requires -Modules Microsoft.Graph.Authentication, Microsoft.Graph.Applications, Microsoft.Graph.Groups
<#
.SYNOPSIS
    Produce a per-application access roster for owner certification (the input
    to the quarterly/semi-annual/annual reviews in Doc 3 §10.3).

.DESCRIPTION
    For each Enterprise Application (optionally filtered to a risk tier), expand
    every assigned group to its direct user members and emit one row per
    (application, group, user). This is the evidence pack an Application Owner
    certifies. Read-only.

    Note: only DIRECT group members are listed — consistent with the platform
    reality that Entra does not honor nested groups for app assignment.

.PARAMETER OutputPath  CSV path. Default .\access-certification.csv
.PARAMETER AppDisplayName  Optional: limit to one application.
.EXAMPLE
    .\Export-AccessCertification.ps1 -AppDisplayName 'Payroll'
#>
[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot 'access-certification.csv'),
    [string]$AppDisplayName,
    [string]$TenantId
)

Import-Module (Join-Path $PSScriptRoot '..\lib\HelpDeskEntra.psm1') -Force
Connect-HelpDeskGraph -ScopeSet InventoryRead -TenantId $TenantId

$filter = if ($AppDisplayName) { "displayName eq '$AppDisplayName'" } else { $null }
$sps = if ($filter) { Get-MgServicePrincipal -Filter $filter } else { Get-MgServicePrincipal -All }

$rows = foreach ($sp in $sps) {
    $assignments = Get-MgServicePrincipalAppRoleAssignedTo -ServicePrincipalId $sp.Id -ErrorAction SilentlyContinue
    foreach ($a in $assignments) {
        if ($a.PrincipalType -eq 'Group') {
            $members = Get-MgGroupMember -GroupId $a.PrincipalId -All -ErrorAction SilentlyContinue |
                       Where-Object { $_.AdditionalProperties['@odata.type'] -eq '#microsoft.graph.user' }
            foreach ($m in $members) {
                [pscustomobject]@{
                    Application = $sp.DisplayName
                    AssignedVia = 'Group'
                    GroupName   = $a.PrincipalDisplayName
                    UserUpn     = $m.AdditionalProperties.userPrincipalName
                    UserName    = $m.AdditionalProperties.displayName
                    Certify     = ''   # owner fills: Approve / Remove / Escalate
                }
            }
        }
        elseif ($a.PrincipalType -eq 'User') {
            # Direct user assignment — flag it: Doc 3 §6.1 mandates group-based only.
            [pscustomobject]@{
                Application = $sp.DisplayName
                AssignedVia = 'DIRECT-USER (policy exception — should be group-based)'
                GroupName   = ''
                UserUpn     = $a.PrincipalDisplayName
                UserName    = $a.PrincipalDisplayName
                Certify     = ''
            }
        }
    }
}

$rows | Sort-Object Application, GroupName, UserUpn | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8
Write-HelpDeskLog -Level INFO -Message "Certification roster written: $OutputPath ($($rows.Count) rows). Send to each Application Owner to certify (Approve/Remove/Escalate)."
