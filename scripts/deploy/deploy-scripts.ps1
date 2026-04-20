<#
.SYNOPSIS
    Install-UIAOServer.ps1
    Full IIS + Python installation for UIAO AD Survey API
    Windows Server 2026

    Run as: Administrator
    Time:   ~15 minutes (depends on Python download speed)
#>
[CmdletBinding()]
param(
    [string]$PythonVersion = "3.13",
    [string]$LogPath = "C:\Logs\uiao-api"
)
$ErrorActionPreference = "Stop"

function Write-Step { param([string]$Msg) Write-Host "`n==> $Msg" -ForegroundColor Cyan }
function Write-OK   { param([string]$Msg) Write-Host "    OK: $Msg" -ForegroundColor Green }
function Write-Warn { param([string]$Msg) Write-Host "    WARN: $Msg" -ForegroundColor Yellow }

# -----------------------------------------------------------------------
# Step 1: IIS + required features
# -----------------------------------------------------------------------
Write-Step "Installing IIS and required Windows features..."

$features = @(
    "Web-Server",
    "Web-WebServer",
    "Web-Common-Http",
    "Web-Default-Doc",
    "Web-Dir-Browsing",
    "Web-Http-Errors",
    "Web-Static-Content",
    "Web-Http-Logging",
    "Web-Log-Libraries",
    "Web-Request-Monitor",
    "Web-Http-Tracing",
    "Web-Security",
    "Web-Filtering",
    "Web-Windows-Auth",        # Windows Authentication module
    "Web-App-Dev",
    "Web-Net-Ext45",
    "Web-Asp-Net45",
    "Web-ISAPI-Ext",
    "Web-ISAPI-Filter",
    "Web-Mgmt-Tools",
    "Web-Mgmt-Console",
    "Web-Scripting-Tools",
    "NET-Framework-45-Core"
)

foreach ($f in $features) {
    $state = (Get-WindowsFeature -Name $f).InstallState
    if ($state -ne "Installed") {
        Install-WindowsFeature -Name $f -IncludeManagementTools | Out-Null
        Write-OK "Installed: $f"
    } else {
        Write-Verbose "Already installed: $f"
    }
}

# -----------------------------------------------------------------------
# Step 2: HttpPlatformHandler 2.0
# -----------------------------------------------------------------------
Write-Step "Installing HttpPlatformHandler 2.0..."

$hphMsi = "C:\Temp\HttpPlatformHandler_amd64.msi"
$hphUrl = "https://download.microsoft.com/download/0/F/A/0FA07E76-5AD9-4F35-8EB8-4A8A940E9B6E/HttpPlatformHandler_amd64.msi"

New-Item -ItemType Directory -Path "C:\Temp" -Force | Out-Null

if (-not (Test-Path $hphMsi)) {
    Write-Verbose "Downloading HttpPlatformHandler..."
    Invoke-WebRequest -Uri $hphUrl -OutFile $hphMsi -UseBasicParsing
}

# Check if already installed
$installed = Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
             Where-Object { $_.DisplayName -like "*HttpPlatformHandler*" }
if (-not $installed) {
    Start-Process msiexec.exe -ArgumentList "/i `"$hphMsi`" /qn" -Wait
    Write-OK "HttpPlatformHandler installed"
} else {
    Write-OK "HttpPlatformHandler already installed"
}

# -----------------------------------------------------------------------
# Step 3: Python 3.13
# -----------------------------------------------------------------------
Write-Step "Installing Python $PythonVersion..."

$pyInstaller = "C:\Temp\python-$PythonVersion-amd64.exe"
$pyUrl = "https://www.python.org/ftp/python/$PythonVersion.0/python-$PythonVersion.0-amd64.exe"

if (-not (Test-Path "C:\Python313\python.exe")) {
    if (-not (Test-Path $pyInstaller)) {
        Write-Verbose "Downloading Python $PythonVersion..."
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyInstaller -UseBasicParsing
    }
    # Install for all users, add to PATH, no shortcuts
    Start-Process $pyInstaller -ArgumentList `
        "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_doc=0" `
        -Wait
    Write-OK "Python $PythonVersion installed to C:\Python313"
} else {
    Write-OK "Python $PythonVersion already installed"
}

# Refresh PATH in current session
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# -----------------------------------------------------------------------
# Step 4: Git (needed for repo clone on server)
# -----------------------------------------------------------------------
Write-Step "Checking Git..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $gitUrl  = "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe"
    $gitExe  = "C:\Temp\git-installer.exe"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitExe -UseBasicParsing
    Start-Process $gitExe -ArgumentList "/SILENT /NORESTART" -Wait
    Write-OK "Git installed"
} else {
    Write-OK "Git already available"
}

# -----------------------------------------------------------------------
# Step 5: Log directory
# -----------------------------------------------------------------------
Write-Step "Creating log directory $LogPath..."
New-Item -ItemType Directory -Path $LogPath -Force | Out-Null
# Grant app pool identity write access (will be set once account is created)
Write-OK "Log directory created: $LogPath"

# -----------------------------------------------------------------------
# Step 6: IIS rewrite module (for HTTP→HTTPS redirect in web.config)
# -----------------------------------------------------------------------
Write-Step "Installing URL Rewrite module..."
$rwUrl = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
$rwMsi = "C:\Temp\rewrite_amd64.msi"

$rwInstalled = Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
               Where-Object { $_.DisplayName -like "*IIS URL Rewrite*" }
if (-not $rwInstalled) {
    if (-not (Test-Path $rwMsi)) {
        Invoke-WebRequest -Uri $rwUrl -OutFile $rwMsi -UseBasicParsing
    }
    Start-Process msiexec.exe -ArgumentList "/i `"$rwMsi`" /qn" -Wait
    Write-OK "URL Rewrite module installed"
} else {
    Write-OK "URL Rewrite module already installed"
}

Write-Host "`n=== Install-UIAOServer complete ===" -ForegroundColor Green
Write-Host "Next: Run Register-ServiceAccount.ps1 on a DC, then Register-UIAOAPI.ps1 here."


# -----------------------------------------------------------------------
# -----------------------------------------------------------------------

<#
.SYNOPSIS
    Register-ServiceAccount.ps1
    Creates the UIAO API service account and registers its SPN.
    Run on a DC or machine with RSAT AD tools.
#>
# (Paste below into Register-ServiceAccount.ps1 — separate file)

[CmdletBinding()]
param(
    [string]$AccountName    = "SVC-UIAO-API",
    [string]$AccountOU      = "OU=Service Accounts,DC=corp,DC=contoso,DC=com",
    [string]$ServerDNS      = "uiao-api.corp.contoso.com",
    [string]$Domain         = "corp.contoso.com"
)
$ErrorActionPreference = "Stop"
Import-Module ActiveDirectory -ErrorAction Stop

Write-Host "Creating service account $AccountName..." -ForegroundColor Cyan

# Generate long random password
Add-Type -AssemblyName System.Web
$Password = [System.Web.Security.Membership]::GeneratePassword(32, 8)
$SecurePassword = ConvertTo-SecureString $Password -AsPlainText -Force

# Create account
try {
    New-ADUser `
        -Name $AccountName `
        -SamAccountName $AccountName `
        -UserPrincipalName "$AccountName@$Domain" `
        -Path $AccountOU `
        -AccountPassword $SecurePassword `
        -PasswordNeverExpires $false `
        -ChangePasswordAtLogon $false `
        -CannotChangePassword $true `
        -Enabled $true `
        -Description "UIAO AD Survey API service account"
    Write-Host "  OK: Account created" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -like "*already exists*") {
        Write-Host "  WARN: Account already exists, skipping creation" -ForegroundColor Yellow
    } else { throw }
}

# Register SPNs
$spns = @(
    "HTTP/$ServerDNS",
    "HTTP/$($ServerDNS.Split('.')[0])"   # short hostname
)
foreach ($spn in $spns) {
    try {
        Set-ADUser $AccountName -ServicePrincipalNames @{ Add = $spn }
        Write-Host "  OK: SPN registered: $spn" -ForegroundColor Green
    } catch {
        Write-Host "  WARN: SPN may already exist: $spn" -ForegroundColor Yellow
    }
}

# Grant read permissions on all user attributes
# (Domain Users already has Read on most attrs; this grants the explicit right)
$acl = Get-Acl "AD:\$AccountOU"
Write-Host "  NOTE: Verify $AccountName has 'Read all user attributes' in AD delegation" -ForegroundColor Yellow

Write-Host "`nSERVICE ACCOUNT PASSWORD (store in vault NOW — not shown again):" -ForegroundColor Red
Write-Host $Password -ForegroundColor Red
Write-Host "`nSPNs registered: $($spns -join ', ')"
Write-Host "Next: configure IIS app pool to run as CORP\$AccountName with this password."


# -----------------------------------------------------------------------
# -----------------------------------------------------------------------

<#
.SYNOPSIS
    Register-UIAOAPI.ps1
    Creates the IIS app pool and site for the UIAO API.
    Run on the target Windows Server 2026 as Administrator.
#>
# (Paste below into Register-UIAOAPI.ps1 — separate file)

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
