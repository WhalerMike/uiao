<#
.SYNOPSIS
    UIAO addressing-plane audit orchestrator.  Runs the full diagnostic
    pipeline: zone export → drift classification → horizon probe → report.

.DESCRIPTION
    Wraps the zone exporter, addressing_collector.py, and
    Invoke-DnsHorizonProbe.ps1 into a single runnable command.

    Zone export source (choose one — no AD/DC required for Azure mode):
      Azure DNS (default)  dns_zone_export_azure.ps1  requires: az login
      AD / RSAT            dns_zone_export.ps1         requires: DC or RSAT tools

    Python 3.x must be on PATH.

    Outputs (all in -OutputDirectory):
      observed_zone.json       exported DNS records
      resources.json           live host/IP inventory
      zone_manifest.json       zone metadata (Azure mode only)
      findings.json            drift-classifier findings (drift_core format)
      horizon_findings.json    DRIFT-HORIZON findings
      horizon_report.txt       human-readable horizon summary
      audit_summary.txt        overall gate decision + finding counts

    Canon reference: UIAO_195, ADR-108

.PARAMETER ZoneName
    DNS zone name(s) to export.  Supports wildcards (Azure mode).
    If omitted, all zones in the subscription / all primary forward zones (AD mode).

.PARAMETER SubscriptionId
    Azure subscription ID(s).  Azure mode only.  Defaults to current az account.

.PARAMETER ResourceGroup
    Limit Azure export to a specific resource group.  Azure mode only.

.PARAMETER ZoneType
    Which Azure zone types to export: Public, Private, or Both.
    Azure mode only.  Default: Both.

.PARAMETER AzureCloud
    Azure cloud environment: AzureCloud | AzureUSGovernment.
    Azure mode only.  If omitted, uses current az cloud setting.
    GCC-Moderate = AzureCloud (commercial infra).
    Azure Government workloads = AzureUSGovernment.

.PARAMETER UseAdDnsExport
    Switch to AD/DC mode (dns_zone_export.ps1).  Requires RSAT DNS tools.
    If set, -DnsServer is used instead of Azure CLI.

.PARAMETER DnsServer
    AD DNS server to query.  AD mode only.  Default: localhost.

.PARAMETER IntendedBindingsPath
    Path to your intended_bindings.json SSOT manifest.
    Use src\uiao\adapters\addressing\sample\intended_bindings.json as a
    template — copy and populate with your agency's governed names.

.PARAMETER ExternalResolver
    Public resolver for horizon probe external vantage.  Default: 8.8.8.8.

.PARAMETER PrivateResolverIP
    Azure DNS Private Resolver inbound endpoint IP.
    Enables per-VNet vantage comparison in the horizon probe.

.PARAMETER OutputDirectory
    Audit output directory.  Created if absent.  Default: .\dns-audit.

.PARAMETER SkipHorizonProbe
    Skip the multi-vantage horizon probe (zone-file drift only).

.EXAMPLE
    # Azure mode — full audit, GCC-Moderate subscription
    .\Invoke-AddressingAudit.ps1 `
        -IntendedBindingsPath .\intended_bindings.json `
        -PrivateResolverIP 10.0.0.4 `
        -OutputDirectory C:\Temp\dns-audit-$(Get-Date -Format 'yyyy-MM-dd')

.EXAMPLE
    # Azure mode — specific zone, Azure Government cloud
    .\Invoke-AddressingAudit.ps1 `
        -ZoneName "agency.gov" `
        -AzureCloud AzureUSGovernment `
        -IntendedBindingsPath .\intended_bindings.json `
        -OutputDirectory .\dns-audit-gov

.EXAMPLE
    # AD/DC mode — zone-file drift only, no horizon probe
    .\Invoke-AddressingAudit.ps1 `
        -UseAdDnsExport `
        -ZoneName "agency.gov" `
        -IntendedBindingsPath .\intended_bindings.json `
        -SkipHorizonProbe `
        -OutputDirectory .\dns-audit
#>
[CmdletBinding()]
param(
    # Shared
    [string[]] $ZoneName,
    [string]   $IntendedBindingsPath,
    [string]   $ExternalResolver     = "8.8.8.8",
    [string]   $PrivateResolverIP,
    [string]   $OutputDirectory      = ".\dns-audit",
    [switch]   $SkipHorizonProbe,
    # Azure mode (default)
    [string[]] $SubscriptionId,
    [string]   $ResourceGroup,
    [ValidateSet("Public","Private","Both")]
    [string]   $ZoneType             = "Both",
    [ValidateSet("AzureCloud","AzureUSGovernment","AzureChinaCloud")]
    [string]   $AzureCloud,
    # AD/DC mode (opt-in)
    [switch]   $UseAdDnsExport,
    [string]   $DnsServer            = "localhost"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Banner([string]$msg) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor Cyan
}
function Write-Step([string]$msg) { Write-Host "[audit] $msg" -ForegroundColor White }

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ" -AsUTC

# ---------------------------------------------------------------------------
# Step 1 — Zone export
# ---------------------------------------------------------------------------

Write-Banner "Step 1 of 3: DNS Zone Export"

if ($UseAdDnsExport) {
    Write-Step "Mode: AD/DC  (dns_zone_export.ps1)  server=$DnsServer"
    $exportArgs = @{ DnsServer = $DnsServer; OutputDirectory = $OutputDirectory }
    if ($ZoneName) { $exportArgs["ZoneName"] = $ZoneName }
    & "$ScriptDir\dns_zone_export.ps1" @exportArgs
} else {
    Write-Step "Mode: Azure DNS  (dns_zone_export_azure.ps1)"
    $exportArgs = @{ OutputDirectory = $OutputDirectory; ZoneType = $ZoneType }
    if ($ZoneName)        { $exportArgs["ZoneName"]        = $ZoneName }
    if ($SubscriptionId)  { $exportArgs["SubscriptionId"]  = $SubscriptionId }
    if ($ResourceGroup)   { $exportArgs["ResourceGroup"]   = $ResourceGroup }
    if ($AzureCloud)      { $exportArgs["AzureCloud"]      = $AzureCloud }
    & "$ScriptDir\dns_zone_export_azure.ps1" @exportArgs
}

$zonePath      = Join-Path $OutputDirectory "observed_zone.json"
$resourcesPath = Join-Path $OutputDirectory "resources.json"

if (-not (Test-Path $zonePath)) {
    Write-Error "Zone export did not produce observed_zone.json — aborting"
}

# ---------------------------------------------------------------------------
# Step 2 — Drift classification (Python collector)
# ---------------------------------------------------------------------------

Write-Banner "Step 2 of 3: Drift Classification"

# Resolve intended_bindings.json
if ($IntendedBindingsPath -and (Test-Path $IntendedBindingsPath)) {
    $bindingsPath = $IntendedBindingsPath
} elseif (Test-Path (Join-Path $OutputDirectory "intended_bindings.json")) {
    $bindingsPath = Join-Path $OutputDirectory "intended_bindings.json"
} else {
    $samplePath = Join-Path $ScriptDir "sample\intended_bindings.json"
    Write-Warning "No intended_bindings.json found — using sample template."
    Write-Warning "Copy $samplePath, populate it with your governed names, and re-run."
    $bindingsPath = $samplePath
}

Write-Step "Using intended bindings: $bindingsPath"
Write-Step "Running: python addressing_collector.py"

$collectorScript = Join-Path $ScriptDir "addressing_collector.py"
$findingsPath    = Join-Path $OutputDirectory "findings.json"

$pythonArgs = @(
    $collectorScript
    "--intended", $bindingsPath
    "--zone",     $zonePath
    "--resources", $resourcesPath
    "--output",   $findingsPath
)

# addressing_collector.py currently uses __main__ with hardcoded paths.
# Pass paths as env vars so the collector can pick them up when called
# with explicit paths; the CLI arg support is added below.
$env:UIAO_INTENDED  = $bindingsPath
$env:UIAO_ZONE      = $zonePath
$env:UIAO_RESOURCES = $resourcesPath
$env:UIAO_OUTPUT    = $findingsPath

python $collectorScript 2>&1 | Tee-Object -Variable collectorOut

# Check exit code
if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
    Write-Warning "Collector exited with code $LASTEXITCODE (P1 findings present — expected)"
}

# Parse gate result from output
$gateLine = $collectorOut | Where-Object { $_ -like "GATE:*" } | Select-Object -Last 1
Write-Step "Classifier gate: $gateLine"

# ---------------------------------------------------------------------------
# Step 3 — Horizon probe (optional)
# ---------------------------------------------------------------------------

$horizonDecision = "SKIPPED"
$horizonP1       = 0
$horizonP2       = 0

if (-not $SkipHorizonProbe) {
    Write-Banner "Step 3 of 3: DRIFT-HORIZON Multi-Vantage Probe"

    $horizonArgs = @{
        ExternalResolver = $ExternalResolver
        OutputDirectory  = $OutputDirectory
    }
    if ($IntendedBindingsPath -and (Test-Path $IntendedBindingsPath)) {
        $horizonArgs["IntendedBindingsPath"] = $bindingsPath
    }
    if ($PrivateResolverIP) { $horizonArgs["PrivateResolverIP"] = $PrivateResolverIP }

    try {
        & "$ScriptDir\Invoke-DnsHorizonProbe.ps1" @horizonArgs
        $horizonDecision = "PASS"
    } catch {
        $horizonDecision = "HALT"
    }

    $hPath = Join-Path $OutputDirectory "horizon_findings.json"
    if (Test-Path $hPath) {
        $hf = Get-Content $hPath -Raw | ConvertFrom-Json
        $horizonP1 = @($hf | Where-Object { $_.severity -eq "P1" }).Count
        $horizonP2 = @($hf | Where-Object { $_.severity -eq "P2" }).Count
        $horizonDecision = if ($horizonP1 -gt 0) { "HALT" } else { "PASS" }
    }
} else {
    Write-Step "Horizon probe skipped (-SkipHorizonProbe)"
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Banner "Audit Summary"

$classifierHalt = $gateLine -like "*HALT*"
$overallDecision = if ($classifierHalt -or $horizonDecision -eq "HALT") { "HALT" } else { "PASS" }

$exportMode = if ($UseAdDnsExport) { "AD/DC ($DnsServer)" } else { "Azure DNS ($(if ($AzureCloud) { $AzureCloud } else { 'current cloud' }))" }
$summary = @(
    "UIAO Addressing-Plane Audit Summary"
    "Generated : $timestamp"
    "Export    : $exportMode"
    "Zone(s)   : $(if ($ZoneName) { $ZoneName -join ', ' } else { '(all)' })"
    ""
    "Step 1 — Zone Export     : DONE  ($zonePath)"
    "Step 2 — Drift Classifier: $gateLine"
    "Step 3 — Horizon Probe   : $horizonDecision  (P1=$horizonP1  P2=$horizonP2)"
    ""
    "OVERALL GATE: $overallDecision"
    ""
    "Outputs:"
    "  $zonePath"
    "  $resourcesPath"
    "  $findingsPath"
    "  $(Join-Path $OutputDirectory 'horizon_findings.json')"
    "  $(Join-Path $OutputDirectory 'horizon_report.txt')"
    ""
    "Deferred (not yet observable from a zone file + local probe):"
    "  DRIFT-CAA/TLSA   : requires endpoint cert inspection vs governed CA set"
    "  DRIFT-DELEGATION : requires parent-NS delegation walk + glue validation"
    ""
    "Next steps if HALT:"
    "  P1 DRIFT-DANGLING/BINDING  : remove or correct records pointing at absent resources"
    "  P1 DRIFT-SRV               : verify DC SRV registration; check _tcp zones"
    "  P1 DRIFT-HORIZON (bypass)  : add conditional forwarder on DCs for each BYPASS zone"
    "                               pointing at Private Resolver inbound endpoint"
    "  P1 DRIFT-CONFLICT          : remove non-CNAME record coexisting with CNAME"
)

$summaryPath = Join-Path $OutputDirectory "audit_summary.txt"
$summary | Set-Content -Path $summaryPath -Encoding UTF8
$summary | ForEach-Object { Write-Host $_ }

Write-Host ""
if ($overallDecision -eq "HALT") {
    Write-Host "GATE: HALT — remediation required before deployment." -ForegroundColor Red
    exit 1
} else {
    Write-Host "GATE: PASS" -ForegroundColor Green
    exit 0
}
