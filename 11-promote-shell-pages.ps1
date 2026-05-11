# 11-promote-shell-pages.ps1
# Promotes the 26 remaining 0-byte shell .md files to shell .qmd files.
# Each gets a YAML header and a visible "in progress" callout so the page
# renders instead of 404ing, and visitors know what's coming.
#
# Groups:
#   A — Whitepapers (4 files)         → high-value, point to source material
#   B — Architecture Series (5 files) → map to existing MOD_* specs
#   C — Case Studies (3 files)        → coming soon with context
#   D — Modernization Specs (7 files) → parallel domain structure
#   E — Validation Suite Domains (7 files) → parallel to D
#
# Usage:  .\11-promote-shell-pages.ps1
# Dry run: .\11-promote-shell-pages.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$promoted = 0
$skipped  = 0
$errors   = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function Promote-ShellPage {
    param(
        [string]$MdPath,
        [string]$Title,
        [string]$Subtitle,
        [string]$CalloutTitle,
        [string]$CalloutBody,
        [string]$CalloutType = "note"   # note | tip | warning | important
    )

    if (-not (Test-Path $MdPath)) {
        Write-Host "  NOT FOUND: $MdPath" -ForegroundColor Red
        $script:errors++
        return
    }

    $size = (Get-Item $MdPath).Length
    if ($size -gt 100) {
        Write-Host "  SKIP (has content — $size bytes): $MdPath" -ForegroundColor Yellow
        $script:skipped++
        return
    }

    $qmdPath = $MdPath -replace '\.md$', '.qmd'
    if (Test-Path $qmdPath) {
        Write-Action "SKIP (.qmd already exists)" $qmdPath "Gray"
        $script:skipped++
        return
    }

    $content  = "---`n"
    $content += "title: `"$Title`"`n"
    $content += "subtitle: `"$Subtitle`"`n"
    $content += "---`n`n"
    $content += "::: {.callout-$CalloutType}`n"
    $content += "## $CalloutTitle`n"
    $content += "$CalloutBody`n"
    $content += ":::`n"

    if (-not $WhatIf) {
        Set-Content -Path $qmdPath -Value $content -Encoding UTF8 -NoNewline
        Remove-Item $MdPath -Force
    }
    $rel = $MdPath.Replace($RepoRoot + "\", "")
    Write-Action "PROMOTED" "$rel  →  $(Split-Path $qmdPath -Leaf)" "Green"
    $script:promoted++
}

Write-Host ""
Write-Host "11-promote-shell-pages.ps1" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN — no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# GROUP A: Whitepapers (4 files)
# ---------------------------------------------------------------------------
Write-Host "Group A: Whitepapers" -ForegroundColor Yellow

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\whitepapers\uiao-governance-os-whitepaper.md") `
    -Title "UIAO Governance OS — Whitepaper" `
    -Subtitle "How deterministic governance replaces attestation-based compliance" `
    -CalloutTitle "Whitepaper in preparation" `
    -CalloutBody "This whitepaper is being drafted from the [Governance OS Canonical Suite](../executive-governance-series/index.qmd). For current coverage, see the [Executive Governance Series](../executive-governance-series/index.qmd) and the [Governance OS Overview](../executive-briefs/governance-os-overview.qmd)."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\whitepapers\modernization-governance-whitepaper.md") `
    -Title "Modernization Governance — Whitepaper" `
    -Subtitle "Governing the AD to Entra ID migration at federal scale" `
    -CalloutTitle "Whitepaper in preparation" `
    -CalloutBody "This whitepaper is being drafted from the [Modernization Program documentation](../modernization/index.qmd). For current coverage, see the [Modernization Overview](../executive-briefs/modernization-overview.qmd) and the [AD to Entra ID migration guide](../modernization/identity-orgtree/index.qmd)."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\whitepapers\zero-trust-governance-whitepaper.md") `
    -Title "Zero Trust Governance — Whitepaper" `
    -Subtitle "Implementing CISA Zero Trust maturity through UIAO's governance model" `
    -CalloutTitle "Whitepaper in preparation" `
    -CalloutBody "This whitepaper is being drafted from the compliance documentation. For current coverage, see the [Zero Trust Overview](../executive-briefs/zero-trust-overview.qmd) and the [FedRAMP and CISA update](../compliance/federal-mandates/index.qmd)."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\whitepapers\scubagear-integration-whitepaper.md") `
    -Title "SCuBAGear Integration — Whitepaper" `
    -Subtitle "Connecting CISA SCuBAGear outputs to UIAO's evidence pipeline" `
    -CalloutTitle "Whitepaper in preparation" `
    -CalloutBody "This whitepaper is being drafted. For current SCuBAGear coverage, see the [SCuBAGear Adapter Spec](../adapter-specs/scubagear/index.qmd) and the [SCuBA evidence telemetry documentation](../compliance/evidence-telemetry/index.qmd)."

# ---------------------------------------------------------------------------
# GROUP B: Architecture Series (5 files)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group B: Architecture Series" -ForegroundColor Yellow

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\architecture-series\drift-engine.md") `
    -Title "Drift Engine Architecture" `
    -Subtitle "How UIAO detects, quantifies, and enforces against configuration drift" `
    -CalloutTitle "Architecture document in preparation" `
    -CalloutBody "Full architecture documentation is being drafted. For current coverage, see the [Drift Engine Overview](../executive-briefs/drift-engine-overview.qmd). The drift detection specification is defined in ``src/uiao/governance/DRIFT-*`` modules."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\architecture-series\evidence-chain.md") `
    -Title "Evidence Chain Architecture" `
    -Subtitle "Provenance, signing, and audit trail from source to artifact" `
    -CalloutTitle "Architecture document in preparation" `
    -CalloutBody "Full architecture documentation is being drafted. For current coverage, see the [Evidence Fabric Overview](../executive-briefs/evidence-fabric-overview.qmd) and the [SCuBA technical specification](../compliance/evidence-telemetry/scuba-technical-spec.qmd)."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\architecture-series\boundary-impact-model.md") `
    -Title "Boundary Impact Model" `
    -Subtitle "Modeling authorization boundaries and their governance implications" `
    -CalloutTitle "Architecture document in preparation" `
    -CalloutBody "Full architecture documentation is being drafted. For current coverage, see the [GCC Moderate Boundary Model](../compliance/boundary-authorization/B1-gcc-moderate-boundary-model.qmd) and the [Findings section](/findings/)."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\architecture-series\six-plane-architecture.md") `
    -Title "Six-Plane Architecture" `
    -Subtitle "UIAO's six control planes and their governance roles" `
    -CalloutTitle "Architecture document in preparation" `
    -CalloutBody "Full architecture documentation is being drafted. For current coverage, see the [Governance OS Canonical Suite](../executive-governance-series/governance-os-canonical-suite.qmd) which covers all six planes in detail."

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\architecture-series\three-layer-rule-model.md") `
    -Title "Three-Layer Rule Model" `
    -Subtitle "Policy, enforcement, and evidence layers in UIAO's governance model" `
    -CalloutTitle "Architecture document in preparation" `
    -CalloutBody "Full architecture documentation is being drafted. For current coverage, see the [Governance OS Overview](../executive-briefs/governance-os-overview.qmd)."

# ---------------------------------------------------------------------------
# GROUP C: Case Studies (3 files)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group C: Case Studies" -ForegroundColor Yellow

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\case-studies\federal-modernization-case-study.md") `
    -Title "Federal Modernization — Case Study" `
    -Subtitle "AD to Entra ID migration governance at a federal civilian agency" `
    -CalloutTitle "Case study in preparation" `
    -CalloutBody "This case study is being developed. For current program documentation, see the [Modernization Program](../modernization/uiao-modernization-program/index.qmd) and the [AD to Entra ID migration guide](../modernization/identity-orgtree/index.qmd)." `
    -CalloutType "tip"

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\case-studies\cloud-boundary-case-study.md") `
    -Title "Cloud Boundary — Case Study" `
    -Subtitle "Governing GCC Moderate compliance gaps with UIAO" `
    -CalloutTitle "Case study in preparation" `
    -CalloutBody "This case study is being developed from the GCC Moderate findings. For current coverage, see the [Findings section](/findings/) documenting specific GCC Moderate capability gaps and the [Boundary Authorization documentation](../compliance/boundary-authorization/index.qmd)." `
    -CalloutType "tip"

Promote-ShellPage `
    -MdPath (Join-Path $RepoRoot "docs\customer-documents\case-studies\identity-modernization-case-study.md") `
    -Title "Identity Modernization — Case Study" `
    -Subtitle "Identity plane governance during a large-scale directory migration" `
    -CalloutTitle "Case study in preparation" `
    -CalloutBody "This case study is being developed. For current coverage, see the [Identity Modernization documentation](../modernization/identity-orgtree/index.qmd) and the [OrgPath Codebook](../modernization/identity-orgtree/ad-to-entraid-tree.qmd)." `
    -CalloutType "tip"

# ---------------------------------------------------------------------------
# GROUP D: Modernization Specs — 6 domains + 1 template (7 files)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group D: Modernization Specs (6 domains + template)" -ForegroundColor Yellow

$domainSpecs = @(
    @{ Slug="cloud";     Title="Cloud Modernization Spec";     Subtitle="Cloud boundary governance and migration specification" }
    @{ Slug="identity";  Title="Identity Modernization Spec";  Subtitle="Identity plane governance and migration specification" }
    @{ Slug="sase";      Title="SASE Modernization Spec";      Subtitle="Secure Access Service Edge governance specification" }
    @{ Slug="sdwan";     Title="SD-WAN Modernization Spec";    Subtitle="Software-Defined WAN governance specification" }
    @{ Slug="telemetry"; Title="Telemetry Modernization Spec"; Subtitle="Telemetry pipeline governance specification" }
    @{ Slug="zero-trust";Title="Zero Trust Modernization Spec";Subtitle="Zero trust implementation governance specification" }
)

foreach ($d in $domainSpecs) {
    Promote-ShellPage `
        -MdPath (Join-Path $RepoRoot "docs\customer-documents\modernization-specs\$($d.Slug)\$($d.Slug).md") `
        -Title $d.Title `
        -Subtitle $d.Subtitle `
        -CalloutTitle "Specification in preparation" `
        -CalloutBody "This domain specification is being drafted. See the [Modernization Program](../uiao-modernization-program/index.qmd) for current phase documentation covering this domain."
}

# Template file — delete rather than promote (it's a scaffold, not a page)
$templatePath = Join-Path $RepoRoot "docs\customer-documents\modernization-specs\_template\generic-template.md"
if (Test-Path $templatePath) {
    if (-not $WhatIf) { Remove-Item $templatePath -Force }
    Write-Action "DELETED (scaffold template, not a page)" $templatePath "DarkGray"
    $script:promoted++
}

# ---------------------------------------------------------------------------
# GROUP E: Validation Suite Domains — 6 domains + 1 template (7 files)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "Group E: Validation Suite Domains (6 domains + template)" -ForegroundColor Yellow

foreach ($d in $domainSpecs) {
    Promote-ShellPage `
        -MdPath (Join-Path $RepoRoot "docs\customer-documents\validation-suites\domains\$($d.Slug)\$($d.Slug).md") `
        -Title "$($d.Title -replace ' Spec',' Validation Suite')" `
        -Subtitle "Conformance tests and validation criteria for the $($d.Slug) domain" `
        -CalloutTitle "Validation suite in preparation" `
        -CalloutBody "Validation criteria for this domain are being developed in parallel with the modernization specification. See the [Modernization Spec](../../modernization-specs/$($d.Slug)/$($d.Slug).qmd) for the corresponding specification."
}

# Template file — delete
$vsTemplatePath = Join-Path $RepoRoot "docs\customer-documents\validation-suites\domains\_template\generic-template.md"
if (Test-Path $vsTemplatePath) {
    if (-not $WhatIf) { Remove-Item $vsTemplatePath -Force }
    Write-Action "DELETED (scaffold template, not a page)" $vsTemplatePath "DarkGray"
    $script:promoted++
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would promote : $($promoted + $skipped) files" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dry run complete — rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Promoted : $promoted files" -ForegroundColor Green
    Write-Host "  Skipped  : $skipped files" -ForegroundColor Gray
    if ($errors -gt 0) {
        Write-Host "  Errors   : $errors" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. quarto preview docs/ — verify each promoted page renders with its callout" -ForegroundColor White
    Write-Host "  2. git add -A && git commit -m 'fix: promote 26 shell pages to shell .qmd with callouts'" -ForegroundColor White
    Write-Host "  3. git push" -ForegroundColor White
    Write-Host "  4. .\UIAO-DocAudit-v3.ps1 — SHELL should hit 0" -ForegroundColor White
    Write-Host "  5. Remaining work: LEGACY-DOCS triage (docs\docs\ — 158 files)" -ForegroundColor White
    Write-Host "     and Group 2 ORPHAN-MD decisions (12 internal files)" -ForegroundColor White
}
Write-Host ""
