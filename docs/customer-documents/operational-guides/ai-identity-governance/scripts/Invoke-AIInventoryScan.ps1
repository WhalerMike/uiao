<#
.SYNOPSIS
    Scans an OMB M-25-21 Federal AI Use Case Inventory CSV for identity
    governance gaps and produces a prioritized findings report.

.DESCRIPTION
    Implements the six drift classes defined in UIAO_196 / ADR-109:

      P1  DRIFT-COMPLIANCE::ai-agentic-ungoverned  Agentic AI without ATO
      P1  DRIFT-IDENTITY::ai-shadow                Registry entry absent from OMB
      P2  DRIFT-COMPLIANCE::ai-ato-gap             Deployed system without ATO
      P2  DRIFT-IDENTITY::ai-no-orgpath            No agency/bureau → OrgPath
      P2  DRIFT-IDENTITY::ai-unowned               No contact email / owner
      P2  DRIFT-COMPLIANCE::ai-pii-no-pia          PII system without PIA URL

    L1 (observe) only. No writes to any system.

.PARAMETER CsvPath
    Path to the OMB AI Use Case Inventory CSV.
    Download from: github.com/ombegov/2025-Federal-Agency-AI-Use-Case-Inventory
    File: Data/2025_individually_reported_AI_use_cases.csv

.PARAMETER Agency
    Agency abbreviation to filter (e.g. "GSA"). Leave blank to scan all agencies.

.PARAMETER OutputPath
    Output file path. Extension determines format:
      .csv  — tabular findings (default)
      .html — formatted report
      .json — ODR-compatible structured output

.PARAMETER KnownRegistryIds
    Optional array of system_name_ato values from your UIAO or IdM registry.
    When supplied, enables shadow AI detection: any registry ID absent from the
    OMB inventory generates a P1 DRIFT-IDENTITY::ai-shadow finding.

.PARAMETER IncludeAllStages
    By default only deployed and pilot systems are scanned. Set this flag to
    include pre-deployment and retired systems in the output (no findings are
    generated for them — they appear as informational rows only).

.EXAMPLE
    # Scan a single agency, output CSV
    .\Invoke-AIInventoryScan.ps1 `
        -CsvPath ".\2025_individually_reported_AI_use_cases.csv" `
        -Agency  "GSA" `
        -OutputPath ".\gsa-ai-identity-gaps.csv"

.EXAMPLE
    # Scan all agencies, HTML report
    .\Invoke-AIInventoryScan.ps1 `
        -CsvPath ".\2025_individually_reported_AI_use_cases.csv" `
        -OutputPath ".\federal-ai-identity-report.html"

.EXAMPLE
    # With shadow AI detection from a known registry
    $known = @("ACAS","ADVANA","MAX.gov")
    .\Invoke-AIInventoryScan.ps1 `
        -CsvPath  ".\2025_individually_reported_AI_use_cases.csv" `
        -Agency   "DOD" `
        -KnownRegistryIds $known `
        -OutputPath ".\dod-ai-gaps.csv"

.NOTES
    Canon reference: UIAO_196, ADR-109
    Version: 1.0.0  2026-06-18
    Author:  Michael Stratton / UIAO governance substrate
    License: Per UIAO repo license
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$CsvPath,

    [string]$Agency = '',

    [string]$OutputPath = '.\ai-identity-gaps.csv',

    [string[]]$KnownRegistryIds = @(),

    [switch]$IncludeAllStages
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Get-OrgPath([string]$AgencyCode, [string]$Bureau) {
    $a = $AgencyCode.Trim().ToUpper()
    $b = $Bureau.Trim()
    if (-not $a)           { return $null }
    if (-not $b -or $b.ToUpper() -eq $a) { return $a }
    return "$a`:$b"
}

function Get-AgentClass([string]$Classification) {
    $v = $Classification.ToLower()
    if ($v -match 'agentic')         { return 'agentic-ai' }
    if ($v -match 'generative')      { return 'generative-ai' }
    if ($v -match 'natural language|nlp') { return 'nlp' }
    if ($v -match 'computer vision') { return 'computer-vision' }
    if ($v -match 'reinforcement')   { return 'reinforcement-learning' }
    if ($v -match 'classical|predictive|machine learning') { return 'classical-ml' }
    return 'other'
}

function Get-AtoStatus([string]$Value) {
    $v = $Value.Trim().ToLower()
    if ($v -in @('yes','true','1'))          { return 'yes' }
    if ($v -in @('no','false','0'))          { return 'no' }
    if ($v -match 'not applicable|n/a')      { return 'not-applicable' }
    return 'unknown'
}

function Get-BoolField([string]$Value) {
    return ($Value.Trim().ToLower() -in @('yes','true','1'))
}

function Get-DevStage([string]$Value) {
    $v = $Value.Trim().ToLower()
    switch -Regex ($v) {
        'deployed'         { return 'deployed' }
        'pilot'            { return 'pilot' }
        'pre.?deployment'  { return 'pre-deployment' }
        'retired'          { return 'retired' }
        default            { return 'unknown' }
    }
}

# ---------------------------------------------------------------------------
# Load and parse CSV
# ---------------------------------------------------------------------------

Write-Host "[1/4] Loading inventory: $CsvPath" -ForegroundColor Cyan

if (-not (Test-Path $CsvPath)) {
    Write-Error "CSV not found: $CsvPath"
    exit 1
}

$rows = Import-Csv -Path $CsvPath -Encoding UTF8

if ($Agency) {
    $rows = $rows | Where-Object { $_.agency -eq $Agency }
    Write-Host "      Filtered to agency '$Agency': $($rows.Count) rows" -ForegroundColor Gray
} else {
    Write-Host "      Loaded $($rows.Count) rows (all agencies)" -ForegroundColor Gray
}

# ---------------------------------------------------------------------------
# Build records
# ---------------------------------------------------------------------------

Write-Host "[2/4] Parsing records..." -ForegroundColor Cyan

$records = foreach ($row in $rows) {
    $stage   = Get-DevStage   $row.development_stage
    $isLive  = $stage -in @('deployed','pilot')
    $orgpath = Get-OrgPath $row.agency $row.agency_bureau

    [PSCustomObject]@{
        OmbId            = $row.id
        SystemName       = if ($row.system_name_ato) { $row.system_name_ato } else { $row.use_case_name }
        Agency           = $row.agency
        AgencyName       = $row.agency_name
        Bureau           = $row.agency_bureau
        OrgPath          = $orgpath
        Stage            = $stage
        IsLive           = $isLive
        AgentClass       = Get-AgentClass $row.classification
        AtoStatus        = Get-AtoStatus  $row.have_ato
        SystemNameAto    = $row.system_name_ato
        VendorName       = $row.vendor_name
        ContactEmail     = $row.contact_email
        HasPii           = Get-BoolField  $row.has_pii
        PiaUrl           = $row.pia_url
        IsHighImpact     = Get-BoolField  $row.is_high_impact
        OperationalDate  = $row.operational_date
    }
}

$live = $records | Where-Object { $_.IsLive }
Write-Host "      $($records.Count) records total, $($live.Count) live (deployed + pilot)" -ForegroundColor Gray

# ---------------------------------------------------------------------------
# Detect findings
# ---------------------------------------------------------------------------

Write-Host "[3/4] Detecting identity governance gaps..." -ForegroundColor Cyan

$findings = [System.Collections.Generic.List[PSCustomObject]]::new()

# Track ATO names in inventory for shadow detection
$inventoryAtoNames = [System.Collections.Generic.HashSet[string]]::new(
    [System.StringComparer]::OrdinalIgnoreCase)
foreach ($r in $live) {
    if ($r.SystemNameAto) { [void]$inventoryAtoNames.Add($r.SystemNameAto) }
}

foreach ($rec in $live) {
    $ref = "omb-inventory:$($rec.OmbId)"

    # P1: Agentic AI without ATO
    if ($rec.AgentClass -eq 'agentic-ai' -and $rec.AtoStatus -ne 'yes') {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P1'
            DriftClass  = 'DRIFT-COMPLIANCE::ai-agentic-ungoverned'
            SystemName  = $rec.SystemName
            Agency      = $rec.Agency
            Bureau      = $rec.Bureau
            OrgPath     = $rec.OrgPath
            AtoStatus   = $rec.AtoStatus
            AgentClass  = $rec.AgentClass
            HasPii      = $rec.HasPii
            PiaUrl      = $rec.PiaUrl
            ContactEmail = $rec.ContactEmail
            Finding     = "Agentic AI system deployed without ATO (have_ato=$($rec.AtoStatus)). " +
                          "Per ADR-109 §4, agentic AI without ATO is the highest-risk identity class. " +
                          "Immediate action: restrict to read-only credentials; initiate ATO."
            EvidenceRef = $ref
        })
    }

    # P2: ATO gap (non-agentic or in addition to agentic check)
    if ($rec.AtoStatus -eq 'no') {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P2'
            DriftClass  = 'DRIFT-COMPLIANCE::ai-ato-gap'
            SystemName  = $rec.SystemName
            Agency      = $rec.Agency
            Bureau      = $rec.Bureau
            OrgPath     = $rec.OrgPath
            AtoStatus   = $rec.AtoStatus
            AgentClass  = $rec.AgentClass
            HasPii      = $rec.HasPii
            PiaUrl      = $rec.PiaUrl
            ContactEmail = $rec.ContactEmail
            Finding     = "Deployed/pilot AI system has no Authorization to Operate. " +
                          "M-25-21 §IV requires ATO before operational use. " +
                          "Remediate: initiate ATO or inherit reciprocity under ADR-054."
            EvidenceRef = $ref
        })
    }

    # P2: No OrgPath
    if (-not $rec.OrgPath) {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P2'
            DriftClass  = 'DRIFT-IDENTITY::ai-no-orgpath'
            SystemName  = $rec.SystemName
            Agency      = $rec.Agency
            Bureau      = $rec.Bureau
            OrgPath     = $null
            AtoStatus   = $rec.AtoStatus
            AgentClass  = $rec.AgentClass
            HasPii      = $rec.HasPii
            PiaUrl      = $rec.PiaUrl
            ContactEmail = $rec.ContactEmail
            Finding     = "AI system has no organizational placement (agency_bureau field blank). " +
                          "Without OrgPath the system is invisible to every governance process " +
                          "that depends on knowing where in the hierarchy it belongs. " +
                          "Remediate: identify responsible bureau; update OMB inventory."
            EvidenceRef = $ref
        })
    }

    # P2: Unowned
    if (-not $rec.ContactEmail) {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P2'
            DriftClass  = 'DRIFT-IDENTITY::ai-unowned'
            SystemName  = $rec.SystemName
            Agency      = $rec.Agency
            Bureau      = $rec.Bureau
            OrgPath     = $rec.OrgPath
            AtoStatus   = $rec.AtoStatus
            AgentClass  = $rec.AgentClass
            HasPii      = $rec.HasPii
            PiaUrl      = $rec.PiaUrl
            ContactEmail = $null
            Finding     = "AI system has no contact email (no owner identity anchor). " +
                          "Without an owner there is no credential rotation target and no " +
                          "incident-response point of contact. " +
                          "Remediate: assign bureau identity governance coordinator as owner."
            EvidenceRef = $ref
        })
    }

    # P2: PII / no PIA
    if ($rec.HasPii -and -not $rec.PiaUrl) {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P2'
            DriftClass  = 'DRIFT-COMPLIANCE::ai-pii-no-pia'
            SystemName  = $rec.SystemName
            Agency      = $rec.Agency
            Bureau      = $rec.Bureau
            OrgPath     = $rec.OrgPath
            AtoStatus   = $rec.AtoStatus
            AgentClass  = $rec.AgentClass
            HasPii      = $rec.HasPii
            PiaUrl      = $null
            ContactEmail = $rec.ContactEmail
            Finding     = "AI system handles PII but has no Privacy Impact Assessment URL. " +
                          "M-25-21 §IV requires a PIA for AI systems that process PII. " +
                          "Remediate: author or locate PIA; publish URL; update OMB inventory."
            EvidenceRef = $ref
        })
    }
}

# P1: Shadow AI detection
foreach ($regId in $KnownRegistryIds) {
    if (-not $inventoryAtoNames.Contains($regId)) {
        $findings.Add([PSCustomObject]@{
            Severity    = 'P1'
            DriftClass  = 'DRIFT-IDENTITY::ai-shadow'
            SystemName  = $regId
            Agency      = if ($Agency) { $Agency } else { 'UNKNOWN' }
            Bureau      = ''
            OrgPath     = $null
            AtoStatus   = 'unknown'
            AgentClass  = 'unknown'
            HasPii      = $false
            PiaUrl      = $null
            ContactEmail = $null
            Finding     = "System present in UIAO/IdM registry but ABSENT from OMB M-25-21 inventory. " +
                          "This is a shadow AI system: an uninventoried deployment evading M-25-21 " +
                          "reporting obligations. Immediate action: investigate and either report " +
                          "to OMB or document exemption."
            EvidenceRef = 'uiao-registry'
        })
    }
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

$p1Count      = ($findings | Where-Object Severity -eq 'P1').Count
$p2Count      = ($findings | Where-Object Severity -eq 'P2').Count
$atoGaps      = ($findings | Where-Object DriftClass -eq 'DRIFT-COMPLIANCE::ai-ato-gap').Count
$agenticP1    = ($findings | Where-Object DriftClass -eq 'DRIFT-COMPLIANCE::ai-agentic-ungoverned').Count
$shadowP1     = ($findings | Where-Object DriftClass -eq 'DRIFT-IDENTITY::ai-shadow').Count
$unowned      = ($findings | Where-Object DriftClass -eq 'DRIFT-IDENTITY::ai-unowned').Count
$piiNoPia     = ($findings | Where-Object DriftClass -eq 'DRIFT-COMPLIANCE::ai-pii-no-pia').Count
$noOrgPath    = ($findings | Where-Object DriftClass -eq 'DRIFT-IDENTITY::ai-no-orgpath').Count
$gateDecision = if ($p1Count -gt 0) { 'HALT' } else { 'PASS' }

Write-Host ""
Write-Host "==============================================" -ForegroundColor White
Write-Host " AI IDENTITY GOVERNANCE SCAN RESULTS"          -ForegroundColor White
Write-Host "==============================================" -ForegroundColor White
Write-Host " Records  : $($records.Count) total  $($live.Count) live" -ForegroundColor Gray
Write-Host " Findings : $($findings.Count) total" -ForegroundColor Gray
Write-Host " Gate     : $gateDecision  (P1=$p1Count  P2=$p2Count)" -ForegroundColor $(if ($gateDecision -eq 'HALT') { 'Red' } else { 'Green' })
Write-Host ""
Write-Host " Finding breakdown:" -ForegroundColor White
Write-Host "   Agentic ungoverned (P1) : $agenticP1" -ForegroundColor $(if ($agenticP1) { 'Red' } else { 'Green' })
Write-Host "   Shadow AI (P1)          : $shadowP1"  -ForegroundColor $(if ($shadowP1)   { 'Red' } else { 'Green' })
Write-Host "   ATO gaps (P2)           : $atoGaps"   -ForegroundColor $(if ($atoGaps)    { 'Yellow' } else { 'Green' })
Write-Host "   No OrgPath (P2)         : $noOrgPath" -ForegroundColor $(if ($noOrgPath)  { 'Yellow' } else { 'Green' })
Write-Host "   Unowned (P2)            : $unowned"   -ForegroundColor $(if ($unowned)    { 'Yellow' } else { 'Green' })
Write-Host "   PII / no PIA (P2)       : $piiNoPia"  -ForegroundColor $(if ($piiNoPia)   { 'Yellow' } else { 'Green' })
Write-Host "==============================================" -ForegroundColor White
Write-Host ""

# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

Write-Host "[4/4] Writing output: $OutputPath" -ForegroundColor Cyan

$ext = [System.IO.Path]::GetExtension($OutputPath).ToLower()

switch ($ext) {
    '.csv' {
        $findings | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8
        Write-Host "      CSV written: $OutputPath ($($findings.Count) rows)" -ForegroundColor Green
    }

    '.json' {
        $scannedAt = (Get-Date -Format 'o')
        $output = [PSCustomObject]@{
            scanned_at        = $scannedAt
            source_path       = $CsvPath
            agency_filter     = $Agency
            gate              = $gateDecision
            counts = [PSCustomObject]@{
                total_records = $records.Count
                live_records  = $live.Count
                findings      = $findings.Count
                p1            = $p1Count
                p2            = $p2Count
            }
            findings = $findings
        }
        $output | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8
        Write-Host "      JSON written: $OutputPath" -ForegroundColor Green
    }

    '.html' {
        $scannedAt  = Get-Date -Format 'yyyy-MM-dd HH:mm UTC'
        $agencyDisp = if ($Agency) { $Agency } else { 'All Agencies' }
        $gateColor  = if ($gateDecision -eq 'HALT') { '#c0392b' } else { '#27ae60' }

        $findingRows = $findings | Sort-Object Severity, DriftClass | ForEach-Object {
            $sevColor = if ($_.Severity -eq 'P1') { '#c0392b' } else { '#e67e22' }
            "<tr>
              <td style='color:$sevColor;font-weight:bold'>$($_.Severity)</td>
              <td><code>$($_.DriftClass)</code></td>
              <td>$($_.SystemName)</td>
              <td>$($_.Agency)</td>
              <td>$($_.Bureau)</td>
              <td>$($_.OrgPath)</td>
              <td>$($_.AtoStatus)</td>
              <td>$($_.AgentClass)</td>
              <td>$($_.Finding)</td>
            </tr>"
        }

        $html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Federal AI Identity Governance Scan — $agencyDisp</title>
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 2rem; background: #fff; color: #1a1a2e; }
  h1   { color: #1a2a6c; }
  h2   { color: #1a2a6c; margin-top: 2rem; }
  .gate { font-size: 1.4rem; font-weight: bold; color: $gateColor; }
  table { border-collapse: collapse; width: 100%; font-size: 0.85rem; }
  th    { background: #1a2a6c; color: #fff; padding: 0.5rem 0.75rem; text-align: left; }
  td    { border-bottom: 1px solid #e0e0e0; padding: 0.4rem 0.75rem; vertical-align: top; }
  tr:nth-child(even) { background: #f8f9fa; }
  .summary-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.5rem 0; }
  .metric { background: #f0f4ff; border-left: 4px solid #1a2a6c; padding: 1rem; border-radius: 4px; }
  .metric .label { font-size: 0.8rem; color: #555; text-transform: uppercase; }
  .metric .value { font-size: 1.8rem; font-weight: bold; color: #1a2a6c; }
  code { background: #f0f0f0; padding: 0.1rem 0.3rem; border-radius: 2px; font-size: 0.8rem; }
  .note { background: #fff8e1; border-left: 4px solid #f39c12; padding: 1rem; margin: 1rem 0; border-radius: 4px; }
</style>
</head>
<body>
<h1>Federal AI Identity Governance Scan</h1>
<p><strong>Agency:</strong> $agencyDisp &nbsp;|&nbsp;
   <strong>Scanned:</strong> $scannedAt &nbsp;|&nbsp;
   <strong>Source:</strong> OMB 2025 Federal AI Use Case Inventory</p>
<p class="gate">Gate: $gateDecision</p>

<div class="summary-grid">
  <div class="metric"><div class="label">Live Systems Scanned</div><div class="value">$($live.Count)</div></div>
  <div class="metric"><div class="label">P1 Findings (halt)</div><div class="value" style="color:#c0392b">$p1Count</div></div>
  <div class="metric"><div class="label">P2 Findings (remediate)</div><div class="value" style="color:#e67e22">$p2Count</div></div>
  <div class="metric"><div class="label">Agentic Ungoverned (P1)</div><div class="value" style="color:#c0392b">$agenticP1</div></div>
  <div class="metric"><div class="label">ATO Gaps (P2)</div><div class="value">$atoGaps</div></div>
  <div class="metric"><div class="label">Unowned Systems (P2)</div><div class="value">$unowned</div></div>
</div>

<div class="note">
  <strong>Scan basis:</strong> UIAO_196 / ADR-109. Six drift classes, L1 (observe only).
  P1 findings require immediate action before any automated remediation pass.
  P2 findings are routed to the bureau identity governance coordinator.
</div>

<h2>Findings</h2>
<table>
<thead>
  <tr>
    <th>Sev</th><th>Drift Class</th><th>System</th><th>Agency</th>
    <th>Bureau</th><th>OrgPath</th><th>ATO</th><th>Type</th><th>Finding</th>
  </tr>
</thead>
<tbody>
$($findingRows -join "`n")
</tbody>
</table>

<p style="margin-top:2rem;font-size:0.75rem;color:#888">
  Generated by Invoke-AIInventoryScan.ps1 v1.0.0 &mdash; UIAO_196 / ADR-109 &mdash;
  <a href="https://github.com/WhalerMike/uiao">github.com/WhalerMike/uiao</a>
</p>
</body>
</html>
"@
        $html | Set-Content -Path $OutputPath -Encoding UTF8
        Write-Host "      HTML report written: $OutputPath" -ForegroundColor Green
    }

    default {
        Write-Warning "Unknown extension '$ext'. Writing CSV to $OutputPath"
        $findings | Export-Csv -Path $OutputPath -NoTypeInformation -Encoding UTF8
    }
}

Write-Host ""
Write-Host "Done. To add OrgPath governance, see the UIAO governed path:" -ForegroundColor Cyan
Write-Host "  https://github.com/WhalerMike/uiao/docs/customer-documents/operational-guides/ai-identity-governance/governed-path.qmd" -ForegroundColor Gray
