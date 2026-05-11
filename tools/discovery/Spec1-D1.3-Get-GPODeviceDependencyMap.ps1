<#
.SYNOPSIS
    UIAO Spec 1 — D1.3: GPO-to-Device Dependency Map
.DESCRIPTION
    Exports every GPO linked to computer OUs and classifies each setting:
    1. Device-targeted vs. user-targeted vs. loopback processing
    2. Security filtering analysis (which groups apply/deny)
    3. WMI filter detection
    4. Intune Settings Catalog equivalent mapping (known patterns)
    5. Migration complexity assessment per GPO

    Outputs:
    - JSON for Quarto dashboard consumption
    - CSV for spreadsheet analysis
    - Markdown summary with migration recommendations

    Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.3
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER ComputerOUFilter
    Restrict analysis to GPOs linked to OUs matching this pattern.
    Default: all OUs containing computer objects.
.EXAMPLE
    .\Spec1-D1.3-Get-GPODeviceDependencyMap.ps1
    .\Spec1-D1.3-Get-GPODeviceDependencyMap.ps1 -OutputPath C:\exports
.NOTES
    Requires: GroupPolicy PowerShell module (RSAT)
    Requires: ActiveDirectory PowerShell module (RSAT)
    Requires: Read access to Group Policy Objects
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [string]$ComputerOUFilter
)

$ErrorActionPreference = "Stop"

# ── Prerequisites ──
foreach ($mod in @('GroupPolicy', 'ActiveDirectory')) {
    if (-not (Get-Module -ListAvailable -Name $mod)) {
        Write-Error "$mod module not found. Install RSAT."
        return
    }
    Import-Module $mod -ErrorAction Stop
}

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = (Get-ADDomain).DNSRoot
$outPrefix = "UIAO_Spec1_D1.3_GPODependencyMap_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 1 — D1.3: GPO-to-Device Dependency Map"             -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════
# Known GPO → Intune Mapping Patterns
# ══════════════════════════════════════════════════════════════

$intuneMap = @{
    # Security Settings
    'Account Policies'                 = @{ Intune = 'Endpoint Security > Account Protection'; Complexity = 'Low' }
    'Password Policy'                  = @{ Intune = 'Endpoint Security > Account Protection (or Entra ID Password Protection)'; Complexity = 'Low' }
    'Account Lockout Policy'           = @{ Intune = 'Endpoint Security > Account Protection'; Complexity = 'Low' }
    'Audit Policy'                     = @{ Intune = 'Settings Catalog > Audit'; Complexity = 'Medium' }
    'Advanced Audit Policy'            = @{ Intune = 'Settings Catalog > Audit'; Complexity = 'Medium' }
    'User Rights Assignment'           = @{ Intune = 'Settings Catalog > User Rights'; Complexity = 'Medium' }
    'Security Options'                 = @{ Intune = 'Settings Catalog > Local Policies Security Options'; Complexity = 'Medium' }
    'Windows Firewall'                 = @{ Intune = 'Endpoint Security > Firewall'; Complexity = 'Medium' }
    'AppLocker'                        = @{ Intune = 'Endpoint Security > Application Control (WDAC)'; Complexity = 'High' }
    'Software Restriction'             = @{ Intune = 'Endpoint Security > Application Control (WDAC)'; Complexity = 'High' }
    'BitLocker'                        = @{ Intune = 'Endpoint Security > Disk Encryption'; Complexity = 'Low' }

    # Administrative Templates — Computer
    'Windows Update'                   = @{ Intune = 'Windows Update for Business (WUfB) Update Rings'; Complexity = 'Low' }
    'Windows Update for Business'      = @{ Intune = 'Windows Update for Business (WUfB) Update Rings'; Complexity = 'Low' }
    'Windows Defender'                  = @{ Intune = 'Endpoint Security > Antivirus'; Complexity = 'Low' }
    'Microsoft Defender Antivirus'      = @{ Intune = 'Endpoint Security > Antivirus'; Complexity = 'Low' }
    'Microsoft Edge'                    = @{ Intune = 'Settings Catalog > Microsoft Edge'; Complexity = 'Low' }
    'Google Chrome'                     = @{ Intune = 'Settings Catalog > Google Chrome (ADMX ingestion)'; Complexity = 'Medium' }
    'OneDrive'                          = @{ Intune = 'Settings Catalog > OneDrive'; Complexity = 'Low' }
    'Remote Desktop'                    = @{ Intune = 'Settings Catalog > Remote Desktop Services'; Complexity = 'Medium' }
    'Power Management'                  = @{ Intune = 'Settings Catalog > Power'; Complexity = 'Low' }
    'Network'                           = @{ Intune = 'Settings Catalog > Network'; Complexity = 'Medium' }
    'Printers'                          = @{ Intune = 'Universal Print + Settings Catalog'; Complexity = 'High' }
    'Drive Maps'                        = @{ Intune = 'Intune Scripts + Azure Files (or SharePoint)'; Complexity = 'High' }
    'Logon Scripts'                     = @{ Intune = 'Intune Platform Scripts / Remediation Scripts'; Complexity = 'High' }
    'Startup Scripts'                   = @{ Intune = 'Intune Platform Scripts / Remediation Scripts'; Complexity = 'High' }
    'Folder Redirection'                = @{ Intune = 'OneDrive Known Folder Move (KFM)'; Complexity = 'Low' }

    # Group Policy Preferences
    'Registry'                          = @{ Intune = 'Settings Catalog (custom OMA-URI if needed)'; Complexity = 'Medium' }
    'Services'                          = @{ Intune = 'Settings Catalog > System Services'; Complexity = 'Medium' }
    'Scheduled Tasks'                   = @{ Intune = 'Intune Remediation Scripts'; Complexity = 'High' }
    'Environment Variables'             = @{ Intune = 'Intune Platform Scripts'; Complexity = 'Medium' }
    'Files'                             = @{ Intune = 'Intune Win32 App / Platform Scripts'; Complexity = 'High' }
    'Shortcuts'                         = @{ Intune = 'Intune Platform Scripts'; Complexity = 'Medium' }
    'INI Files'                         = @{ Intune = 'Intune Platform Scripts'; Complexity = 'Medium' }
    'Local Users and Groups'            = @{ Intune = 'Endpoint Security > Account Protection > Local Admin Password Solution'; Complexity = 'Medium' }
}

# ══════════════════════════════════════════════════════════════
# Step 1: Identify Computer OUs
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/5] Identifying OUs containing computer objects..." -ForegroundColor Yellow

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }

# Get all OUs that have computer objects
$allComputers = Get-ADComputer -Filter * -Properties DistinguishedName @adParams |
    ForEach-Object {
        $parts = $_.DistinguishedName -split ',', 2
        if ($parts.Count -gt 1) { $parts[1] }
    } |
    Sort-Object -Unique

$computerOUs = $allComputers | Where-Object { $_ -match '^OU=' }
if ($ComputerOUFilter) {
    $computerOUs = $computerOUs | Where-Object { $_ -match $ComputerOUFilter }
}

Write-Host "  Found $($computerOUs.Count) OUs containing computer objects" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Step 2: Get all GPOs and their links
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/5] Enumerating GPOs and link targets..." -ForegroundColor Yellow

$allGPOs = Get-GPO -All @adParams
Write-Host "  Found $($allGPOs.Count) GPOs in domain" -ForegroundColor Green

# Build GPO link map
$gpoLinks = [System.Collections.Generic.List[object]]::new()

foreach ($ou in $computerOUs) {
    try {
        $inheritance = Get-GPInheritance -Target $ou @adParams -ErrorAction SilentlyContinue
        if ($inheritance -and $inheritance.GpoLinks) {
            foreach ($link in $inheritance.GpoLinks) {
                $gpoLinks.Add([ordered]@{
                    OU          = $ou
                    GpoId       = $link.GpoId
                    DisplayName = $link.DisplayName
                    Enabled     = $link.Enabled
                    Enforced    = $link.Enforced
                    Order       = $link.Order
                })
            }
        }

        # Check inherited GPOs
        if ($inheritance -and $inheritance.InheritedGpoLinks) {
            foreach ($link in $inheritance.InheritedGpoLinks) {
                # Only add if not already present (avoid duplicates)
                $exists = $gpoLinks | Where-Object { $_.GpoId -eq $link.GpoId -and $_.OU -eq $ou }
                if (-not $exists) {
                    $gpoLinks.Add([ordered]@{
                        OU          = $ou
                        GpoId       = $link.GpoId
                        DisplayName = $link.DisplayName
                        Enabled     = $link.Enabled
                        Enforced    = $link.Enforced
                        Order       = $link.Order
                        Inherited   = $true
                    })
                }
            }
        }
    }
    catch {
        Write-Host "    WARN: Could not read inheritance for $ou — $($_.Exception.Message)" -ForegroundColor DarkYellow
    }
}

# Deduplicate by GPO ID (keep unique GPOs)
$uniqueGPOIds = @($gpoLinks | ForEach-Object { $_.GpoId } | Sort-Object -Unique)
Write-Host "  Found $($uniqueGPOIds.Count) unique GPOs linked to computer OUs" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Step 3: Analyze each GPO
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/5] Analyzing GPO settings and targeting..." -ForegroundColor Yellow

$gpoAnalysis = [System.Collections.Generic.List[object]]::new()
$counter = 0

foreach ($gpoId in $uniqueGPOIds) {
    $counter++
    if ($counter % 10 -eq 0) {
        Write-Progress -Activity "Analyzing GPOs" -Status "$counter / $($uniqueGPOIds.Count)" -PercentComplete (($counter / $uniqueGPOIds.Count) * 100)
    }

    $gpo = $allGPOs | Where-Object { $_.Id -eq $gpoId }
    if (-not $gpo) { continue }

    # Get GPO report as XML for detailed analysis
    $xmlReport = $null
    try {
        $xmlReport = [xml](Get-GPOReport -Guid $gpoId -ReportType XML @adParams)
    }
    catch {
        Write-Host "    WARN: Could not generate report for '$($gpo.DisplayName)'" -ForegroundColor DarkYellow
    }

    # Determine settings scope
    $hasComputerSettings = $false
    $hasUserSettings = $false
    $computerSettingCategories = [System.Collections.Generic.List[string]]::new()
    $userSettingCategories = [System.Collections.Generic.List[string]]::new()

    if ($xmlReport) {
        $ns = New-Object System.Xml.XmlNamespaceManager($xmlReport.NameTable)
        $ns.AddNamespace('gp', 'http://www.microsoft.com/GroupPolicy/Settings')
        $ns.AddNamespace('types', 'http://www.microsoft.com/GroupPolicy/Types')

        # Check computer configuration
        $compConfig = $xmlReport.SelectSingleNode('//gp:Computer', $ns)
        if ($compConfig) {
            $compEnabled = $compConfig.SelectSingleNode('gp:Enabled', $ns)
            if ($compEnabled -and $compEnabled.InnerText -eq 'true') {
                $extData = $compConfig.SelectNodes('.//gp:ExtensionData', $ns)
                if ($extData -and $extData.Count -gt 0) {
                    $hasComputerSettings = $true
                    foreach ($ext in $extData) {
                        $extName = $ext.SelectSingleNode('gp:Name', $ns)
                        if ($extName) {
                            $computerSettingCategories.Add($extName.InnerText)
                        }
                    }
                }
            }
        }

        # Check user configuration
        $userConfig = $xmlReport.SelectSingleNode('//gp:User', $ns)
        if ($userConfig) {
            $userEnabled = $userConfig.SelectSingleNode('gp:Enabled', $ns)
            if ($userEnabled -and $userEnabled.InnerText -eq 'true') {
                $extData = $userConfig.SelectNodes('.//gp:ExtensionData', $ns)
                if ($extData -and $extData.Count -gt 0) {
                    $hasUserSettings = $true
                    foreach ($ext in $extData) {
                        $extName = $ext.SelectSingleNode('gp:Name', $ns)
                        if ($extName) {
                            $userSettingCategories.Add($extName.InnerText)
                        }
                    }
                }
            }
        }
    }

    # Determine targeting type
    $targetingType = if ($hasComputerSettings -and $hasUserSettings) { "Mixed (Computer + User)" }
                     elseif ($hasComputerSettings) { "Computer Only" }
                     elseif ($hasUserSettings) { "User Only" }
                     else { "Empty / Disabled" }

    # Check for loopback processing
    $hasLoopback = $false
    $loopbackMode = $null
    if ($xmlReport) {
        $loopbackNode = $xmlReport.SelectSingleNode("//*[contains(text(),'LoopbackProcessingMode')]", $ns)
        if (-not $loopbackNode) {
            # Alternative check via raw XML text
            $rawXml = $xmlReport.OuterXml
            if ($rawXml -match 'User Group Policy Loopback Processing' -or $rawXml -match 'LoopbackProcessingMode') {
                $hasLoopback = $true
                if ($rawXml -match 'Replace') { $loopbackMode = 'Replace' }
                elseif ($rawXml -match 'Merge') { $loopbackMode = 'Merge' }
                else { $loopbackMode = 'Detected (mode unknown)' }
            }
        }
        else {
            $hasLoopback = $true
            $loopbackMode = 'Detected'
        }
    }

    # Security filtering
    $securityFiltering = [System.Collections.Generic.List[object]]::new()
    try {
        $gpoPerms = Get-GPPermission -Guid $gpoId -All @adParams -ErrorAction SilentlyContinue
        foreach ($perm in $gpoPerms) {
            if ($perm.Permission -eq 'GpoApply') {
                $securityFiltering.Add([ordered]@{
                    Trustee    = $perm.Trustee.Name
                    Type       = $perm.Trustee.SidType.ToString()
                    Permission = 'Apply'
                    Denied     = $perm.Denied
                })
            }
        }
    }
    catch { }

    # WMI filter
    $wmiFilter = $null
    if ($gpo.WmiFilter) {
        $wmiFilter = [ordered]@{
            Name  = $gpo.WmiFilter.Name
            Query = $gpo.WmiFilter.Query
        }
    }

    # Linked OUs for this GPO
    $linkedOUs = @($gpoLinks | Where-Object { $_.GpoId -eq $gpoId } |
        ForEach-Object { $_.OU } | Sort-Object -Unique)

    # Intune mapping for detected categories
    $intuneEquivalents = [System.Collections.Generic.List[object]]::new()
    $overallComplexity = 'Low'
    $allCategories = @($computerSettingCategories) + @($userSettingCategories)

    foreach ($cat in $allCategories) {
        $mapped = $false
        foreach ($key in $intuneMap.Keys) {
            if ($cat -match [regex]::Escape($key)) {
                $intuneEquivalents.Add([ordered]@{
                    GPOCategory     = $cat
                    IntuneEquivalent = $intuneMap[$key].Intune
                    Complexity       = $intuneMap[$key].Complexity
                })
                if ($intuneMap[$key].Complexity -eq 'High') { $overallComplexity = 'High' }
                elseif ($intuneMap[$key].Complexity -eq 'Medium' -and $overallComplexity -ne 'High') { $overallComplexity = 'Medium' }
                $mapped = $true
                break
            }
        }
        if (-not $mapped) {
            $intuneEquivalents.Add([ordered]@{
                GPOCategory      = $cat
                IntuneEquivalent = "Settings Catalog — manual mapping required"
                Complexity       = "Medium"
            })
            if ($overallComplexity -eq 'Low') { $overallComplexity = 'Medium' }
        }
    }

    # Migration priority
    $migrationPriority = if ($targetingType -eq 'Empty / Disabled') { 'None — can be deleted' }
                         elseif ($targetingType -eq 'Computer Only' -and $overallComplexity -eq 'Low') { 'High — straightforward migration' }
                         elseif ($targetingType -eq 'Computer Only') { 'Medium — requires mapping effort' }
                         elseif ($hasLoopback) { 'Medium — loopback requires device-targeted Intune policy' }
                         elseif ($targetingType -eq 'User Only') { 'Low — user targeting via Intune user groups' }
                         else { 'Medium — mixed targeting requires split into device + user policies' }

    $record = [ordered]@{
        # Identity
        DisplayName               = $gpo.DisplayName
        GpoId                     = $gpoId.ToString()
        GpoStatus                 = $gpo.GpoStatus.ToString()
        CreationTime              = $gpo.CreationTime.ToString("o")
        ModificationTime          = $gpo.ModificationTime.ToString("o")
        Description               = $gpo.Description

        # Targeting
        TargetingType             = $targetingType
        HasComputerSettings       = $hasComputerSettings
        HasUserSettings           = $hasUserSettings
        ComputerSettingCategories = @($computerSettingCategories)
        UserSettingCategories     = @($userSettingCategories)

        # Loopback
        HasLoopbackProcessing     = $hasLoopback
        LoopbackMode              = $loopbackMode

        # Filtering
        SecurityFiltering         = @($securityFiltering)
        WMIFilter                 = $wmiFilter

        # Linking
        LinkedComputerOUs         = $linkedOUs
        LinkedOUCount             = $linkedOUs.Count

        # Intune mapping
        IntuneEquivalents         = @($intuneEquivalents)
        OverallComplexity         = $overallComplexity
        MigrationPriority         = $migrationPriority
    }

    $gpoAnalysis.Add($record)
}

Write-Progress -Activity "Analyzing GPOs" -Completed

# ══════════════════════════════════════════════════════════════
# Step 4: Summary Statistics
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/5] Computing summary..." -ForegroundColor Yellow

$targetingDistribution = $gpoAnalysis |
    Group-Object -Property TargetingType |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Type = $_.Name; Count = $_.Count } }

$complexityDistribution = $gpoAnalysis |
    Where-Object { $_.TargetingType -ne 'Empty / Disabled' } |
    Group-Object -Property OverallComplexity |
    Sort-Object Count -Descending |
    ForEach-Object { [ordered]@{ Complexity = $_.Name; Count = $_.Count } }

$loopbackGPOs = @($gpoAnalysis | Where-Object { $_.HasLoopbackProcessing })
$emptyGPOs = @($gpoAnalysis | Where-Object { $_.TargetingType -eq 'Empty / Disabled' })
$wmiFilteredGPOs = @($gpoAnalysis | Where-Object { $_.WMIFilter })

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain           = $domain
        Timestamp        = (Get-Date).ToString("o")
        TotalGPOsInDomain = $allGPOs.Count
        GPOsLinkedToComputerOUs = $gpoAnalysis.Count
        ComputerOUsAnalyzed = $computerOUs.Count
        Script           = "UIAO Spec 1 D1.3 — GPO-to-Device Dependency Map"
        Reference        = "UIAO_136"
    }
    TargetingDistribution   = @($targetingDistribution)
    ComplexityDistribution  = @($complexityDistribution)
    Highlights = [ordered]@{
        LoopbackGPOs      = $loopbackGPOs.Count
        EmptyGPOs         = $emptyGPOs.Count
        WMIFilteredGPOs   = $wmiFilteredGPOs.Count
        ComputerOnlyGPOs  = ($gpoAnalysis | Where-Object { $_.TargetingType -eq 'Computer Only' }).Count
        UserOnlyGPOs      = ($gpoAnalysis | Where-Object { $_.TargetingType -eq 'User Only' }).Count
        MixedGPOs         = ($gpoAnalysis | Where-Object { $_.TargetingType -eq 'Mixed (Computer + User)' }).Count
        HighComplexity    = ($gpoAnalysis | Where-Object { $_.OverallComplexity -eq 'High' }).Count
    }
}

# ══════════════════════════════════════════════════════════════
# Step 5: Output
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/5] Writing output files..." -ForegroundColor Yellow

# JSON
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{ Summary = $summary; GPOs = @($gpoAnalysis) } |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "  JSON:     $jsonFile" -ForegroundColor Green

# CSV
$csvFile = Join-Path $OutputPath "${outPrefix}.csv"
$gpoAnalysis | ForEach-Object {
    [PSCustomObject]@{
        DisplayName           = $_.DisplayName
        GpoId                 = $_.GpoId
        TargetingType         = $_.TargetingType
        HasLoopback           = $_.HasLoopbackProcessing
        LoopbackMode          = $_.LoopbackMode
        OverallComplexity     = $_.OverallComplexity
        MigrationPriority     = $_.MigrationPriority
        ComputerCategories    = ($_.ComputerSettingCategories -join '; ')
        UserCategories        = ($_.UserSettingCategories -join '; ')
        LinkedOUCount         = $_.LinkedOUCount
        HasWMIFilter          = ($null -ne $_.WMIFilter)
        SecurityFilterCount   = $_.SecurityFiltering.Count
        GpoStatus             = $_.GpoStatus
        ModificationTime      = $_.ModificationTime
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV:      $csvFile" -ForegroundColor Green

# Console Dashboard
Write-Host "`n-- GPO-to-Device Dependency Map --" -ForegroundColor Cyan
Write-Host "  Total GPOs in domain:           $($allGPOs.Count)"
Write-Host "  GPOs linked to computer OUs:    $($gpoAnalysis.Count)"
Write-Host "  Computer OUs analyzed:          $($computerOUs.Count)"

Write-Host "`n-- Targeting Type --" -ForegroundColor Cyan
foreach ($t in $targetingDistribution) {
    $color = switch ($t.Type) {
        'Computer Only'              { 'Green' }
        'User Only'                  { 'Yellow' }
        'Mixed (Computer + User)'    { 'DarkYellow' }
        'Empty / Disabled'           { 'DarkGray' }
        default                      { 'Gray' }
    }
    Write-Host "  $($t.Count.ToString().PadLeft(4))  $($t.Type)" -ForegroundColor $color
}

Write-Host "`n-- Migration Complexity --" -ForegroundColor Cyan
foreach ($c in $complexityDistribution) {
    $color = switch ($c.Complexity) { 'Low' { 'Green' } 'Medium' { 'Yellow' } 'High' { 'Red' } default { 'Gray' } }
    Write-Host "  $($c.Count.ToString().PadLeft(4))  $($c.Complexity)" -ForegroundColor $color
}

Write-Host "`n-- Special Cases --" -ForegroundColor Cyan
Write-Host "  Loopback processing:   $($loopbackGPOs.Count)" -ForegroundColor $(if ($loopbackGPOs.Count -gt 0) { 'Yellow' } else { 'Green' })
Write-Host "  WMI filtered:          $($wmiFilteredGPOs.Count)"
Write-Host "  Empty/disabled:        $($emptyGPOs.Count) (cleanup candidates)"

if ($loopbackGPOs.Count -gt 0) {
    Write-Host "`n-- Loopback GPOs (migrate to device-targeted Intune policy) --" -ForegroundColor Yellow
    foreach ($lb in $loopbackGPOs) {
        Write-Host "    $($lb.DisplayName) ($($lb.LoopbackMode))" -ForegroundColor Yellow
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
