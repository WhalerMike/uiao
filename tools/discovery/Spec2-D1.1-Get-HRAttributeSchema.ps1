# UIAO Spec 2 — D1.1 HR Attribute Schema Discovery
# Full discovery of HR/EMPL-relevant attributes on Active Directory user objects.
# Builds schema table with attribute name, type, and sample values.

param(
    [string]$OutputPath = ".\output",
    [string]$SearchBase,
    [bool]$IncludeDisabled = $true
)

if (-not (Get-Module -ListAvailable -Name ActiveDirectory)) {
    Write-Error "ActiveDirectory module not found. Install RSAT or run on a domain-joined machine."
    return
}

Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$domain = (Get-ADDomain).DNSRoot
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outFile = Join-Path $OutputPath "UIAO_Spec2_D1.1_HRAttributeSchema_${domain}_${timestamp}.json"

Write-Host "UIAO Spec 2 — D1.1 HR Attribute Schema Discovery" -ForegroundColor Cyan
Write-Host "  Domain: $domain"
Write-Host "  Timestamp: $timestamp"

$searchParams = @{
    Filter = '(objectClass=user)'
    Properties = '*'
}
if ($SearchBase) { $searchParams.SearchBase = $SearchBase }

Write-Host "Querying AD for user objects..." -ForegroundColor Yellow
$users = Get-ADUser @searchParams -ErrorAction Stop
Write-Host "  Found $($users.Count) user objects" -ForegroundColor Green

# Sample first 100 users for schema inference
$sample = $users | Select-Object -First 100
if (-not $sample) {
    Write-Error "No user objects returned."
    return
}

# Build schema table
$schema = @()
foreach ($u in $sample) {
    foreach ($attr in $u.PSObject.Properties.Name) {
        if (-not ($schema | Where-Object { $_.AttributeName -eq $attr })) {
            $value = $u.$attr
            $type = if ($value) { $value.GetType().Name } else { "Unknown" }
            $schema += [pscustomobject]@{
                AttributeName = $attr
                Type          = $type
                SampleValue   = $value
            }
        }
    }
}

# Focus on HR/EMPL-relevant attributes
$HRInterest = $schema | Where-Object {
    $_.AttributeName -match '(employee|manager|department|orgPath|location)'
}

$output = [pscustomobject]@{
    Summary = @{
        Domain        = $domain
        Timestamp     = $timestamp
        Script        = "UIAO Spec 2 — D1.1 HR Attribute Schema Discovery"
    }
    Statistics = @{
        TotalAttributes = $schema.Count
        HRRelevant      = $HRInterest.Count
    }
    Attributes = $schema
}

$output |
    ConvertTo-Json -Depth 10 |
    Out-File -FilePath $outFile -Encoding utf8NoBOM

Write-Host "Output: $outFile" -ForegroundColor Green
