<#
.SYNOPSIS
    Build-UIAOSourceZip.ps1
    Assembles the uiao.zip offline bundle for the UIAO CLI.

.DESCRIPTION
    Produces a single zip that an operator can extract on a machine with no
    internet access and install completely offline (no PyPI / proxy needed).

    The bundle includes:

      Source tree
        src\uiao\             — the installable Python package
        pyproject.toml        — package metadata / dependency declarations
        README.md             — project README
        LICENSE               — Apache-2.0

      Offline pip wheels (pre-downloaded by Download-UIAODeps.ps1 / CI)
        deps\                 — all required .whl files for pip install . and .[api]
                                pip never contacts PyPI when installing from this bundle.

      Installers
        Install-UIAO.ps1              — one-shot offline installer (runs pip from deps\)
        Install-UIAOPrerequisites.ps1 — validates + installs PowerShell prerequisites
                                        (modules, RSAT, PSRemoting, execution policy)
      CLI command guide
        docs\cli-reference.qmd        — canonical command reference source
        docs\cli-reference.docx       — pre-rendered Word output (when available)

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

.PARAMETER DepsDir
    Path to the pre-downloaded wheels folder produced by Download-UIAODeps.ps1.
    Default: deps\ (relative to repo root).  If the folder does not exist the
    script warns but continues — the resulting zip will not support offline
    install without separately providing deps\.

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
    [string]$ZipName = "",
    [string]$DepsDir = ""
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

function Convert-ToWindowsPowerShellText {
    param([string]$Root)

    $utf8Bom = New-Object System.Text.UTF8Encoding($true)
    $extensions = @("*.ps1", "*.psm1", "*.psd1")

    foreach ($pattern in $extensions) {
        Get-ChildItem -Path $Root -Recurse -File -Filter $pattern | ForEach-Object {
            $content = [System.IO.File]::ReadAllText($_.FullName)
            $content = $content -replace "`r?`n", "`r`n"
            [System.IO.File]::WriteAllText($_.FullName, $content, $utf8Bom)
        }
    }
}

# ── Python source tree ────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Python source:" -ForegroundColor DarkCyan

Add-Dir  (Join-Path $RepoRoot "src")        "src"
Add-File (Join-Path $RepoRoot "pyproject.toml")
Add-File (Join-Path $RepoRoot "README.md")
Add-File (Join-Path $RepoRoot "LICENSE")    # Apache-2.0

# ── Pre-downloaded pip wheels (offline install) ──────────────────────────────

Write-Host ""
Write-Host "Offline pip wheels (deps\):" -ForegroundColor DarkCyan

$ResolvedDeps = if ($DepsDir) { $DepsDir } else { Join-Path $RepoRoot "deps" }
if (Test-Path $ResolvedDeps) {
    $wheelCount = (Get-ChildItem $ResolvedDeps -Filter "*.whl" | Measure-Object).Count
    Add-Dir $ResolvedDeps "deps"
    Write-Host "  ($wheelCount wheel(s) bundled)" -ForegroundColor DarkGray
} else {
    Write-Warning "  ! deps\ not found at $ResolvedDeps — bundle will NOT support fully offline install."
    Write-Warning "    Run Download-UIAODeps.ps1 first (or let the CI workflow do it), then rebuild."
}

# ── Installer scripts ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "Installer scripts:" -ForegroundColor DarkCyan

Add-File (Join-Path $RepoRoot "scripts\Install-UIAO.ps1")
Add-File (Join-Path $RepoRoot "scripts\Install-UIAOPrerequisites.ps1")

# ── CLI command guide ─────────────────────────────────────────────────────────

Write-Host ""
Write-Host "CLI command guide:" -ForegroundColor DarkCyan

Add-File (Join-Path $RepoRoot "docs\docs\cli-reference.qmd") "docs"
$CliRefDocx = Join-Path $RepoRoot "docs\docs\cli-reference.docx"
if (Test-Path $CliRefDocx) {
    Add-File $CliRefDocx "docs"
} else {
    Write-Warning "  ! cli-reference.docx not found — qmd source is included; docx can be rendered with Quarto."
}

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
Fully offline install kit for the UIAO CLI and companion PowerShell scripts.
No internet access required at install time.
Download page: https://whalermike.github.io/uiao/download/
Full docs:     https://whalermike.github.io/uiao/

QUICK INSTALL (OFFLINE — NO INTERNET NEEDED)
---------------------------------------------
All pip wheels are pre-bundled in deps\.  Run from this directory:

  Step 1 — install PowerShell prerequisites (run once, as Administrator):
    .\Install-UIAOPrerequisites.ps1

  Step 2 — install the UIAO CLI (no internet required):
    .\Install-UIAO.ps1              # base CLI only
    .\Install-UIAO.ps1 -ApiExtras   # base CLI + FastAPI REST server

If your proxy blocks PyPI you'll see a 407 error without step 2 above.
Install-UIAO.ps1 uses --no-index --find-links deps\ so pip never contacts PyPI.

INSTALL MANUALLY (OPTIONAL)
----------------------------
If you prefer running pip directly:

  python -m pip install --no-index --find-links deps\ setuptools wheel build
  python -m pip install --no-index --find-links deps\ .
  python -m pip install --no-index --find-links deps\ ".[api]"  # optional REST server

BUNDLE CONTENTS
---------------
  README.txt                          This file
  Install-UIAO.ps1                    One-shot offline CLI installer
  Install-UIAOPrerequisites.ps1       PowerShell prerequisites installer
  docs\cli-reference.qmd              Canonical CLI command reference source
  docs\cli-reference.docx             CLI command reference (Word; included when pre-rendered)

  src\                                Installable Python source tree
  pyproject.toml                      Package metadata / dependency declarations
  README.md                           Project README
  LICENSE                             Apache-2.0

  deps\                               Pre-downloaded pip wheels (offline install)
    pip-*.whl
    setuptools-*.whl
    wheel-*.whl
    build-*.whl
    ... (all runtime + [api] transitive dependencies)

  scripts\
    Invoke-ZtDashboard.ps1            Zero Trust Assessment Dashboard
    Invoke-ADSurvey.ps1               AD Forest Survey (Phase 1 discovery)
    Invoke-GpoMigrationTriage.ps1     GPO → Intune / Azure Arc classification
    Invoke-GpoObsoleteAudit.ps1       GPO obsolete-setting audit

    helpdesk-entra\                   Help Desk / Cloud Services Entra Operations
      HelpDeskEntra.psm1                Shared module
      Invoke-RequestTriage.ps1          Request triage classifier
      Get-EnterpriseAppInventory.ps1    Enterprise app inventory + risk tiering
      New-HelpDeskPAG.ps1               Help Desk PAG + PIM setup
      Add-AppAccessGroup.ps1            Group-to-app assignment
      Repair-ImmutableId.ps1            ImmutableID repair
      Export-AccessCertification.ps1    Access-certification export

    intune-arc\                       Intune + Azure Arc Modernization
      IntuneArcModernization.psm1       Shared module
      Invoke-ArcOnboarding.ps1          Arc onboarding
      Set-ArcPolicyBaseline.ps1         Arc security baseline
      Set-IntuneAutoEnrollment.ps1      Intune auto-enrollment
      Get-IntuneEnrollmentStatus.ps1    Intune enrollment posture
      Get-NtlmAudit.ps1                 NTLM audit
      Set-NtlmRestriction.ps1           LSA / NTLM restriction
      Repair-Spn.ps1                    SPN repair
      Invoke-SqlHardeningAudit.ps1      SQL hardening audit
      Deploy-ConditionalAccessBaseline.ps1  Conditional Access baseline
      Compare-ConditionalAccessDrift.ps1    CA policy drift detection
      Get-ModernizationDriftReport.ps1  Cross-domain status roll-up
      Get-OrgPathSurvey.ps1             OrgPath survey helper (retrofit)

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

# ── Normalize bundled PowerShell files for Windows hosts ─────────────────────

Write-Host ""
Write-Host "Normalizing PowerShell files for Windows compatibility..." -ForegroundColor DarkCyan
Convert-ToWindowsPowerShellText -Root $Stage
Write-Host "  + Rewrote bundled .ps1/.psm1/.psd1 files as UTF-8 BOM + CRLF" -ForegroundColor DarkGray

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
