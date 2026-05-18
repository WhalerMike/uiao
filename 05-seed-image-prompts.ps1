<#
.SYNOPSIS
  UIAO Fix 05 — Seed IMAGE-PROMPTS.md files and inject [IMAGE-NN:] placeholders
  into the top-priority documents so the NanoBanana pipeline can generate images.

.DESCRIPTION
  Two-part operation:

  Part A — Fills the IMAGE-PROMPTS.md sidecar files for the 5 highest-impact
  documents with real, domain-accurate prompts (replacing the TODO scaffolds).

  Part B — Injects [IMAGE-01: ...] placeholders into each document's .qmd
  body at the appropriate location so generate_images.py can find and process
  them during the next pipeline run.

  Target documents (Priority order):
    1. AODIM Architecture
    2. AD to Entra ID Whitepaper
    3. Client-Server Ch01 (Platform Foundation)
    4. Client-Server Ch04 (Identity Transformation)
    5. Client-Server Ch09 (Migration Roadmap)

.NOTES
  Run from the repo root after 04-enrich-landing-page.ps1.
  Idempotent — checks for existing prompts before writing.
  After running, execute: python scripts/generate_images.py --scan-only
  to verify the pipeline detects the new placeholders.
#>

param(
    [switch]$DryRun,
    [string]$RepoRoot = (Get-Location).Path
)

$docsPath = Join-Path $RepoRoot "docs"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 05: Seed Image Prompts" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified.`n" -ForegroundColor Yellow
}

# ─── PROMPT DEFINITIONS ───
# Each entry: document path, IMAGE-PROMPTS.md path, array of prompts
$documents = @(
    @{
        Name = "AODIM Architecture"
        QmdPath = "customer-documents/architecture-series/aodim-architecture.qmd"
        PromptsPath = "customer-documents/architecture-series/IMAGE-PROMPTS.md"
        Prompts = @(
            @{
                Id = "IMAGE-01"
                Prompt = "Technical architecture diagram showing the AODIM attribute flow: HR System arrow to Identity Attributes arrow to Dynamic Groups arrow to Access Policies arrow to Resource Authorization. Each stage labeled with governance checkpoints. Clean engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) color scheme on white background. No photographs, purely diagrammatic."
                InsertAfter = "## Attribute Flow"
                FallbackInsertAfter = "## Overview"
            }
            @{
                Id = "IMAGE-02"
                Prompt = "Side-by-side comparison diagram: Left panel labeled 'Legacy OU-Based Delegation' showing a rigid tree hierarchy with Organizational Units and static group nesting. Right panel labeled 'AODIM Attribute-Based Delegation' showing a flat, dynamic model with attribute tags flowing to policy engines. Arrows show the transformation path between them. Clean engineering diagram, dark navy and teal color scheme."
                InsertAfter = "## Delegation Model"
                FallbackInsertAfter = "## Attribute"
            }
            @{
                Id = "IMAGE-03"
                Prompt = "Operational flow diagram showing the AODIM runtime cycle: Identity Event triggers Attribute Evaluation, which feeds Rule Engine, which produces Access Decision plus Drift Report plus Evidence Object. Feedback loop from Drift Report back to Identity Event for remediation. Clean engineering style, dark navy and teal on white, no photographs."
                InsertAfter = "## Operational"
                FallbackInsertAfter = "## Runtime"
            }
        )
    }
    @{
        Name = "AD to Entra ID Whitepaper"
        QmdPath = "customer-documents/whitepapers/ad-to-entraid-migration-problem.qmd"
        PromptsPath = "customer-documents/whitepapers/IMAGE-PROMPTS.md"
        Prompts = @(
            @{
                Id = "IMAGE-01"
                Prompt = "Architecture comparison diagram with two panels: Left panel 'Active Directory Governance Surface' showing AD at center connected to 11 dependency spokes (GPO, DNS/DHCP/IPAM, SPN, PKI, RADIUS, LDAP Apps, Service Accounts, OU Delegation, Trusts, Schema Extensions, Site Topology). Right panel 'Entra ID' showing the same 11 spokes but 9 are disconnected/broken (shown as dashed red lines), only Identity and some basic auth remain connected. Title: 'What Migrates vs. What Breaks'. Clean technical diagram, navy and teal with red (#C74040) for broken connections."
                InsertAfter = "## The Migration Gap"
                FallbackInsertAfter = "## Introduction"
            }
            @{
                Id = "IMAGE-02"
                Prompt = "Bridge architecture diagram showing UIAO as a governance layer spanning between Active Directory (left) and Entra ID (right). Below the bridge: FIMF Adapter slots connecting to legacy systems (DNS, PKI, RADIUS, LDAP). Above the bridge: Continuous Evidence Flow with KSI metrics, drift detection, and compliance artifacts. Labeled 'UIAO Governance Bridge'. Clean engineering style, dark navy and teal color scheme."
                InsertAfter = "## UIAO"
                FallbackInsertAfter = "## Solution"
            }
        )
    }
    @{
        Name = "Client-Server Ch01 — Platform Foundation"
        QmdPath = "customer-documents/modernization/client-server-to-hybrid-cloud/01-platform-foundation.qmd"
        PromptsPath = "customer-documents/modernization/client-server-to-hybrid-cloud/IMAGE-PROMPTS.md"
        Prompts = @(
            @{
                Id = "IMAGE-01"
                Prompt = "Layered platform architecture diagram showing the UIAO substrate stack from bottom to top: Infrastructure Layer (Azure Arc, on-premises compute), Platform Services Layer (Canon Registry, Adapter Framework, CLI Tooling), Governance Layer (DRIFT Modules, KSI Engine, Evidence Fabric), and Operations Layer (Dashboards, Alerts, Compliance Reports). Each layer connected by bidirectional arrows. Clean engineering blueprint style, dark navy and teal color scheme."
                InsertAfter = "## Platform Architecture"
                FallbackInsertAfter = "## Overview"
            }
        )
    }
    @{
        Name = "Client-Server Ch04 — Identity Transformation"
        QmdPath = "customer-documents/modernization/client-server-to-hybrid-cloud/04-identity-transformation.qmd"
        PromptsPath = "customer-documents/modernization/client-server-to-hybrid-cloud/IMAGE-PROMPTS.md"
        Prompts = @(
            @{
                Id = "IMAGE-02"
                Prompt = "Identity transformation pipeline diagram showing the flow: Legacy AD Objects (Users, Groups, OUs, GPOs) entering a Transformation Engine with three processing stages (Attribute Mapping, Policy Conversion, Delegation Translation), producing Entra ID Objects (Cloud Users, Dynamic Groups, Conditional Access, Administrative Units) with a Drift Detection feedback loop. Governance checkpoints marked at each stage. Clean technical diagram, navy and teal color scheme."
                InsertAfter = "## Identity Transformation"
                FallbackInsertAfter = "## Overview"
            }
        )
    }
    @{
        Name = "Client-Server Ch09 — Migration Roadmap"
        QmdPath = "customer-documents/modernization/client-server-to-hybrid-cloud/09-migration-roadmap.qmd"
        PromptsPath = "customer-documents/modernization/client-server-to-hybrid-cloud/IMAGE-PROMPTS.md"
        Prompts = @(
            @{
                Id = "IMAGE-03"
                Prompt = "Migration roadmap timeline diagram showing six phases (Phase 0 Discovery through Phase 5 Continuous Governance) on a horizontal timeline. Each phase shown as a block with key milestones, deliverables, and go/no-go gates between phases. Color-coded: completed phases in teal, current phase highlighted with amber border, future phases in light gray. Decision diamonds at phase boundaries. Clean Gantt-style engineering diagram, navy and teal color scheme."
                InsertAfter = "## Roadmap"
                FallbackInsertAfter = "## Overview"
            }
        )
    }
)

$totalPrompts = 0
$totalPlaceholders = 0

foreach ($doc in $documents) {
    Write-Host "  Processing: $($doc.Name)" -ForegroundColor White

    # ── Part A: Write/update IMAGE-PROMPTS.md ──
    $promptsFullPath = Join-Path $docsPath $doc.PromptsPath

    # Build prompt file content
    $promptContent = "# IMAGE-PROMPTS — $($doc.Name)`n`n"
    $promptContent += "<!-- Generated by 05-seed-image-prompts.ps1 -->`n`n"

    foreach ($p in $doc.Prompts) {
        $promptContent += "## $($p.Id)`n`n"
        $promptContent += "$($p.Prompt)`n`n"
        $totalPrompts++
    }

    # Check if file exists and has real content (not just TODO)
    $shouldWrite = $true
    if (Test-Path $promptsFullPath) {
        $existing = Get-Content -Path $promptsFullPath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($existing -and $existing -notmatch "TODO" -and $existing -match "IMAGE-0") {
            Write-Host "    [SKIP] IMAGE-PROMPTS.md already has real prompts" -ForegroundColor DarkGray
            $shouldWrite = $false
        }
    }

    if ($shouldWrite) {
        if ($DryRun) {
            Write-Host "    [WOULD WRITE] $($doc.PromptsPath) ($($doc.Prompts.Count) prompt(s))" -ForegroundColor Yellow
        } else {
            # Ensure directory exists
            $promptDir = Split-Path $promptsFullPath -Parent
            if (-not (Test-Path $promptDir)) {
                New-Item -ItemType Directory -Path $promptDir -Force | Out-Null
            }

            # For shared IMAGE-PROMPTS.md files (like the client-server series),
            # append instead of overwrite
            if ((Test-Path $promptsFullPath) -and ($doc.PromptsPath -match "client-server")) {
                Add-Content -Path $promptsFullPath -Value "`n$promptContent" -Encoding UTF8
                Write-Host "    [APPEND] $($doc.PromptsPath) ($($doc.Prompts.Count) prompt(s))" -ForegroundColor Green
            } else {
                Set-Content -Path $promptsFullPath -Value $promptContent -Encoding UTF8
                Write-Host "    [WRITE] $($doc.PromptsPath) ($($doc.Prompts.Count) prompt(s))" -ForegroundColor Green
            }
        }
    }

    # ── Part B: Inject [IMAGE-NN:] placeholders into .qmd ──
    $qmdFullPath = Join-Path $docsPath $doc.QmdPath

    if (-not (Test-Path $qmdFullPath)) {
        Write-Host "    [SKIP] .qmd file not found: $($doc.QmdPath)" -ForegroundColor Yellow
        continue
    }

    $qmdContent = Get-Content -Path $qmdFullPath -Raw -Encoding UTF8

    foreach ($p in $doc.Prompts) {
        $placeholder = "[$($p.Id): $($p.Prompt)]"

        # Check if already present
        if ($qmdContent -match [regex]::Escape("[$($p.Id):")) {
            Write-Host "    [SKIP] $($p.Id) placeholder already exists in .qmd" -ForegroundColor DarkGray
            continue
        }

        # Try to insert after the specified heading
        $inserted = $false
        foreach ($anchor in @($p.InsertAfter, $p.FallbackInsertAfter)) {
            if ($qmdContent -match "(?m)^(#+\s*$anchor.*)$") {
                $headingLine = $Matches[0]
                $insertionText = "$headingLine`n`n$placeholder`n"
                $qmdContent = $qmdContent.Replace($headingLine, $insertionText)
                $inserted = $true
                $totalPlaceholders++

                if ($DryRun) {
                    Write-Host "    [WOULD INSERT] $($p.Id) after '$anchor'" -ForegroundColor Yellow
                } else {
                    Write-Host "    [INSERT] $($p.Id) after '$anchor'" -ForegroundColor Green
                }
                break
            }
        }

        if (-not $inserted) {
            Write-Host "    [MANUAL] $($p.Id) — could not find heading anchor. Add manually:" -ForegroundColor Yellow
            Write-Host "             $placeholder" -ForegroundColor White
        }
    }

    # Write back the modified .qmd
    if (-not $DryRun -and $qmdContent -ne (Get-Content -Path $qmdFullPath -Raw -Encoding UTF8)) {
        Set-Content -Path $qmdFullPath -Value $qmdContent -Encoding UTF8 -NoNewline
    }
}

# ─── ADAPTER SPEC TEMPLATE ───
Write-Host "`n  Generating adapter spec image prompt template..." -ForegroundColor White

$templatePath = Join-Path $RepoRoot "scripts" "adapter-image-prompt-template.txt"
$templateContent = @'
# Adapter Spec Image Prompt Template
#
# Usage: For each adapter spec, replace {ADAPTER_NAME}, {DATA_SOURCE},
# and {CONTROLS} with the adapter-specific values from adapter-registry.yaml.
#
# Then insert as [IMAGE-01: <prompt>] at the top of the adapter's .qmd file.

[IMAGE-01: Technical architecture diagram showing the {ADAPTER_NAME} adapter
data flow within the UIAO FIMF framework: {DATA_SOURCE} as the data source
connecting to the {ADAPTER_NAME} Adapter component, which produces three
outputs: ClaimSet (governance assertions), DriftReport (deviation detection),
and EvidenceObject (compliance artifacts). Control mapping annotations for
{CONTROLS} shown as labels on the data flow arrows. Clean engineering
blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) color scheme on
white background. No photographs, purely diagrammatic.]

# ─── EXAMPLE: CyberArk ───
# [IMAGE-01: Technical architecture diagram showing the CyberArk PAM adapter
# data flow within the UIAO FIMF framework: CyberArk Vault as the data source
# connecting to the CyberArk Adapter component, which produces three outputs:
# ClaimSet (privileged account governance assertions), DriftReport (credential
# rotation and policy deviation detection), and EvidenceObject (PAM compliance
# artifacts). Control mapping annotations for AC-2, AC-6, IA-5 shown as labels
# on the data flow arrows. Clean engineering blueprint style, dark navy
# (#0D1B2E) and teal (#1E8C8C) color scheme on white background. No
# photographs, purely diagrammatic.]
'@

if ($DryRun) {
    Write-Host "    [WOULD WRITE] scripts/adapter-image-prompt-template.txt" -ForegroundColor Yellow
} else {
    Set-Content -Path $templatePath -Value $templateContent -Encoding UTF8
    Write-Host "    [WRITE] scripts/adapter-image-prompt-template.txt" -ForegroundColor Green
}

# ─── SUMMARY ───
Write-Host ""
if ($DryRun) {
    Write-Host "DRY RUN COMPLETE:" -ForegroundColor Yellow
    Write-Host "  Would write $totalPrompts prompt(s) to IMAGE-PROMPTS.md files" -ForegroundColor Yellow
    Write-Host "  Would insert $totalPlaceholders placeholder(s) into .qmd files" -ForegroundColor Yellow
} else {
    Write-Host "COMPLETE:" -ForegroundColor Green
    Write-Host "  Wrote $totalPrompts prompt(s) to IMAGE-PROMPTS.md files" -ForegroundColor Green
    Write-Host "  Inserted $totalPlaceholders placeholder(s) into .qmd files" -ForegroundColor Green
}

Write-Host "`nNEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Run the pipeline scan to verify detection:" -ForegroundColor White
Write-Host "     python scripts/generate_images.py --scan-only" -ForegroundColor White
Write-Host "  2. If scan detects all placeholders, run generation:" -ForegroundColor White
Write-Host "     python scripts/generate_images.py" -ForegroundColor White
Write-Host "  3. For adapter specs, use the template at:" -ForegroundColor White
Write-Host "     scripts/adapter-image-prompt-template.txt" -ForegroundColor White
Write-Host ""
Write-Host "Next step: Run 06-verify-all-fixes.ps1`n" -ForegroundColor Cyan
