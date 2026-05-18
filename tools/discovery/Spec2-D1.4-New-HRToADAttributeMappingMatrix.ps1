<#
.SYNOPSIS
    UIAO Spec 2 — D1.4: HR-to-On-Prem AD Attribute Mapping Matrix
.DESCRIPTION
    Generates a complete attribute mapping matrix documenting how HR system
    attributes map to on-premises Active Directory user properties during the
    coexistence period. This is the bridge document between legacy AD
    provisioning and the cloud-native API-driven model (ADR-003).

    Produces:
    1. Canonical Mapping Matrix — 22+ HR attributes mapped to AD properties
       with transformation expressions, provisioning behavior, and JML
       (Joiner/Mover/Leaver) lifecycle semantics
    2. Current-State Audit — Examines actual AD population rates for each
       mapped attribute to establish baseline quality
    3. OrgPath Mapping — extensionAttribute1/2 mapping per ADR-048
    4. Coexistence Rules — Documents which attributes flow AD→Entra,
       Entra→AD, or are cloud-only during transition
    5. Gap Analysis — Identifies unmapped HR attributes, AD attributes with
       no HR source, and conflicting mappings

    Output: JSON for Quarto dashboard + Markdown mapping specification

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.4
         ADR-003 (API-Driven Inbound Provisioning)
         ADR-048 (extensionAttribute1 = OrgPath)
         Feeds: D1.5 (UPN Generation Rules)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER DomainController
    Target a specific DC. If omitted, uses auto-discovery.
.PARAMETER SampleSize
    Number of user objects to sample for population rate audit.
    Default: 500. Use 0 for full domain scan.
.PARAMETER D1InputFile
    Optional path to D1.1 HR Attribute Discovery JSON for cross-reference.
.EXAMPLE
    .\Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1
    .\Spec2-D1.4-New-HRToADAttributeMappingMatrix.ps1 -SampleSize 0
.NOTES
    Requires: ActiveDirectory PowerShell module (RSAT)
    No HR system connectivity required — produces the canonical mapping
    specification plus AD-side population audit.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [int]$SampleSize = 500,
    [string]$D1InputFile
)

$ErrorActionPreference = "Stop"

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT."
    return
}
Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = (Get-ADDomain).DNSRoot
$outPrefix = "UIAO_Spec2_D1.4_HRToADMapping_${domain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 2 — D1.4: HR-to-AD Attribute Mapping Matrix"        -ForegroundColor Cyan
Write-Host "  Domain:    $domain"                                            -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

$adParams = @{}
if ($DomainController) { $adParams['Server'] = $DomainController }

# ══════════════════════════════════════════════════════════════
# Section 1: Canonical Attribute Mapping Matrix
# ══════════════════════════════════════════════════════════════
Write-Host "  [1/5] Building canonical attribute mapping matrix..." -ForegroundColor Yellow

# The canonical mapping — this IS the deliverable specification
$mappingMatrix = @(
    # --- Section A: Core Identity ---
    [ordered]@{
        Section            = "A. Core Identity"
        HRAttribute        = "Employee ID"
        HRDescription      = "Unique identifier assigned by HR system"
        ADAttribute        = "employeeID"
        ADLdapName         = "employeeID"
        EntraAttribute     = "employeeId"
        TransformExpression = '[HR.EmployeeID]'
        Writeback          = $false
        JML_Joiner         = "SET — from HR source"
        JML_Mover          = "NO CHANGE — immutable identifier"
        JML_Leaver         = "RETAIN — required for audit trail"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID (direct)"
        Notes              = "Primary join/match attribute between HR and AD. Must be unique. Never reused."
    },
    [ordered]@{
        Section            = "A. Core Identity"
        HRAttribute        = "Employee Number"
        HRDescription      = "Alternate HR system identifier (payroll ID, badge number)"
        ADAttribute        = "employeeNumber"
        ADLdapName         = "employeeNumber"
        EntraAttribute     = "employeeId (if employeeID unused)"
        TransformExpression = '[HR.EmployeeNumber]'
        Writeback          = $false
        JML_Joiner         = "SET — from HR source"
        JML_Mover          = "NO CHANGE"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Use employeeID as primary. employeeNumber is secondary/legacy."
    },
    [ordered]@{
        Section            = "A. Core Identity"
        HRAttribute        = "Worker Type"
        HRDescription      = "Employment classification: Employee, Contractor, Intern, etc."
        ADAttribute        = "employeeType"
        ADLdapName         = "employeeType"
        EntraAttribute     = "employeeType"
        TransformExpression = 'Switch([HR.WorkerType], "FTE", "Employee", "CW", "Contractor", "INT", "Intern", "VOL", "Volunteer")'
        Writeback          = $false
        JML_Joiner         = "SET — determines license, access scope, retention"
        JML_Mover          = "UPDATE — if worker type changes (conversion)"
        JML_Leaver         = "NO CHANGE — retained through offboarding"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Drives D1.6 Worker Type Classification Taxonomy. Affects license assignment and group membership."
    },

    # --- Section B: Name Attributes ---
    [ordered]@{
        Section            = "B. Name Attributes"
        HRAttribute        = "Legal First Name"
        HRDescription      = "Legal given name from HR system"
        ADAttribute        = "givenName"
        ADLdapName         = "givenName"
        EntraAttribute     = "givenName"
        TransformExpression = '[HR.LegalFirstName]'
        Writeback          = $false
        JML_Joiner         = "SET — from HR source"
        JML_Mover          = "UPDATE — on legal name change"
        JML_Leaver         = "NO CHANGE"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Legal name for compliance. Preferred/display name may differ."
    },
    [ordered]@{
        Section            = "B. Name Attributes"
        HRAttribute        = "Legal Last Name"
        HRDescription      = "Legal surname from HR system"
        ADAttribute        = "sn"
        ADLdapName         = "sn"
        EntraAttribute     = "surname"
        TransformExpression = '[HR.LegalLastName]'
        Writeback          = $false
        JML_Joiner         = "SET — from HR source"
        JML_Mover          = "UPDATE — on legal name change"
        JML_Leaver         = "NO CHANGE"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Surname. Combined with givenName for displayName generation."
    },
    [ordered]@{
        Section            = "B. Name Attributes"
        HRAttribute        = "Preferred First Name"
        HRDescription      = "Employee's preferred/chosen first name"
        ADAttribute        = "displayName (component)"
        ADLdapName         = "displayName"
        EntraAttribute     = "displayName"
        TransformExpression = 'IIF(IsPresent([HR.PreferredFirstName]), Join(" ", [HR.PreferredFirstName], [HR.LegalLastName]), Join(" ", [HR.LegalFirstName], [HR.LegalLastName]))'
        Writeback          = $false
        JML_Joiner         = "SET — preferred name if available, else legal"
        JML_Mover          = "UPDATE — on name change"
        JML_Leaver         = "NO CHANGE"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "displayName uses preferred name when present. UPN may also use preferred name per D1.5 rules."
    },

    # --- Section C: UPN & Login ---
    [ordered]@{
        Section            = "C. UPN & Login"
        HRAttribute        = "(Computed)"
        HRDescription      = "Generated from name attributes per D1.5 UPN Generation Rules"
        ADAttribute        = "userPrincipalName"
        ADLdapName         = "userPrincipalName"
        EntraAttribute     = "userPrincipalName"
        TransformExpression = 'Join("@", Join(".", IIF(IsPresent([HR.PreferredFirstName]), [HR.PreferredFirstName], [HR.LegalFirstName]), [HR.LegalLastName]), "contoso.com")'
        Writeback          = $false
        JML_Joiner         = "SET — generated per D1.5 rules with collision detection"
        JML_Mover          = "CONDITIONAL — update on name change (with alias retention)"
        JML_Leaver         = "BLOCK SIGN-IN — UPN retained for audit, account disabled"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "See D1.5 for full UPN generation rules. Collision resolution appends incrementing number."
    },
    [ordered]@{
        Section            = "C. UPN & Login"
        HRAttribute        = "(Computed)"
        HRDescription      = "Legacy pre-Windows 2000 logon name"
        ADAttribute        = "sAMAccountName"
        ADLdapName         = "sAMAccountName"
        EntraAttribute     = "onPremisesSamAccountName (read-only)"
        TransformExpression = 'Left(Join(".", IIF(IsPresent([HR.PreferredFirstName]), Left([HR.PreferredFirstName], 1), Left([HR.LegalFirstName], 1)), [HR.LegalLastName]), 20)'
        Writeback          = $false
        JML_Joiner         = "SET — generated, max 20 chars, collision detection"
        JML_Mover          = "NO CHANGE — legacy identifier, never updated"
        JML_Leaver         = "RETAIN — required for legacy system compatibility"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID (read-only sync)"
        PostMigrationFlow  = "ELIMINATED — cloud-native accounts use UPN only"
        Notes              = "sAMAccountName is AD-only. Post-migration, new cloud-native accounts will not have sAMAccountName."
    },

    # --- Section D: Organizational Attributes ---
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Department"
        HRDescription      = "Department name from HR org structure"
        ADAttribute        = "department"
        ADLdapName         = "department"
        EntraAttribute     = "department"
        TransformExpression = '[HR.Department]'
        Writeback          = $false
        JML_Joiner         = "SET — from HR source"
        JML_Mover          = "UPDATE — on department transfer"
        JML_Leaver         = "RETAIN — for offboarding audit"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Component of OrgPath (ADR-048). Feeds dynamic group membership."
    },
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Division"
        HRDescription      = "Division or business unit"
        ADAttribute        = "division"
        ADLdapName         = "division"
        EntraAttribute     = "extension attribute or custom"
        TransformExpression = '[HR.Division]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE — on transfer"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "May be component of OrgPath depending on org hierarchy depth."
    },
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Company"
        HRDescription      = "Legal entity / company name"
        ADAttribute        = "company"
        ADLdapName         = "company"
        EntraAttribute     = "companyName"
        TransformExpression = '[HR.Company]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE — on entity transfer"
        JML_Leaver         = "RETAIN"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Top-level OrgPath component in multi-entity organizations."
    },
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Job Title"
        HRDescription      = "Job title from HR system"
        ADAttribute        = "title"
        ADLdapName         = "title"
        EntraAttribute     = "jobTitle"
        TransformExpression = '[HR.JobTitle]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE — on role change"
        JML_Leaver         = "RETAIN"
        Required           = $true
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Informational. May drive access reviews or role-based group membership."
    },
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Manager Employee ID"
        HRDescription      = "Employee ID of the user's manager in HR"
        ADAttribute        = "manager"
        ADLdapName         = "manager"
        EntraAttribute     = "manager (relationship)"
        TransformExpression = 'LookupDN([HR.ManagerEmployeeID], "employeeID", "distinguishedName")'
        Writeback          = $false
        JML_Joiner         = "SET — resolved to AD DN via employeeID lookup"
        JML_Mover          = "UPDATE — on manager change"
        JML_Leaver         = "CLEAR — manager relationship removed on termination"
        Required           = $true
        CoexistenceFlow    = "HR → Provisioning Engine → AD (DN lookup) → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID (ObjectId lookup)"
        Notes              = "AD stores manager as DN. Entra stores as ObjectId. Provisioning engine must resolve. Manager must exist in AD before the report can be linked."
    },
    [ordered]@{
        Section            = "D. Organizational"
        HRAttribute        = "Cost Center"
        HRDescription      = "Financial cost center code"
        ADAttribute        = "extensionAttribute3"
        ADLdapName         = "extensionAttribute3"
        EntraAttribute     = "onPremisesExtensionAttributes.extensionAttribute3"
        TransformExpression = '[HR.CostCenter]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE — on transfer"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Financial attribute. extensionAttribute3 chosen to avoid OrgPath collision (ea1=OrgPath, ea2=OrgPathDepth per ADR-048)."
    },

    # --- Section E: Location ---
    [ordered]@{
        Section            = "E. Location"
        HRAttribute        = "Work Location / Office"
        HRDescription      = "Physical office location"
        ADAttribute        = "physicalDeliveryOfficeName"
        ADLdapName         = "physicalDeliveryOfficeName"
        EntraAttribute     = "officeLocation"
        TransformExpression = '[HR.OfficeLocation]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE — on location change"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "OrgPath REGION/STATE/CITY components derived from this. Feeds location-based Conditional Access."
    },
    [ordered]@{
        Section            = "E. Location"
        HRAttribute        = "Work State/Province"
        HRDescription      = "State or province of work location"
        ADAttribute        = "st"
        ADLdapName         = "st"
        EntraAttribute     = "state"
        TransformExpression = '[HR.WorkState]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "OrgPath STATE component."
    },
    [ordered]@{
        Section            = "E. Location"
        HRAttribute        = "Work City"
        HRDescription      = "City of work location"
        ADAttribute        = "l"
        ADLdapName         = "l"
        EntraAttribute     = "city"
        TransformExpression = '[HR.WorkCity]'
        Writeback          = $false
        JML_Joiner         = "SET"
        JML_Mover          = "UPDATE"
        JML_Leaver         = "RETAIN"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "OrgPath CITY component."
    },
    [ordered]@{
        Section            = "E. Location"
        HRAttribute        = "Work Country"
        HRDescription      = "Country code (ISO 3166-1 alpha-2)"
        ADAttribute        = "c / co / countryCode"
        ADLdapName         = "c"
        EntraAttribute     = "country / usageLocation"
        TransformExpression = '[HR.WorkCountry]'
        Writeback          = $false
        JML_Joiner         = "SET — also sets usageLocation for license assignment"
        JML_Mover          = "UPDATE"
        JML_Leaver         = "RETAIN"
        Required           = $true
        CoexistenceFlow    = "HR → AD (c, co, countryCode) → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID (country + usageLocation)"
        Notes              = "CRITICAL for M365 license assignment. usageLocation must be set before license can be assigned. AD has 3 country fields (c=2-letter, co=full name, countryCode=numeric)."
    },

    # --- Section F: OrgPath (ADR-048) ---
    [ordered]@{
        Section            = "F. OrgPath (ADR-048)"
        HRAttribute        = "(Computed from Company/Region/State/City/Dept)"
        HRDescription      = "Deterministic organizational path replacing OU tree"
        ADAttribute        = "extensionAttribute1"
        ADLdapName         = "extensionAttribute1"
        EntraAttribute     = "onPremisesExtensionAttributes.extensionAttribute1"
        TransformExpression = 'Join("/", [HR.Company], IIF(IsPresent([HR.Region]), [HR.Region], "HQ"), [HR.WorkState], [HR.WorkCity], [HR.Department])'
        Writeback          = $false
        JML_Joiner         = "SET — computed from HR organizational attributes"
        JML_Mover          = "UPDATE — recomputed on any component change (dept, location, etc.)"
        JML_Leaver         = "RETAIN — required for offboarding scope and audit"
        Required           = $true
        CoexistenceFlow    = "HR → Provisioning Engine (compute) → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning (compute) → Entra ID"
        Notes              = "ADR-048: extensionAttribute1 is the canonical OrgPath attribute. Single most cross-cutting attribute — drives dynamic groups, AUs, CA device filters, Intune scope tags, and HR provisioning mapping."
    },
    [ordered]@{
        Section            = "F. OrgPath (ADR-048)"
        HRAttribute        = "(Computed)"
        HRDescription      = "Depth level of the OrgPath hierarchy"
        ADAttribute        = "extensionAttribute2"
        ADLdapName         = "extensionAttribute2"
        EntraAttribute     = "onPremisesExtensionAttributes.extensionAttribute2"
        TransformExpression = 'Count(Split([OrgPath], "/"))'
        Writeback          = $false
        JML_Joiner         = "SET — computed from OrgPath"
        JML_Mover          = "UPDATE — recomputed when OrgPath changes"
        JML_Leaver         = "RETAIN"
        Required           = $true
        CoexistenceFlow    = "Provisioning Engine (compute) → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "API Provisioning (compute) → Entra ID"
        Notes              = "ADR-048: extensionAttribute2 = OrgPath depth. Enables dynamic group rules like depth >= 3 for regional scoping."
    },

    # --- Section G: Contact Information ---
    [ordered]@{
        Section            = "G. Contact Information"
        HRAttribute        = "Work Email"
        HRDescription      = "Corporate email address"
        ADAttribute        = "mail"
        ADLdapName         = "mail"
        EntraAttribute     = "mail"
        TransformExpression = '[Computed.UPN] or [HR.WorkEmail]'
        Writeback          = $true
        JML_Joiner         = "SET — typically matches UPN"
        JML_Mover          = "UPDATE — if UPN changes"
        JML_Leaver         = "RETAIN — required for mailbox retention"
        Required           = $true
        CoexistenceFlow    = "AD → Entra Connect → Entra ID (Exchange Online manages)"
        PostMigrationFlow  = "Entra ID / Exchange Online (authoritative)"
        Notes              = "In hybrid Exchange, mail is managed by Exchange. Post-migration, Exchange Online is authoritative."
    },
    [ordered]@{
        Section            = "G. Contact Information"
        HRAttribute        = "Work Phone"
        HRDescription      = "Office telephone number"
        ADAttribute        = "telephoneNumber"
        ADLdapName         = "telephoneNumber"
        EntraAttribute     = "businessPhones"
        TransformExpression = '[HR.WorkPhone]'
        Writeback          = $false
        JML_Joiner         = "SET — if available from HR"
        JML_Mover          = "UPDATE"
        JML_Leaver         = "CLEAR"
        Required           = $false
        CoexistenceFlow    = "HR → AD → Entra Connect → Entra ID"
        PostMigrationFlow  = "HR → API Provisioning → Entra ID"
        Notes              = "Optional. May also be populated from Teams/telephony system."
    },

    # --- Section H: OU Placement (Coexistence Only) ---
    [ordered]@{
        Section            = "H. OU Placement (Coexistence)"
        HRAttribute        = "(Computed from OrgPath)"
        HRDescription      = "Target OU in AD derived from OrgPath components"
        ADAttribute        = "distinguishedName (OU component)"
        ADLdapName         = "distinguishedName"
        EntraAttribute     = "N/A — OUs do not exist in Entra ID"
        TransformExpression = 'MapOrgPathToOU([OrgPath], $OUMappingTable)'
        Writeback          = $false
        JML_Joiner         = "SET — user created in OU matching OrgPath"
        JML_Mover          = "MOVE — user moved to new OU on OrgPath change"
        JML_Leaver         = "MOVE — user moved to Disabled Users OU"
        Required           = $true
        CoexistenceFlow    = "Provisioning Engine → AD (OU placement)"
        PostMigrationFlow  = "ELIMINATED — no OUs in cloud-native model"
        Notes              = "Coexistence-only. OU placement is the legacy equivalent of OrgPath scoping. Post-migration, OrgPath in extensionAttribute1 replaces OU hierarchy entirely."
    }
)

Write-Host "    Canonical mappings defined: $($mappingMatrix.Count)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Section 2: AD Population Rate Audit
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/5] Auditing AD attribute population rates..." -ForegroundColor Yellow

$auditAttributes = @(
    'employeeID', 'employeeNumber', 'employeeType',
    'givenName', 'sn', 'displayName',
    'userPrincipalName', 'sAMAccountName',
    'department', 'division', 'company', 'title',
    'manager', 'physicalDeliveryOfficeName',
    'st', 'l', 'c', 'co', 'countryCode',
    'mail', 'telephoneNumber',
    'extensionAttribute1', 'extensionAttribute2', 'extensionAttribute3',
    'extensionAttribute4', 'extensionAttribute5'
)

$userFilter = "objectClass -eq 'user' -and objectCategory -eq 'person'"
$allUserCount = (Get-ADUser -Filter $userFilter @adParams).Count

$sampleParams = @{ Filter = $userFilter; Properties = $auditAttributes }
$sampleParams += $adParams
if ($SampleSize -gt 0 -and $SampleSize -lt $allUserCount) {
    Write-Host "    Sampling $SampleSize of $allUserCount users..." -ForegroundColor DarkGray
    $sampleUsers = Get-ADUser @sampleParams | Get-Random -Count $SampleSize
} else {
    Write-Host "    Full scan: $allUserCount users..." -ForegroundColor DarkGray
    $sampleUsers = @(Get-ADUser @sampleParams)
}

$sampleCount = $sampleUsers.Count
$populationRates = [ordered]@{}

foreach ($attr in $auditAttributes) {
    $populated = @($sampleUsers | Where-Object {
        $val = $_.$attr
        $val -ne $null -and $val -ne '' -and $val -ne 0
    }).Count

    $rate = if ($sampleCount -gt 0) { [math]::Round(($populated / $sampleCount) * 100, 1) } else { 0 }

    $quality = switch ($true) {
        ($rate -ge 95) { "EXCELLENT" }
        ($rate -ge 75) { "GOOD" }
        ($rate -ge 50) { "FAIR" }
        ($rate -ge 25) { "POOR" }
        default        { "CRITICAL" }
    }

    $populationRates[$attr] = [ordered]@{
        Attribute       = $attr
        Populated       = $populated
        SampleSize      = $sampleCount
        PopulationRate  = $rate
        Quality         = $quality
    }
}

Write-Host "    Audit complete for $($auditAttributes.Count) attributes" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Section 3: Coexistence Flow Analysis
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/5] Analyzing coexistence attribute flows..." -ForegroundColor Yellow

$coexistenceFlows = [ordered]@{
    "HR_to_AD" = @($mappingMatrix | Where-Object { $_.CoexistenceFlow -match 'HR.*AD' } |
        ForEach-Object { $_.ADAttribute }) | Sort-Object -Unique
    "AD_to_Entra" = @($mappingMatrix | Where-Object { $_.CoexistenceFlow -match 'AD.*Entra|Entra Connect' } |
        ForEach-Object { $_.ADAttribute }) | Sort-Object -Unique
    "Writeback_Entra_to_AD" = @($mappingMatrix | Where-Object { $_.Writeback -eq $true } |
        ForEach-Object { $_.ADAttribute }) | Sort-Object -Unique
    "Eliminated_PostMigration" = @($mappingMatrix | Where-Object { $_.PostMigrationFlow -match 'ELIMINATED' } |
        ForEach-Object { $_.ADAttribute }) | Sort-Object -Unique
    "Cloud_Only_PostMigration" = @($mappingMatrix | Where-Object { $_.PostMigrationFlow -match 'Entra ID.*direct|Entra ID.*authoritative' } |
        ForEach-Object { $_.EntraAttribute }) | Sort-Object -Unique
}

Write-Host "    HR → AD attributes:           $($coexistenceFlows.HR_to_AD.Count)" -ForegroundColor DarkGray
Write-Host "    AD → Entra (sync):             $($coexistenceFlows.AD_to_Entra.Count)" -ForegroundColor DarkGray
Write-Host "    Entra → AD (writeback):        $($coexistenceFlows.Writeback_Entra_to_AD.Count)" -ForegroundColor DarkGray
Write-Host "    Eliminated post-migration:     $($coexistenceFlows.Eliminated_PostMigration.Count)" -ForegroundColor DarkGray

# ══════════════════════════════════════════════════════════════
# Section 4: Gap Analysis
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/5] Performing gap analysis..." -ForegroundColor Yellow

# Identify extensionAttributes already in use that might conflict
$eaInUse = @{}
for ($i = 1; $i -le 15; $i++) {
    $eaName = "extensionAttribute$i"
    if ($populationRates.ContainsKey($eaName)) {
        $rate = $populationRates[$eaName].PopulationRate
        if ($rate -gt 0) {
            $eaInUse[$eaName] = $rate

            # Sample values for context
            $sampleVals = @($sampleUsers | Where-Object { $_.$eaName } |
                Select-Object -ExpandProperty $eaName -First 5)
            $eaInUse["${eaName}_samples"] = $sampleVals
        }
    }
}

$gapAnalysis = [ordered]@{
    ExtensionAttributeConflicts = [ordered]@{
        Description = "extensionAttributes already populated that may conflict with OrgPath (ADR-048)"
        OrgPathAttribute = "extensionAttribute1"
        OrgPathDepthAttribute = "extensionAttribute2"
        CostCenterAttribute = "extensionAttribute3"
        CurrentUsage = $eaInUse
        Action = if ($eaInUse.ContainsKey('extensionAttribute1') -and $eaInUse['extensionAttribute1'] -gt 0) {
            "WARNING: extensionAttribute1 already has $($eaInUse['extensionAttribute1'])% population. Current values must be migrated/cleared before OrgPath deployment."
        } else {
            "OK: extensionAttribute1 is available for OrgPath deployment."
        }
    }
    CriticalGaps = @(
        $populationRates.GetEnumerator() |
        Where-Object { $_.Value.Quality -eq 'CRITICAL' -and $_.Key -in @('employeeID','department','company','c','mail') } |
        ForEach-Object {
            [ordered]@{
                Attribute     = $_.Key
                PopulationRate = $_.Value.PopulationRate
                Impact        = "This attribute is required for provisioning. Low population rate indicates missing HR data flow."
            }
        }
    )
    UnmappedHRAttributes = @(
        "Benefits Eligibility", "Pay Grade", "Union Membership",
        "Work Schedule", "FTE Percentage", "Probation End Date",
        "Performance Rating", "Skills/Certifications"
    )
    UnmappedADAttributes = @(
        "description", "info", "homeDirectory", "homeDrive",
        "scriptPath", "profilePath", "logonWorkstation"
    )
}

Write-Host "    Extension attribute conflicts: $($eaInUse.Count / 2)" -ForegroundColor $(if ($eaInUse.ContainsKey('extensionAttribute1')) { 'Yellow' } else { 'Green' })

# ══════════════════════════════════════════════════════════════
# Section 5: D1.1 Cross-Reference (if available)
# ══════════════════════════════════════════════════════════════
$d1CrossRef = $null
if ($D1InputFile -and (Test-Path $D1InputFile)) {
    Write-Host "  [5/5] Cross-referencing D1.1 HR Attribute Discovery..." -ForegroundColor Yellow
    try {
        $d1Data = Get-Content $D1InputFile -Raw | ConvertFrom-Json
        $d1CrossRef = [ordered]@{
            D1InputFile   = $D1InputFile
            UPNDomains    = if ($d1Data.UPNDomainInventory) { @($d1Data.UPNDomainInventory) } else { @() }
            OUStructure   = if ($d1Data.OUStructureAnalysis) { "Available — $($d1Data.OUStructureAnalysis.Count) OUs mapped" } else { "Not available" }
            Note          = "D1.1 HR attribute discovery data cross-referenced for population rates and OU structure."
        }
        Write-Host "    D1.1 cross-reference loaded" -ForegroundColor Green
    }
    catch {
        Write-Host "    Could not parse D1.1 file: $($_.Exception.Message)" -ForegroundColor Yellow
        $d1CrossRef = [ordered]@{ Error = $_.Exception.Message }
    }
} else {
    Write-Host "  [5/5] No D1.1 file provided — skipping cross-reference" -ForegroundColor DarkGray
}

# ══════════════════════════════════════════════════════════════
# Output: JSON
# ══════════════════════════════════════════════════════════════

$output = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain           = $domain
        Timestamp        = (Get-Date).ToString("o")
        Script           = "UIAO Spec 2 D1.4 — HR-to-AD Attribute Mapping Matrix"
        Reference        = "UIAO_136, ADR-003, ADR-048"
        SampleSize       = $sampleCount
        TotalUsers       = $allUserCount
    }
    MappingMatrix          = $mappingMatrix
    PopulationRates        = @($populationRates.Values)
    CoexistenceFlows       = $coexistenceFlows
    GapAnalysis            = $gapAnalysis
    D1CrossReference       = $d1CrossRef
}

$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Output: Markdown Specification
# ══════════════════════════════════════════════════════════════
$mdFile = Join-Path $OutputPath "${outPrefix}.md"

$md = [System.Text.StringBuilder]::new()
[void]$md.AppendLine("# HR-to-AD Attribute Mapping Matrix")
[void]$md.AppendLine("")
[void]$md.AppendLine("> Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm') | Domain: $domain | Ref: UIAO_136, ADR-003, ADR-048")
[void]$md.AppendLine("")

# Group by section
$sections = $mappingMatrix | Group-Object { $_.Section }
foreach ($section in $sections) {
    [void]$md.AppendLine("## $($section.Name)")
    [void]$md.AppendLine("")
    [void]$md.AppendLine("| HR Attribute | AD Attribute | Entra Attribute | Required | Joiner | Mover | Leaver |")
    [void]$md.AppendLine("|---|---|---|---|---|---|---|")
    foreach ($m in $section.Group) {
        $req = if ($m.Required) { "Yes" } else { "No" }
        [void]$md.AppendLine("| $($m.HRAttribute) | ``$($m.ADAttribute)`` | ``$($m.EntraAttribute)`` | $req | $($m.JML_Joiner) | $($m.JML_Mover) | $($m.JML_Leaver) |")
    }
    [void]$md.AppendLine("")
}

[void]$md.AppendLine("## Attribute Population Rates (Current State)")
[void]$md.AppendLine("")
[void]$md.AppendLine("| Attribute | Populated | Sample | Rate | Quality |")
[void]$md.AppendLine("|---|---|---|---|---|")
foreach ($pr in $populationRates.Values) {
    [void]$md.AppendLine("| ``$($pr.Attribute)`` | $($pr.Populated) | $($pr.SampleSize) | $($pr.PopulationRate)% | $($pr.Quality) |")
}
[void]$md.AppendLine("")

[void]$md.AppendLine("## Coexistence Flow Summary")
[void]$md.AppendLine("")
[void]$md.AppendLine("- **HR → AD:** $($coexistenceFlows.HR_to_AD -join ', ')")
[void]$md.AppendLine("- **AD → Entra (sync):** $($coexistenceFlows.AD_to_Entra -join ', ')")
[void]$md.AppendLine("- **Entra → AD (writeback):** $($coexistenceFlows.Writeback_Entra_to_AD -join ', ')")
[void]$md.AppendLine("- **Eliminated post-migration:** $($coexistenceFlows.Eliminated_PostMigration -join ', ')")
[void]$md.AppendLine("")

[void]$md.AppendLine("## ADR-048 OrgPath Configuration")
[void]$md.AppendLine("")
[void]$md.AppendLine("| Attribute | Purpose | Expression |")
[void]$md.AppendLine("|---|---|---|")
[void]$md.AppendLine('| `extensionAttribute1` | OrgPath | `Join("/", Company, Region, State, City, Dept)` |')
[void]$md.AppendLine('| `extensionAttribute2` | OrgPath Depth | `Count(Split(OrgPath, "/"))` |')
[void]$md.AppendLine('| `extensionAttribute3` | Cost Center | `[HR.CostCenter]` |')
[void]$md.AppendLine("")

$md.ToString() | Out-File -FilePath $mdFile -Encoding utf8NoBOM
Write-Host "  Markdown: $mdFile" -ForegroundColor Green

# Console
Write-Host "`n-- HR-to-AD Attribute Mapping Matrix --" -ForegroundColor Cyan
Write-Host "  Canonical Mappings:     $($mappingMatrix.Count)"
Write-Host "  Total AD Users:         $allUserCount"
Write-Host "  Sample Audited:         $sampleCount"

Write-Host "`n-- Population Quality --" -ForegroundColor Cyan
$qualityCounts = $populationRates.Values | Group-Object Quality
foreach ($q in ($qualityCounts | Sort-Object Name)) {
    $color = switch ($q.Name) {
        "EXCELLENT" { 'Green' }
        "GOOD"      { 'Green' }
        "FAIR"      { 'Yellow' }
        "POOR"      { 'Red' }
        "CRITICAL"  { 'Red' }
        default     { 'White' }
    }
    Write-Host "  ${($q.Name)}: $($q.Count) attributes" -ForegroundColor $color
}

Write-Host "`n-- OrgPath Readiness (ADR-048) --" -ForegroundColor Cyan
$ea1Status = if ($populationRates.ContainsKey('extensionAttribute1') -and $populationRates['extensionAttribute1'].PopulationRate -gt 0) {
    "IN USE ($($populationRates['extensionAttribute1'].PopulationRate)% populated) — migration required"
} else {
    "AVAILABLE — ready for OrgPath deployment"
}
Write-Host "  extensionAttribute1: $ea1Status"

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
