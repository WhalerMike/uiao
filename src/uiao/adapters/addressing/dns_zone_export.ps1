<#
.SYNOPSIS
    Export AD-integrated DNS zones to the UIAO addressing-collector JSON format.

.DESCRIPTION
    Runs on a Domain Controller (or any machine with RSAT DNS Server Tools).
    Exports all records from one or more zones and writes:
      observed_zone.json   flat record list (input for addressing_collector.py)
      resources.json       live host/IP inventory derived from A/AAAA records

    For Azure DNS zones, use dns_zone_export_azure.ps1 (companion script).

    Canon reference: UIAO_195, ADR-108

.PARAMETER ZoneName
    One or more AD DNS zone names to export (e.g. "agency.gov", "10.in-addr.arpa").
    If omitted, exports all primary zones on the target server.

.PARAMETER DnsServer
    DNS server to query.  Defaults to localhost.

.PARAMETER OutputDirectory
    Directory to write output files.  Created if absent.  Defaults to .\dns-audit.

.PARAMETER IncludeReverse
    Include reverse-lookup (in-addr.arpa) zones.  Default: false.

.EXAMPLE
    # Export primary forward zone from local DC
    .\dns_zone_export.ps1 -ZoneName "agency.gov" -OutputDirectory C:\Temp\dns-audit

.EXAMPLE
    # Export all zones (including reverse) from a remote DC
    .\dns_zone_export.ps1 -DnsServer dc01.agency.gov -IncludeReverse -OutputDirectory .\audit
#>
[CmdletBinding()]
param(
    [string[]] $ZoneName,
    [string]   $DnsServer        = "localhost",
    [string]   $OutputDirectory  = ".\dns-audit",
    [switch]   $IncludeReverse
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step([string]$msg) { Write-Host "[dns_zone_export] $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Warning "[dns_zone_export] $msg" }

function ConvertTo-FlatRecord {
    param([Microsoft.Management.Infrastructure.CimInstance]$rec, [string]$zoneFqdn)
    $name = if ($rec.HostName -eq "@") { $zoneFqdn } else { "$($rec.HostName).$zoneFqdn" }
    $type = $rec.RecordType
    $ttl  = [int]$rec.TimeToLive.TotalSeconds

    $value = switch ($type) {
        "A"     { $rec.RecordData.IPv4Address.IPAddressToString }
        "AAAA"  { $rec.RecordData.IPv6Address.IPAddressToString }
        "CNAME" { $rec.RecordData.HostNameAlias.TrimEnd(".") }
        "MX"    { $rec.RecordData.MailExchange.TrimEnd(".") }
        "NS"    { $rec.RecordData.NameServer.TrimEnd(".") }
        "PTR"   { $rec.RecordData.PtrDomainName.TrimEnd(".") }
        "TXT"   { ($rec.RecordData.DescriptiveText -join " ") }
        "SRV"   { $null }  # SRV uses 'target' field below
        default { $null }
    }

    $out = [ordered]@{
        name = $name.ToLower()
        type = $type
        ttl  = $ttl
    }

    if ($type -eq "SRV") {
        $out["target"] = "$($rec.RecordData.Priority) $($rec.RecordData.Weight) $($rec.RecordData.Port) $($rec.RecordData.DomainName.TrimEnd('.'))"
    } elseif ($null -ne $value) {
        $out["value"] = $value
    } else {
        return $null  # unsupported type — skip
    }
    return $out
}

# ---------------------------------------------------------------------------
# Resolve zone list
# ---------------------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

Write-Step "Connecting to DNS server: $DnsServer"

if (-not $ZoneName) {
    Write-Step "No zones specified — enumerating primary zones on $DnsServer"
    $allZones = Get-DnsServerZone -ComputerName $DnsServer |
        Where-Object { $_.ZoneType -eq "Primary" -and -not $_.IsAutoCreated }
    if (-not $IncludeReverse) {
        $allZones = $allZones | Where-Object { $_.ZoneName -notlike "*.arpa" }
    }
    $ZoneName = $allZones | Select-Object -ExpandProperty ZoneName
    Write-Step "Found $($ZoneName.Count) zone(s): $($ZoneName -join ', ')"
}

# ---------------------------------------------------------------------------
# Export records
# ---------------------------------------------------------------------------

$allRecords  = [System.Collections.Generic.List[object]]::new()
$liveIPs     = [System.Collections.Generic.HashSet[string]]::new()
$liveHosts   = [System.Collections.Generic.HashSet[string]]::new()
$skipped     = 0
$total       = 0

foreach ($zone in $ZoneName) {
    Write-Step "Exporting zone: $zone"
    try {
        $recs = Get-DnsServerResourceRecord -ComputerName $DnsServer -ZoneName $zone
    } catch {
        Write-Warn "Failed to read zone '$zone': $_  — skipping"
        continue
    }

    foreach ($rec in $recs) {
        $total++
        $flat = ConvertTo-FlatRecord -rec $rec -zoneFqdn $zone
        if ($null -eq $flat) { $skipped++; continue }

        $allRecords.Add($flat)

        # Build live inventory for dangling detection
        if ($rec.RecordType -eq "A") {
            $liveIPs.Add($flat.value) | Out-Null
            $liveHosts.Add($flat.name) | Out-Null
        } elseif ($rec.RecordType -eq "AAAA") {
            $liveIPs.Add($flat.value) | Out-Null
            $liveHosts.Add($flat.name) | Out-Null
        }
    }
    Write-Step "  ${zone}: $($recs.Count) records read"
}

Write-Step "Total: $total records read, $skipped skipped (unsupported type), $($allRecords.Count) exported"

# ---------------------------------------------------------------------------
# Write outputs
# ---------------------------------------------------------------------------

$zonePath      = Join-Path $OutputDirectory "observed_zone.json"
$resourcesPath = Join-Path $OutputDirectory "resources.json"

$allRecords | ConvertTo-Json -Depth 5 |
    Set-Content -Path $zonePath -Encoding UTF8
Write-Step "Wrote: $zonePath ($($allRecords.Count) records)"

[ordered]@{
    exported_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
    dns_server  = $DnsServer
    zones       = @($ZoneName)
    ips         = @($liveIPs | Sort-Object)
    hosts       = @($liveHosts | Sort-Object)
} | ConvertTo-Json -Depth 5 |
    Set-Content -Path $resourcesPath -Encoding UTF8
Write-Step "Wrote: $resourcesPath ($($liveIPs.Count) IPs, $($liveHosts.Count) hosts)"

Write-Step ""
Write-Step "Next: populate intended_bindings.json (see sample/ for schema), then run:"
Write-Step "  python addressing_collector.py --intended intended_bindings.json --zone $zonePath --resources $resourcesPath"
