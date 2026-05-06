# 07-insert-image-placeholders.ps1
# Inserts [IMAGE-NN:] placeholders into 5 .qmd files (8 total insertions)

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 07: Insert Image Placeholders" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$insertions = @(
    @{
        File   = "docs\customer-documents\architecture-series\aodim-architecture.qmd"
        Anchor = "Architecture Overview"
        Tag    = "IMAGE-01"
        Prompt = "Technical architecture diagram showing the AODIM attribute flow: HR System arrow to Identity Attributes arrow to Dynamic Groups arrow to Access Policies arrow to Resource Authorization. Each stage labeled with governance checkpoints. Clean engineering blueprint style, dark navy (#0D1B2E) and teal (#1E8C8C) color scheme on white background. No photographs, purely diagrammatic."
    },
    @{
        File   = "docs\customer-documents\architecture-series\aodim-architecture.qmd"
        Anchor = "Delegation Model"
        Tag    = "IMAGE-02"
        Prompt = "Side-by-side comparison diagram: Left panel labeled Legacy OU-Based Delegation showing a rigid tree hierarchy with Organizational Units and static group nesting. Right panel labeled AODIM Attribute-Based Delegation showing a flat, dynamic model with attribute tags flowing to policy engines. Arrows show the transformation path between them. Clean engineering diagram, dark navy and teal color scheme."
    },
    @{
        File   = "docs\customer-documents\architecture-series\aodim-architecture.qmd"
        Anchor = "Operational Flow"
        Tag    = "IMAGE-03"
        Prompt = "Operational flow diagram showing the AODIM runtime cycle: Identity Event triggers Attribute Evaluation, which feeds Rule Engine, which produces Access Decision plus Drift Report plus Evidence Object. Feedback loop from Drift Report back to Identity Event for remediation. Clean engineering style, dark navy and teal on white, no photographs."
    },
    @{
        File   = "docs\customer-documents\whitepapers\ad-to-entraid-migration-problem.qmd"
        Anchor = "The Forced Migration Problem"
        Tag    = "IMAGE-01"
        Prompt = "Architecture comparison diagram with two panels: Left panel Active Directory Governance Surface showing AD at center connected to 11 dependency spokes. Right panel Entra ID showing the same 11 spokes but 9 are disconnected/broken (dashed red lines). Title: What Migrates vs. What Breaks. Clean technical diagram, navy and teal with red (#C74040) for broken connections."
    },
    @{
        File   = "docs\customer-documents\whitepapers\ad-to-entraid-migration-problem.qmd"
        Anchor = "What UIAO Actually Is"
        Tag    = "IMAGE-02"
        Prompt = "Bridge architecture diagram showing UIAO as a governance layer spanning between Active Directory (left) and Entra ID (right). Below the bridge: FIMF Adapter slots connecting to legacy systems (DNS, PKI, RADIUS, LDAP). Above the bridge: Continuous Evidence Flow with KSI metrics, drift detection, and compliance artifacts. Labeled UIAO Governance Bridge. Clean engineering style, dark navy and teal color scheme."
    },
    @{
        File   = "docs\customer-documents\modernization\client-server-to-hybrid-cloud\01-platform-foundation.qmd"
        Anchor = "The five roles"
        Tag    = "IMAGE-01"
        Prompt = "Layered platform architecture diagram showing the UIAO substrate stack from bottom to top: Infrastructure Layer (Azure Arc, on-premises compute), Platform Services Layer (Canon Registry, Adapter Framework, CLI Tooling), Governance Layer (DRIFT Modules, KSI Engine, Evidence Fabric), and Operations Layer (Dashboards, Alerts, Compliance Reports). Each layer connected by bidirectional arrows. Clean engineering blueprint style, dark navy and teal color scheme."
    },
    @{
        File   = "docs\customer-documents\modernization\client-server-to-hybrid-cloud\04-identity-transformation.qmd"
        Anchor = "Migration (MOD_F)"
        Tag    = "IMAGE-02"
        Prompt = "Identity transformation pipeline diagram showing the flow: Legacy AD Objects entering a Transformation Engine with three processing stages (Attribute Mapping, Policy Conversion, Delegation Translation), producing Entra ID Objects with a Drift Detection feedback loop. Governance checkpoints marked at each stage. Clean technical diagram, navy and teal color scheme."
    },
    @{
        File   = "docs\customer-documents\modernization\client-server-to-hybrid-cloud\09-migration-roadmap.qmd"
        Anchor = "The seven phases"
        Tag    = "IMAGE-03"
        Prompt = "Migration roadmap timeline diagram showing six phases (Phase 0 Discovery through Phase 5 Continuous Governance) on a horizontal timeline. Each phase shown as a block with key milestones, deliverables, and go/no-go gates between phases. Color-coded: completed phases in teal, current phase highlighted with amber border, future phases in light gray. Decision diamonds at phase boundaries. Clean Gantt-style engineering diagram, navy and teal color scheme."
    }
)

$totalInserted = 0
$totalSkipped  = 0

foreach ($ins in $insertions) {
    $filePath  = $ins.File
    $shortPath = $filePath -replace '^docs\\', ''

    if (-not (Test-Path $filePath)) {
        Write-Host "  [MISS] $shortPath - file not found" -ForegroundColor Red
        $totalSkipped++
        continue
    }

    $fullPath = (Resolve-Path $filePath).Path
    $lines    = [System.IO.File]::ReadAllLines($fullPath)

    $tagPattern = "[$($ins.Tag):"
    $alreadyPresent = $false
    foreach ($line in $lines) {
        if ($line.Contains($tagPattern)) {
            $alreadyPresent = $true
            break
        }
    }
    if ($alreadyPresent) {
        Write-Host "  [SKIP] $shortPath - $($ins.Tag) already present" -ForegroundColor Yellow
        $totalSkipped++
        continue
    }

    $anchorIndex = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Contains($ins.Anchor)) {
            $anchorIndex = $i
            break
        }
    }
    if ($anchorIndex -eq -1) {
        Write-Host "  [MISS] $shortPath - anchor '$($ins.Anchor)' not found" -ForegroundColor Red
        $totalSkipped++
        continue
    }

    $placeholder = "[$($ins.Tag): $($ins.Prompt)]"
    $newLines = [System.Collections.ArrayList]::new()
    for ($i = 0; $i -lt $lines.Count; $i++) {
        [void]$newLines.Add($lines[$i])
        if ($i -eq $anchorIndex) {
            [void]$newLines.Add("")
            [void]$newLines.Add($placeholder)
            [void]$newLines.Add("")
        }
    }

    [System.IO.File]::WriteAllLines($fullPath, $newLines.ToArray())
    Write-Host "  [INSERT] $shortPath - $($ins.Tag) after '$($ins.Anchor)' (line $($anchorIndex + 1))" -ForegroundColor Green
    $totalInserted++
}

Write-Host ""
if ($totalInserted -gt 0) {
    Write-Host "COMPLETE: Inserted $totalInserted placeholder(s)." -ForegroundColor Green
}
if ($totalSkipped -gt 0) {
    Write-Host "ATTENTION: $totalSkipped item(s) skipped - see details above." -ForegroundColor Yellow
}
Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Cyan
Write-Host "  1. Review:   git diff docs/"
Write-Host "  2. Scan:     python scripts/generate_images.py --scan-only"
Write-Host "  3. Generate: python scripts/generate_images.py"
Write-Host "  4. Commit:   git add docs/ && git commit -m 'feat(images): insert 8 image placeholders'"
Write-Host "  5. Push:     git push origin main"
Write-Host "  6. Preview:  quarto preview docs/"
Write-Host ""
