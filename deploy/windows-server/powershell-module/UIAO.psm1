#Requires -Version 5.1
<#
.SYNOPSIS
    UIAO PowerShell Management Module
    Manage the UIAO governance API Windows Service installation.

.DESCRIPTION
    Provides Install-UIAO, Uninstall-UIAO, Get-UIAOStatus, Test-UIAOHealth,
    and Update-UIAO for day-to-day management of the UIAO API service.

    Install the module:
        Copy-Item -Recurse .\UIAO\ "$env:ProgramFiles\WindowsPowerShell\Modules\UIAO"
        Import-Module UIAO

    Or for the current session only:
        Import-Module .\UIAO.psd1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

function _Resolve-Python {
    $candidates = @(
        [System.Environment]::GetEnvironmentVariable("UIAO_PYTHON_EXE", "Machine"),
        "C:\srv\uiao\.venv\Scripts\python.exe",
        "C:\Python313\python.exe",
        (Get-Command python -ErrorAction SilentlyContinue)?.Source
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    throw "Python not found. Set UIAO_PYTHON_EXE machine env var or install Python 3.13."
}

function _Resolve-BaseUrl {
    $host = [System.Environment]::GetEnvironmentVariable("UIAO_API_HOST", "Machine")
    if (-not $host) { $host = "$env:COMPUTERNAME" }
    return "https://$host"
}

# -----------------------------------------------------------------------
# Install-UIAO
# -----------------------------------------------------------------------

function Install-UIAO {
    <#
    .SYNOPSIS
        Install or upgrade the UIAO governance API service.

    .DESCRIPTION
        Runs the full deployment sequence:
          1. Installs IIS features and Python (Install-UIAOServer.ps1)
          2. Installs the Python package (pip install uiao[api,service])
          3. Registers UIAOService as a Windows Service
          4. Configures the IIS reverse-proxy web.config

    .PARAMETER RepoPath
        Path to the UIAO repository root (default: C:\srv\uiao).

    .PARAMETER TenantId
        Entra ID tenant GUID. Set as machine env var UIAO_ENTRA_TENANT_ID.

    .PARAMETER ClientId
        App registration client ID. Set as machine env var UIAO_ENTRA_CLIENT_ID.

    .PARAMETER ClientSecret
        App registration client secret (SecureString).

    .PARAMETER ServicePort
        Loopback port for UIAOService (default: 8001).

    .EXAMPLE
        $secret = Read-Host "Client secret" -AsSecureString
        Install-UIAO -TenantId "<guid>" -ClientId "<guid>" -ClientSecret $secret
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$RepoPath     = "C:\srv\uiao",
        [string]$TenantId,
        [string]$ClientId,
        [SecureString]$ClientSecret,
        [string]$ServicePort  = "8001",
        [string]$IISSitePath  = "C:\inetpub\uiao-api",
        [string]$ServiceAccount = ""
    )

    if (-not (Test-Path $RepoPath)) {
        throw "Repo not found at $RepoPath. Clone the repo first: git clone https://github.com/WhalerMike/uiao.git $RepoPath"
    }

    Write-Host "Installing UIAO Governance API..." -ForegroundColor Cyan

    # Set credentials as machine env vars
    if ($TenantId) {
        [System.Environment]::SetEnvironmentVariable("UIAO_ENTRA_TENANT_ID", $TenantId, "Machine")
        Write-Host "  Set UIAO_ENTRA_TENANT_ID" -ForegroundColor Green
    }
    if ($ClientId) {
        [System.Environment]::SetEnvironmentVariable("UIAO_ENTRA_CLIENT_ID", $ClientId, "Machine")
        Write-Host "  Set UIAO_ENTRA_CLIENT_ID" -ForegroundColor Green
    }
    if ($ClientSecret) {
        $plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ClientSecret))
        [System.Environment]::SetEnvironmentVariable("UIAO_ENTRA_CLIENT_SECRET", $plain, "Machine")
        Write-Host "  Set UIAO_ENTRA_CLIENT_SECRET" -ForegroundColor Green
    }

    # Run the service installer
    $script = Join-Path $RepoPath "deploy\windows-server\Install-UIAOService.ps1"
    if (-not (Test-Path $script)) {
        throw "Install-UIAOService.ps1 not found at $script"
    }

    $params = @{
        PythonExe      = (_Resolve-Python)
        ServicePort    = $ServicePort
        IISSitePath    = $IISSitePath
        StartImmediately = $true
    }
    if ($ClientSecret) { $params.ServicePassword = $ClientSecret }
    if ($ServiceAccount) { $params.ServiceAccount = $ServiceAccount }

    & $script @params
}

# -----------------------------------------------------------------------
# Uninstall-UIAO
# -----------------------------------------------------------------------

function Uninstall-UIAO {
    <#
    .SYNOPSIS
        Stop and remove the UIAOService Windows Service.

    .DESCRIPTION
        Stops the service, unregisters it from the SCM, and optionally
        removes the IIS site. Does not delete the Python package or
        machine env vars (use -RemoveCredentials to clear those).

    .PARAMETER RemoveCredentials
        Also remove UIAO_ENTRA_* machine env vars.

    .PARAMETER RemoveIISSite
        Also remove the UIAO-API IIS site.
    #>
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = "High")]
    param(
        [switch]$RemoveCredentials,
        [switch]$RemoveIISSite
    )

    if ($PSCmdlet.ShouldProcess("UIAOService", "Stop and remove")) {
        $svc = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
        if ($svc) {
            if ($svc.Status -eq "Running") {
                Stop-Service -Name "UIAOService" -Force
                Write-Host "  Stopped UIAOService" -ForegroundColor Green
            }
            $py = _Resolve-Python
            & $py -m uiao.service remove 2>&1 | Out-Null
            Write-Host "  Removed UIAOService from SCM" -ForegroundColor Green
        } else {
            Write-Host "  UIAOService not found — nothing to remove" -ForegroundColor Yellow
        }
    }

    if ($RemoveIISSite) {
        Import-Module WebAdministration -ErrorAction SilentlyContinue
        $site = Get-Website -Name "UIAO-API" -ErrorAction SilentlyContinue
        if ($site) {
            Remove-Website -Name "UIAO-API"
            Write-Host "  Removed IIS site UIAO-API" -ForegroundColor Green
        }
        $pool = Get-WebAppPool -Name "UIAO-API-Pool" -ErrorAction SilentlyContinue
        if ($pool) {
            Remove-WebAppPool -Name "UIAO-API-Pool"
            Write-Host "  Removed IIS app pool UIAO-API-Pool" -ForegroundColor Green
        }
    }

    if ($RemoveCredentials) {
        foreach ($var in @("UIAO_ENTRA_TENANT_ID","UIAO_ENTRA_CLIENT_ID","UIAO_ENTRA_CLIENT_SECRET","UIAO_SERVICE_PORT")) {
            [System.Environment]::SetEnvironmentVariable($var, $null, "Machine")
        }
        Write-Host "  Cleared UIAO machine env vars" -ForegroundColor Green
    }

    Write-Host "Uninstall complete." -ForegroundColor Cyan
}

# -----------------------------------------------------------------------
# Get-UIAOStatus
# -----------------------------------------------------------------------

function Get-UIAOStatus {
    <#
    .SYNOPSIS
        Show the current status of the UIAO governance API.

    .DESCRIPTION
        Reports IIS site state, app pool state, service state, Python
        process presence, and the running version.
    #>
    [CmdletBinding()]
    param()

    $status = [ordered]@{}

    # Windows Service
    $svc = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
    $status["Service (UIAOService)"] = if ($svc) { $svc.Status } else { "Not installed" }
    $status["Service StartType"]     = if ($svc) { $svc.StartType } else { "—" }

    # IIS
    Import-Module WebAdministration -ErrorAction SilentlyContinue
    $site = Get-Website -Name "UIAO-API" -ErrorAction SilentlyContinue
    $status["IIS Site (UIAO-API)"]  = if ($site) { $site.State } else { "Not found" }

    $pool = Get-WebAppPoolState -Name "UIAO-API-Pool" -ErrorAction SilentlyContinue
    $status["IIS App Pool"]         = if ($pool) { $pool.Value } else { "Not found" }

    # Python process
    $py = Get-Process python -ErrorAction SilentlyContinue
    $status["Python process"]       = if ($py) { "Running (PID $($py[0].Id))" } else { "Not running" }

    # Port
    $port = [System.Environment]::GetEnvironmentVariable("UIAO_SERVICE_PORT","Machine")
    $status["Service port"]         = if ($port) { $port } else { "8001 (default)" }

    # Version
    try {
        $pyExe = _Resolve-Python
        $ver = & $pyExe -c "import uiao; print(uiao.__version__)" 2>&1
        $status["UIAO version"]     = $ver
    } catch {
        $status["UIAO version"]     = "Unknown"
    }

    [PSCustomObject]$status | Format-List
}

# -----------------------------------------------------------------------
# Test-UIAOHealth
# -----------------------------------------------------------------------

function Test-UIAOHealth {
    <#
    .SYNOPSIS
        Run a health check against the deployed UIAO governance API.

    .DESCRIPTION
        Checks: IIS site, app pool, Python process, /health endpoint,
        Entra token acquisition, and TLS certificate expiry.
        Prints a PASS/WARN/FAIL per check.

    .PARAMETER BaseUrl
        Base HTTPS URL of the UIAO API (default: https://<ComputerName>).

    .PARAMETER WarnCertDays
        Warn if TLS cert expires within this many days (default: 30).

    .OUTPUTS
        Array of PSCustomObjects with Check, Status, Detail columns.
        Returns exit code 1 if any check is FAIL.
    #>
    [CmdletBinding()]
    param(
        [string]$BaseUrl       = (_Resolve-BaseUrl),
        [int]$WarnCertDays     = 30
    )

    $results = [System.Collections.Generic.List[PSCustomObject]]::new()

    function Add-Check {
        param([string]$Name, [string]$Status, [string]$Detail = "")
        $color = switch ($Status) {
            "PASS" { "Green" } "WARN" { "Yellow" } default { "Red" }
        }
        Write-Host ("  [{0,-4}] {1}" -f $Status, $Name) -ForegroundColor $color
        if ($Detail) { Write-Host "         $Detail" -ForegroundColor DarkGray }
        $results.Add([PSCustomObject]@{ Check = $Name; Status = $Status; Detail = $Detail })
    }

    Write-Host "`nUIAO Health Check — $BaseUrl" -ForegroundColor Cyan
    Write-Host ("-" * 50)

    # 1. Windows Service
    $svc = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq "Running") { Add-Check "UIAOService" "PASS" }
    elseif ($svc) { Add-Check "UIAOService" "FAIL" "Service state: $($svc.Status)" }
    else { Add-Check "UIAOService" "FAIL" "Service not installed" }

    # 2. IIS app pool
    Import-Module WebAdministration -ErrorAction SilentlyContinue
    $pool = Get-WebAppPoolState -Name "UIAO-API-Pool" -ErrorAction SilentlyContinue
    if ($pool -and $pool.Value -eq "Started") { Add-Check "IIS App Pool" "PASS" }
    elseif ($pool) { Add-Check "IIS App Pool" "FAIL" "State: $($pool.Value)" }
    else { Add-Check "IIS App Pool" "FAIL" "App pool UIAO-API-Pool not found" }

    # 3. Python process
    $py = Get-Process python -ErrorAction SilentlyContinue
    if ($py) { Add-Check "Python process" "PASS" "PID $($py[0].Id)" }
    else { Add-Check "Python process" "FAIL" "No python.exe process running" }

    # 4. /health endpoint
    try {
        $r = Invoke-WebRequest -Uri "$BaseUrl/health" `
             -UseDefaultCredentials -TimeoutSec 10 -UseBasicParsing
        if ($r.StatusCode -eq 200) { Add-Check "/health endpoint" "PASS" "HTTP 200" }
        else { Add-Check "/health endpoint" "FAIL" "HTTP $($r.StatusCode)" }
    } catch {
        Add-Check "/health endpoint" "FAIL" $_.Exception.Message
    }

    # 5. Entra token acquisition (calls the API's token-check route)
    try {
        $r2 = Invoke-WebRequest -Uri "$BaseUrl/api/v1/entra/token-check" `
              -UseDefaultCredentials -TimeoutSec 15 -UseBasicParsing
        if ($r2.StatusCode -eq 200) { Add-Check "Entra token" "PASS" }
        else { Add-Check "Entra token" "WARN" "HTTP $($r2.StatusCode) — check UIAO_ENTRA_* env vars" }
    } catch {
        Add-Check "Entra token" "FAIL" $_.Exception.Message
    }

    # 6. TLS certificate expiry
    $cert = Get-ChildItem Cert:\LocalMachine\My |
        Where-Object { $_.Subject -like "*$env:COMPUTERNAME*" -or $_.Subject -like "*uiao-api*" } |
        Sort-Object NotAfter | Select-Object -First 1
    if ($cert) {
        $days = [math]::Floor(($cert.NotAfter - (Get-Date)).TotalDays)
        if ($days -gt $WarnCertDays) { Add-Check "TLS certificate" "PASS" "Expires in $days days ($($cert.NotAfter.ToString('yyyy-MM-dd')))" }
        elseif ($days -gt 0) { Add-Check "TLS certificate" "WARN" "Expires in $days days — renew soon" }
        else { Add-Check "TLS certificate" "FAIL" "Certificate has expired" }
    } else {
        Add-Check "TLS certificate" "WARN" "No certificate found in LocalMachine\My matching hostname"
    }

    Write-Host ("-" * 50)
    $fails  = @($results | Where-Object { $_.Status -eq "FAIL" }).Count
    $warns  = @($results | Where-Object { $_.Status -eq "WARN" }).Count
    $passes = @($results | Where-Object { $_.Status -eq "PASS" }).Count
    Write-Host "Result: $passes PASS  $warns WARN  $fails FAIL" -ForegroundColor $(if ($fails) { "Red" } elseif ($warns) { "Yellow" } else { "Green" })

    if ($fails -gt 0) { $global:LASTEXITCODE = 1 }
    return $results
}

# -----------------------------------------------------------------------
# Update-UIAO
# -----------------------------------------------------------------------

function Update-UIAO {
    <#
    .SYNOPSIS
        Upgrade the UIAO Python package to the latest release.

    .DESCRIPTION
        Stops the service, runs pip install --upgrade uiao[api,service],
        then restarts the service. Checks GitHub Releases for the latest
        version and reports whether an upgrade is available before acting.

    .PARAMETER Force
        Skip the version check and upgrade unconditionally.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [switch]$Force
    )

    $py = _Resolve-Python

    # Check current version
    $current = & $py -c "import uiao; print(uiao.__version__)" 2>&1

    if (-not $Force) {
        Write-Host "Checking GitHub Releases for latest version..." -ForegroundColor Cyan
        try {
            $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/WhalerMike/uiao/releases/latest" `
                   -TimeoutSec 10
            $latest = $rel.tag_name -replace '^v',''
            Write-Host "  Current: $current"
            Write-Host "  Latest:  $latest"
            if ($current -eq $latest) {
                Write-Host "  Already up to date." -ForegroundColor Green
                return
            }
        } catch {
            Write-Host "  Could not reach GitHub API — proceeding with local upgrade." -ForegroundColor Yellow
        }
    }

    if ($PSCmdlet.ShouldProcess("UIAOService", "Stop, upgrade package, restart")) {
        # Stop service
        $svc = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -eq "Running") {
            Stop-Service -Name "UIAOService" -Force
            Write-Host "  Stopped UIAOService" -ForegroundColor Yellow
        }

        # Upgrade
        Write-Host "  Running pip install --upgrade uiao[api,service]..." -ForegroundColor Cyan
        & $py -m pip install --upgrade "uiao[api,service]"

        # Restart
        Start-Service -Name "UIAOService"
        Start-Sleep -Seconds 3
        $state = (Get-Service -Name "UIAOService").Status
        Write-Host "  UIAOService: $state" -ForegroundColor $(if ($state -eq "Running") { "Green" } else { "Red" })

        $new = & $py -c "import uiao; print(uiao.__version__)" 2>&1
        Write-Host "  Upgraded from $current to $new" -ForegroundColor Green
    }
}

# -----------------------------------------------------------------------
# Module exports
# -----------------------------------------------------------------------

Export-ModuleMember -Function @(
    "Install-UIAO",
    "Uninstall-UIAO",
    "Get-UIAOStatus",
    "Test-UIAOHealth",
    "Update-UIAO"
)
