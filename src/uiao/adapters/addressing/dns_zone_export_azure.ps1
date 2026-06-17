<#
.SYNOPSIS
    Export Azure DNS zones (Public + Private) to the UIAO addressing-collector
    JSON format.  No Domain Controller or RSAT required.

.DESCRIPTION
    Uses the Azure CLI (az) to pull record sets from Azure DNS Public zones
    and Azure Private DNS zones in one or more subscriptions, then normalises
    them to the flat record list that addressing_collector.py expects.

    Outputs (written to -OutputDirectory):
      observed_zone.json   flat record list  (input for addressing_collector.py)
      resources.json       live host/IP inventory derived from A/AAAA records
      zone_manifest.json   metadata: zone name, type (public|private), resource group

    Prerequisites:
      az login  (or az login --use-device-code for headless)
      Contributor or DNS Zone Contributor on the target subscriptions/RGs

    GCC-Moderate note:
      Set your cloud BEFORE running:
        az cloud set --name AzureUSGovernment   # Azure Government workloads
        az cloud set --name AzureCloud          # M365 GCC-Moderate (commercial infra)
      If you use both, run the script twice with different -AzureCloud values
      and merge the outputs with dns_zone_merge.ps1 (companion).

    Canon reference: UIAO_195, ADR-108

.PARAMETER SubscriptionId
    One or more subscription IDs to scan.
    Defaults to the current az account subscription.

.PARAMETER ResourceGroup
    Limit scan to a specific resource group.
    If omitted, all RGs in the subscription(s) are scanned.

.PARAMETER ZoneName
    Limit to specific zone name(s).  Supports wildcards (e.g. "*.agency.gov").
    If omitted, all zones are exported.

.PARAMETER ZoneType
    Which zone type(s) to export: Public, Private, or Both.  Default: Both.

.PARAMETER AzureCloud
    Azure cloud environment.  Passed to `az cloud set`.
    Values: AzureCloud (default) | AzureUSGovernment | AzureChinaCloud
    If already set correctly, omit this parameter.

.PARAMETER OutputDirectory
    Directory to write output files.  Created if absent.  Default: .\dns-audit.

.EXAMPLE
    # Export all DNS zones from current subscription (commercial / GCC-M)
    .\dns_zone_export_azure.ps1 -OutputDirectory C:\Temp\dns-audit

.EXAMPLE
    # Export Azure Government workload zones
    .\dns_zone_export_azure.ps1 `
        -AzureCloud AzureUSGovernment `
        -SubscriptionId "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" `
        -OutputDirectory C:\Temp\dns-audit-gov

.EXAMPLE
    # Export only private DNS zones from a specific RG
    .\dns_zone_export_azure.ps1 `
        -ResourceGroup rg-networking `
        -ZoneType Private `
        -OutputDirectory .\dns-audit
#>
[CmdletBinding()]
param(
    [string[]] $SubscriptionId,
    [string]   $ResourceGroup,
    [string[]] $ZoneName,
    [ValidateSet("Public", "Private", "Both")]
    [string]   $ZoneType        = "Both",
    [ValidateSet("AzureCloud", "AzureUSGovernment", "AzureChinaCloud")]
    [string]   $AzureCloud,
    [string]   $OutputDirectory = ".\dns-audit"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step([string]$msg) { Write-Host "[dns_zone_export_azure] $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Warning "[dns_zone_export_azure] $msg" }

function Assert-AzCli {
    if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
        throw "Azure CLI (az) not found on PATH.  Install from https://learn.microsoft.com/cli/azure/install-azure-cli"
    }
    $account = az account show 2>$null | ConvertFrom-Json
    if (-not $account) {
        throw "Not logged in to Azure CLI.  Run: az login  (or: az login --use-device-code)"
    }
    Write-Step "Authenticated as: $($account.user.name)  tenant: $($account.tenantId)"
    return $account
}

function Invoke-Az([string[]]$args) {
    $result = az @args 2>&1
    if ($LASTEXITCODE -ne 0) {
        $msg = $result -join " "
        Write-Warn "az $($args -join ' ')  exited $LASTEXITCODE: $msg"
        return $null
    }
    return $result | ConvertFrom-Json
}

function Normalise-FlatRecord {
    param([object]$rs, [string]$zoneFqdn, [string]$zoneType)

    $rname  = $rs.name
    # "@" = zone apex
    $fqdn   = if ($rname -eq "@") { $zoneFqdn } else { "$rname.$zoneFqdn" }
    $fqdn   = $fqdn.ToLower().TrimEnd(".")
    $ttl    = [int]($rs.TTL ?? $rs.properties.TTL ?? 300)

    $records = [System.Collections.Generic.List[object]]::new()

    # A records
    foreach ($r in @($rs.ARecords ?? $rs.properties.ARecords ?? @())) {
        $records.Add([ordered]@{ name = $fqdn; type = "A";    ttl = $ttl; value = $r.ipv4Address }) | Out-Null
    }
    # AAAA records
    foreach ($r in @($rs.AaaaRecords ?? $rs.properties.AaaaRecords ?? @())) {
        $records.Add([ordered]@{ name = $fqdn; type = "AAAA"; ttl = $ttl; value = $r.ipv6Address }) | Out-Null
    }
    # CNAME
    $cn = $rs.CNAMERecord ?? $rs.properties.CNAMERecord
    if ($cn) {
        $records.Add([ordered]@{ name = $fqdn; type = "CNAME"; ttl = $ttl; value = $cn.cname.TrimEnd(".") }) | Out-Null
    }
    # MX
    foreach ($r in @($rs.MXRecords ?? $rs.properties.MXRecords ?? @())) {
        $records.Add([ordered]@{ name = $fqdn; type = "MX"; ttl = $ttl; value = $r.exchange.TrimEnd(".") }) | Out-Null
    }
    # TXT
    foreach ($r in @($rs.TXTRecords ?? $rs.properties.TXTRecords ?? @())) {
        $val = ($r.value ?? $r.Value) -join " "
        $records.Add([ordered]@{ name = $fqdn; type = "TXT"; ttl = $ttl; value = $val }) | Out-Null
    }
    # NS
    foreach ($r in @($rs.NSRecords ?? $rs.properties.NSRecords ?? @())) {
        $records.Add([ordered]@{ name = $fqdn; type = "NS"; ttl = $ttl; value = $r.nsdname.TrimEnd(".") }) | Out-Null
    }
    # PTR
    foreach ($r in @($rs.PTRRecords ?? $rs.properties.PTRRecords ?? @())) {
        $records.Add([ordered]@{ name = $fqdn; type = "PTR"; ttl = $ttl; value = $r.ptrdname.TrimEnd(".") }) | Out-Null
    }
    # SRV
    foreach ($r in @($rs.SRVRecords ?? $rs.properties.SRVRecords ?? @())) {
        $tgt = "$($r.priority) $($r.weight) $($r.port) $($r.target.TrimEnd('.'))"
        $records.Add([ordered]@{ name = $fqdn; type = "SRV"; ttl = $ttl; target = $tgt }) | Out-Null
    }

    return $records
}

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

if ($AzureCloud) {
    Write-Step "Setting Azure cloud: $AzureCloud"
    az cloud set --name $AzureCloud | Out-Null
}

$account = Assert-AzCli

# Resolve subscription list
if (-not $SubscriptionId) {
    $SubscriptionId = @($account.id)
    Write-Step "Using current subscription: $($SubscriptionId[0])"
}

# ---------------------------------------------------------------------------
# Discover and export zones
# ---------------------------------------------------------------------------

$allRecords   = [System.Collections.Generic.List[object]]::new()
$liveIPs      = [System.Collections.Generic.HashSet[string]]::new()
$liveHosts    = [System.Collections.Generic.HashSet[string]]::new()
$zoneManifest = [System.Collections.Generic.List[object]]::new()

foreach ($subId in $SubscriptionId) {
    Write-Step "Setting subscription: $subId"
    az account set --subscription $subId | Out-Null

    foreach ($type in @("Public", "Private")) {
        if ($ZoneType -ne "Both" -and $ZoneType -ne $type) { continue }

        $azCmd = if ($type -eq "Public") {
            @("network", "dns", "zone", "list")
        } else {
            @("network", "private-dns", "zone", "list")
        }
        if ($ResourceGroup) { $azCmd += @("--resource-group", $ResourceGroup) }

        Write-Step "Listing $type DNS zones in sub $subId..."
        $zones = Invoke-Az $azCmd
        if (-not $zones) { Write-Warn "No $type zones found or access denied"; continue }

        # Filter by ZoneName pattern if specified
        if ($ZoneName) {
            $zones = $zones | Where-Object {
                $zn = $_.name
                $ZoneName | Where-Object { $zn -like $_ }
            }
        }

        Write-Step "  Found $($zones.Count) $type zone(s)"

        foreach ($zone in $zones) {
            $zname = $zone.name
            $rg    = $zone.resourceGroup ?? ($zone.id -split "/resourceGroups/")[1].Split("/")[0]

            Write-Step "  Exporting $type zone: $zname (RG: $rg)"
            $zoneManifest.Add([ordered]@{
                name           = $zname
                type           = $type.ToLower()
                resource_group = $rg
                subscription   = $subId
                record_count   = $zone.numberOfRecordSets ?? "?"
            }) | Out-Null

            $rsCmd = if ($type -eq "Public") {
                @("network", "dns", "record-set", "list",
                  "--resource-group", $rg, "--zone-name", $zname)
            } else {
                @("network", "private-dns", "record-set", "list",
                  "--resource-group", $rg, "--zone-name", $zname)
            }

            $recordSets = Invoke-Az $rsCmd
            if (-not $recordSets) {
                Write-Warn "    No record sets returned for $zname"
                continue
            }

            $count = 0
            foreach ($rs in $recordSets) {
                $flat = Normalise-FlatRecord -rs $rs -zoneFqdn $zname -zoneType $type
                foreach ($r in $flat) {
                    $allRecords.Add($r) | Out-Null
                    if ($r.type -eq "A")    { $liveIPs.Add($r.value) | Out-Null; $liveHosts.Add($r.name) | Out-Null }
                    if ($r.type -eq "AAAA") { $liveIPs.Add($r.value) | Out-Null; $liveHosts.Add($r.name) | Out-Null }
                    $count++
                }
            }
            Write-Step "    $count records exported"
        }
    }
}

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------

$zonePath      = Join-Path $OutputDirectory "observed_zone.json"
$resourcesPath = Join-Path $OutputDirectory "resources.json"
$manifestPath  = Join-Path $OutputDirectory "zone_manifest.json"

$allRecords | ConvertTo-Json -Depth 5 |
    Set-Content -Path $zonePath -Encoding UTF8
Write-Step "Wrote: $zonePath  ($($allRecords.Count) records)"

[ordered]@{
    exported_at  = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    azure_cloud  = if ($AzureCloud) { $AzureCloud } else { "AzureCloud (default)" }
    subscription = $SubscriptionId
    ips          = @($liveIPs  | Sort-Object)
    hosts        = @($liveHosts | Sort-Object)
} | ConvertTo-Json -Depth 5 |
    Set-Content -Path $resourcesPath -Encoding UTF8
Write-Step "Wrote: $resourcesPath  ($($liveIPs.Count) IPs, $($liveHosts.Count) hosts)"

$zoneManifest | ConvertTo-Json -Depth 5 |
    Set-Content -Path $manifestPath -Encoding UTF8
Write-Step "Wrote: $manifestPath  ($($zoneManifest.Count) zone(s))"

Write-Step ""
Write-Step "Total: $($allRecords.Count) records across $($zoneManifest.Count) zones"
Write-Step ""
Write-Step "Next: populate intended_bindings.json, then run:"
Write-Step "  python addressing_collector.py --intended intended_bindings.json --zone $zonePath --resources $resourcesPath"
