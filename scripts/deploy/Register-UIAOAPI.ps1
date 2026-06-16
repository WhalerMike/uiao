<#
.SYNOPSIS
    Register-UIAOAPI.ps1
    Creates the IIS app pool and site for the UIAO API.
    Run on the target Windows Server 2026 as Administrator.
#>
[CmdletBinding()]
param(
    [string]$SiteName          = "UIAO-API",
    [string]$AppPoolName       = "UIAO-API-Pool",
    [string]$AppPoolIdentity   = "CORP\SVC-UIAO-API",
    [SecureString]$AppPoolPassword,
    [string]$PhysicalPath      = "C:\inetpub\uiao-api",
    [int]$BindingPort          = 443,
    [string]$CertThumbprint,
    [string]$LogPath           = "C:\Logs\uiao-api"
)
$ErrorActionPreference = "Stop"
Import-Module WebAdministration -ErrorAction Stop

Write-Host "Configuring IIS for UIAO API..." -ForegroundColor Cyan

# Physical path
New-Item -ItemType Directory -Path $PhysicalPath -Force | Out-Null

# Copy web.config
$webConfigSrc = "C:\srv\uiao\deploy\windows-server\web.config"
if (Test-Path $webConfigSrc) {
    Copy-Item $webConfigSrc "$PhysicalPath\web.config" -Force
    Write-Host "  OK: web.config copied" -ForegroundColor Green
}

# Copy run.py
Copy-Item "C:\srv\uiao\deploy\windows-server\run.py" "$PhysicalPath\run.py" -Force
Write-Host "  OK: run.py copied" -ForegroundColor Green

# -----------------------------------------------------------------------
# App pool
# -----------------------------------------------------------------------
if (-not (Test-Path "IIS:\AppPools\$AppPoolName")) {
    New-WebAppPool -Name $AppPoolName
    Write-Host "  OK: App pool created: $AppPoolName" -ForegroundColor Green
}

# No managed code (Python app)
Set-ItemProperty "IIS:\AppPools\$AppPoolName" -Name managedRuntimeVersion -Value ""

# Service account identity
$cred = New-Object System.Management.Automation.PSCredential(
    $AppPoolIdentity, $AppPoolPassword
)
Set-ItemProperty "IIS:\AppPools\$AppPoolName" processModel -Value @{
    userName   = $AppPoolIdentity
    password   = ($cred.GetNetworkCredential().Password)
    logonType  = "SpecificUser"
}

# Idle timeout: 0 = never recycle on idle (keep Python warm)
Set-ItemProperty "IIS:\AppPools\$AppPoolName" -Name processModel.idleTimeout `
    -Value ([TimeSpan]::Zero)

# Recycle: daily at 2 AM (not on demand)
Set-ItemProperty "IIS:\AppPools\$AppPoolName" recycling.periodicRestart.time `
    -Value ([TimeSpan]::Zero)

Write-Host "  OK: App pool configured" -ForegroundColor Green

# -----------------------------------------------------------------------
# IIS Site
# -----------------------------------------------------------------------
if (Get-Website -Name $SiteName -ErrorAction SilentlyContinue) {
    Remove-Website -Name $SiteName
}

if ($CertThumbprint) {
    New-Website `
        -Name $SiteName `
        -PhysicalPath $PhysicalPath `
        -ApplicationPool $AppPoolName `
        -Port $BindingPort `
        -Ssl | Out-Null

    # Bind the TLS certificate
    $cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object { $_.Thumbprint -eq $CertThumbprint }
    if (-not $cert) { throw "Certificate thumbprint $CertThumbprint not found in LocalMachine\My" }

    $binding = Get-WebBinding -Name $SiteName -Port $BindingPort -Protocol "https"
    $binding.AddSslCertificate($CertThumbprint, "My")
    Write-Host "  OK: TLS certificate bound" -ForegroundColor Green
} else {
    Write-Host "  WARN: No CertThumbprint provided — binding HTTP only (not for production!)" -ForegroundColor Yellow
    New-Website `
        -Name $SiteName `
        -PhysicalPath $PhysicalPath `
        -ApplicationPool $AppPoolName `
        -Port 8080 | Out-Null
}

# -----------------------------------------------------------------------
# Authentication: Windows only
# -----------------------------------------------------------------------
Set-WebConfigurationProperty -Filter "system.webServer/security/authentication/anonymousAuthentication" `
    -PSPath "IIS:\Sites\$SiteName" -Name enabled -Value $false
Set-WebConfigurationProperty -Filter "system.webServer/security/authentication/windowsAuthentication" `
    -PSPath "IIS:\Sites\$SiteName" -Name enabled -Value $true

# Kernel mode auth (required for Kerberos to work with service account SPN)
Set-WebConfigurationProperty -Filter "system.webServer/security/authentication/windowsAuthentication" `
    -PSPath "IIS:\Sites\$SiteName" -Name useKernelMode -Value $true

Write-Host "  OK: Windows Authentication enabled (kernel mode)" -ForegroundColor Green

# -----------------------------------------------------------------------
# Log directory permissions
# -----------------------------------------------------------------------
$acl = Get-Acl $LogPath
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $AppPoolIdentity, "Modify", "ContainerInherit,ObjectInherit", "None", "Allow"
)
$acl.SetAccessRule($rule)
Set-Acl $LogPath $acl
Write-Host "  OK: Log directory permissions set for $AppPoolIdentity" -ForegroundColor Green

# -----------------------------------------------------------------------
# Restart IIS
# -----------------------------------------------------------------------
iisreset /noforce
Write-Host "`n=== IIS configuration complete ===" -ForegroundColor Green
Write-Host "Test: Invoke-WebRequest -Uri 'https://$($env:COMPUTERNAME)/health' -UseDefaultCredentials"
