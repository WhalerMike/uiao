<#
.SYNOPSIS
    Seed an Azure subscription (trial or sandbox) with realistic DNS zones and
    bindings for end-to-end validation of the UIAO addressing-plane pipeline.

.DESCRIPTION
    Creates:
      - 1 Azure Public DNS zone  (agency-test.gov)
      - 3 Azure Private DNS zones (corp.agency-test.gov, privatelink.blob.core.windows.net,
                                   privatelink.vaultcore.azure.net)
      - ~20 record sets spanning A, CNAME, MX, TXT, SRV, PTR record types
      - Intentional drift: one dangling A, one CNAME-conflict, one shadow record
      - my_bindings.json pre-populated for the created records

    After this script completes, run:
        .\Invoke-AddressingAudit.ps1 `
            -IntendedBindingsPath .\test-env\my_bindings.json `
            -OutputDirectory      .\test-env\audit

    Expected gate result: HALT (intentional drift seeded)

.PARAMETER ResourceGroup
    Resource group to create.  Default: rg-uiao-dns-test

.PARAMETER Location
    Azure region.  Default: eastus

.PARAMETER OutputDirectory
    Where to write my_bindings.json.  Default: .\test-env

.EXAMPLE
    az login
    .\Initialize-EntraTestEnvironment.ps1

.EXAMPLE
    .\Initialize-EntraTestEnvironment.ps1 -ResourceGroup rg-dns-lab -Location westus2
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $ResourceGroup  = "rg-uiao-dns-test",
    [string] $Location       = "eastus",
    [string] $OutputDirectory = ".\test-env"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) { Write-Host "[init-env] $msg" -ForegroundColor Cyan }
function Write-Done([string]$msg) { Write-Host "[init-env] OK  $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Warning "[init-env] $msg" }

# -------------------------------------------------------------------------
# Prerequisites
# -------------------------------------------------------------------------

if (-not (Get-Command az -ErrorAction SilentlyContinue)) {
    throw "Azure CLI not found.  Install: https://learn.microsoft.com/cli/azure/install-azure-cli"
}
$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    throw "Not logged in.  Run: az login"
}
Write-Step "Authenticated: $($account.user.name)  sub: $($account.id)"

New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null

# -------------------------------------------------------------------------
# Resource group
# -------------------------------------------------------------------------

Write-Step "Creating resource group: $ResourceGroup ($Location)"
az group create --name $ResourceGroup --location $Location | Out-Null
Write-Done "Resource group ready"

# -------------------------------------------------------------------------
# Zone names
# -------------------------------------------------------------------------

$pubZone     = "agency-test.gov"
$privZone    = "corp.agency-test.gov"
$plBlob      = "privatelink.blob.core.windows.net"
$plVault     = "privatelink.vaultcore.azure.net"

# -------------------------------------------------------------------------
# Public DNS zone
# -------------------------------------------------------------------------

Write-Step "Creating public zone: $pubZone"
az network dns zone create `
    --resource-group $ResourceGroup `
    --name $pubZone | Out-Null
Write-Done "Public zone: $pubZone"

# A records — some live, one dangling (intentional drift)
$pubRecords = @(
    @{ name = "www";   type = "A";     value = "203.0.113.10";  ttl = 300 }  # live (rfc5737 doc range)
    @{ name = "mail";  type = "A";     value = "203.0.113.11";  ttl = 300 }  # live
    @{ name = "vpn";   type = "A";     value = "203.0.113.99";  ttl = 300 }  # DANGLING — not in resources.json
    @{ name = "portal"; type = "CNAME"; value = "agency-test-portal.azurewebsites.net"; ttl = 300 }
)

foreach ($r in $pubRecords) {
    Write-Step "  $pubZone  $($r.name) $($r.type) $($r.value)"
    if ($r.type -eq "A") {
        az network dns record-set a add-record `
            --resource-group $ResourceGroup --zone-name $pubZone `
            --record-set-name $r.name --ipv4-address $r.value | Out-Null
        az network dns record-set a update `
            --resource-group $ResourceGroup --zone-name $pubZone `
            --name $r.name --set "properties.TTL=$($r.ttl)" | Out-Null
    } elseif ($r.type -eq "CNAME") {
        az network dns record-set cname set-record `
            --resource-group $ResourceGroup --zone-name $pubZone `
            --record-set-name $r.name --cname $r.value | Out-Null
    }
}

# MX record
Write-Step "  $pubZone  MX"
az network dns record-set mx add-record `
    --resource-group $ResourceGroup --zone-name $pubZone `
    --record-set-name "@" --exchange "mail.$pubZone" --preference 10 | Out-Null

# TXT record (SPF)
Write-Step "  $pubZone  TXT (SPF)"
az network dns record-set txt add-record `
    --resource-group $ResourceGroup --zone-name $pubZone `
    --record-set-name "@" --value "v=spf1 include:spf.protection.outlook.com -all" | Out-Null

# CNAME conflict (intentional drift): also add an A at the same name as portal CNAME
Write-Step "  $pubZone  CONFLICT — adding A at 'portal' (same name as CNAME)"
az network dns record-set a add-record `
    --resource-group $ResourceGroup --zone-name $pubZone `
    --record-set-name "portal" --ipv4-address "203.0.113.50" | Out-Null

Write-Done "Public zone records seeded (includes 1 dangling A + 1 CNAME-conflict)"

# -------------------------------------------------------------------------
# Private DNS zone — corp.agency-test.gov
# -------------------------------------------------------------------------

Write-Step "Creating private zone: $privZone"
az network private-dns zone create `
    --resource-group $ResourceGroup `
    --name $privZone | Out-Null
Write-Done "Private zone: $privZone"

$privRecords = @(
    @{ name = "app";    ip = "10.20.0.10" }
    @{ name = "api";    ip = "10.20.0.11" }
    @{ name = "dc1";    ip = "10.20.0.5"  }
    @{ name = "dc2";    ip = "10.20.0.6"  }
    @{ name = "shadow"; ip = "10.20.0.99" }   # SHADOW — not in intended_bindings
)

foreach ($r in $privRecords) {
    Write-Step "  $privZone  $($r.name) A $($r.ip)"
    az network private-dns record-set a add-record `
        --resource-group $ResourceGroup --zone-name $privZone `
        --record-set-name $r.name --ipv4-address $r.ip | Out-Null
}

# SRV records (Kerberos / LDAP locators)
$srvRecords = @(
    @{ name = "_ldap._tcp";     priority = 0; weight = 100; port = 389;  target = "dc1.$privZone" }
    @{ name = "_kerberos._tcp"; priority = 0; weight = 100; port = 88;   target = "dc1.$privZone" }
    @{ name = "_gc._tcp";       priority = 0; weight = 100; port = 3268; target = "dc1.$privZone" }
    # _kpasswd._tcp intentionally OMITTED — will generate DRIFT-SRV finding
)

foreach ($s in $srvRecords) {
    Write-Step "  $privZone  $($s.name) SRV"
    az network private-dns record-set srv add-record `
        --resource-group $ResourceGroup --zone-name $privZone `
        --record-set-name $s.name `
        --priority $s.priority --weight $s.weight --port $s.port --target $s.target | Out-Null
}

Write-Done "Private zone seeded (shadow record + missing _kpasswd SRV)"

# -------------------------------------------------------------------------
# Private DNS zones — privatelink.*
# These simulate the required Private Link DNS override zones.
# In a real environment the Private Resolver would forward to these;
# here we just create the zones so the horizon probe can detect them.
# -------------------------------------------------------------------------

foreach ($plZone in @($plBlob, $plVault)) {
    Write-Step "Creating privatelink zone: $plZone"
    az network private-dns zone create `
        --resource-group $ResourceGroup `
        --name $plZone | Out-Null
    Write-Done "  Created: $plZone"
}

# Blob endpoint A record (RFC1918) — correct Private Link config
Write-Step "  $plBlob  storageaccount.blob.core.windows.net → 10.30.0.4"
az network private-dns record-set a add-record `
    --resource-group $ResourceGroup --zone-name $plBlob `
    --record-set-name "storageaccount" --ipv4-address "10.30.0.4" | Out-Null

# Key Vault — intentionally NO record (zone exists, but no A record)
# Horizon probe will flag this as BYPASS risk if external probe returns public IP
Write-Step "  $plVault  (no records — simulates unconfigured Private Link)"

Write-Done "privatelink zones created"

# -------------------------------------------------------------------------
# Write intended_bindings.json
# -------------------------------------------------------------------------

Write-Step "Writing my_bindings.json ..."

$bindings = [ordered]@{
    "_comment" = "UIAO addressing-plane SSOT — generated by Initialize-EntraTestEnvironment.ps1"
    "zones"    = [ordered]@{
        $pubZone  = [ordered]@{ ref_count = 3 }
        $privZone = [ordered]@{ ref_count = 6 }
        $plBlob   = [ordered]@{ ref_count = 1 }
        $plVault  = [ordered]@{ ref_count = 0 }   # DRIFT-ORPHAN — no bindings
    }
    "bindings" = [ordered]@{
        "www.$pubZone"    = [ordered]@{ type = "A";     target = "203.0.113.10"; boundary_intent = "any";          requires_fcrdns = $false }
        "mail.$pubZone"   = [ordered]@{ type = "A";     target = "203.0.113.11"; boundary_intent = "any";          requires_fcrdns = $true  }
        "portal.$pubZone" = [ordered]@{ type = "CNAME"; target = "agency-test-portal.azurewebsites.net"; boundary_intent = "any"; requires_fcrdns = $false }
        "app.$privZone"   = [ordered]@{ type = "A";     target = "10.20.0.10";   boundary_intent = "private";      requires_fcrdns = $false }
        "api.$privZone"   = [ordered]@{ type = "A";     target = "10.20.0.11";   boundary_intent = "private";      requires_fcrdns = $false }
        "dc1.$privZone"   = [ordered]@{ type = "A";     target = "10.20.0.5";    boundary_intent = "private";      requires_fcrdns = $true  }
        "dc2.$privZone"   = [ordered]@{ type = "A";     target = "10.20.0.6";    boundary_intent = "private";      requires_fcrdns = $true  }
        "storageaccount.$plBlob" = [ordered]@{ type = "A"; target = "10.30.0.4"; boundary_intent = "gcc-moderate"; requires_fcrdns = $false }
    }
    "required_srv" = @(
        "_ldap._tcp"
        "_kerberos._tcp"
        "_gc._tcp"
        "_kpasswd._tcp"
    )
    "system_names" = @(
        "_ldap._tcp.$privZone"
        "_kerberos._tcp.$privZone"
        "_gc._tcp.$privZone"
        "_kpasswd._tcp.$privZone"
    )
    "_boundary_intent_values" = [ordered]@{
        "private"      = "Must resolve RFC1918 from internal; must NOT resolve from external"
        "gcc-moderate" = "GCC-M commercial endpoint — any vantage but must land on correct IP"
        "any"          = "Split-horizon acceptable; divergent answers are P2"
    }
}

$bindingsPath = Join-Path $OutputDirectory "my_bindings.json"
$bindings | ConvertTo-Json -Depth 5 | Set-Content -Path $bindingsPath -Encoding UTF8
Write-Done "Wrote: $bindingsPath"

# -------------------------------------------------------------------------
# Summary
# -------------------------------------------------------------------------

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "  Test environment seeded.  Expected drift findings:" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host ""
Write-Host "  P1  DRIFT-DANGLING   vpn.$pubZone -> 203.0.113.99 (resource absent)" -ForegroundColor Red
Write-Host "  P1  DRIFT-CONFLICT   portal.$pubZone (CNAME + A coexist)" -ForegroundColor Red
Write-Host "  P1  DRIFT-SRV        _kpasswd._tcp (missing)" -ForegroundColor Red
Write-Host "  P2  DRIFT-SHADOW     shadow.$privZone (not in SSOT)" -ForegroundColor Yellow
Write-Host "  P3  DRIFT-ORPHAN     $plVault (zero bindings)" -ForegroundColor White
Write-Host ""
Write-Host "  Run the full audit:" -ForegroundColor Cyan
Write-Host ""
Write-Host "    .\Invoke-AddressingAudit.ps1 ``" -ForegroundColor White
Write-Host "        -IntendedBindingsPath $bindingsPath ``" -ForegroundColor White
Write-Host "        -OutputDirectory      $OutputDirectory\audit" -ForegroundColor White
Write-Host ""
Write-Host "  Expected gate: HALT (P1 findings present)" -ForegroundColor Red
Write-Host ""
