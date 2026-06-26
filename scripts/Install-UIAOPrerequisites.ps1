<#
.SYNOPSIS
    Install-UIAOPrerequisites.ps1
    Validates and installs all prerequisites required to run the UIAO CLI and its
    companion PowerShell scripts on an operator workstation or Windows Server.

.DESCRIPTION
    Runs seven sequential steps:

      1. Verify PowerShell 5.1 or 7.x is present (7.x required for the UIAO CLI helper
         scripts; 5.1 is sufficient for Invoke-ADSurvey.ps1).
      2. Load core prerequisite modules (ActiveDirectory, GroupPolicy, PKI,
         CimCmdlets, ScheduledTasks, NetAdapter).
      3. Install RSAT DNS + DHCP server tools via DISM / Add-WindowsFeature if
         running on Windows Server; skips silently on a non-Server SKU.
      4. Load DnsServer and DhcpServer modules after the RSAT install.
      5. Enable PowerShell Remoting (required for UIAO orchestration across hosts).
      6. Set the process-scoped execution policy to RemoteSigned.
      7. Validate that all expected modules are discoverable and write a final
         pass/fail summary.

    All state-changing steps (RSAT install, PSRemoting, execution policy) require
    an elevated (Administrator) process.  The script will warn if it detects that
    it is not elevated and prompt before continuing — it does NOT silently self-
    elevate.

    This script ships inside the uiao.zip offline bundle; it is also available
    individually at:
      https://whalermike.github.io/uiao/download/

.PARAMETER SkipRsatInstall
    Skip the RSAT DNS/DHCP install step (useful on domain controllers where the
    role is already present, or on workstations with no internet access).

.PARAMETER SkipPSRemoting
    Skip the Enable-PSRemoting step (useful if remoting is already configured
    by Group Policy).

.PARAMETER WhatIf
    Dry-run: report what each step would do without making changes.

.EXAMPLE
    # Full install — run as Administrator
    .\Install-UIAOPrerequisites.ps1

.EXAMPLE
    # Skip RSAT and PSRemoting (e.g. on a DC where both are already present)
    .\Install-UIAOPrerequisites.ps1 -SkipRsatInstall -SkipPSRemoting

.EXAMPLE
    # Dry-run — see what would happen without changing anything
    .\Install-UIAOPrerequisites.ps1 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$SkipRsatInstall,
    [switch]$SkipPSRemoting
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ───────────────────────────────────────────────────────────────────

function Write-Step {
    param([string]$Number, [string]$Title)
    Write-Host ""
    Write-Host "Step $Number — $Title" -ForegroundColor Cyan
    Write-Host ("-" * 60) -ForegroundColor DarkGray
}

function Write-OK   { param([string]$Msg) Write-Host "  [OK]   $Msg" -ForegroundColor Green  }
function Write-WARN { param([string]$Msg) Write-Host "  [WARN] $Msg" -ForegroundColor Yellow }
function Write-FAIL { param([string]$Msg) Write-Host "  [FAIL] $Msg" -ForegroundColor Red    }
function Write-SKIP { param([string]$Msg) Write-Host "  [SKIP] $Msg" -ForegroundColor DarkGray }

# Track overall result
$script:Failures = [System.Collections.Generic.List[string]]::new()
$script:Warnings = [System.Collections.Generic.List[string]]::new()

# ── Elevation check ───────────────────────────────────────────────────────────

$IsAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $IsAdmin) {
    Write-WARN "This session is NOT elevated (Administrator).  Steps 3, 5, and 6 may fail."
    Write-WARN "Re-run from an elevated PowerShell prompt for a full install."
    Write-Host ""
}

# ── Step 1 — Verify PowerShell version ───────────────────────────────────────

Write-Step "1" "Verify PowerShell version"

$psVer = $PSVersionTable.PSVersion
Write-Host "  Detected: PowerShell $psVer"

if ($psVer.Major -ge 7) {
    Write-OK "PowerShell 7+ detected — full UIAO CLI support."
} elseif ($psVer.Major -eq 5 -and $psVer.Minor -ge 1) {
    Write-WARN "PowerShell 5.1 detected.  Invoke-ADSurvey.ps1 is compatible; the UIAO CLI"
    Write-WARN "and companion scripts require PowerShell 7.  Install from:"
    Write-WARN "  https://github.com/PowerShell/PowerShell/releases"
    $script:Warnings.Add("PowerShell 7 not installed (5.1 present)")
} else {
    Write-FAIL "PowerShell $psVer is too old.  Minimum supported: 5.1."
    $script:Failures.Add("PowerShell version too old: $psVer")
}

# ── Step 2 — Load core prerequisite modules ───────────────────────────────────

Write-Step "2" "Load core prerequisite PowerShell modules"

$CoreModules = @(
    "ActiveDirectory",
    "GroupPolicy",
    "PKI",
    "CimCmdlets",
    "ScheduledTasks",
    "NetAdapter"
)

foreach ($mod in $CoreModules) {
    if (Get-Module -Name $mod -ListAvailable -ErrorAction SilentlyContinue) {
        if ($PSCmdlet.ShouldProcess($mod, "Import-Module")) {
            try {
                Import-Module $mod -ErrorAction Stop
                Write-OK "$mod loaded"
            } catch {
                Write-WARN "$mod available but failed to import: $_"
                $script:Warnings.Add("$mod import failed")
            }
        } else {
            Write-SKIP "$mod (WhatIf — would import)"
        }
    } else {
        Write-WARN "$mod not found — may require RSAT or the ActiveDirectory role."
        $script:Warnings.Add("$mod not available")
    }
}

# ── Step 3 — Install RSAT role tools (DNS & DHCP) ─────────────────────────────

Write-Step "3" "Install RSAT role tools (DNS & DHCP)"

if ($SkipRsatInstall) {
    Write-SKIP "RSAT install skipped (-SkipRsatInstall)"
} elseif (-not $IsAdmin) {
    Write-WARN "Skipping RSAT install — not running as Administrator."
    $script:Warnings.Add("RSAT install skipped (not admin)")
} else {
    # Windows Server: Add-WindowsFeature; Desktop: Add-WindowsCapability (DISM)
    $osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
    $isServer = $osInfo.ProductType -in @(2, 3)  # 2 = domain controller, 3 = server

    if ($isServer) {
        if ($PSCmdlet.ShouldProcess("RSAT-DNS-Server, RSAT-DHCP", "Install-WindowsFeature")) {
            try {
                Import-Module ServerManager -ErrorAction SilentlyContinue
                $result = Install-WindowsFeature RSAT-DNS-Server, RSAT-DHCP -IncludeManagementTools -Verbose
                if ($result.Success) {
                    Write-OK "RSAT-DNS-Server and RSAT-DHCP installed (Server)"
                    if ($result.RestartNeeded -eq "Yes") {
                        Write-WARN "A restart is required to complete the RSAT install."
                    }
                } else {
                    Write-FAIL "Install-WindowsFeature returned a failure for one or more features."
                    $script:Failures.Add("RSAT install failed on Server")
                }
            } catch {
                Write-FAIL "RSAT install error: $_"
                $script:Failures.Add("RSAT install exception: $_")
            }
        } else {
            Write-SKIP "Install-WindowsFeature RSAT-DNS-Server, RSAT-DHCP (WhatIf)"
        }
    } else {
        # Windows 10 / 11 workstation — use DISM capabilities
        if ($PSCmdlet.ShouldProcess("DNS.Tools, DHCP.Tools", "Add-WindowsCapability")) {
            try {
                $caps = @(
                    "Rsat.Dns.Tools~~~~0.0.1.0",
                    "Rsat.DHCP.Tools~~~~0.0.1.0"
                )
                foreach ($cap in $caps) {
                    $existing = Get-WindowsCapability -Online -Name $cap -ErrorAction SilentlyContinue
                    if ($existing -and $existing.State -eq "Installed") {
                        Write-OK "$cap already installed"
                    } else {
                        Add-WindowsCapability -Online -Name $cap | Out-Null
                        Write-OK "$cap installed"
                    }
                }
            } catch {
                Write-WARN "DISM capability install encountered an error: $_"
                Write-WARN "Install RSAT manually via Settings → Apps → Optional Features."
                $script:Warnings.Add("RSAT capability install failed on workstation")
            }
        } else {
            Write-SKIP "Add-WindowsCapability RSAT DNS/DHCP (WhatIf)"
        }
    }
}

# ── Step 4 — Load DnsServer and DhcpServer ────────────────────────────────────

Write-Step "4" "Load DnsServer and DhcpServer modules"

$RsatModules = @("DnsServer", "DhcpServer")

foreach ($mod in $RsatModules) {
    if (Get-Module -Name $mod -ListAvailable -ErrorAction SilentlyContinue) {
        if ($PSCmdlet.ShouldProcess($mod, "Import-Module")) {
            try {
                Import-Module $mod -ErrorAction Stop
                Write-OK "$mod loaded"
            } catch {
                Write-WARN "$mod available but failed to import: $_"
                $script:Warnings.Add("$mod import failed")
            }
        } else {
            Write-SKIP "$mod (WhatIf — would import)"
        }
    } else {
        Write-WARN "$mod not found — RSAT DNS/DHCP install may not have completed or may require a restart."
        $script:Warnings.Add("$mod not available after RSAT step")
    }
}

# ── Step 5 — Enable PowerShell Remoting ───────────────────────────────────────

Write-Step "5" "Enable PowerShell Remoting"

if ($SkipPSRemoting) {
    Write-SKIP "PSRemoting step skipped (-SkipPSRemoting)"
} elseif (-not $IsAdmin) {
    Write-WARN "Skipping Enable-PSRemoting — not running as Administrator."
    $script:Warnings.Add("PSRemoting not enabled (not admin)")
} else {
    if ($PSCmdlet.ShouldProcess("localhost", "Enable-PSRemoting -Force")) {
        try {
            Enable-PSRemoting -Force -ErrorAction Stop
            Write-OK "PSRemoting enabled"
        } catch {
            Write-WARN "Enable-PSRemoting failed: $_.  May already be enabled or blocked by policy."
            $script:Warnings.Add("Enable-PSRemoting failed: $_")
        }
    } else {
        Write-SKIP "Enable-PSRemoting -Force (WhatIf)"
    }
}

# ── Step 6 — Set execution policy ─────────────────────────────────────────────

Write-Step "6" "Set execution policy (Process scope)"

if (-not $IsAdmin) {
    Write-WARN "Not running as Administrator — setting process-scope policy anyway (no elevation needed for Process scope)."
}

if ($PSCmdlet.ShouldProcess("Process scope", "Set-ExecutionPolicy RemoteSigned")) {
    try {
        Set-ExecutionPolicy RemoteSigned -Scope Process -Force -ErrorAction Stop
        Write-OK "ExecutionPolicy set to RemoteSigned (Process scope)"
    } catch {
        Write-WARN "Set-ExecutionPolicy failed: $_"
        $script:Warnings.Add("ExecutionPolicy not set: $_")
    }
} else {
    Write-SKIP "Set-ExecutionPolicy RemoteSigned -Scope Process (WhatIf)"
}

# ── Step 7 — Validate all prerequisites ─────────────────────────────────────

Write-Step "7" "Validate all prerequisites"

$AllModules = @("ActiveDirectory","GroupPolicy","DnsServer","DhcpServer","PKI","CimCmdlets","ScheduledTasks","NetAdapter")

$ModuleStatus = Get-Module -ListAvailable $AllModules |
    Select-Object Name, Version, ModuleBase |
    Sort-Object Name

if ($ModuleStatus) {
    $ModuleStatus | Format-Table -AutoSize | Out-String | Write-Host
} else {
    Write-WARN "No modules from the expected list were found."
}

$FoundNames = $ModuleStatus.Name
foreach ($mod in $AllModules) {
    if ($FoundNames -contains $mod) {
        Write-OK "$mod available"
    } else {
        Write-WARN "$mod NOT available"
        $script:Warnings.Add("$mod unavailable at validation")
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host ("=" * 60) -ForegroundColor DarkGray
Write-Host "  UIAO Prerequisites — Summary" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor DarkGray

if ($script:Failures.Count -eq 0 -and $script:Warnings.Count -eq 0) {
    Write-Host "  All prerequisites satisfied.  You may proceed with:" -ForegroundColor Green
    Write-Host ""
    Write-Host "    pip install uiao" -ForegroundColor White
    Write-Host '    pip install "uiao[api]"' -ForegroundColor White
    Write-Host ""
    Write-Host "  Optional — export GPO baseline and run the UIAO auditor:" -ForegroundColor DarkGray
    Write-Host '    Get-GPOReport -All -ReportType Xml -Path C:\Temp\gpo.xml' -ForegroundColor White
    Write-Host '    uiao ir auditor-bundle C:\Temp\gpo.xml --out-dir C:\Temp\uiao-bundle' -ForegroundColor White
} elseif ($script:Failures.Count -eq 0) {
    Write-Host "  Prerequisites check completed with $($script:Warnings.Count) warning(s)." -ForegroundColor Yellow
    Write-Host "  Review warnings above.  The UIAO CLI may still function for most operations."
    foreach ($w in $script:Warnings) { Write-WARN $w }
} else {
    Write-Host "  Prerequisites check FAILED ($($script:Failures.Count) error(s), $($script:Warnings.Count) warning(s))." -ForegroundColor Red
    foreach ($f in $script:Failures) { Write-FAIL $f }
    foreach ($w in $script:Warnings) { Write-WARN $w }
    Write-Host ""
    Write-Host "  Resolve the errors above before proceeding." -ForegroundColor Red
    exit 1
}

Write-Host ("=" * 60) -ForegroundColor DarkGray
