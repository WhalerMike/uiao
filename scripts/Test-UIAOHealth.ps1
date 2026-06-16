<#
.SYNOPSIS
    Test-UIAOHealth.ps1
    Standalone health check for the UIAO governance API on Windows Server.
    Run as any user with network access to the UIAO API endpoint.

.DESCRIPTION
    Checks: UIAOService state, IIS app pool, Python process, /health
    endpoint, Entra token acquisition, and TLS certificate expiry.
    Exits 0 if all checks pass; exits 1 if any check fails.

.PARAMETER BaseUrl
    Base HTTPS URL (default: https://<ComputerName>).

.EXAMPLE
    .\Test-UIAOHealth.ps1
    .\Test-UIAOHealth.ps1 -BaseUrl "https://uiao-api.corp.contoso.com"
#>
[CmdletBinding()]
param(
    [string]$BaseUrl     = "https://$env:COMPUTERNAME",
    [int]$WarnCertDays   = 30
)

# If the UIAO module is installed, delegate to it
if (Get-Module -ListAvailable -Name UIAO -ErrorAction SilentlyContinue) {
    Import-Module UIAO
    $results = Test-UIAOHealth -BaseUrl $BaseUrl -WarnCertDays $WarnCertDays
    exit ($results | Where-Object { $_.Status -eq "FAIL" } | Measure-Object).Count
}

# Inline fallback (no module dependency)
$results = [System.Collections.Generic.List[PSCustomObject]]::new()

function Add-Check {
    param([string]$Name, [string]$Status, [string]$Detail = "")
    $color = switch ($Status) { "PASS" { "Green" } "WARN" { "Yellow" } default { "Red" } }
    Write-Host ("  [{0,-4}] {1}" -f $Status, $Name) -ForegroundColor $color
    if ($Detail) { Write-Host "         $Detail" -ForegroundColor DarkGray }
    $results.Add([PSCustomObject]@{ Check = $Name; Status = $Status; Detail = $Detail })
}

Write-Host "`nUIAO Health Check — $BaseUrl" -ForegroundColor Cyan
Write-Host ("-" * 50)

# 1. Windows Service
$svc = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
if     ($svc -and $svc.Status -eq "Running") { Add-Check "UIAOService"    "PASS" }
elseif ($svc)                                { Add-Check "UIAOService"    "FAIL" "State: $($svc.Status)" }
else                                         { Add-Check "UIAOService"    "FAIL" "Service not installed — check IIS HttpPlatformHandler mode" }

# 2. IIS app pool
Import-Module WebAdministration -ErrorAction SilentlyContinue
$pool = Get-WebAppPoolState -Name "UIAO-API-Pool" -ErrorAction SilentlyContinue
if     ($pool -and $pool.Value -eq "Started") { Add-Check "IIS App Pool" "PASS" }
elseif ($pool)                                { Add-Check "IIS App Pool" "FAIL" "State: $($pool.Value)" }
else                                          { Add-Check "IIS App Pool" "FAIL" "UIAO-API-Pool not found" }

# 3. Python process
$py = Get-Process python -ErrorAction SilentlyContinue
if ($py) { Add-Check "Python process" "PASS" "PID $($py[0].Id)" }
else     { Add-Check "Python process" "FAIL" "No python.exe process running" }

# 4. /health endpoint
try {
    $r = Invoke-WebRequest -Uri "$BaseUrl/health" -UseDefaultCredentials -TimeoutSec 10 -UseBasicParsing
    if ($r.StatusCode -eq 200) { Add-Check "/health endpoint" "PASS" "HTTP 200" }
    else                       { Add-Check "/health endpoint" "FAIL" "HTTP $($r.StatusCode)" }
} catch { Add-Check "/health endpoint" "FAIL" $_.Exception.Message }

# 5. Entra token
try {
    $r2 = Invoke-WebRequest -Uri "$BaseUrl/api/v1/entra/token-check" `
          -UseDefaultCredentials -TimeoutSec 15 -UseBasicParsing
    if ($r2.StatusCode -eq 200) { Add-Check "Entra token" "PASS" }
    else                        { Add-Check "Entra token" "WARN" "HTTP $($r2.StatusCode)" }
} catch { Add-Check "Entra token" "FAIL" $_.Exception.Message }

# 6. TLS cert expiry
$cert = Get-ChildItem Cert:\LocalMachine\My |
    Where-Object { $_.Subject -like "*$env:COMPUTERNAME*" -or $_.Subject -like "*uiao-api*" } |
    Sort-Object NotAfter | Select-Object -First 1
if ($cert) {
    $days = [math]::Floor(($cert.NotAfter - (Get-Date)).TotalDays)
    if    ($days -gt $WarnCertDays) { Add-Check "TLS certificate" "PASS" "Expires in $days days" }
    elseif ($days -gt 0)            { Add-Check "TLS certificate" "WARN" "Expires in $days days — renew soon" }
    else                            { Add-Check "TLS certificate" "FAIL" "Certificate has expired" }
} else { Add-Check "TLS certificate" "WARN" "No cert found in LocalMachine\My" }

Write-Host ("-" * 50)
$fails  = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
$warns  = @($results | Where-Object { $_.Status -eq "WARN" }).Count
$passes = @($results | Where-Object { $_.Status -eq "PASS" }).Count
$color  = if ($fails) { "Red" } elseif ($warns) { "Yellow" } else { "Green" }
Write-Host "Result: $passes PASS  $warns WARN  $fails FAIL" -ForegroundColor $color

exit $fails
