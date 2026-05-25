#Requires -Modules GroupPolicy, ActiveDirectory
<#
.SYNOPSIS
    Audits all GPOs in the domain and flags obsolete or misconfigured objects.

.DESCRIPTION
    Evaluates every GPO against six rules:

        OBSOLETE_UNLINKED               GPO has no links to any OU, domain, or site
        OBSOLETE_LINKED_TO_DELETED_OU   GPO is linked to an OU that no longer exists
        OBSOLETE_NO_ENABLED_SETTINGS    GPO has no settings in either configuration section
        OBSOLETE_STALE                  GPO has not been modified within $StaleDays
        OBSOLETE_DISABLED               GPO has a disabled section that also has no settings
        OBSOLETE_ORPHAN_WMI_FILTER      GPO references a WMI filter that no longer exists in AD
        EVIDENCE_ERROR                  GPO report could not be generated or parsed

    Output is a JSON array. Each entry carries GpoName, GpoId, and a Rules array.
    GPOs with no findings appear in output with an empty Rules array, making the
    result set suitable for direct ingestion into a UIAO Evidence Ledger or
    Drift Engine without post-processing.

.PARAMETER StaleDays
    Days since last modification before a GPO is considered stale. Default: 365.

.PARAMETER OutputPath
    Optional file path for JSON output. Omit to write to stdout.

.EXAMPLE
    .\Invoke-GpoObsoleteAudit.ps1

.EXAMPLE
    .\Invoke-GpoObsoleteAudit.ps1 -StaleDays 180 -OutputPath C:\Audit\gpo-audit.json

.EXAMPLE
    .\Invoke-GpoObsoleteAudit.ps1 -Verbose
#>
[CmdletBinding()]
param(
    [ValidateRange(1, 3650)]
    [int]    $StaleDays  = 365,

    [string] $OutputPath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region --- Bootstrap -----------------------------------------------------------

Import-Module GroupPolicy     -ErrorAction Stop
Import-Module ActiveDirectory -ErrorAction Stop

$now     = Get-Date
$results = [System.Collections.Generic.List[object]]::new()
$tempDir = $env:TEMP

#endregion

#region --- Pre-load domain lookups (single pass each, not per-GPO) ------------

Write-Verbose 'Loading domain context...'
$domain   = Get-ADDomain
$domainDN = $domain.DistinguishedName

# GPOReport XML SOMPath uses canonical/DNS notation:  "contoso.com/Finance/HR"
# Get-ADOrganizationalUnit DistinguishedName looks like: "OU=HR,OU=Finance,DC=contoso,DC=com"
# These never match — load CanonicalName instead.
$ouCanonicalNames = @{}
Get-ADOrganizationalUnit -Filter * -Properties CanonicalName |
    ForEach-Object { $ouCanonicalNames[$_.CanonicalName] = $true }

Write-Verbose "Loaded $($ouCanonicalNames.Count) OUs."

$allGpos = Get-GPO -All
Write-Verbose "Processing $($allGpos.Count) GPOs..."

#endregion

#region --- Helper: detect settings in a configuration section -----------------
function Test-SectionHasSettings {
    param([System.Xml.XmlElement] $Section)

    if (-not $Section) { return $false }

    # SelectNodes handles single-node and multi-node ExtensionData uniformly.
    # An empty section has no Extension children, so InnerXml is empty.
    foreach ($ext in $Section.SelectNodes('ExtensionData/Extension')) {
        if ($ext.InnerXml -and $ext.InnerXml.Trim().Length -gt 0) {
            return $true
        }
    }
    return $false
}
#endregion

#region --- GPO loop ------------------------------------------------------------

foreach ($gpo in $allGpos) {

    $gpoObject = [ordered]@{
        GpoName = $gpo.DisplayName
        GpoId   = $gpo.Id.ToString()
        Rules   = [System.Collections.Generic.List[object]]::new()
    }

    $reportPath = Join-Path $tempDir "gpo-audit-$($gpo.Id).xml"

    #region --- Generate and parse XML report -----------------------------------
    try {
        Get-GPOReport -Guid $gpo.Id -ReportType Xml -Path $reportPath -ErrorAction Stop
        $xml = [xml](Get-Content -Path $reportPath -Raw -ErrorAction Stop)
    }
    catch {
        $gpoObject.Rules.Add([ordered]@{
            RuleId      = 'EVIDENCE_ERROR'
            Description = 'Failed to generate or parse GPO report XML.'
            Error       = $_.Exception.Message
        })
        $results.Add($gpoObject)
        continue
    }
    finally {
        # Runs even when catch triggers 'continue' — temp file always cleaned up.
        Remove-Item -Path $reportPath -ErrorAction SilentlyContinue
    }
    #endregion

    #region --- Rule: OBSOLETE_UNLINKED / OBSOLETE_LINKED_TO_DELETED_OU --------
    #
    # SelectNodes returns an XmlNodeList — always iterable, correctly handles
    # zero, one, or many LinksTo elements without @() wrapping artifacts.
    #
    # SOMType values from GPOReport XML: "OU", "Domain", "Site"
    # Only OU links are validated against the known-OU set.
    # Domain-root and site links are accepted without validation.
    #
    $linkNodes = $xml.SelectNodes('/Report/GPO/LinksTo')

    if ($linkNodes.Count -eq 0) {
        $gpoObject.Rules.Add([ordered]@{
            RuleId      = 'OBSOLETE_UNLINKED'
            Description = 'GPO has no links to any OU, domain, or site.'
        })
    }
    else {
        foreach ($link in $linkNodes) {
            if ($link.SOMType -eq 'OU' -and
                -not $ouCanonicalNames.ContainsKey($link.SOMPath)) {
                $gpoObject.Rules.Add([ordered]@{
                    RuleId      = 'OBSOLETE_LINKED_TO_DELETED_OU'
                    Description = 'GPO is linked to an OU that no longer exists.'
                    Target      = $link.SOMPath
                })
            }
        }
    }
    #endregion

    #region --- Detect settings presence per section ---------------------------
    $computerHasSettings = Test-SectionHasSettings -Section $xml.GPO.Computer
    $userHasSettings     = Test-SectionHasSettings -Section $xml.GPO.User
    #endregion

    #region --- Rule: OBSOLETE_NO_ENABLED_SETTINGS -----------------------------
    if (-not $computerHasSettings -and -not $userHasSettings) {
        $gpoObject.Rules.Add([ordered]@{
            RuleId      = 'OBSOLETE_NO_ENABLED_SETTINGS'
            Description = 'GPO contains no settings in either the computer or user configuration.'
        })
    }
    #endregion

    #region --- Rule: OBSOLETE_STALE -------------------------------------------
    $ageDays = [int]($now - $gpo.ModificationTime).TotalDays
    if ($ageDays -gt $StaleDays) {
        $gpoObject.Rules.Add([ordered]@{
            RuleId      = 'OBSOLETE_STALE'
            Description = "GPO has not been modified in $ageDays days (threshold: $StaleDays)."
            AgeDays     = $ageDays
        })
    }
    #endregion

    #region --- Rule: OBSOLETE_DISABLED ----------------------------------------
    #
    # Only flag a disabled section when that same section has no settings.
    # A GPO with ComputerSettingsDisabled but active user settings is a valid
    # deployment pattern — flagging it produces noise, not signal.
    #
    switch ($gpo.GpoStatus) {
        'AllSettingsDisabled' {
            if (-not $computerHasSettings -and -not $userHasSettings) {
                $gpoObject.Rules.Add([ordered]@{
                    RuleId      = 'OBSOLETE_DISABLED'
                    Description = 'All settings are disabled and no settings are configured.'
                    Status      = $gpo.GpoStatus
                })
            }
        }
        'ComputerSettingsDisabled' {
            if (-not $computerHasSettings) {
                $gpoObject.Rules.Add([ordered]@{
                    RuleId      = 'OBSOLETE_DISABLED'
                    Description = 'Computer section is disabled and has no computer settings.'
                    Status      = $gpo.GpoStatus
                })
            }
        }
        'UserSettingsDisabled' {
            if (-not $userHasSettings) {
                $gpoObject.Rules.Add([ordered]@{
                    RuleId      = 'OBSOLETE_DISABLED'
                    Description = 'User section is disabled and has no user settings.'
                    Status      = $gpo.GpoStatus
                })
            }
        }
    }
    #endregion

    #region --- Rule: OBSOLETE_ORPHAN_WMI_FILTER --------------------------------
    #
    # WMI filters are AD objects stored at:
    #   CN={<FilterGuid>},CN=SOM,CN=WMIPolicy,CN=System,<DomainDN>
    #
    # root\Policy\MSFT_WmiFilter (CimInstance) does not exist on standard
    # Windows systems — AD is the authoritative source.
    #
    if ($null -ne $gpo.WmiFilter) {
        $filterDN     = "CN={$($gpo.WmiFilter.Id)},CN=SOM,CN=WMIPolicy,CN=System,$domainDN"
        $filterExists = [bool](Get-ADObject -Filter { DistinguishedName -eq $filterDN } `
                                            -ErrorAction SilentlyContinue)

        if (-not $filterExists) {
            $gpoObject.Rules.Add([ordered]@{
                RuleId      = 'OBSOLETE_ORPHAN_WMI_FILTER'
                Description = 'GPO references a WMI filter that no longer exists in AD.'
                WmiFilter   = $gpo.WmiFilter.Name
                FilterDN    = $filterDN
            })
        }
    }
    #endregion

    $results.Add($gpoObject)
}

#endregion

#region --- Output --------------------------------------------------------------

$json = $results | ConvertTo-Json -Depth 10

if ($OutputPath) {
    $json | Set-Content -Path $OutputPath -Encoding UTF8
    $withFindings = ($results | Where-Object { $_.Rules.Count -gt 0 }).Count
    Write-Host "Audit complete. Results written to: $OutputPath"
    Write-Host "GPOs evaluated : $($results.Count)"
    Write-Host "GPOs with findings : $withFindings"
    Write-Host "Clean GPOs : $($results.Count - $withFindings)"
}
else {
    $json
}

#endregion
