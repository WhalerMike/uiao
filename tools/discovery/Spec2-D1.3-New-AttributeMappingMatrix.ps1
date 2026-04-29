<#
.SYNOPSIS
    UIAO Spec 2 — D1.3: Attribute Mapping Matrix (HR → Entra ID)
.DESCRIPTION
    Generates the canonical attribute mapping matrix that defines how every
    HR source attribute maps to its Entra ID user property. This is the
    master reference for provisioning engine configuration (D3.4).

    The matrix covers:
    1. Core identity attributes (UPN, mail, displayName, name components)
    2. Organizational attributes (department, title, manager, company, division)
    3. Location attributes (city, state, country, office)
    4. HR-specific attributes (employeeId, employeeType, hireDate, termDate)
    5. OrgPath attributes (extensionAttribute1/2 per ADR-048)
    6. Provisioning control attributes (accountEnabled, usageLocation)

    For each mapping:
    - Source field name (HR-agnostic canonical name)
    - Entra ID target property (Graph API property name)
    - Transformation expression (Entra ID provisioning expression syntax)
    - Validation rules
    - Required/optional classification
    - JML lifecycle behavior (Joiner/Mover/Leaver impact)

    Can optionally consume D1.1 HR Attribute Discovery JSON to pre-populate
    population rates and data quality flags.

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.3
         ADR-048 (extensionAttribute1 = OrgPath)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER D1InputFile
    Path to D1.1 HR Attribute Discovery JSON for data quality enrichment.
    Optional.
.PARAMETER D2InputFile
    Path to D1.2 OrgPath Translation Rules JSON for OrgPath expression.
    Optional.
.EXAMPLE
    .\Spec2-D1.3-New-AttributeMappingMatrix.ps1
    .\Spec2-D1.3-New-AttributeMappingMatrix.ps1 -D1InputFile .\output\UIAO_Spec2_D1.1_HRAttributeDiscovery.json
.NOTES
    No AD/Entra connectivity required — generates canonical mapping specification.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$D1InputFile,
    [string]$D2InputFile
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 2 — D1.3: Attribute Mapping Matrix (HR to Entra ID)" -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Load optional D1.1 data ──
$d1Data = $null
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  Loading D1.1 HR attribute discovery for enrichment..." -ForegroundColor Yellow
    $d1Data = Get-Content $D1InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "  Loaded D1.1 data ($($d1Data.ExportMetadata.TotalUsers) users)" -ForegroundColor Green
}

# ── Load optional D1.2 OrgPath rules ──
$d2Data = $null
if ($D2InputFile -and (Test-Path $D2InputFile)) {
    Write-Host "  Loading D1.2 OrgPath translation rules..." -ForegroundColor Yellow
    $d2Data = Get-Content $D2InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host "  Loaded OrgPath schema" -ForegroundColor Green
}

# ══════════════════════════════════════════════════════════════
# Canonical Attribute Mapping Matrix
# ══════════════════════════════════════════════════════════════

$mappings = [System.Collections.Generic.List[object]]::new()

# Helper to get population rate from D1.1
function Get-PopRate {
    param([string]$ADAttribute)
    if (-not $d1Data -or -not $d1Data.HRAttributePopulation.$ADAttribute) { return $null }
    return $d1Data.HRAttributePopulation.$ADAttribute.PopulationRate
}

# ── Section 1: Core Identity ──

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 1
    HRCanonicalField = "employeeId"
    EntraIDProperty  = "employeeId"
    GraphAPIProperty = "employeeId"
    ADProperty       = "employeeID"
    DataType         = "String"
    MaxLength        = 1024
    Required         = $true
    Unique           = $true
    Expression       = "[employeeId]"
    Validation       = "Not null; unique across tenant; numeric or alphanumeric"
    JoinerBehavior   = "Set on creation — primary correlation key"
    MoverBehavior    = "Never changes — immutable HR identifier"
    LeaverBehavior   = "Retained on disabled account for audit trail"
    PopulationRate   = Get-PopRate 'EmployeeID'
    Notes            = "Primary HR-to-identity correlation key. Must be populated before provisioning can function."
})

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 2
    HRCanonicalField = "firstName"
    EntraIDProperty  = "givenName"
    GraphAPIProperty = "givenName"
    ADProperty       = "givenName"
    DataType         = "String"
    MaxLength        = 64
    Required         = $true
    Unique           = $false
    Expression       = "[firstName]"
    Validation       = "Not null; no leading/trailing whitespace"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated if legal name changes"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'GivenName'
    Notes            = "Legal first name from HR. Preferred name handling via displayName."
})

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 3
    HRCanonicalField = "lastName"
    EntraIDProperty  = "surname"
    GraphAPIProperty = "surname"
    ADProperty       = "sn"
    DataType         = "String"
    MaxLength        = 64
    Required         = $true
    Unique           = $false
    Expression       = "[lastName]"
    Validation       = "Not null; no leading/trailing whitespace"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated if legal name changes (marriage, etc.)"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Surname'
    Notes            = ""
})

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 4
    HRCanonicalField = "displayName"
    EntraIDProperty  = "displayName"
    GraphAPIProperty = "displayName"
    ADProperty       = "displayName"
    DataType         = "String"
    MaxLength        = 256
    Required         = $true
    Unique           = $false
    Expression       = 'Join(" ", [firstName], [lastName])'
    Validation       = "Not null"
    JoinerBehavior   = "Set on creation — derived from first + last"
    MoverBehavior    = "Updated on name change"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'DisplayName'
    Notes            = "If HR provides preferredName, use: IIF(IsPresent([preferredName]), Join(' ', [preferredName], [lastName]), Join(' ', [firstName], [lastName]))"
})

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 5
    HRCanonicalField = "(derived)"
    EntraIDProperty  = "userPrincipalName"
    GraphAPIProperty = "userPrincipalName"
    ADProperty       = "userPrincipalName"
    DataType         = "String"
    MaxLength        = 113
    Required         = $true
    Unique           = $true
    Expression       = 'Join("@", Join(".", ToLower([firstName]), ToLower([lastName])), "contoso.com")'
    Validation       = "Must be unique; valid email format; conflict resolution required (see D1.5)"
    JoinerBehavior   = "Generated on creation per UPN rules (D1.5)"
    MoverBehavior    = "Updated only on legal name change"
    LeaverBehavior   = "Retained (UPN is the immutable sign-in identifier)"
    PopulationRate   = Get-PopRate 'UserPrincipalName'
    Notes            = "UPN generation rules defined in D1.5. Conflict resolution: append incrementing number (john.smith2@). Domain suffix defined per environment."
})

$mappings.Add([ordered]@{
    Section          = "Core Identity"
    Order            = 6
    HRCanonicalField = "email"
    EntraIDProperty  = "mail"
    GraphAPIProperty = "mail"
    ADProperty       = "mail"
    DataType         = "String"
    MaxLength        = 256
    Required         = $true
    Unique           = $true
    Expression       = "[userPrincipalName]"
    Validation       = "Valid email format; typically equals UPN"
    JoinerBehavior   = "Set to UPN value on creation"
    MoverBehavior    = "Updated if UPN changes"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Mail'
    Notes            = "In most deployments, mail = UPN. Override from HR only if HR provides a distinct email."
})

# ── Section 2: Organizational ──

$mappings.Add([ordered]@{
    Section          = "Organizational"
    Order            = 10
    HRCanonicalField = "department"
    EntraIDProperty  = "department"
    GraphAPIProperty = "department"
    ADProperty       = "department"
    DataType         = "String"
    MaxLength        = 64
    Required         = $true
    Unique           = $false
    Expression       = "[department]"
    Validation       = "Not null; must match department taxonomy (D1.2)"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated on department change — triggers OrgPath recalculation and group cascade"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Department'
    Notes            = "Primary input to OrgPath department segment. Change triggers dynamic group re-evaluation."
})

$mappings.Add([ordered]@{
    Section          = "Organizational"
    Order            = 11
    HRCanonicalField = "jobTitle"
    EntraIDProperty  = "jobTitle"
    GraphAPIProperty = "jobTitle"
    ADProperty       = "title"
    DataType         = "String"
    MaxLength        = 128
    Required         = $false
    Unique           = $false
    Expression       = "[jobTitle]"
    Validation       = "Free text"
    JoinerBehavior   = "Set on creation if available"
    MoverBehavior    = "Updated on title change"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Title'
    Notes            = ""
})

$mappings.Add([ordered]@{
    Section          = "Organizational"
    Order            = 12
    HRCanonicalField = "managerId"
    EntraIDProperty  = "manager"
    GraphAPIProperty = "manager (navigation property)"
    ADProperty       = "manager (DN)"
    DataType         = "Reference"
    MaxLength        = $null
    Required         = $true
    Unique           = $false
    Expression       = 'Lookup(employeeId, [managerId], "user", "employeeId", "id")'
    Validation       = "Manager must exist in directory before direct report; referential integrity check"
    JoinerBehavior   = "Set after manager account exists — may require two-pass provisioning"
    MoverBehavior    = "Updated on manager change — critical for access reviews and approval chains"
    LeaverBehavior   = "Cleared (manager link removed on termination)"
    PopulationRate   = Get-PopRate 'Manager'
    Notes            = "Manager is a navigation property in Graph API, not a flat attribute. Requires the manager's Entra ID object ID, resolved via employeeId lookup."
})

$mappings.Add([ordered]@{
    Section          = "Organizational"
    Order            = 13
    HRCanonicalField = "company"
    EntraIDProperty  = "companyName"
    GraphAPIProperty = "companyName"
    ADProperty       = "company"
    DataType         = "String"
    MaxLength        = 64
    Required         = $false
    Unique           = $false
    Expression       = "[company]"
    Validation       = "Must match company taxonomy if used in OrgPath"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated on company change (inter-company transfer)"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Company'
    Notes            = "Used as OrgPath Company segment if multiple companies exist in tenant."
})

$mappings.Add([ordered]@{
    Section          = "Organizational"
    Order            = 14
    HRCanonicalField = "division"
    EntraIDProperty  = "onPremisesExtensionAttributes.extensionAttribute6"
    GraphAPIProperty = "onPremisesExtensionAttributes.extensionAttribute6"
    ADProperty       = "division"
    DataType         = "String"
    MaxLength        = 64
    Required         = $false
    Unique           = $false
    Expression       = "[division]"
    Validation       = "Must match division taxonomy if used in OrgPath"
    JoinerBehavior   = "Set on creation if available"
    MoverBehavior    = "Updated on division change"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Division'
    Notes            = "Entra ID has no native 'division' property. Maps to extensionAttribute6 (reserved outside ADR-048 OrgPath range 1-5)."
})

# ── Section 3: Location ──

$mappings.Add([ordered]@{
    Section          = "Location"
    Order            = 20
    HRCanonicalField = "city"
    EntraIDProperty  = "city"
    GraphAPIProperty = "city"
    ADProperty       = "l"
    DataType         = "String"
    MaxLength        = 128
    Required         = $true
    Unique           = $false
    Expression       = "[city]"
    Validation       = "Not null; consistent casing preferred"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated on location change — triggers OrgPath recalculation"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'City'
    Notes            = "Input to OrgPath City segment. Normalized to UPPERCASE in OrgPath calculation."
})

$mappings.Add([ordered]@{
    Section          = "Location"
    Order            = 21
    HRCanonicalField = "state"
    EntraIDProperty  = "state"
    GraphAPIProperty = "state"
    ADProperty       = "st"
    DataType         = "String"
    MaxLength        = 128
    Required         = $true
    Unique           = $false
    Expression       = "[state]"
    Validation       = "Use 2-letter state code for US; consistent format"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated on location change — triggers OrgPath region recalculation"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'State'
    Notes            = "Used for both OrgPath State segment and Region segment (via state-to-region lookup table in D1.2)."
})

$mappings.Add([ordered]@{
    Section          = "Location"
    Order            = 22
    HRCanonicalField = "country"
    EntraIDProperty  = "country"
    GraphAPIProperty = "country"
    ADProperty       = "co"
    DataType         = "String"
    MaxLength        = 128
    Required         = $false
    Unique           = $false
    Expression       = "[country]"
    Validation       = "ISO 3166 country name or 2-letter code"
    JoinerBehavior   = "Set on creation"
    MoverBehavior    = "Updated on international transfer"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'Country'
    Notes            = ""
})

$mappings.Add([ordered]@{
    Section          = "Location"
    Order            = 23
    HRCanonicalField = "officeLocation"
    EntraIDProperty  = "officeLocation"
    GraphAPIProperty = "officeLocation"
    ADProperty       = "physicalDeliveryOfficeName"
    DataType         = "String"
    MaxLength        = 128
    Required         = $false
    Unique           = $false
    Expression       = "[officeLocation]"
    Validation       = "Free text; building/floor/room"
    JoinerBehavior   = "Set on creation if available"
    MoverBehavior    = "Updated on office change"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'PhysicalDeliveryOfficeName'
    Notes            = ""
})

$mappings.Add([ordered]@{
    Section          = "Location"
    Order            = 24
    HRCanonicalField = "postalCode"
    EntraIDProperty  = "postalCode"
    GraphAPIProperty = "postalCode"
    ADProperty       = "postalCode"
    DataType         = "String"
    MaxLength        = 40
    Required         = $false
    Unique           = $false
    Expression       = "[postalCode]"
    Validation       = "Valid postal/ZIP code format"
    JoinerBehavior   = "Set on creation if available"
    MoverBehavior    = "Updated on location change"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'PostalCode'
    Notes            = ""
})

# ── Section 4: HR-Specific ──

$mappings.Add([ordered]@{
    Section          = "HR Lifecycle"
    Order            = 30
    HRCanonicalField = "employeeType"
    EntraIDProperty  = "employeeType"
    GraphAPIProperty = "employeeType"
    ADProperty       = "employeeType"
    DataType         = "String"
    MaxLength        = 1024
    Required         = $true
    Unique           = $false
    Expression       = "[employeeType]"
    Validation       = "Must match worker type taxonomy (D1.6): Employee, Contractor, Intern, etc."
    JoinerBehavior   = "Set on creation — drives license assignment and access scope"
    MoverBehavior    = "Updated on conversion (contractor to employee, etc.)"
    LeaverBehavior   = "Retained for audit"
    PopulationRate   = Get-PopRate 'EmployeeType'
    Notes            = "Worker type classification defined in D1.6. Drives dynamic group membership for license assignment."
})

$mappings.Add([ordered]@{
    Section          = "HR Lifecycle"
    Order            = 31
    HRCanonicalField = "hireDate"
    EntraIDProperty  = "employeeHireDate"
    GraphAPIProperty = "employeeHireDate"
    ADProperty       = "(not synced)"
    DataType         = "DateTimeOffset"
    MaxLength        = $null
    Required         = $true
    Unique           = $false
    Expression       = "[hireDate]"
    Validation       = "Valid ISO 8601 datetime; must be in the future for pre-hire provisioning"
    JoinerBehavior   = "Triggers Joiner workflow — account created N days before hire date"
    MoverBehavior    = "Not updated on moves"
    LeaverBehavior   = "Retained"
    PopulationRate   = $null
    Notes            = "Entra ID Lifecycle Workflows use employeeHireDate to trigger Joiner workflow. Pre-hire provisioning creates account in disabled state before start date."
})

$mappings.Add([ordered]@{
    Section          = "HR Lifecycle"
    Order            = 32
    HRCanonicalField = "terminationDate"
    EntraIDProperty  = "employeeLeaveDateTime"
    GraphAPIProperty = "employeeLeaveDateTime"
    ADProperty       = "(not synced)"
    DataType         = "DateTimeOffset"
    MaxLength        = $null
    Required         = $false
    Unique           = $false
    Expression       = "[terminationDate]"
    Validation       = "Valid ISO 8601 datetime; null for active employees"
    JoinerBehavior   = "Not set"
    MoverBehavior    = "Not updated"
    LeaverBehavior   = "Set by HR — triggers Leaver workflow (disable, revoke, archive)"
    PopulationRate   = $null
    Notes            = "Entra ID Lifecycle Workflows use employeeLeaveDateTime to trigger Leaver workflow. Account disabled on term date, deleted after retention period."
})

# ── Section 5: OrgPath (ADR-048) ──

$orgPathExpression = if ($d2Data -and $d2Data.TranslationRules.CalculationExpression) {
    $d2Data.TranslationRules.CalculationExpression
} else {
    'Join("/", "CORP", Switch([state], "UNKNOWN", "MD", "EAST", "VA", "EAST"), ToUpper([state]), ToUpper(Replace([city], " ", "_")), ToUpper(Replace([department], " ", "_")))'
}

$mappings.Add([ordered]@{
    Section          = "OrgPath (ADR-048)"
    Order            = 40
    HRCanonicalField = "(calculated)"
    EntraIDProperty  = "onPremisesExtensionAttributes.extensionAttribute1"
    GraphAPIProperty = "onPremisesExtensionAttributes.extensionAttribute1"
    ADProperty       = "extensionAttribute1"
    DataType         = "String"
    MaxLength        = 1024
    Required         = $true
    Unique           = $false
    Expression       = $orgPathExpression
    Validation       = "Must match OrgPath format: SEGMENT/SEGMENT/... All uppercase, / separator, no special chars except underscore"
    JoinerBehavior   = "Calculated and set on creation from HR attributes"
    MoverBehavior    = "Recalculated on any input change (department, city, state, company, division) — triggers dynamic group cascade"
    LeaverBehavior   = "Retained on disabled account"
    PopulationRate   = Get-PopRate 'extensionAttribute1'
    Notes            = "ADR-048 designates extensionAttribute1 for OrgPath. This is the most impactful attribute — it drives dynamic groups, AUs, CA, Intune scope tags. See D1.2 for full schema definition."
})

$mappings.Add([ordered]@{
    Section          = "OrgPath (ADR-048)"
    Order            = 41
    HRCanonicalField = "(calculated)"
    EntraIDProperty  = "onPremisesExtensionAttributes.extensionAttribute2"
    GraphAPIProperty = "onPremisesExtensionAttributes.extensionAttribute2"
    ADProperty       = "extensionAttribute2"
    DataType         = "String"
    MaxLength        = 1024
    Required         = $false
    Unique           = $false
    Expression       = 'Count(Split([extensionAttribute1], "/"))'
    Validation       = "Positive integer as string"
    JoinerBehavior   = "Calculated from OrgPath depth"
    MoverBehavior    = "Recalculated when OrgPath changes"
    LeaverBehavior   = "Retained"
    PopulationRate   = Get-PopRate 'extensionAttribute2'
    Notes            = "OrgPath depth level — enables filtering by hierarchy depth (e.g., all Level 3+ orgs)."
})

# ── Section 6: Provisioning Control ──

$mappings.Add([ordered]@{
    Section          = "Provisioning Control"
    Order            = 50
    HRCanonicalField = "(derived from hireDate/terminationDate)"
    EntraIDProperty  = "accountEnabled"
    GraphAPIProperty = "accountEnabled"
    ADProperty       = "userAccountControl"
    DataType         = "Boolean"
    MaxLength        = $null
    Required         = $true
    Unique           = $false
    Expression       = 'IIF([terminationDate] > Now() OR IsNullOrEmpty([terminationDate]), True, False)'
    Validation       = "Boolean"
    JoinerBehavior   = "True on hire date (or False before hire date for pre-provisioning)"
    MoverBehavior    = "Not changed"
    LeaverBehavior   = "Set to False on termination date"
    PopulationRate   = 100
    Notes            = "Lifecycle Workflows control enable/disable based on hire and term dates."
})

$mappings.Add([ordered]@{
    Section          = "Provisioning Control"
    Order            = 51
    HRCanonicalField = "countryCode"
    EntraIDProperty  = "usageLocation"
    GraphAPIProperty = "usageLocation"
    ADProperty       = "msExchUsageLocation"
    DataType         = "String"
    MaxLength        = 2
    Required         = $true
    Unique           = $false
    Expression       = 'Switch([country], "US", "United States", "US", "Canada", "CA", "UK", "GB", "United Kingdom", "GB")'
    Validation       = "ISO 3166-1 alpha-2 country code; required for license assignment"
    JoinerBehavior   = "Set on creation — must be set before license assignment"
    MoverBehavior    = "Updated on international transfer"
    LeaverBehavior   = "Retained"
    PopulationRate   = $null
    Notes            = "usageLocation must be set before any M365 license can be assigned via group-based licensing. The Switch() expression must be expanded for all countries in scope."
})

$mappings.Add([ordered]@{
    Section          = "Provisioning Control"
    Order            = 52
    HRCanonicalField = "phone"
    EntraIDProperty  = "mobilePhone"
    GraphAPIProperty = "mobilePhone"
    ADProperty       = "mobile"
    DataType         = "String"
    MaxLength        = 64
    Required         = $false
    Unique           = $false
    Expression       = "[phone]"
    Validation       = "E.164 format preferred (+1xxxxxxxxxx)"
    JoinerBehavior   = "Set on creation if available"
    MoverBehavior    = "Updated on change"
    LeaverBehavior   = "Cleared"
    PopulationRate   = Get-PopRate 'Mobile'
    Notes            = "Used for MFA phone registration. If HR provides, avoids user self-registration step."
})

# ══════════════════════════════════════════════════════════════
# Output
# ══════════════════════════════════════════════════════════════
Write-Host "`n  Writing output files..." -ForegroundColor Yellow

$outPrefix = "UIAO_Spec2_D1.3_AttributeMappingMatrix_${timestamp}"

# Summary
$sections = $mappings | Group-Object -Property Section
$sectionSummary = $sections | ForEach-Object {
    [ordered]@{
        Section    = $_.Name
        Attributes = $_.Count
        Required   = ($_.Group | Where-Object { $_.Required }).Count
        Optional   = ($_.Group | Where-Object { -not $_.Required }).Count
    }
}

$summary = [ordered]@{
    ExportMetadata = [ordered]@{
        Timestamp        = (Get-Date).ToString("o")
        TotalMappings    = $mappings.Count
        RequiredFields   = ($mappings | Where-Object { $_.Required }).Count
        OptionalFields   = ($mappings | Where-Object { -not $_.Required }).Count
        Script           = "UIAO Spec 2 D1.3 — Attribute Mapping Matrix"
        Reference        = "UIAO_136, ADR-048"
        D1_1_Source      = if ($D1InputFile) { $D1InputFile } else { "Not provided" }
        D1_2_Source      = if ($D2InputFile) { $D2InputFile } else { "Not provided" }
    }
    Sections = @($sectionSummary)
}

# JSON
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
[ordered]@{ Summary = $summary; Mappings = @($mappings) } |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "  JSON: $jsonFile" -ForegroundColor Green

# CSV
$csvFile = Join-Path $OutputPath "${outPrefix}.csv"
$mappings | ForEach-Object {
    [PSCustomObject]@{
        Section          = $_.Section
        Order            = $_.Order
        HRCanonicalField = $_.HRCanonicalField
        EntraIDProperty  = $_.EntraIDProperty
        GraphAPIProperty = $_.GraphAPIProperty
        ADProperty       = $_.ADProperty
        DataType         = $_.DataType
        MaxLength        = $_.MaxLength
        Required         = $_.Required
        Unique           = $_.Unique
        Expression       = $_.Expression
        Validation       = $_.Validation
        JoinerBehavior   = $_.JoinerBehavior
        MoverBehavior    = $_.MoverBehavior
        LeaverBehavior   = $_.LeaverBehavior
        PopulationRate   = $_.PopulationRate
        Notes            = $_.Notes
    }
} | Export-Csv -Path $csvFile -NoTypeInformation -Encoding utf8NoBOM
Write-Host "  CSV:  $csvFile" -ForegroundColor Green

# Console
Write-Host "`n-- Attribute Mapping Matrix Summary --" -ForegroundColor Cyan
Write-Host "  Total mappings:   $($mappings.Count)"
Write-Host "  Required:         $(($mappings | Where-Object { $_.Required }).Count)"
Write-Host "  Optional:         $(($mappings | Where-Object { -not $_.Required }).Count)"

Write-Host "`n-- Sections --" -ForegroundColor Cyan
foreach ($s in $sectionSummary) {
    Write-Host "  $($s.Attributes.ToString().PadLeft(3)) attributes  $($s.Section) ($($s.Required) required)"
}

# Data quality flags from D1.1
if ($d1Data) {
    Write-Host "`n-- Data Quality (from D1.1) --" -ForegroundColor Cyan
    $lowPopulation = $mappings | Where-Object { $_.Required -and $_.PopulationRate -ne $null -and $_.PopulationRate -lt 70 }
    if ($lowPopulation) {
        foreach ($lp in $lowPopulation) {
            Write-Host "  ! $($lp.HRCanonicalField) -> $($lp.EntraIDProperty): $($lp.PopulationRate)% populated (REQUIRED)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "  All required attributes have adequate population rates" -ForegroundColor Green
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
