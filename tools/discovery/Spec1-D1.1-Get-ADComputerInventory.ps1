# UIAO Spec 1 — D1.1: AD Computer Object Inventory
# Full export of all computer objects from all AD domains/forests.
# Collects: DN, OS, OS version, last logon timestamp, OU path,
# managed-by, SPN list, BitLocker recovery keys present,
# LAPS password age, extensionAttribute1 (OrgPath baseline).

# Outputs structured JSON for downstream consumption by
# D1.2 (Device State Classification) and D1.9 (Migration Readiness).

# Ref: UIAO_136 Spec 1, Phase 1, Deliverable D1.1
# ADR‑048 (extensionAttribute1 = OrgPath)

param(
    [string]$OutputPath = ".\output",
    [string]$DomainController,
    [bool]$IncludeStale = $true,
    [string]$SearchBase
)

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT or run on a domain-joined machine."
    return
}

Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$domain = (Get-ADDomain).DNSRoot
$outFile = Join-Path $OutputPath "UIAO_Spec1_D1.1_ADComputerInventory_${domain}_${timestamp}.json"

Write-Host "UIAO Spec 1 — D1.1 AD Computer Inventory" -ForegroundColor Cyan
Write-Host "  Domain: $domain"
Write-Host "  Timestamp: $timestamp"

$searchParams = @{
    Filter = '(objectClass=computer)'
    Properties = '*'
}
if ($SearchBase) { $searchParams.SearchBase = $SearchBase }
if ($DomainController) { $searchParams.Server = $DomainController }

Write-Host "Querying AD for computer objects..." -ForegroundColor Yellow
$computers = Get-ADComputer @searchParams -ErrorAction Stop
Write-Host "  Found $($computers.Count) computer objects" -ForegroundColor Green

# Build structured inventory
$inventory = foreach ($c in $computers) {
    [pscustomobject]@{
        Name                = $c.Name
        DistinguishedName   = $c.DistinguishedName
        OperatingSystem     = $c.OperatingSystem
        OperatingSystemVer  = $c.OperatingSystemVersion
        LastLogonDate       = $c.LastLogonDate
        ManagedBy           = $c.ManagedBy
        SPNs                = $c.ServicePrincipalName
        OrgPath             = $c.extensionAttribute1
        LAPS_PasswordAge    = $c.'ms-Mcs-AdmPwdExpirationTime'
        BitLockerKeys       = $c.'ms-FVE-RecoveryInformation'
    }
}

$inventory |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath $outFile -Encoding utf8NoBOM

Write-Host "Output: $outFile" -ForegroundColor Green
