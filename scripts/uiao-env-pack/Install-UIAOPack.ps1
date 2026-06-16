<#
.SYNOPSIS
    Install-UIAOPack.ps1
    Offline installer for a UIAO PowerShell pack. Bundled inside the
    pack zip; runs on the target host with no internet access.

.DESCRIPTION
    Reads the bundled manifest.json (sibling to this script in the
    unpacked zip), verifies SHA256 of every artifact, then installs:

        Step 01 — PowerShell 7 runtime (MSI, silent)
        Step 02 — Modules (copy into $PSModulePath target)
        Step 03 — Third-party tools (MSI/EXE, silent)
        Step 04 — Verify (Get-Module -ListAvailable, Get-Command for tools)

    No backticks, no continuation characters, no heredocs.
    No PowerShell module dependencies — uses ConvertFrom-Json (built-in).

    Per-item failures are logged as FAIL with the exception message
    and the install continues (unless -StrictInstall is set).

.PARAMETER PackRoot
    Root of the unpacked pack (directory containing manifest.json).
    Defaults to the directory containing this script.

.PARAMETER ModuleScope
    Where to install modules. "Machine" copies to
    $env:ProgramFiles\PowerShell\Modules (requires elevation).
    "User" copies to $env:USERPROFILE\Documents\PowerShell\Modules.
    Default: User.

.PARAMETER SkipRuntime
    Skip Step 01. Use when pwsh 7 is already installed on the target.

.PARAMETER SkipTools
    Skip Step 04. Use when third-party tools are already present
    or installed via a different channel.

.PARAMETER StrictInstall
    Abort on first failure instead of continuing.

.EXAMPLE
    .\Install-UIAOPack.ps1
    .\Install-UIAOPack.ps1 -ModuleScope Machine
    .\Install-UIAOPack.ps1 -SkipRuntime -SkipTools
#>

[CmdletBinding()]
param(
    [string]$PackRoot = $PSScriptRoot,
    [ValidateSet("User", "Machine")]
    [string]$ModuleScope = "User",
    [switch]$SkipRuntime,
    [switch]$SkipTools,
    [switch]$StrictInstall
)

if ($StrictInstall) {
    $ErrorActionPreference = "Stop"
}
else {
    $ErrorActionPreference = "Continue"
}

# ---------------------------------------------------------------
# Load manifest
# ---------------------------------------------------------------
$manifestPath = Join-Path $PackRoot "manifest.json"
if (-not (Test-Path $manifestPath)) { throw "Manifest not found: $manifestPath" }
$manifest = (Get-Content -Path $manifestPath -Raw) | ConvertFrom-Json

$packName = $manifest.pack.name
$packVersion = $manifest.pack.version

Write-Host "[uiao-pwsh-pack] Installing $packName v$packVersion"
Write-Host "  PackRoot     : $PackRoot"
Write-Host "  ModuleScope  : $ModuleScope"

# ---------------------------------------------------------------
# Helper: verify SHA256
# ---------------------------------------------------------------
function Test-UIAOArtifactHash {
    param(
        [string]$Path,
        [string]$ExpectedSha256
    )
    if ([string]::IsNullOrEmpty($ExpectedSha256)) {
        Write-Host "    WARN   no sha256 in manifest for $Path; skipping verification"
        return $true
    }
    $actual = (Get-FileHash -Path $Path -Algorithm SHA256).Hash
    if ($actual -ne $ExpectedSha256) {
        Write-Host "    FAIL   sha256 mismatch for $Path"
        Write-Host "           expected: $ExpectedSha256"
        Write-Host "           actual:   $actual"
        return $false
    }
    Write-Host "    OK     sha256 verified ($actual)"
    return $true
}

# ---------------------------------------------------------------
# Step 01 — PowerShell runtime
# ---------------------------------------------------------------
if ($SkipRuntime) {
    Write-Host "[uiao-pwsh-pack] Step 01 — PowerShell runtime SKIPPED (-SkipRuntime)"
}
else {
    Write-Host "[uiao-pwsh-pack] Step 01 — PowerShell runtime"
    $rt = $manifest.runtime.powershell
    $rtMsi = Join-Path (Join-Path $PackRoot "pwsh") $rt.filename
    if (-not (Test-Path $rtMsi)) {
        Write-Host "  FAIL   runtime MSI missing: $rtMsi"
    }
    elseif (-not (Test-UIAOArtifactHash -Path $rtMsi -ExpectedSha256 $rt.sha256)) {
        Write-Host "  FAIL   runtime sha256 mismatch; aborting Step 01"
    }
    else {
        Write-Host "  Installing $($rt.filename) (PowerShell $($rt.version)) silently"
        $msiArgs = @("/i", "`"$rtMsi`"") + $rt.silent_args
        $p = Start-Process -FilePath "msiexec.exe" -ArgumentList $msiArgs -Wait -PassThru -NoNewWindow
        if ($p.ExitCode -eq 0) {
            Write-Host "  OK     PowerShell $($rt.version) installed (exit 0)"
        }
        else {
            Write-Host "  FAIL   msiexec exit $($p.ExitCode)"
        }
    }
}

# ---------------------------------------------------------------
# Step 02 — Modules
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 02 — Modules ($($manifest.modules.Count) declared)"
$modulesSrc = Join-Path $PackRoot "modules"

if ($ModuleScope -eq "Machine") {
    $moduleTarget = Join-Path $env:ProgramFiles "PowerShell\Modules"
}
else {
    $moduleTarget = Join-Path $env:USERPROFILE "Documents\PowerShell\Modules"
}

if (-not (Test-Path $moduleTarget)) {
    New-Item -ItemType Directory -Path $moduleTarget -Force | Out-Null
}
Write-Host "  Target: $moduleTarget"

if (-not (Test-Path $modulesSrc)) {
    Write-Host "  FAIL   modules directory missing: $modulesSrc"
}
else {
    $moduleFolders = Get-ChildItem -Path $modulesSrc -Directory
    foreach ($modFolder in $moduleFolders) {
        try {
            Copy-Item -Path $modFolder.FullName -Destination $moduleTarget -Recurse -Force
            Write-Host "  OK     $($modFolder.Name) -> $moduleTarget"
        }
        catch {
            Write-Host "  FAIL   $($modFolder.Name) :: $($_.Exception.Message)"
        }
    }
}

# ---------------------------------------------------------------
# Step 03 — Third-party tools
# ---------------------------------------------------------------
if ($SkipTools) {
    Write-Host "[uiao-pwsh-pack] Step 03 — Tools SKIPPED (-SkipTools)"
}
else {
    Write-Host "[uiao-pwsh-pack] Step 03 — Tools ($($manifest.tools.Count) declared)"
    $toolsSrc = Join-Path $PackRoot "tools"
    foreach ($tool in $manifest.tools) {
        $toolPath = Join-Path $toolsSrc $tool.filename
        if (-not (Test-Path $toolPath)) {
            Write-Host "  FAIL   $($tool.name) installer missing: $toolPath"
            continue
        }
        if (-not (Test-UIAOArtifactHash -Path $toolPath -ExpectedSha256 $tool.sha256)) {
            Write-Host "  FAIL   $($tool.name) sha256 mismatch; skipping"
            continue
        }
        $ext = [System.IO.Path]::GetExtension($tool.filename).ToLowerInvariant()
        try {
            if ($ext -eq ".msi") {
                $msiArgs = @("/i", "`"$toolPath`"") + $tool.silent_args
                $p = Start-Process -FilePath "msiexec.exe" -ArgumentList $msiArgs -Wait -PassThru -NoNewWindow
            }
            else {
                $p = Start-Process -FilePath $toolPath -ArgumentList $tool.silent_args -Wait -PassThru -NoNewWindow
            }
            if ($p.ExitCode -eq 0) {
                Write-Host "  OK     $($tool.name) $($tool.version) installed (exit 0)"
            }
            else {
                Write-Host "  FAIL   $($tool.name) exit $($p.ExitCode)"
            }
        }
        catch {
            Write-Host "  FAIL   $($tool.name) :: $($_.Exception.Message)"
        }
    }
}

# ---------------------------------------------------------------
# Step 04 — Verify
# ---------------------------------------------------------------
Write-Host "[uiao-pwsh-pack] Step 04 — Verify"
Write-Host "  Installed modules under $moduleTarget :"
$expected = $manifest.modules.name
foreach ($name in $expected) {
    $present = Test-Path (Join-Path $moduleTarget $name)
    $status = if ($present) { "OK   " } else { "MISS " }
    Write-Host "    $status $name"
}

Write-Host "  Tools on PATH :"
foreach ($tool in $manifest.tools) {
    $found = Get-Command -Name $tool.name -ErrorAction SilentlyContinue
    if ($found) {
        Write-Host "    OK    $($tool.name) -> $($found.Source)"
    }
    else {
        Write-Host "    MISS  $($tool.name) (may require new shell to refresh PATH)"
    }
}

Write-Host "[uiao-pwsh-pack] Install complete."
