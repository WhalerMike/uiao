<#
.SYNOPSIS
    Build-UIAOSourceZip.ps1
    Assembles the uiao.zip offline bundle for the UIAO CLI.

.DESCRIPTION
    Produces a single zip that an operator can extract on a machine with no
    internet access and run:

      python -m pip install .
      python -m pip install ".[api]"

    The bundle includes:

      Source tree
        src\uiao\             — the installable Python package
        pyproject.toml        — package metadata / dependency declarations
        README.md             — project README
        LICENSE               — Apache-2.0

      Prerequisites
        Install-UIAOPrerequisites.ps1  — validates + installs all PS prerequisites
                                         (modules, RSAT, PSRemoting, exec policy)

      Assessment & analysis scripts
        scripts\Invoke-ZtDashboard.ps1         — Zero Trust Assessment Dashboard
        scripts\Invoke-ADSurvey.ps1            — AD Forest Survey (Phase 1 discovery)

      Group Policy migration scripts
        scripts\Invoke-GpoMigrationTriage.ps1  — GPO → Intune / Arc classification
        scripts\Invoke-GpoObsoleteAudit.ps1    — GPO obsolete-setting audit

      Help Desk / Cloud Services Entra Operations scripts
        scripts\helpdesk-entra\                — module + 6 Graph scripts

      Intune + Azure Arc Modernization scripts
        scripts\intune-arc\                    — module + 12 Graph/Az scripts

      README.txt — bundle manifest and quick-start

    Output: dist/uiao-<version>.zip  (or the name you specify with -ZipName)

    This script is invoked by .github/workflows/source-zip-build.yml but can
    also be run locally on Windows or Linux (pwsh 7 required).

.PARAMETER Version
    Version string embedded in the zip filename.
    Default: read from src/uiao/__version__.py.

.PARAMETER OutDir
    Output directory (default: dist/).

.PARAMETER ZipName
    Override the output filename entirely (default: uiao-<version>.zip).

.EXAMPLE
    # Local build
    pwsh ./scripts/Build-UIAOSourceZip.ps1

.EXAMPLE
    pwsh ./scripts/Build-UIAOSourceZip.ps1 -Version "1.0.0" -OutDir "dist"
#>
[CmdletBinding()]
param(
    [string]$Version = "",
    [string]$OutDir  = "dist",
    [string]$ZipName = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

# ── Resolve version ───────────────────────────────────────────────────────────

if (-not $Version) {
    $verFile = Join-Path $RepoRoot "src/uiao/__version__.py"
    if (Test-Path $verFile) {
        $line = (Get-Content $verFile) | Where-Object { $_ -match '__version__' } | Select-Object -First 1
        if ($line -match '"([^"]+)"') { $Version = $Matches[1] }
    }
    if (-not $Version) { $Version = "0.0.0" }
}

if (-not $ZipName) { $ZipName = "uiao-$Version.zip" }

Write-Host "Building UIAO Source ZIP v$Version → $ZipName" -ForegroundColor Cyan

# ── Staging directory ─────────────────────────────────────────────────────────

$Stage = Join-Path ([System.IO.Path]::GetTempPath()) "uiao-source-zip-$Version"
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage | Out-Null

function Add-File {
    param([string]$Src, [string]$DstSubdir = "")
    if (-not (Test-Path $Src)) { Write-Warning "  ! Not found (skipped): $Src"; return }
    $dest = if ($DstSubdir) { Join-Path $Stage $DstSubdir } else { $Stage }
    if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest | Out-Null }
    Copy-Item $Src -Destination $dest
    $rel = (Split-Path $Src -Leaf)
    Write-Host "  + $(if ($DstSubdir) { "$DstSubdir\$rel" } else { $rel })" -ForegroundColor DarkGray
}

function Add-Dir {
    param([string]$Src, [string]$DstSubdir)
    if (-not (Test-Path $Src)) { Write-Warning "  ! Not found (skipped): $Src"; return }
    $dest = Join-Path $Stage $DstSubdir
    Copy-Item $Src -Destination $dest -Recurse
    Write-Host "  + $DstSubdir\" -ForegroundColor DarkGray
}

# ── Python source tree ────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Python source:" -ForegroundColor DarkCyan

Add-Dir  (Join-Path $RepoRoot "src")        "src"
Add-File (Join-Path $RepoRoot "pyproject.toml")
Add-File (Join-Path $RepoRoot "README.md")
Add-File (Join-Path $RepoRoot "LICENSE")    # Apache-2.0

# ── Prerequisites script ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "Prerequisites:" -ForegroundColor DarkCyan

Add-File (Join-Path $RepoRoot "scripts\Install-UIAOPrerequisites.ps1")

# ── Assessment & analysis scripts ────────────────────────────────────────────

Write-Host ""
Write-Host "Assessment & analysis scripts:" -ForegroundColor DarkCyan

Add-File (Join-Path $RepoRoot "docs\customer-documents\operational-guides\zero-trust-assessment\scripts\Invoke-ZtDashboard.ps1") "scripts"
Add-File (Join-Path $RepoRoot "scripts\ad-survey\Invoke-ADSurvey.ps1") "scripts"

# ── GPO migration scripts ─────────────────────────────────────────────────────

Write-Host ""
Write-Host "Group Policy migration scripts:" -ForegroundColor DarkCyan

Add-File (Join-Path $RepoRoot "docs\customer-documents\substrate\platform-tooling\scripts\Invoke-GpoMigrationTriage.ps1") "scripts"
Add-File (Join-Path $RepoRoot "docs\customer-documents\substrate\platform-tooling\scripts\Invoke-GpoObsoleteAudit.ps1")   "scripts"

# ── Help Desk / Cloud Services Entra Operations scripts ──────────────────────

Write-Host ""
Write-Host "Help Desk / Entra Operations scripts:" -ForegroundColor DarkCyan

$HdSrc = Join-Path $RepoRoot "docs\customer-documents\operational-guides\helpdesk-entra-operations\scripts"
Add-Dir $HdSrc "scripts\helpdesk-entra"

# ── Intune + Azure Arc Modernization scripts ──────────────────────────────────

Write-Host ""
Write-Host "Intune + Azure Arc Modernization scripts:" -ForegroundColor DarkCyan

$IaSrc = Join-Path $RepoRoot "docs\customer-documents\operational-guides\intune-arc-modernization\scripts"
Add-Dir $IaSrc "scripts\intune-arc"

# ── README.txt ────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Bundle README:" -ForegroundColor DarkCyan

$ReadmePath = Join-Path $Stage "README.txt"
[System.IO.File]::WriteAllText($ReadmePath, @"
UIAO Source Bundle v$Version
==============================
Offline install kit for the UIAO CLI and companion PowerShell scripts.
Download page: https://whalermike.github.io/uiao/download/
Full docs:     https://whalermike.github.io/uiao/

INSTALLING THE UIAO CLI
-----------------------
Run from this directory (Python 3.11+ required):

  python -m pip install .
  python -m pip install ".[api]"      # adds the FastAPI REST server

PREREQUISITES (POWERSHELL)
--------------------------
Before running any of the companion PS scripts, validate your workstation:

  .\Install-UIAOPrerequisites.ps1         # full check + install
  .\Install-UIAOPrerequisites.ps1 -WhatIf # dry-run only

The script verifies PS version, loads required modules (ActiveDirectory,
GroupPolicy, PKI, DnsServer, DhcpServer, etc.), installs RSAT role tools,
enables PSRemoting, and sets the execution policy.

INCLUDED SCRIPTS
----------------
scripts\
  Install-UIAOPrerequisites.ps1       -- Step 0: validate / install prerequisites

  Invoke-ZtDashboard.ps1              -- Zero Trust Assessment Dashboard
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/operational-guides/
                                           zero-trust-assessment/

  Invoke-ADSurvey.ps1                 -- AD Forest Survey (Phase 1 discovery)
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/substrate/
                                           platform-tooling/invoke-ad-survey.html

  Invoke-GpoMigrationTriage.ps1       -- GPO → Intune / Azure Arc classification
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/substrate/
                                           platform-tooling/invoke-gpo-migration-triage.html

  Invoke-GpoObsoleteAudit.ps1         -- GPO obsolete-setting audit
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/substrate/
                                           platform-tooling/invoke-gpo-obsolete-audit.html

  helpdesk-entra\                     -- Help Desk / Cloud Services Entra Operations
    HelpDeskEntra.psm1                   Shared module
    Invoke-RequestTriage.ps1             Request triage classifier
    Get-EnterpriseAppInventory.ps1       Enterprise app inventory + risk tiering
    New-HelpDeskPAG.ps1                  Help Desk PAG + PIM setup
    Add-AppAccessGroup.ps1               Group-to-app assignment
    Repair-ImmutableId.ps1               ImmutableID repair
    Export-AccessCertification.ps1       Access-certification export
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/operational-guides/
                                           helpdesk-entra-operations/

  intune-arc\                         -- Intune + Azure Arc Modernization
    IntuneArcModernization.psm1          Shared module
    Invoke-ArcOnboarding.ps1             Arc onboarding
    Set-ArcPolicyBaseline.ps1            Arc security baseline
    Set-IntuneAutoEnrollment.ps1         Intune auto-enrollment
    Get-IntuneEnrollmentStatus.ps1       Intune enrollment posture
    Get-NtlmAudit.ps1                    NTLM audit
    Set-NtlmRestriction.ps1              LSA / NTLM restriction
    Repair-Spn.ps1                       SPN repair
    Invoke-SqlHardeningAudit.ps1         SQL hardening audit
    Deploy-ConditionalAccessBaseline.ps1 Conditional Access baseline
    Compare-ConditionalAccessDrift.ps1   CA policy drift detection
    Get-ModernizationDriftReport.ps1     Cross-domain status roll-up
    Get-OrgPathSurvey.ps1                OrgPath survey helper (retrofit)
                                         Guide: https://whalermike.github.io/uiao/
                                           customer-documents/operational-guides/
                                           intune-arc-modernization/

OPTIONAL NEXT STEPS
-------------------
Export your GPO baseline and run the UIAO auditor bundle:

  Get-GPOReport -All -ReportType Xml -Path C:\Temp\gpo.xml
  uiao ir auditor-bundle C:\Temp\gpo.xml --out-dir C:\Temp\uiao-bundle

VERIFY THIS ZIP
---------------
  Get-FileHash .\$ZipName -Algorithm SHA256
  # compare to the SHA-256 published at https://whalermike.github.io/uiao/download/

LICENSE
-------
Apache-2.0.  See LICENSE in this archive.
Source:  https://github.com/WhalerMike/uiao
"@, [System.Text.UTF8Encoding]::new($false))

Write-Host "  + README.txt" -ForegroundColor DarkGray

# ── Compress ─────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Compressing…" -ForegroundColor DarkCyan

$OutPath = Join-Path $RepoRoot $OutDir
if (-not (Test-Path $OutPath)) { New-Item -ItemType Directory -Path $OutPath | Out-Null }
$ZipPath = Join-Path $OutPath $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Compress-Archive -Path "$Stage\*" -DestinationPath $ZipPath
$Hash   = (Get-FileHash $ZipPath -Algorithm SHA256).Hash.ToLower()
$SizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)

Write-Host ""
Write-Host "Zip:    $ZipPath"   -ForegroundColor Green
Write-Host "Size:   $SizeMB MB" -ForegroundColor Green
Write-Host "SHA256: $Hash"      -ForegroundColor Green

# Clean staging
Remove-Item $Stage -Recurse -Force
