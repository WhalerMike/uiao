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
$rwInfoUrl = "https://www.iis.net/downloads/microsoft/url-rewrite"
$rwMsi = "C:\Temp\rewrite_amd64_en-US.msi"

$rwInstalled = Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\* |
               Where-Object { $_.DisplayName -like "*IIS URL Rewrite*" }
if (-not $rwInstalled) {
    if (-not (Test-Path $rwMsi)) {
        throw "URL Rewrite installer not found at $rwMsi. Open $rwInfoUrl, download the x64 MSI, save it to $rwMsi, then rerun this script."
    }
    Start-Process msiexec.exe -ArgumentList "/i `"$rwMsi`" /qn" -Wait
    Write-OK "URL Rewrite module installed"
} else {
    Write-OK "URL Rewrite module already installed"
}

Write-Host "`n=== Install-UIAOServer complete ===" -ForegroundColor Green
Write-Host "Next: Run Register-ServiceAccount.ps1 on a DC, then Register-UIAOAPI.ps1 here."
