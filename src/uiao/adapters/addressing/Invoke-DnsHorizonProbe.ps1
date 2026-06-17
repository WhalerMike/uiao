<#
.SYNOPSIS
    Multi-vantage DNS resolution probe — detects Private Link bypass and
    split-horizon boundary leaks (DRIFT-HORIZON class, UIAO_195).

.DESCRIPTION
    Queries each governed name from multiple vantage points and compares
    the answers.  A "boundary leak" is when a name that should resolve to
    a private IP (RFC 1918) from inside the boundary resolves to a public
    IP from any vantage point — or when the answers differ unexpectedly
    across vantage points.

    Vantage points:
      Internal   — the local machine's resolver (your on-prem DNS / DC)
      External   — a public resolver (default: 8.8.8.8, configurable)
      PerVNet    — a Private Resolver inbound endpoint IP (if provided)

    Private Link detection:
      For each name matching a privatelink.* pattern, verifies the internal
      vantage returns an RFC 1918 address.  If the internal resolver returns
      a public IP, the Private Link forwarder chain is broken (DRIFT-HORIZON P1).

    Outputs:
      horizon_findings.json   UIAO_195 DRIFT-HORIZON findings (drift_core format)
      horizon_report.txt      human-readable summary

    Canon reference: UIAO_195 §3.2, ADR-108

.PARAMETER IntendedBindingsPath
    Path to intended_bindings.json (the SSOT manifest).
    Used to enumerate governed names and their boundary_intent.

.PARAMETER ExternalResolver
    Public DNS resolver IP to use for external vantage.  Default: 8.8.8.8.

.PARAMETER PrivateResolverIP
    Azure DNS Private Resolver inbound endpoint IP.
    If omitted, per-VNet vantage is skipped.

.PARAMETER PrivateLinkNamespaces
    Comma-separated list of privatelink.* namespaces to check beyond those
    in intended_bindings.json.
    Default: the 16 standard Azure Private Link zones.

.PARAMETER OutputDirectory
    Directory to write output files.  Defaults to .\dns-audit.

.EXAMPLE
    .\Invoke-DnsHorizonProbe.ps1 `
        -IntendedBindingsPath .\dns-audit\intended_bindings.json `
        -PrivateResolverIP 10.0.0.4 `
        -OutputDirectory .\dns-audit

.EXAMPLE
    # Quick check without a manifest — probe standard Private Link zones only
    .\Invoke-DnsHorizonProbe.ps1 `
        -PrivateResolverIP 10.0.0.4 `
        -OutputDirectory .\dns-audit
#>
[CmdletBinding()]
param(
    [string]   $IntendedBindingsPath,
    [string]   $ExternalResolver        = "8.8.8.8",
    [string]   $PrivateResolverIP,
    [string[]] $PrivateLinkNamespaces,
    [string]   $OutputDirectory         = ".\dns-audit"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Standard Azure Private Link zones (commercial + GCC-Moderate)
# ---------------------------------------------------------------------------
$DEFAULT_PRIVATELINK_ZONES = @(
    "privatelink.blob.core.windows.net"
    "privatelink.file.core.windows.net"
    "privatelink.queue.core.windows.net"
    "privatelink.table.core.windows.net"
    "privatelink.dfs.core.windows.net"
    "privatelink.web.core.windows.net"
    "privatelink.database.windows.net"
    "privatelink.documents.azure.com"
    "privatelink.vaultcore.azure.net"
    "privatelink.azurewebsites.net"
    "privatelink.servicebus.windows.net"
    "privatelink.azure-devices.net"
    "privatelink.azurecr.io"
    "privatelink.openai.azure.com"
    "privatelink.cognitiveservices.azure.com"
    "privatelink.search.windows.net"
    # GCC-Moderate / Azure Government equivalents
    "privatelink.blob.core.usgovcloudapi.net"
    "privatelink.file.core.usgovcloudapi.net"
    "privatelink.database.usgovcloudapi.net"
    "privatelink.vaultcore.usgovcloudapi.net"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

function Write-Step([string]$msg) { Write-Host "[DnsHorizonProbe] $msg" -ForegroundColor Cyan }
function Write-Warn([string]$msg) { Write-Warning "[DnsHorizonProbe] $msg" }

function Test-RFC1918([string]$ip) {
    if (-not $ip) { return $false }
    try {
        $addr = [System.Net.IPAddress]::Parse($ip)
        $bytes = $addr.GetAddressBytes()
        return ($bytes[0] -eq 10) -or
               ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31) -or
               ($bytes[0] -eq 192 -and $bytes[1] -eq 168)
    } catch { return $false }
}

function Resolve-Via([string]$name, [string]$server) {
    try {
        if ($server -eq "local") {
            $result = Resolve-DnsName -Name $name -Type A -ErrorAction SilentlyContinue
        } else {
            $result = Resolve-DnsName -Name $name -Type A -Server $server -ErrorAction SilentlyContinue
        }
        if (-not $result) { return @{ ips = @(); error = "NXDOMAIN" } }
        $ips = @($result | Where-Object { $_.Type -eq "A" } | Select-Object -ExpandProperty IPAddress)
        return @{ ips = $ips; error = $null }
    } catch {
        return @{ ips = @(); error = $_.Exception.Message }
    }
}

function New-HorizonFinding([string]$name, [string]$intended, [string]$observed, [string]$sev) {
    $plain = "$name|$intended|$observed"
    $hash  = [System.Security.Cryptography.SHA256]::Create().ComputeHash(
        [System.Text.Encoding]::UTF8.GetBytes("addressing|$name|DRIFT-HORIZON|$intended|$observed")
    ) | ForEach-Object { $_.ToString("x2") }
    $id = "DF-" + ($hash -join "")[0..15] -join ""
    return [ordered]@{
        schema       = "drift-core/1.0"
        finding_id   = $id
        plane        = "addressing"
        drift_class  = "DRIFT-HORIZON"
        severity     = $sev
        posture      = "never-autofix"
        name         = $name
        intended     = $intended
        observed     = $observed
        evidence_ref = "Invoke-DnsHorizonProbe"
        detected_at  = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
        provenance   = [ordered]@{
            emitter          = "uiao.addressing.horizon-probe"
            deterministic_id = $true
        }
    }
}

# ---------------------------------------------------------------------------
# Load governed names from manifest
# ---------------------------------------------------------------------------

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

$governedNames  = [System.Collections.Generic.List[hashtable]]::new()
$privateLinkSet = [System.Collections.Generic.HashSet[string]]::new()

if ($IntendedBindingsPath -and (Test-Path $IntendedBindingsPath)) {
    Write-Step "Loading intended bindings from: $IntendedBindingsPath"
    $manifest = Get-Content $IntendedBindingsPath -Raw | ConvertFrom-Json
    foreach ($name in ($manifest.bindings.PSObject.Properties.Name)) {
        $b = $manifest.bindings.$name
        $governedNames.Add(@{
            name           = $name
            target         = $b.target
            boundary_intent = if ($b.PSObject.Properties["boundary_intent"]) { $b.boundary_intent } else { "any" }
        }) | Out-Null
    }
    Write-Step "  $($governedNames.Count) governed names loaded"
} else {
    Write-Warn "No intended_bindings.json provided — will probe Private Link zones only"
}

# Build Private Link namespace set
$plZones = if ($PrivateLinkNamespaces) { $PrivateLinkNamespaces } else { $DEFAULT_PRIVATELINK_ZONES }
foreach ($z in $plZones) { $privateLinkSet.Add($z) | Out-Null }

# ---------------------------------------------------------------------------
# Probe 1: Private Link forwarder chain check
# ---------------------------------------------------------------------------

Write-Step ""
Write-Step "=== Probe 1: Private Link forwarder chain ==="
Write-Step "Checking $($privateLinkSet.Count) privatelink.* zones..."
Write-Step "Internal resolver: (local)"
Write-Step "External resolver: $ExternalResolver"

$findings  = [System.Collections.Generic.List[object]]::new()
$plResults = [System.Collections.Generic.List[object]]::new()

foreach ($zone in ($privateLinkSet | Sort-Object)) {
    # Use a canary name: the zone itself (SOA check) or a test FQDN
    # A zone that has forwarders configured will return NXDOMAIN (not SERVFAIL)
    # A zone with NO forwarder configured will either return the public IP or time out
    $internal = Resolve-Via -name $zone -server "local"
    $external = Resolve-Via -name $zone -server $ExternalResolver

    $internalPublic = $internal.ips | Where-Object { $_ -and -not (Test-RFC1918 $_) }
    $externalIPs    = $external.ips

    $status = if ($internal.error -eq "NXDOMAIN" -and $external.error -ne "NXDOMAIN") {
        "FORWARDER-OK"   # internal NXDOMAIN = zone exists locally (no public answer); external resolves
    } elseif (-not $internal.error -and $internalPublic.Count -gt 0) {
        "BYPASS"         # internal returns public IP = forwarder missing or misconfigured
    } elseif ($internal.error -and $internal.error -ne "NXDOMAIN") {
        "UNREACHABLE"    # internal can't reach zone at all
    } else {
        "UNKNOWN"
    }

    $row = [ordered]@{
        zone              = $zone
        status            = $status
        internal_ips      = $internal.ips
        internal_error    = $internal.error
        external_ips      = $externalIPs
        external_error    = $external.error
    }
    $plResults.Add($row) | Out-Null

    $icon = switch ($status) {
        "FORWARDER-OK"  { "[OK]  " }
        "BYPASS"        { "[P1]  " }
        "UNREACHABLE"   { "[WARN]" }
        default         { "[?]   " }
    }
    Write-Host "  $icon $zone  ($status)" -ForegroundColor $(
        if ($status -eq "BYPASS") { "Red" } elseif ($status -eq "FORWARDER-OK") { "Green" } else { "Yellow" }
    )

    if ($status -eq "BYPASS") {
        $findings.Add((New-HorizonFinding `
            -name    $zone `
            -intended "privatelink.* zone resolves to RFC1918 from internal vantage (forwarder present)" `
            -observed "internal resolver returned public IP(s): $($internalPublic -join ', ') — forwarder chain broken; traffic bypasses Private Link" `
            -sev     "P1"
        )) | Out-Null
    }
}

$bypassCount = ($plResults | Where-Object { $_.status -eq "BYPASS" }).Count
Write-Step "Private Link result: $bypassCount of $($privateLinkSet.Count) zone(s) show forwarder bypass (P1)"

# ---------------------------------------------------------------------------
# Probe 2: Governed-name answer consistency
# ---------------------------------------------------------------------------

if ($governedNames.Count -gt 0) {
    Write-Step ""
    Write-Step "=== Probe 2: Governed-name answer consistency ==="

    foreach ($entry in $governedNames) {
        $name   = $entry.name
        $intent = $entry.boundary_intent  # "private" | "gcc-moderate" | "any"

        $internal = Resolve-Via -name $name -server "local"
        $external = Resolve-Via -name $name -server $ExternalResolver

        # Private-intent name should NOT be resolvable from external vantage
        if ($intent -eq "private" -and $external.ips.Count -gt 0) {
            $findings.Add((New-HorizonFinding `
                -name     $name `
                -intended "private-intent name: no answer from external vantage" `
                -observed "external resolver ($ExternalResolver) returned: $($external.ips -join ', ') — name is publicly resolvable; boundary-intent violation" `
                -sev      "P1"
            )) | Out-Null
            Write-Host "  [P1]   $name  — private-intent but publicly resolvable" -ForegroundColor Red
            continue
        }

        # Any governed name: flag if internal and external answers diverge unexpectedly
        $internalSet = [System.Collections.Generic.HashSet[string]]($internal.ips)
        $externalSet = [System.Collections.Generic.HashSet[string]]($external.ips)
        $onlyInternal = $internal.ips | Where-Object { $_ -notin $external.ips }
        $onlyExternal = $external.ips | Where-Object { $_ -notin $internal.ips }

        if ($onlyInternal.Count -gt 0 -or $onlyExternal.Count -gt 0) {
            $sev = if (($onlyInternal | Where-Object { Test-RFC1918 $_ }) -and
                       ($onlyExternal | Where-Object { -not (Test-RFC1918 $_) })) {
                "P2"  # expected split-horizon — different answers by design
            } else {
                "P2"  # unexpected divergence
            }
            $observed = "internal: $($internal.ips -join ',')  external: $($external.ips -join ',')"
            $findings.Add((New-HorizonFinding `
                -name     $name `
                -intended "consistent answer across vantage points (or documented split-horizon)" `
                -observed $observed `
                -sev      $sev
            )) | Out-Null
            Write-Host "  [P2]   $name  — answers diverge (split-horizon candidate, verify intent)" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK]   $name  — consistent" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Probe 3: Per-VNet (Private Resolver) vantage (if endpoint provided)
# ---------------------------------------------------------------------------

if ($PrivateResolverIP) {
    Write-Step ""
    Write-Step "=== Probe 3: Private Resolver vantage ($PrivateResolverIP) ==="
    Write-Step "Comparing internal (local) vs Private Resolver answers for governed names..."

    foreach ($entry in ($governedNames | Select-Object -First 20)) {
        $name     = $entry.name
        $internal = Resolve-Via -name $name -server "local"
        $vnet     = Resolve-Via -name $name -server $PrivateResolverIP

        if ($internal.ips -join "," -ne $vnet.ips -join ",") {
            $findings.Add((New-HorizonFinding `
                -name     $name `
                -intended "on-prem resolver and Private Resolver return same answer" `
                -observed "local: $($internal.ips -join ',')  private-resolver: $($vnet.ips -join ',') — resolver chain inconsistency" `
                -sev      "P2"
            )) | Out-Null
            Write-Host "  [P2]   $name  — local vs Private Resolver diverge" -ForegroundColor Yellow
        } else {
            Write-Host "  [OK]   $name  — consistent with Private Resolver" -ForegroundColor Green
        }
    }
}

# ---------------------------------------------------------------------------
# Gate + output
# ---------------------------------------------------------------------------

$p1 = @($findings | Where-Object { $_.severity -eq "P1" })
$p2 = @($findings | Where-Object { $_.severity -eq "P2" })
$decision = if ($p1.Count -gt 0) { "HALT" } else { "PASS" }

Write-Step ""
Write-Step "=== GATE: $decision   P1=$($p1.Count)  P2=$($p2.Count) ==="

$findingsPath = Join-Path $OutputDirectory "horizon_findings.json"
$reportPath   = Join-Path $OutputDirectory "horizon_report.txt"

$findings | ConvertTo-Json -Depth 8 |
    Set-Content -Path $findingsPath -Encoding UTF8
Write-Step "Findings written to: $findingsPath"

# Human-readable report
$report = @()
$report += "UIAO Addressing-Plane DRIFT-HORIZON Report"
$report += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss UTC' -AsUTC)"
$report += "Gate: $decision   P1=$($p1.Count)  P2=$($p2.Count)"
$report += ""
$report += "--- Private Link Forwarder Status ---"
foreach ($r in $plResults) {
    $report += "  $($r.status.PadRight(14)) $($r.zone)"
}
$report += ""
$report += "--- Findings ---"
foreach ($f in $findings) {
    $report += "[$($f.severity)] $($f.name)"
    $report += "     intended: $($f.intended)"
    $report += "     observed: $($f.observed)"
}
if ($findings.Count -eq 0) { $report += "  (none)" }
$report += ""
$report += "--- DEFERRED (require infrastructure not available from this host) ---"
$report += "  DRIFT-CAA/TLSA  : endpoint cert inspection + CAA read vs governed CA set"
$report += "  DRIFT-DELEGATION: parent-NS delegation walk + glue validation"

$report | Set-Content -Path $reportPath -Encoding UTF8
Write-Step "Report written to:   $reportPath"

if ($decision -eq "HALT") {
    Write-Host ""
    Write-Host "GATE: HALT — $($p1.Count) P1 finding(s) require remediation before deployment." -ForegroundColor Red
    Write-Host "Most likely cause: Private Link conditional forwarders missing on Domain Controllers." -ForegroundColor Red
    Write-Host "Fix: Add forwarders for each BYPASS zone pointing at your Private Resolver inbound endpoint." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host ""
    Write-Host "GATE: PASS — no P1 horizon findings." -ForegroundColor Green
    exit 0
}
