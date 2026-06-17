<#
.SYNOPSIS
    Install-UIAOService.ps1
    Registers UIAOService as a Windows Service and starts it.
    Run as: Administrator

.DESCRIPTION
    Installs the UIAO governance API as a native Windows Service
    (UIAOService). The service appears in Services.msc and survives
    IIS restarts independently.

    Prerequisites:
      - Install-UIAOServer.ps1 already run (Python 3.13 + IIS installed)
      - pip install "uiao[api,service]" already run in the target venv
      - Machine-level env vars set (UIAO_ENTRA_TENANT_ID etc.)

    After installation, copy web.config.service-mode to your IIS site
    path as web.config (replaces the HttpPlatformHandler config).
#>
[CmdletBinding()]
param(
    [string]$PythonExe        = "C:\srv\uiao\.venv\Scripts\python.exe",
    [string]$ServicePort      = "8001",
    [string]$ServiceAccount   = "CORP\SVC-UIAO-API",
    [SecureString]$ServicePassword,
    [string]$IISSitePath      = "C:\inetpub\uiao-api",
    [bool]$StartImmediately = $true
)
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$Msg) Write-Host "    OK: $Msg" -ForegroundColor Green }

# -----------------------------------------------------------------------
# 1. Verify prerequisites
# -----------------------------------------------------------------------
Write-Step "Verifying prerequisites..."

if (-not (Test-Path $PythonExe)) {
    throw "Python not found at $PythonExe. Run Install-UIAOServer.ps1 first."
}

# Verify uiao[service] is installed
$check = & $PythonExe -c "import win32serviceutil; print('ok')" 2>&1
if ($check -ne "ok") {
    throw "pywin32 not installed. Run: pip install 'uiao[api,service]' using $PythonExe"
}
Write-OK "pywin32 available"

# -----------------------------------------------------------------------
# 2. Set UIAO_SERVICE_PORT as machine-level env var
# -----------------------------------------------------------------------
Write-Step "Setting UIAO_SERVICE_PORT=$ServicePort..."
[System.Environment]::SetEnvironmentVariable("UIAO_SERVICE_PORT", $ServicePort, "Machine")
Write-OK "UIAO_SERVICE_PORT=$ServicePort"

# -----------------------------------------------------------------------
# 3. Register the Windows Service
# -----------------------------------------------------------------------
Write-Step "Registering UIAOService..."

$servicePy = Join-Path (Split-Path $PythonExe) "uiao-service.exe"
if (-not (Test-Path $servicePy)) {
    # Fall back to running as a Python module
    $servicePy = $PythonExe
    $serviceArgs = "-m uiao.service"
} else {
    $serviceArgs = ""
}

# Remove existing registration if present
$existing = Get-Service -Name "UIAOService" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "    Removing existing UIAOService registration..." -ForegroundColor Yellow
    & $PythonExe -m uiao.service remove 2>&1 | Out-Null
    Start-Sleep -Seconds 2
}

# Register via pywin32 (sets DisplayName + Description automatically)
& $PythonExe -m uiao.service --startup=auto install
Write-OK "UIAOService registered (auto-start)"

# -----------------------------------------------------------------------
# 4. Configure service to run as the UIAO service account
# -----------------------------------------------------------------------
Write-Step "Configuring service account $ServiceAccount..."

if ($ServicePassword) {
    $plainPwd = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($ServicePassword)
    )
    sc.exe config UIAOService obj= "$ServiceAccount" password= "$plainPwd" | Out-Null
    Write-OK "Service account set to $ServiceAccount"
} else {
    Write-Host "    No password provided — service will run as LocalSystem." -ForegroundColor Yellow
    Write-Host "    For production, rerun with -ServiceAccount and -ServicePassword." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# 5. Swap IIS web.config to service-mode (ARR reverse proxy)
# -----------------------------------------------------------------------
Write-Step "Updating IIS web.config to service-mode..."

$srcConfig  = Join-Path $PSScriptRoot "web.config.service-mode"
$destConfig = Join-Path $IISSitePath "web.config"

if (Test-Path $srcConfig) {
    Copy-Item $srcConfig $destConfig -Force
    Write-OK "web.config replaced with service-mode reverse-proxy config"
} else {
    Write-Host "    web.config.service-mode not found at $srcConfig — update IIS manually." -ForegroundColor Yellow
}

# -----------------------------------------------------------------------
# 6. Start the service
# -----------------------------------------------------------------------
if ($StartImmediately) {
    Write-Step "Starting UIAOService..."
    Start-Service -Name "UIAOService"
    Start-Sleep -Seconds 3
    $state = (Get-Service -Name "UIAOService").Status
    if ($state -eq "Running") {
        Write-OK "UIAOService is Running on port $ServicePort"
    } else {
        Write-Host "    Service state: $state — check Event Viewer / Application log" -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------------
# 7. Restart IIS to pick up new web.config
# -----------------------------------------------------------------------
Write-Step "Restarting IIS..."
iisreset /noforce
Write-OK "IIS restarted"

Write-Host "`n=== UIAOService installation complete ===" -ForegroundColor Green
Write-Host "Verify: Invoke-WebRequest -Uri 'https://$($env:COMPUTERNAME)/health' -UseDefaultCredentials"
Write-Host "Manage: Get-Service UIAOService | Select Status, StartType"
Write-Host "Logs:   Get-EventLog -LogName Application -Source UIAOService -Newest 20"
