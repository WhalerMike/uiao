#Requires -Modules GroupPolicy, ActiveDirectory
<#
.SYNOPSIS
    Triages every GPO in the domain for migration to Intune (workstations) or
    Azure Arc (servers), and writes two complementary JSON artifacts.

.DESCRIPTION
    For every GPO in the domain the script produces two outputs:

      Summary record (one per GPO)
        - Side-by-side classification of the GPO's target plane:
            ByOuOSPredominance  derived from the OperatingSystem attribute of
                                Computer objects in the GPO's linked OUs
            ByOuNameHeuristic   derived from regex/wildcard match against the
                                linked OU's canonical path
            Agreement           true when both classifiers return the same plane
        - Aggregate counts per linked OU (workstation/server/other)
        - Roll-up tag counts across all extensions

      Detail record (one per Extension / Section in the GPO XML report)
        - Section            'Computer' or 'User'
        - ExtensionName      from the GPO report XML (Extension/Name)
        - IntuneTarget       most likely Intune Settings Catalog destination
        - ArcTarget          most likely Azure Arc destination (Guest Config,
                             Azure Policy, Defender for Servers, Update Mgr, ...)
        - Complexity         Low / Medium / High

    Both artifacts are JSON arrays. Clean / unclassifiable GPOs appear in the
    summary with an explicit 'Unknown' marker so downstream Evidence-Ledger or
    sizing tools never have to reconcile against an external GPO inventory.

.PARAMETER OutputDirectory
    Directory for the two output files. Defaults to the current directory.
    Files written:
        gpo-migration-triage-summary.json
        gpo-migration-triage-detail.json

.PARAMETER WorkstationOSPattern
    Wildcard patterns that match workstation OperatingSystem values on
    Computer objects. Default: 'Windows 10*','Windows 11*','Windows 7*','Windows 8*'.

.PARAMETER ServerOSPattern
    Wildcard patterns for server Computer.OperatingSystem.
    Default: 'Windows Server*'.

.PARAMETER WorkstationOUNamePattern
    Wildcard patterns matched against the GPO link's canonical OU path for the
    name heuristic. Default: '*Workstation*','*Desktop*','*Laptop*','*Client*',
    '*Endpoint*','*PC*'.

.PARAMETER ServerOUNamePattern
    Default: '*Server*','*DC*','*SQL*','*Domain Controllers'.

.PARAMETER SkipComputerEnumeration
    Skip OU OS-predominance classification (no Get-ADComputer reads).
    The summary still produces ByOuNameHeuristic and an Agreement field that
    will reflect only the heuristic result. Use this on very large directories
    where reading every Computer object is prohibitive.

.EXAMPLE
    .\Invoke-GpoMigrationTriage.ps1 -OutputDirectory C:\Triage

.EXAMPLE
    .\Invoke-GpoMigrationTriage.ps1 -OutputDirectory C:\Triage `
        -WorkstationOUNamePattern '*WKS*','*Desktop*' `
        -ServerOUNamePattern '*SRV*','*Server*'

.EXAMPLE
    .\Invoke-GpoMigrationTriage.ps1 -SkipComputerEnumeration -Verbose
#>
[CmdletBinding()]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'WorkstationOSPattern', Justification = 'Documented CLI tuning parameter; read inside the script-scoped Get-OuComputerCount helper when classifying OU OS predominance.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'ServerOSPattern', Justification = 'Documented CLI tuning parameter; read inside the script-scoped Get-OuComputerCount helper when classifying OU OS predominance.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'WorkstationOUNamePattern', Justification = 'Documented CLI tuning parameter; read inside the script-scoped Get-PlaneFromName helper for the OU-name heuristic.')]
[Diagnostics.CodeAnalysis.SuppressMessageAttribute('PSReviewUnusedParameter', 'ServerOUNamePattern', Justification = 'Documented CLI tuning parameter; read inside the script-scoped Get-PlaneFromName helper for the OU-name heuristic.')]
param(
    [string]   $OutputDirectory           = '.',
    [string[]] $WorkstationOSPattern      = @('Windows 10*','Windows 11*','Windows 7*','Windows 8*'),
    [string[]] $ServerOSPattern           = @('Windows Server*'),
    [string[]] $WorkstationOUNamePattern  = @('*Workstation*','*Desktop*','*Laptop*','*Client*','*Endpoint*','*PC*'),
    [string[]] $ServerOUNamePattern       = @('*Server*','*DC*','*SQL*','*Domain Controllers'),
    [switch]   $SkipComputerEnumeration
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

#region --- Bootstrap -----------------------------------------------------------

Import-Module GroupPolicy     -ErrorAction Stop
Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}
$summaryPath = Join-Path $OutputDirectory 'gpo-migration-triage-summary.json'
$detailPath  = Join-Path $OutputDirectory 'gpo-migration-triage-detail.json'
$tempDir     = $env:TEMP

$summary = [System.Collections.Generic.List[object]]::new()
$detail  = [System.Collections.Generic.List[object]]::new()

#endregion

#region --- Migration mapping (Extension display name -> Intune + Arc) ---------
#
# Keys are matched case-insensitively against the GPO report XML
# Extension/Name attribute. Values declare the most-likely Intune target,
# the most-likely Azure Arc target, and an estimated migration complexity.
#
# Sources reconciled:
#   - tools/discovery/Spec1-D1.3-Get-GPODeviceDependencyMap.ps1 ($intuneMap)
#   - AGENTS.md modernization-registry entries
#   - Microsoft Learn topology for Intune Settings Catalog and Arc Guest
#     Configuration (extensions known to have a 1:1 cloud equivalent).
#
$migrationMap = @{
    # ----- Security Settings -----
    'Account Policies'                  = @{ Intune='Endpoint Security > Account Protection';            Arc='Azure Policy guest configuration: domain-account policy (DCs only — Entra ID for cloud)'; Complexity='Low' }
    'Password Policy'                   = @{ Intune='Endpoint Security > Account Protection';            Arc='Azure Policy guest configuration: PasswordPolicy';                                          Complexity='Low' }
    'Account Lockout Policy'            = @{ Intune='Endpoint Security > Account Protection';            Arc='Azure Policy guest configuration: AccountLockoutPolicy';                                    Complexity='Low' }
    'Kerberos Policy'                   = @{ Intune='N/A (DC scope only)';                               Arc='N/A (DC scope only — manage on Active Directory)';                                          Complexity='High' }
    'Audit Policy'                      = @{ Intune='Settings Catalog > Audit';                          Arc='Azure Monitor Agent + Defender for Servers audit policy';                                   Complexity='Medium' }
    'Advanced Audit Policy Configuration' = @{ Intune='Settings Catalog > Audit (Advanced)';             Arc='Azure Monitor Agent + Defender for Servers advanced audit';                                 Complexity='Medium' }
    'User Rights Assignment'            = @{ Intune='Settings Catalog > User Rights';                    Arc='Azure Policy guest configuration: UserRightsAssignment';                                    Complexity='Medium' }
    'Security Options'                  = @{ Intune='Settings Catalog > Local Policies Security Options'; Arc='Azure Policy guest configuration: SecurityOptions';                                        Complexity='Medium' }
    'Restricted Groups'                 = @{ Intune='Account Protection (LAPS) + Endpoint Privilege Management'; Arc='Azure Policy guest configuration: GroupMembership';                                  Complexity='High' }
    'System Services'                   = @{ Intune='Settings Catalog > Services';                       Arc='Azure Policy guest configuration: ServiceState';                                            Complexity='Medium' }
    'Registry'                          = @{ Intune='Settings Catalog > Registry (custom)';              Arc='Azure Policy guest configuration: Registry';                                                Complexity='High' }
    'File System'                       = @{ Intune='Intune Platform Scripts (no native equivalent)';    Arc='Azure Policy guest configuration: AuditFile / Azure Automanage Machine Configuration';     Complexity='High' }
    'Wired Network (IEEE 802.3) Policies' = @{ Intune='Settings Catalog > Wired Network';                Arc='Manage via Azure Arc machine config (custom DSC)';                                          Complexity='High' }
    'Wireless Network (IEEE 802.11) Policies' = @{ Intune='Settings Catalog > Wi-Fi profiles';           Arc='Not applicable to servers (no wireless)';                                                   Complexity='Low' }
    'Public Key Policies'               = @{ Intune='Endpoint Security > PKCS / SCEP certificate profile'; Arc='Azure Arc-enabled servers: certificate management via Key Vault + Automanage';            Complexity='High' }
    'Software Restriction Policies'     = @{ Intune='Endpoint Security > Application Control (WDAC)';    Arc='Defender for Servers + Defender Application Control';                                       Complexity='High' }
    'Application Control Policies'      = @{ Intune='Endpoint Security > Application Control (WDAC)';    Arc='Defender for Servers + Defender Application Control';                                       Complexity='High' }
    'AppLocker'                         = @{ Intune='Endpoint Security > Application Control (WDAC)';    Arc='Defender for Servers + Defender Application Control';                                       Complexity='High' }
    'IP Security Policies on Active Directory' = @{ Intune='Endpoint Security > Firewall (IPsec rules)'; Arc='Azure Policy guest configuration: IPsec / Windows Firewall';                                Complexity='High' }
    'Advanced Audit Configuration'      = @{ Intune='Settings Catalog > Audit (Advanced)';               Arc='Azure Monitor Agent + Defender for Servers advanced audit';                                 Complexity='Medium' }
    'Windows Firewall with Advanced Security' = @{ Intune='Endpoint Security > Firewall';                Arc='Azure Policy guest configuration: WindowsFirewall';                                         Complexity='Medium' }
    'BitLocker Drive Encryption'        = @{ Intune='Endpoint Security > Disk Encryption';               Arc='Defender for Servers: disk encryption posture (Azure Disk Encryption for IaaS only)';       Complexity='Low' }
    'Windows Defender Antivirus'        = @{ Intune='Endpoint Security > Antivirus';                     Arc='Defender for Servers (Plan 2)';                                                             Complexity='Low' }
    'Windows Defender Exploit Guard'    = @{ Intune='Endpoint Security > Attack Surface Reduction';      Arc='Defender for Servers (Plan 2) ASR rules';                                                   Complexity='Low' }
    'Windows Defender SmartScreen'      = @{ Intune='Settings Catalog > SmartScreen';                    Arc='Not applicable (server-side SmartScreen unsupported)';                                      Complexity='Low' }
    'Microsoft Edge'                    = @{ Intune='Settings Catalog > Microsoft Edge';                 Arc='Azure Policy guest config + ADMX-ingested Edge policy';                                     Complexity='Low' }
    'Google Chrome'                     = @{ Intune='Settings Catalog > Chrome (ADMX ingestion)';        Arc='Azure Policy guest config + ADMX ingestion';                                                Complexity='Medium' }
    'OneDrive'                          = @{ Intune='Settings Catalog > OneDrive';                       Arc='Not applicable (server-side OneDrive unsupported)';                                         Complexity='Low' }

    # ----- Windows Settings -----
    'Folder Redirection'                = @{ Intune='OneDrive Known Folder Move (KFM)';                  Arc='Not applicable on servers (user-scope)';                                                    Complexity='Low' }
    'Scripts'                           = @{ Intune='Intune Platform Scripts / Remediation Scripts';     Arc='Azure Automation / Run Command for Arc machines';                                           Complexity='High' }
    'Deployed Printers'                 = @{ Intune='Universal Print + Settings Catalog';                Arc='Universal Print connector on Arc-enabled print servers';                                    Complexity='High' }
    'Group Policy Preferences (Drives)' = @{ Intune='Intune Platform Scripts + Azure Files (or SharePoint)'; Arc='Azure Automation / Run Command (server-side drive mapping is rare)';                    Complexity='High' }
    'Group Policy Preferences (Printers)' = @{ Intune='Universal Print + Settings Catalog';              Arc='Universal Print connector on Arc print servers';                                            Complexity='High' }
    'Group Policy Preferences (Registry)' = @{ Intune='Settings Catalog > Registry (custom)';            Arc='Azure Policy guest configuration: Registry';                                                Complexity='Medium' }
    'Group Policy Preferences (Files)'  = @{ Intune='Intune Platform Scripts';                           Arc='Azure Automation / Run Command';                                                            Complexity='High' }
    'Group Policy Preferences (Folders)' = @{ Intune='Intune Platform Scripts';                          Arc='Azure Automation / Run Command';                                                            Complexity='High' }
    'Group Policy Preferences (Shortcuts)' = @{ Intune='Intune Platform Scripts';                        Arc='Azure Automation / Run Command';                                                            Complexity='Medium' }
    'Group Policy Preferences (Services)' = @{ Intune='Settings Catalog > Services';                     Arc='Azure Policy guest configuration: ServiceState';                                            Complexity='Medium' }
    'Group Policy Preferences (Scheduled Tasks)' = @{ Intune='Intune Platform Scripts';                  Arc='Azure Automation / Run Command';                                                            Complexity='Medium' }
    'Group Policy Preferences (Power Options)' = @{ Intune='Settings Catalog > Power';                   Arc='Azure Policy guest configuration: PowerPolicy';                                             Complexity='Low' }
    'Group Policy Preferences (Network Options)' = @{ Intune='Settings Catalog > Network';              Arc='Azure Policy guest configuration: Networking';                                              Complexity='Medium' }
    'Group Policy Preferences (Network Shares)' = @{ Intune='Not applicable (no server role on workstations)'; Arc='Azure Automation / Run Command (SMB share management)';                              Complexity='High' }
    'Group Policy Preferences (Environment)' = @{ Intune='Intune Platform Scripts (env-var set)';        Arc='Azure Automation / Run Command';                                                            Complexity='Low' }
    'Group Policy Preferences (Ini Files)' = @{ Intune='Intune Platform Scripts';                        Arc='Azure Automation / Run Command';                                                            Complexity='High' }
    'Group Policy Preferences (Local Users and Groups)' = @{ Intune='Account Protection (LAPS)';         Arc='Azure Policy guest configuration: GroupMembership';                                         Complexity='High' }
    'Group Policy Preferences (Internet Settings)' = @{ Intune='Settings Catalog > Internet Explorer / Edge'; Arc='Azure Policy guest configuration: InternetExplorerSettings';                          Complexity='Medium' }
    'Group Policy Preferences (Regional Options)' = @{ Intune='Settings Catalog > Locale';               Arc='Azure Policy guest configuration: LocaleSettings';                                          Complexity='Low' }
    'Group Policy Preferences (Devices)' = @{ Intune='Endpoint Security > Attack Surface Reduction (device control)'; Arc='Defender for Servers device control';                                          Complexity='Medium' }
    'Group Policy Preferences (Drive Maps)' = @{ Intune='Intune Platform Scripts + Azure Files';         Arc='Not applicable on servers';                                                                 Complexity='High' }
    'Group Policy Preferences (Power Schemes)' = @{ Intune='Settings Catalog > Power';                   Arc='Azure Policy guest configuration: PowerPolicy';                                             Complexity='Low' }
    'Group Policy Preferences (Start Menu)' = @{ Intune='Settings Catalog > Start';                      Arc='Not applicable on servers';                                                                 Complexity='Medium' }
    'Group Policy Preferences (Internet Explorer Maintenance)' = @{ Intune='Settings Catalog > IE Mode (Edge)'; Arc='Not applicable';                                                                     Complexity='High' }

    # ----- Administrative Templates -----
    'Administrative Templates'          = @{ Intune='Settings Catalog (ADMX-backed)';                    Arc='Azure Policy guest configuration: ADMX templates (or Automanage Machine Configuration)';   Complexity='Medium' }
    'Windows Update'                    = @{ Intune='Windows Update for Business Update Rings';          Arc='Azure Update Manager';                                                                      Complexity='Low' }
    'Windows Update for Business'       = @{ Intune='Windows Update for Business Update Rings';          Arc='Azure Update Manager';                                                                      Complexity='Low' }
    'Power Management'                  = @{ Intune='Settings Catalog > Power';                          Arc='Azure Policy guest configuration: PowerPolicy';                                             Complexity='Low' }
    'Network'                           = @{ Intune='Settings Catalog > Network';                        Arc='Azure Policy guest configuration: Networking';                                              Complexity='Medium' }
    'Printers'                          = @{ Intune='Universal Print + Settings Catalog';                Arc='Universal Print connector on Arc print servers';                                            Complexity='High' }
    'Remote Desktop'                    = @{ Intune='Settings Catalog > Remote Desktop Services';        Arc='Azure Bastion + Just-in-Time access (Defender for Servers)';                                Complexity='Medium' }
    'Remote Desktop Services'           = @{ Intune='Settings Catalog > Remote Desktop Services';        Arc='Azure Bastion + Just-in-Time access (Defender for Servers)';                                Complexity='Medium' }
    'Drive Maps'                        = @{ Intune='Intune Scripts + Azure Files (or SharePoint)';      Arc='Not applicable on servers';                                                                 Complexity='High' }
    'Logon Scripts'                     = @{ Intune='Intune Platform Scripts / Remediation Scripts';     Arc='Azure Automation / Run Command';                                                            Complexity='High' }
    'Startup Scripts'                   = @{ Intune='Intune Platform Scripts / Remediation Scripts';     Arc='Azure Automation Runbook (scheduled / startup)';                                            Complexity='High' }

    # ----- Default for unknown extensions -----
    'DEFAULT'                           = @{ Intune='Manual review — no known mapping';                  Arc='Manual review — no known mapping';                                                          Complexity='High' }
}

function Resolve-MigrationTarget {
    param([string] $ExtensionName)

    if ([string]::IsNullOrWhiteSpace($ExtensionName)) {
        return $migrationMap['DEFAULT']
    }
    if ($migrationMap.ContainsKey($ExtensionName)) {
        return $migrationMap[$ExtensionName]
    }
    foreach ($k in $migrationMap.Keys) {
        if ($k -ne 'DEFAULT' -and $ExtensionName -like "*$k*") {
            return $migrationMap[$k]
        }
    }
    return $migrationMap['DEFAULT']
}

#endregion

#region --- Pre-load domain context --------------------------------------------

Write-Verbose 'Loading domain context...'
Get-ADDomain | Out-Null

# OU canonical-name -> DistinguishedName lookup (canonical paths match the GPO
# report XML SOMPath; DN is what Get-ADComputer -SearchBase needs).
$ouByCanonical = @{}
Get-ADOrganizationalUnit -Filter * -Properties CanonicalName |
    ForEach-Object { $ouByCanonical[$_.CanonicalName] = $_.DistinguishedName }

Write-Verbose "Loaded $($ouByCanonical.Count) OUs."

$allGpos = Get-GPO -All
Write-Verbose "Processing $($allGpos.Count) GPOs..."

#endregion

#region --- Helpers ------------------------------------------------------------

function Get-OuComputerCount {
    param([string] $OuDN)

    $result = [ordered]@{
        Workstation = 0
        Server      = 0
        Other       = 0
        Total       = 0
    }

    try {
        $computers = Get-ADComputer -SearchBase $OuDN -SearchScope OneLevel `
            -Filter * -Properties OperatingSystem -ErrorAction Stop
    }
    catch {
        return $result
    }

    foreach ($c in $computers) {
        $result.Total++
        $os = $c.OperatingSystem
        $matched = $false
        if ($os) {
            foreach ($p in $ServerOSPattern)      { if ($os -like $p) { $result.Server++;      $matched = $true; break } }
            if (-not $matched) {
                foreach ($p in $WorkstationOSPattern) { if ($os -like $p) { $result.Workstation++; $matched = $true; break } }
            }
        }
        if (-not $matched) { $result.Other++ }
    }
    return $result
}

function Test-OUNameMatch {
    param(
        [string]   $CanonicalPath,
        [string[]] $Patterns
    )
    foreach ($p in $Patterns) {
        if ($CanonicalPath -like $p) { return $true }
    }
    return $false
}

function Get-PlaneFromCount {
    param([hashtable] $Counts)

    if ($Counts.Total -eq 0) { return 'Unknown' }
    $wks = [int]$Counts.Workstation
    $srv = [int]$Counts.Server
    if ($wks -gt 0 -and $srv -eq 0) { return 'Intune' }
    if ($srv -gt 0 -and $wks -eq 0) { return 'Arc' }
    if ($wks -gt 0 -and $srv -gt 0) { return 'Both' }
    return 'Unknown'
}

function Get-PlaneFromName {
    param([string] $CanonicalPath)

    $isWks = Test-OUNameMatch -CanonicalPath $CanonicalPath -Patterns $WorkstationOUNamePattern
    $isSrv = Test-OUNameMatch -CanonicalPath $CanonicalPath -Patterns $ServerOUNamePattern
    if ($isWks -and -not $isSrv) { return 'Intune' }
    if ($isSrv -and -not $isWks) { return 'Arc' }
    if ($isWks -and $isSrv)      { return 'Both' }
    return 'Unknown'
}

function Resolve-GpoPlane {
    param([string[]] $LinkPlanes)

    if (-not $LinkPlanes -or $LinkPlanes.Count -eq 0) { return 'Unknown' }
    $set = @($LinkPlanes | Where-Object { $_ -ne 'Unknown' } | Select-Object -Unique)
    if ($set.Count -eq 0) { return 'Unknown' }
    if ($set.Count -eq 1) { return $set[0] }
    return 'Both'
}

#endregion

#region --- GPO loop ------------------------------------------------------------

foreach ($gpo in $allGpos) {

    $reportPath = Join-Path $tempDir "gpo-triage-$($gpo.Id).xml"
    $xml = $null
    $reportError = $null
    try {
        Get-GPOReport -Guid $gpo.Id -ReportType Xml -Path $reportPath -ErrorAction Stop
        $xml = [xml](Get-Content -Path $reportPath -Raw -ErrorAction Stop)
    }
    catch {
        $reportError = $_.Exception.Message
    }
    finally {
        Remove-Item -Path $reportPath -ErrorAction SilentlyContinue
    }

    # ---- Link classification -------------------------------------------------
    $links              = [System.Collections.Generic.List[object]]::new()
    $byOSPlanes         = [System.Collections.Generic.List[string]]::new()
    $byNamePlanes       = [System.Collections.Generic.List[string]]::new()

    if ($xml) {
        # Use PowerShell dot-notation (namespace-agnostic) instead of SelectNodes,
        # which requires a NamespaceManager for Get-GPOReport's default namespace.
        $linkNodes = @($xml.GPO.LinksTo)
        foreach ($link in $linkNodes) {
            $somType  = $link.SOMType
            $somPath  = $link.SOMPath

            $byOSPlane   = 'Unknown'
            $byNamePlane = 'Unknown'
            $ouCounts    = [ordered]@{ Workstation = 0; Server = 0; Other = 0; Total = 0 }

            if ($somType -eq 'OU') {
                if (-not $SkipComputerEnumeration -and $ouByCanonical.ContainsKey($somPath)) {
                    $ouCounts  = Get-OuComputerCount -OuDN $ouByCanonical[$somPath]
                    $byOSPlane = Get-PlaneFromCount -Counts $ouCounts
                }
                $byNamePlane = Get-PlaneFromName -CanonicalPath $somPath
            }
            elseif ($somType -eq 'Domain') {
                # Domain-root link applies to every Computer object; treat as Both.
                $byNamePlane = 'Both'
                if (-not $SkipComputerEnumeration) { $byOSPlane = 'Both' }
            }
            elseif ($somType -eq 'Site') {
                $byNamePlane = 'Both'
                if (-not $SkipComputerEnumeration) { $byOSPlane = 'Both' }
            }

            $links.Add([ordered]@{
                SOMType            = $somType
                SOMPath            = $somPath
                ByOuOSPredominance = $byOSPlane
                ByOuNameHeuristic  = $byNamePlane
                OuComputerCounts   = $ouCounts
            })
            $byOSPlanes.Add($byOSPlane)
            $byNamePlanes.Add($byNamePlane)
        }
    }

    $planeByOS   = Resolve-GpoPlane -LinkPlanes $byOSPlanes.ToArray()
    $planeByName = Resolve-GpoPlane -LinkPlanes $byNamePlanes.ToArray()
    $agreement   = ($planeByOS -eq $planeByName) -and ($planeByOS -ne 'Unknown')

    # ---- Extension walk (settings sizing) -----------------------------------
    $extSummary  = [System.Collections.Generic.List[object]]::new()
    $complexity  = @{ Low = 0; Medium = 0; High = 0 }

    if ($xml) {
        foreach ($section in 'Computer','User') {
            $sectionNode = $xml.GPO.$section
            if (-not $sectionNode) { continue }
            # Iterate ExtensionData (namespace-agnostic dot notation).
            # The human-readable name is on <ExtensionData><Name>, NOT on the
            # <Extension> child — $extData.Name gives "Security Settings" etc.
            $extDataNodes = @($sectionNode.ExtensionData)
            foreach ($extData in $extDataNodes) {
                $extName = [string]$extData.Name
                if ([string]::IsNullOrWhiteSpace($extName)) {
                    # Fall back to xsi:type on the Extension child if Name is missing.
                    $extChild = $extData.Extension
                    if ($extChild) {
                        $raw = $extChild.GetAttributeNS(
                            'http://www.w3.org/2001/XMLSchema-instance', 'type')
                        if ($raw -match ':(.+)$') { $extName = $Matches[1] }
                        elseif ($raw)             { $extName = $raw }
                    }
                }
                $map = Resolve-MigrationTarget -ExtensionName $extName
                $extSummary.Add([ordered]@{
                    Section       = $section
                    ExtensionName = $extName
                    IntuneTarget  = $map.Intune
                    ArcTarget     = $map.Arc
                    Complexity    = $map.Complexity
                })
                $complexity[$map.Complexity]++

                # Mirror into the detail artifact (one row per (GPO, Section, Extension)).
                $detail.Add([ordered]@{
                    GpoName       = $gpo.DisplayName
                    GpoId         = $gpo.Id.ToString()
                    Section       = $section
                    ExtensionName = $extName
                    IntuneTarget  = $map.Intune
                    ArcTarget     = $map.Arc
                    Complexity    = $map.Complexity
                })
            }
        }
    }

    # ---- Summary record -----------------------------------------------------
    $summaryRecord = [ordered]@{
        GpoName            = $gpo.DisplayName
        GpoId              = $gpo.Id.ToString()
        ReportError        = $reportError
        Classification     = [ordered]@{
            ByOuOSPredominance = $planeByOS
            ByOuNameHeuristic  = $planeByName
            Agreement          = $agreement
        }
        Links              = $links
        ExtensionCount     = $extSummary.Count
        ComplexityTally    = $complexity
        Extensions         = $extSummary
    }
    $summary.Add($summaryRecord)
}

#endregion

#region --- Output --------------------------------------------------------------

$summary | ConvertTo-Json -Depth 12 | Set-Content -Path $summaryPath -Encoding UTF8
$detail  | ConvertTo-Json -Depth 6  | Set-Content -Path $detailPath  -Encoding UTF8

# Cross-tab roll-up by classification plane (uses the OU OS predominance when
# available, otherwise falls back to the name heuristic).
$planeRollup = @{ Intune = 0; Arc = 0; Both = 0; Unknown = 0 }
foreach ($s in $summary) {
    $p = $s.Classification.ByOuOSPredominance
    if ($p -eq 'Unknown') { $p = $s.Classification.ByOuNameHeuristic }
    $planeRollup[$p]++
}
$disagreement = @($summary | Where-Object {
    -not $_.Classification.Agreement -and
    $_.Classification.ByOuOSPredominance -ne 'Unknown' -and
    $_.Classification.ByOuNameHeuristic  -ne 'Unknown'
}).Count

Write-Host "Triage complete."
Write-Host "  Summary : $summaryPath"
Write-Host "  Detail  : $detailPath"
Write-Host ''
Write-Host 'Plane roll-up (preferring OU OS predominance):'
Write-Host ('  Intune  : {0}' -f $planeRollup.Intune)
Write-Host ('  Arc     : {0}' -f $planeRollup.Arc)
Write-Host ('  Both    : {0}' -f $planeRollup.Both)
Write-Host ('  Unknown : {0}' -f $planeRollup.Unknown)
Write-Host ''
Write-Host ('Classifier disagreement (both available, planes differ): {0}' -f $disagreement)

#endregion
