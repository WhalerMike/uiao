<#
.SYNOPSIS
    UIAO Spec 2 — D1.2: HR-to-OrgPath Translation Rules Generator
.DESCRIPTION
    Consumes the D1.1 HR Attribute Schema Discovery JSON and produces:
    1. Candidate OrgPath translation rules derived from existing OU structure,
       Department/Division/Company taxonomy, and location data
    2. OrgPath segment definitions (CORP/REGION/STATE/CITY/DEPT)
    3. Hierarchy flattening rules for multi-level org structures
    4. Conflict detection (ambiguous mappings, missing data)
    5. Sample OrgPath output for validation

    The output is a canonical mapping rules specification (JSON + Markdown)
    that feeds D3.4 (Attribute Mapping Engine Configuration) and D3.5
    (OrgPath Population Pipeline).

    OrgPath Format (per ADR-048):
      extensionAttribute1 = CORP/REGION/STATE/CITY/DEPT
      extensionAttribute2 = depth level count (e.g., "5")

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.2
         ADR-048 (extensionAttribute1 = OrgPath)
.PARAMETER InputFile
    Path to D1.1 HR Attribute Discovery JSON output file.
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER RootSegment
    The root segment of the OrgPath hierarchy. Default: "CORP"
.PARAMETER RegionMap
    Path to optional JSON file mapping state codes to regions.
    If omitted, a default US region map is used.
.EXAMPLE
    .\Spec2-D1.2-ConvertTo-OrgPathTranslationRules.ps1 -InputFile .\output\UIAO_Spec2_D1.1_HRAttributeDiscovery_contoso.com_20260428.json
.NOTES
    Requires: D1.1 output JSON
    No AD or Entra connectivity required — operates on exported data only.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$InputFile,

    [string]$OutputPath = ".\output",
    [string]$RootSegment = "CORP",
    [string]$RegionMap
)

$ErrorActionPreference = "Stop"

# ── Validate input ──
if (-not (Test-Path $InputFile)) {
    Write-Error "Input file not found: $InputFile"
    return
}

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 2 — D1.2: HR-to-OrgPath Translation Rules"          -ForegroundColor Cyan
Write-Host "  Input:     $InputFile"                                         -ForegroundColor Cyan
Write-Host "  Root:      $RootSegment"                                       -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ── Load D1.1 data ──
Write-Host "  Loading D1.1 HR attribute discovery..." -ForegroundColor Yellow
$raw = Get-Content $InputFile -Raw -Encoding UTF8 | ConvertFrom-Json
$domain = $raw.ExportMetadata.Domain

Write-Host "  Loaded data for $domain ($($raw.ExportMetadata.TotalUsers) users)" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Default US State → Region Map
# ══════════════════════════════════════════════════════════════

$defaultRegionMap = @{
    # Northeast
    'CT' = 'NORTHEAST'; 'ME' = 'NORTHEAST'; 'MA' = 'NORTHEAST'; 'NH' = 'NORTHEAST'
    'RI' = 'NORTHEAST'; 'VT' = 'NORTHEAST'; 'NJ' = 'NORTHEAST'; 'NY' = 'NORTHEAST'
    'PA' = 'NORTHEAST'
    # Southeast
    'AL' = 'SOUTHEAST'; 'AR' = 'SOUTHEAST'; 'FL' = 'SOUTHEAST'; 'GA' = 'SOUTHEAST'
    'KY' = 'SOUTHEAST'; 'LA' = 'SOUTHEAST'; 'MS' = 'SOUTHEAST'; 'NC' = 'SOUTHEAST'
    'SC' = 'SOUTHEAST'; 'TN' = 'SOUTHEAST'; 'VA' = 'SOUTHEAST'; 'WV' = 'SOUTHEAST'
    'DC' = 'EAST'; 'MD' = 'EAST'; 'DE' = 'EAST'
    # Midwest
    'IL' = 'MIDWEST'; 'IN' = 'MIDWEST'; 'IA' = 'MIDWEST'; 'KS' = 'MIDWEST'
    'MI' = 'MIDWEST'; 'MN' = 'MIDWEST'; 'MO' = 'MIDWEST'; 'NE' = 'MIDWEST'
    'ND' = 'MIDWEST'; 'OH' = 'MIDWEST'; 'SD' = 'MIDWEST'; 'WI' = 'MIDWEST'
    # Southwest
    'AZ' = 'SOUTHWEST'; 'NM' = 'SOUTHWEST'; 'OK' = 'SOUTHWEST'; 'TX' = 'SOUTHWEST'
    # West
    'AK' = 'WEST'; 'CA' = 'WEST'; 'CO' = 'WEST'; 'HI' = 'WEST'
    'ID' = 'WEST'; 'MT' = 'WEST'; 'NV' = 'WEST'; 'OR' = 'WEST'
    'UT' = 'WEST'; 'WA' = 'WEST'; 'WY' = 'WEST'
}

# Load custom region map if provided
if ($RegionMap -and (Test-Path $RegionMap)) {
    Write-Host "  Loading custom region map: $RegionMap" -ForegroundColor Yellow
    $customMap = Get-Content $RegionMap -Raw | ConvertFrom-Json
    $defaultRegionMap = @{}
    foreach ($prop in $customMap.PSObject.Properties) {
        $defaultRegionMap[$prop.Name] = $prop.Value
    }
}

# ══════════════════════════════════════════════════════════════
# Section 1: Analyze OU Structure for OrgPath Derivation
# ══════════════════════════════════════════════════════════════
Write-Host "`n  [1/5] Analyzing OU structure for OrgPath patterns..." -ForegroundColor Yellow

$ouData = $raw.OUStructure.TopOUs
$ouRules = [System.Collections.Generic.List[object]]::new()
$ouConflicts = [System.Collections.Generic.List[object]]::new()

foreach ($ou in $ouData) {
    $ouPath = $ou.OUPath
    if (-not $ouPath) { continue }

    # Parse OU components (reverse order — AD stores leaf-first)
    $ouParts = @()
    foreach ($segment in ($ouPath -split ',')) {
        if ($segment -match '^OU=(.+)$') {
            $ouParts += $Matches[1].Trim()
        }
    }
    [array]::Reverse($ouParts)

    # Generate candidate OrgPath from OU structure
    $candidateSegments = @($RootSegment)
    foreach ($part in $ouParts) {
        $normalized = $part.ToUpper() -replace '\s+', '_' -replace '[^A-Z0-9_]', ''
        if ($normalized -and $normalized -ne 'USERS' -and $normalized -ne 'COMPUTERS') {
            $candidateSegments += $normalized
        }
    }

    $candidateOrgPath = $candidateSegments -join '/'

    $ouRules.Add([ordered]@{
        SourceOUPath     = $ouPath
        OUComponents     = $ouParts
        OUDepth          = $ouParts.Count
        CandidateOrgPath = $candidateOrgPath
        OrgPathDepth     = $candidateSegments.Count
        UserCount        = $ou.UserCount
        Confidence       = if ($ouParts.Count -ge 2 -and $ouParts.Count -le 5) { "High" }
                          elseif ($ouParts.Count -eq 1) { "Medium — flat structure" }
                          else { "Low — review manually" }
    })
}

# ══════════════════════════════════════════════════════════════
# Section 2: Build Department → OrgPath Segment Map
# ══════════════════════════════════════════════════════════════
Write-Host "  [2/5] Building department taxonomy map..." -ForegroundColor Yellow

$deptMap = [ordered]@{}
foreach ($dept in $raw.DepartmentTaxonomy) {
    $normalized = $dept.Department.ToUpper() -replace '\s+', '_' -replace '[^A-Z0-9_]', ''
    if ($normalized) {
        $deptMap[$dept.Department] = [ordered]@{
            OriginalName   = $dept.Department
            NormalizedName = $normalized
            UserCount      = $dept.UserCount
            OrgPathSegment = $normalized
        }
    }
}

$divisionMap = [ordered]@{}
foreach ($div in $raw.DivisionTaxonomy) {
    $normalized = $div.Division.ToUpper() -replace '\s+', '_' -replace '[^A-Z0-9_]', ''
    if ($normalized) {
        $divisionMap[$div.Division] = [ordered]@{
            OriginalName   = $div.Division
            NormalizedName = $normalized
            UserCount      = $div.UserCount
            OrgPathSegment = $normalized
        }
    }
}

$companyMap = [ordered]@{}
foreach ($co in $raw.CompanyTaxonomy) {
    $normalized = $co.Company.ToUpper() -replace '\s+', '_' -replace '[^A-Z0-9_]', ''
    if ($normalized) {
        $companyMap[$co.Company] = [ordered]@{
            OriginalName   = $co.Company
            NormalizedName = $normalized
            UserCount      = $co.UserCount
            OrgPathSegment = $normalized
        }
    }
}

# ══════════════════════════════════════════════════════════════
# Section 3: Define Canonical OrgPath Schema
# ══════════════════════════════════════════════════════════════
Write-Host "  [3/5] Defining canonical OrgPath schema..." -ForegroundColor Yellow

# Determine hierarchy depth based on available data
$hasCompany   = ($companyMap.Count -gt 0)
$hasDivision  = ($divisionMap.Count -gt 0)
$hasDept      = ($deptMap.Count -gt 0)
$hasLocation  = ($raw.HRAttributePopulation.City.PopulationRate -gt 30)
$hasState     = ($raw.HRAttributePopulation.State.PopulationRate -gt 30)

# Build recommended OrgPath schema
$schemaSegments = [System.Collections.Generic.List[object]]::new()

$schemaSegments.Add([ordered]@{
    Position    = 0
    SegmentName = "Root"
    SourceField = "(constant)"
    Value       = $RootSegment
    Required    = $true
    Example     = $RootSegment
})

if ($hasCompany -and $companyMap.Count -gt 1) {
    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "Company"
        SourceField = "Company (AD) / companyName (HR)"
        Value       = "(derived from Company attribute)"
        Required    = $true
        Example     = ($companyMap.Values | Select-Object -First 1).NormalizedName
    })
}

if ($hasState) {
    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "Region"
        SourceField = "State → Region lookup table"
        Value       = "(derived from State via region map)"
        Required    = $true
        Example     = "EAST"
    })

    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "State"
        SourceField = "State (AD) / state (HR)"
        Value       = "(state abbreviation, uppercase)"
        Required    = $true
        Example     = "MD"
    })
}

if ($hasLocation) {
    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "City"
        SourceField = "City / l (AD) / city (HR)"
        Value       = "(city name, uppercase, underscores for spaces)"
        Required    = $true
        Example     = "BALTIMORE"
    })
}

if ($hasDivision -and $divisionMap.Count -gt 1) {
    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "Division"
        SourceField = "Division (AD) / division (HR)"
        Value       = "(division name, normalized)"
        Required    = $false
        Example     = ($divisionMap.Values | Select-Object -First 1).NormalizedName
    })
}

if ($hasDept) {
    $schemaSegments.Add([ordered]@{
        Position    = $schemaSegments.Count
        SegmentName = "Department"
        SourceField = "Department (AD) / department (HR)"
        Value       = "(department name, normalized)"
        Required    = $true
        Example     = ($deptMap.Values | Select-Object -First 1).NormalizedName
    })
}

$exampleOrgPath = ($schemaSegments | ForEach-Object { $_.Example }) -join '/'

# ══════════════════════════════════════════════════════════════
# Section 4: Generate Translation Rules
# ══════════════════════════════════════════════════════════════
Write-Host "  [4/5] Generating translation rules..." -ForegroundColor Yellow

$translationRules = [ordered]@{
    SchemaVersion     = "1.0"
    ADR               = "ADR-048"
    TargetAttribute   = "extensionAttribute1"
    DepthAttribute    = "extensionAttribute2"
    RootSegment       = $RootSegment
    PathSeparator     = "/"
    MaxDepth          = $schemaSegments.Count
    NormalizationRules = [ordered]@{
        CaseRule          = "UPPERCASE — all segments converted to uppercase"
        SpaceReplacement  = "Spaces replaced with underscores (_)"
        SpecialCharacters = "All non-alphanumeric characters except underscore are stripped"
        MaxSegmentLength  = 30
        EmptySegmentRule  = "If a segment source is empty, use 'UNKNOWN' as placeholder"
    }
    SchemaDefinition  = @($schemaSegments)
    ExampleOutput     = $exampleOrgPath
}

# Generate the OrgPath calculation expression for Entra ID provisioning
# This is the expression that goes into the attribute mapping engine (D3.4)
$expressionParts = [System.Collections.Generic.List[string]]::new()
foreach ($seg in $schemaSegments) {
    switch ($seg.SegmentName) {
        "Root"       { $expressionParts.Add("`"$RootSegment`"") }
        "Company"    { $expressionParts.Add("ToUpper(Replace([company], `" `", `"_`"))") }
        "Region"     { $expressionParts.Add("Switch([state], `"UNKNOWN`", `"MD`", `"EAST`", `"VA`", `"EAST`", `"DC`", `"EAST`", `"CA`", `"WEST`", `"TX`", `"SOUTHWEST`", `"NY`", `"NORTHEAST`", `"IL`", `"MIDWEST`")") }
        "State"      { $expressionParts.Add("ToUpper([state])") }
        "City"       { $expressionParts.Add("ToUpper(Replace([city], `" `", `"_`"))") }
        "Division"   { $expressionParts.Add("ToUpper(Replace([division], `" `", `"_`"))") }
        "Department" { $expressionParts.Add("ToUpper(Replace([department], `" `", `"_`"))") }
    }
}
$calculationExpression = "Join(`"/`", " + ($expressionParts -join ", ") + ")"

$translationRules['CalculationExpression'] = $calculationExpression
$translationRules['ExpressionNote'] = "This expression uses Entra ID provisioning expression syntax. The Switch() for Region requires expansion to cover all state codes in use. See the RegionMap in this output for the full mapping."

# ══════════════════════════════════════════════════════════════
# Section 5: Data Quality & Conflict Analysis
# ══════════════════════════════════════════════════════════════
Write-Host "  [5/5] Analyzing data quality and conflicts..." -ForegroundColor Yellow

$dataQuality = [ordered]@{}
$qualityIssues = [System.Collections.Generic.List[object]]::new()

foreach ($seg in $schemaSegments) {
    if ($seg.SegmentName -eq 'Root') { continue }

    $sourceField = switch ($seg.SegmentName) {
        'Company'    { 'Company' }
        'Region'     { 'State' }
        'State'      { 'State' }
        'City'       { 'City' }
        'Division'   { 'Division' }
        'Department' { 'Department' }
    }

    if (-not $sourceField) { continue }

    $popRate = 0
    if ($raw.HRAttributePopulation.$sourceField) {
        $popRate = $raw.HRAttributePopulation.$sourceField.PopulationRate
    }

    $status = if ($popRate -ge 90) { "PASS" }
              elseif ($popRate -ge 70) { "WARN — partial coverage" }
              elseif ($popRate -ge 30) { "WARN — low coverage, many UNKNOWN segments expected" }
              else { "FAIL — insufficient data for this segment" }

    $dataQuality[$seg.SegmentName] = [ordered]@{
        SourceField    = $sourceField
        PopulationRate = $popRate
        Status         = $status
        Required       = $seg.Required
    }

    if ($popRate -lt 70 -and $seg.Required) {
        $qualityIssues.Add([ordered]@{
            Segment        = $seg.SegmentName
            SourceField    = $sourceField
            PopulationRate = $popRate
            Issue          = "Required OrgPath segment has <70% source data coverage"
            Remediation    = "Enrich $sourceField in HR system or AD before OrgPath deployment. Users without this attribute will get 'UNKNOWN' in this segment."
        })
    }
}

# Check extensionAttribute1 availability
$orgPathSlot = $raw.OrgPathReadiness
if (-not $orgPathSlot.CurrentlyAvailable) {
    $qualityIssues.Add([ordered]@{
        Segment        = "OrgPath Target Attribute"
        SourceField    = "extensionAttribute1"
        PopulationRate = (100 - $orgPathSlot.CurrentPopulationRate)
        Issue          = "extensionAttribute1 already in use — $($orgPathSlot.ConflictRisk)"
        Remediation    = "Audit current extensionAttribute1 usage. Migrate existing values to another attribute before deploying OrgPath."
    })
}

# ══════════════════════════════════════════════════════════════
# Assemble full output
# ══════════════════════════════════════════════════════════════

$output = [ordered]@{
    ExportMetadata = [ordered]@{
        SourceFile       = $InputFile
        SourceDomain     = $domain
        Timestamp        = (Get-Date).ToString("o")
        Script           = "UIAO Spec 2 D1.2 — HR-to-OrgPath Translation Rules"
        Reference        = "UIAO_136, ADR-048"
    }
    TranslationRules     = $translationRules
    RegionMap            = $defaultRegionMap
    DepartmentMap        = $deptMap
    DivisionMap          = $divisionMap
    CompanyMap           = $companyMap
    OUDerivedRules       = @($ouRules)
    DataQualityAssessment = $dataQuality
    QualityIssues        = @($qualityIssues)
    OrgPathReadiness     = $orgPathSlot
}

# ── Write JSON ──
$jsonFile = Join-Path $OutputPath "UIAO_Spec2_D1.2_OrgPathTranslationRules_${domain}_${timestamp}.json"
$output | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON output: $jsonFile" -ForegroundColor Green

# ── Write Markdown specification ──
$mdFile = Join-Path $OutputPath "UIAO_Spec2_D1.2_OrgPathTranslationRules_${domain}_${timestamp}.md"
$mdContent = @"
# UIAO OrgPath Translation Rules — $domain

> Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
> Source: $InputFile
> Ref: UIAO_136, ADR-048

## OrgPath Schema

**Target Attribute:** ``extensionAttribute1`` (ADR-048)
**Depth Attribute:** ``extensionAttribute2``
**Format:** ``$($translationRules.PathSeparator)``-separated segments, all UPPERCASE
**Example:** ``$exampleOrgPath``

### Segment Definitions

| Position | Segment | Source Field | Required | Example |
|----------|---------|-------------|----------|---------|
$( ($schemaSegments | ForEach-Object { "| $($_.Position) | $($_.SegmentName) | $($_.SourceField) | $($_.Required) | ``$($_.Example)`` |" }) -join "`n" )

### Normalization Rules

- **Case:** All segments converted to UPPERCASE
- **Spaces:** Replaced with underscores (``_``)
- **Special characters:** All non-alphanumeric characters except underscore are stripped
- **Max segment length:** 30 characters
- **Empty values:** If a source field is empty, the segment value is ``UNKNOWN``

## Entra ID Provisioning Expression

```
$calculationExpression
```

> **Note:** The ``Switch()`` function for Region must be expanded to cover all state codes in use.
> See the RegionMap section in the JSON output for the full state-to-region mapping.

## Data Quality Assessment

| Segment | Source Field | Population Rate | Status |
|---------|-------------|----------------|--------|
$( ($dataQuality.GetEnumerator() | ForEach-Object { "| $($_.Key) | $($_.Value.SourceField) | $($_.Value.PopulationRate)% | $($_.Value.Status) |" }) -join "`n" )

## Quality Issues

$( if ($qualityIssues.Count -eq 0) { "> No quality issues detected." } else { ($qualityIssues | ForEach-Object { "- **$($_.Segment)** ($($_.SourceField)): $($_.Issue). Remediation: $($_.Remediation)" }) -join "`n" } )

## Department Taxonomy ($($deptMap.Count) departments)

$( ($deptMap.Values | Select-Object -First 20 | ForEach-Object { "- ``$($_.NormalizedName)`` ← $($_.OriginalName) ($($_.UserCount) users)" }) -join "`n" )

$( if ($deptMap.Count -gt 20) { "> ... and $($deptMap.Count - 20) more departments (see JSON output)" } )

## OU-Derived OrgPath Candidates (Top 15)

| OU Path | Candidate OrgPath | Users | Confidence |
|---------|------------------|-------|------------|
$( ($ouRules | Select-Object -First 15 | ForEach-Object { "| ``$($_.SourceOUPath | Select-Object -First 80)`` | ``$($_.CandidateOrgPath)`` | $($_.UserCount) | $($_.Confidence) |" }) -join "`n" )

## extensionAttribute1 Readiness

- **Currently available:** $($orgPathSlot.CurrentlyAvailable)
- **Conflict risk:** $($orgPathSlot.ConflictRisk)
- **Recommendation:** $($orgPathSlot.Recommendation)
"@

$mdContent | Out-File -FilePath $mdFile -Encoding utf8NoBOM
Write-Host "  Markdown output: $mdFile" -ForegroundColor Green

# ══════════════════════════════════════════════════════════════
# Console Dashboard
# ══════════════════════════════════════════════════════════════
Write-Host "`n-- OrgPath Schema --" -ForegroundColor Cyan
Write-Host "  Format: $exampleOrgPath"
Write-Host "  Depth:  $($schemaSegments.Count) segments"
foreach ($seg in $schemaSegments) {
    Write-Host "    [$($seg.Position)] $($seg.SegmentName.PadRight(12)) ← $($seg.SourceField)"
}

Write-Host "`n-- Data Quality --" -ForegroundColor Cyan
foreach ($dq in $dataQuality.GetEnumerator()) {
    $color = switch -Wildcard ($dq.Value.Status) {
        'PASS*'  { 'Green' }
        'WARN*'  { 'Yellow' }
        'FAIL*'  { 'Red' }
        default  { 'Gray' }
    }
    Write-Host "  $($dq.Value.Status.PadRight(40))  $($dq.Key) ($($dq.Value.PopulationRate)%)" -ForegroundColor $color
}

Write-Host "`n-- Taxonomy Size --" -ForegroundColor Cyan
Write-Host "  Departments:  $($deptMap.Count)"
Write-Host "  Divisions:    $($divisionMap.Count)"
Write-Host "  Companies:    $($companyMap.Count)"
Write-Host "  OU paths:     $($ouRules.Count)"

if ($qualityIssues.Count -gt 0) {
    Write-Host "`n-- Quality Issues ($($qualityIssues.Count)) --" -ForegroundColor Red
    foreach ($qi in $qualityIssues) {
        Write-Host "  ! $($qi.Segment): $($qi.Issue)" -ForegroundColor Red
    }
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
