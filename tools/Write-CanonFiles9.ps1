param(
    [string]$Root = "C:\Users\whale\git\uiao\phase2"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $Root)) {
    throw "Phase 2 root not found: $Root"
}

function Write-AsciiFile {
    param(
        [string]$Path,
        [string[]]$Lines
    )
    $Lines | Set-Content -LiteralPath $Path -Encoding ASCII -Force
}

# --------------------------------------------
# Artifact definitions
# --------------------------------------------
$Artifacts = @(
    @{ Id="UIAO_P2_201"; Name="Identity Domain Spec"; Folder="domains" }
    @{ Id="UIAO_P2_202"; Name="Device Domain Spec"; Folder="domains" }
    @{ Id="UIAO_P2_203"; Name="Access Domain Spec"; Folder="domains" }
    @{ Id="UIAO_P2_204"; Name="Governance Domain Spec"; Folder="domains" }
    @{ Id="UIAO_P2_205"; Name="HR Provisioning Spec"; Folder="domains" }
    @{ Id="UIAO_P2_206"; Name="Application Integration Spec"; Folder="domains" }
    @{ Id="UIAO_P2_207"; Name="Network Domain Spec"; Folder="domains" }

    @{ Id="UIAO_P2_211"; Name="Human Identity Lifecycle"; Folder="lifecycles" }
    @{ Id="UIAO_P2_212"; Name="Device Lifecycle"; Folder="lifecycles" }
    @{ Id="UIAO_P2_213"; Name="Workload Identity Lifecycle"; Folder="lifecycles" }
    @{ Id="UIAO_P2_214"; Name="Policy Lifecycle"; Folder="lifecycles" }

    @{ Id="UIAO_P2_221"; Name="AD to Entra Transformations"; Folder="transformations" }
    @{ Id="UIAO_P2_222"; Name="GPO to Intune Transformations"; Folder="transformations" }
    @{ Id="UIAO_P2_223"; Name="Service Account to Workload Identity"; Folder="transformations" }
    @{ Id="UIAO_P2_224"; Name="Kerberos/NTLM to Modern Auth"; Folder="transformations" }

    @{ Id="UIAO_P2_231"; Name="Identity Baselines"; Folder="baselines" }
    @{ Id="UIAO_P2_232"; Name="Device Compliance Baselines"; Folder="baselines" }

    @{ Id="UIAO_P2_241"; Name="Governance Substrate Spec"; Folder="governance" }

    @{ Id="UIAO_P2_251"; Name="Workload Identity Patterns"; Folder="workloads" }

    @{ Id="UIAO_P2_261"; Name="Application Auth Patterns"; Folder="apps" }

    @{ Id="UIAO_P2_271"; Name="DNS and Named Locations Spec"; Folder="network" }
)

# --------------------------------------------
# Generate scaffolding files
# --------------------------------------------
foreach ($a in $Artifacts) {

    $folder = Join-Path $Root $a.Folder
    if (-not (Test-Path -LiteralPath $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
    }

    $path = Join-Path $folder "$($a.Id).md"

    $content = @(
        "# $($a.Name)"
        "Id: $($a.Id)"
        ""
        "## Description"
        "Placeholder for $($a.Name)."
        ""
        "## Scope"
        "To be defined in Phase 2 design sessions."
        ""
        "## Dependencies"
        "- TBD"
        ""
        "## Detailed Design"
        "To be elaborated."
        ""
    )

    Write-AsciiFile -Path $path -Lines $content
}

# --------------------------------------------
# Generate registry entries
# --------------------------------------------
$regDir = Join-Path $Root "registry"
if (-not (Test-Path -LiteralPath $regDir)) {
    New-Item -ItemType Directory -Path $regDir -Force | Out-Null
}

foreach ($a in $Artifacts) {
    $regPath = Join-Path $regDir "$($a.Id).md"

    $reg = @(
        "# Registry Entry - $($a.Id)"
        ""
        "Id: $($a.Id)"
        "Title: $($a.Name)"
        "Type: Phase 2 Artifact"
        "Status: Placeholder"
        ""
        "## Description"
        "Placeholder registry entry for $($a.Name)."
        ""
        "## Dependencies"
        "- TBD"
        ""
    )

    Write-AsciiFile -Path $regPath -Lines $reg
}

# --------------------------------------------
# Generate master index
# --------------------------------------------
$indexPath = Join-Path $Root "UIAO_Phase2_Index.md"

$index = @(
    "# UIAO Phase 2 - Master Index"
    ""
)

foreach ($a in $Artifacts) {
    $index += "- $($a.Id) - $($a.Name) ($($a.Folder)/$($a.Id).md)"
}

Write-AsciiFile -Path $indexPath -Lines $index

Write-Host "Phase 2 scaffolding, registry, and index generated." -ForegroundColor Green
