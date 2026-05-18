<#
.SYNOPSIS
  UIAO Fix 06 — Verify all fixes were applied correctly.

.DESCRIPTION
  Runs a comprehensive check across all five previous fix scripts:
    1. No remaining .qmd/.md href links in document content
    2. All _quarto.yml sidebar entries have matching files on disk
    3. Index page tables contain clickable links (not plain text slugs)
    4. Landing page contains the new overview sections
    5. IMAGE-PROMPTS.md files contain real prompts (not TODO scaffolds)
    6. .qmd files contain [IMAGE-NN:] placeholders for the pipeline

.NOTES
  Run from the repo root after all fix scripts (01–05).
  This script makes NO modifications — read-only verification only.
#>

param(
    [string]$RepoRoot = (Get-Location).Path
)

$docsPath = Join-Path $RepoRoot "docs"
if (-not (Test-Path $docsPath)) {
    Write-Error "docs/ directory not found at $docsPath. Run from the repo root."
    exit 1
}

Write-Host "`n╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  UIAO Fix 06: Comprehensive Verification ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝`n" -ForegroundColor Cyan

$totalIssues = 0
$totalChecks = 0

# ═══════════════════════════════════════════
# CHECK 1: Broken link extensions
# ═══════════════════════════════════════════
Write-Host "─── CHECK 1: Link Extensions ───" -ForegroundColor White

$brokenLinks = @()
$qmdFiles = Get-ChildItem -Path $docsPath -Recurse -Filter "*.qmd" |
    Where-Object { $_.Name -ne "_quarto.yml" }

foreach ($file in $qmdFiles) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $relPath = $file.FullName.Substring($RepoRoot.Length + 1)

    # Check for href="...qmd" in HTML blocks
    $matches1 = [regex]::Matches($content, 'href="([^"]*?)\.qmd"')
    foreach ($m in $matches1) {
        $brokenLinks += [PSCustomObject]@{ File = $relPath; Link = $m.Value; Type = "href .qmd" }
    }

    # Check for href="...md" (non-external) in HTML blocks
    $matches2 = [regex]::Matches($content, 'href="((?!https?://)[^"]*?)\.md"')
    foreach ($m in $matches2) {
        $brokenLinks += [PSCustomObject]@{ File = $relPath; Link = $m.Value; Type = "href .md" }
    }

    # Check markdown-style [text](file.qmd)
    $matches3 = [regex]::Matches($content, '\]\(([^)]*?)\.qmd\)')
    foreach ($m in $matches3) {
        $brokenLinks += [PSCustomObject]@{ File = $relPath; Link = $m.Value; Type = "markdown .qmd" }
    }

    # Check markdown-style [text](file.md) (non-external)
    $matches4 = [regex]::Matches($content, '\]\(((?!https?://)[^)]*?)\.md\)')
    foreach ($m in $matches4) {
        $brokenLinks += [PSCustomObject]@{ File = $relPath; Link = $m.Value; Type = "markdown .md" }
    }
}
$totalChecks++

if ($brokenLinks.Count -eq 0) {
    Write-Host "  [PASS] No broken .qmd/.md link extensions found" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] $($brokenLinks.Count) broken link extension(s) remain:" -ForegroundColor Red
    $brokenLinks | ForEach-Object {
        Write-Host "         $($_.File): $($_.Link)" -ForegroundColor Red
    }
    $totalIssues += $brokenLinks.Count
}

# ═══════════════════════════════════════════
# CHECK 2: _quarto.yml sidebar file existence
# ═══════════════════════════════════════════
Write-Host "`n─── CHECK 2: Sidebar Entry File Existence ───" -ForegroundColor White

$quartoPath = Join-Path $docsPath "_quarto.yml"
$quartoContent = Get-Content -Path $quartoPath -Raw -Encoding UTF8
$missingFiles = @()

# Extract all file references from _quarto.yml
$fileRefs = [regex]::Matches($quartoContent, '^\s*-\s+((?:customer-documents|modernization|findings|academy|docs)/[^\s]+\.(?:qmd|md))', [System.Text.RegularExpressions.RegexOptions]::Multiline)

foreach ($ref in $fileRefs) {
    $filePath = $ref.Groups[1].Value
    $fullPath = Join-Path $docsPath $filePath
    if (-not (Test-Path $fullPath)) {
        $missingFiles += $filePath
    }
}
$totalChecks++

if ($missingFiles.Count -eq 0) {
    Write-Host "  [PASS] All $($fileRefs.Count) sidebar entries have matching files" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] $($missingFiles.Count) sidebar entry file(s) missing:" -ForegroundColor Red
    $missingFiles | ForEach-Object {
        Write-Host "         $_" -ForegroundColor Red
    }
    $totalIssues += $missingFiles.Count
    Write-Host ""
    Write-Host "  ACTION: These files may use .md instead of .qmd (or vice versa)." -ForegroundColor Yellow
    Write-Host "  Check the actual file extension on disk and update _quarto.yml accordingly." -ForegroundColor Yellow
}

# ═══════════════════════════════════════════
# CHECK 3: Index page table links
# ═══════════════════════════════════════════
Write-Host "`n─── CHECK 3: Index Page Table Links ───" -ForegroundColor White

$indexPages = @(
    "customer-documents/adapter-specs/index.qmd"
    "customer-documents/validation-suites/index.qmd"
    "customer-documents/modernization-specs/index.qmd"
    "customer-documents/case-studies/index.qmd"
)

foreach ($page in $indexPages) {
    $fullPath = Join-Path $docsPath $page
    $totalChecks++

    if (-not (Test-Path $fullPath)) {
        Write-Host "  [SKIP] $page not found" -ForegroundColor Yellow
        continue
    }

    $content = Get-Content -Path $fullPath -Raw -Encoding UTF8

    # Check for table rows with backtick slugs that are NOT links
    $unlinkedSlugs = [regex]::Matches($content, '\|\s*`([a-z][-a-z0-9]*)`\s*\|')
    $linkedSlugs = [regex]::Matches($content, '\|\s*\[`[a-z][-a-z0-9]*`\]\(')

    if ($unlinkedSlugs.Count -gt 0 -and $linkedSlugs.Count -eq 0) {
        Write-Host "  [FAIL] $page — $($unlinkedSlugs.Count) unlinked slug(s)" -ForegroundColor Red
        $totalIssues += $unlinkedSlugs.Count
    } elseif ($linkedSlugs.Count -gt 0) {
        Write-Host "  [PASS] $page — $($linkedSlugs.Count) linked slug(s)" -ForegroundColor Green
    } else {
        Write-Host "  [INFO] $page — no backtick slugs found (may use different format)" -ForegroundColor DarkGray
    }
}

# ═══════════════════════════════════════════
# CHECK 4: Landing page overview sections
# ═══════════════════════════════════════════
Write-Host "`n─── CHECK 4: Landing Page Overview Content ───" -ForegroundColor White

$indexQmd = Join-Path $docsPath "index.qmd"
$indexContent = Get-Content -Path $indexQmd -Raw -Encoding UTF8
$totalChecks++

$requiredSections = @(
    @{ Id = "what-is-uiao"; Name = "What UIAO Actually Is" }
    @{ Id = "governance-crisis"; Name = "Hidden Governance Crisis (11 Dependencies)" }
    @{ Id = "modernization-arc"; Name = "Modernization Arc (6 Phases)" }
    @{ Id = "key-documents"; Name = "Key Documents (Read the Full Story)" }
)

$sectionsMissing = 0
foreach ($section in $requiredSections) {
    if ($indexContent -match $section.Id) {
        Write-Host "  [PASS] $($section.Name)" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($section.Name) — section not found" -ForegroundColor Red
        $sectionsMissing++
    }
}
$totalIssues += $sectionsMissing

# ═══════════════════════════════════════════
# CHECK 5: Image prompts and placeholders
# ═══════════════════════════════════════════
Write-Host "`n─── CHECK 5: Image Prompts & Placeholders ───" -ForegroundColor White

$promptFiles = Get-ChildItem -Path $docsPath -Recurse -Filter "IMAGE-PROMPTS.md"
$todoCount = 0
$realCount = 0

foreach ($pf in $promptFiles) {
    $pfContent = Get-Content -Path $pf.FullName -Raw -Encoding UTF8
    if ($pfContent -match "TODO") {
        $todoCount++
    } elseif ($pfContent -match "IMAGE-0") {
        $realCount++
    }
}
$totalChecks++

Write-Host "  IMAGE-PROMPTS.md files with real prompts:  $realCount" -ForegroundColor $(if ($realCount -gt 0) { "Green" } else { "Yellow" })
Write-Host "  IMAGE-PROMPTS.md files still TODO scaffold: $todoCount" -ForegroundColor $(if ($todoCount -gt 0) { "Yellow" } else { "Green" })

# Check for [IMAGE-NN:] placeholders in .qmd files
$placeholderFiles = @()
foreach ($qf in $qmdFiles) {
    $qfContent = Get-Content -Path $qf.FullName -Raw -Encoding UTF8
    if ($qfContent -match '\[IMAGE-\d+:') {
        $relPath = $qf.FullName.Substring($RepoRoot.Length + 1)
        $placeholderFiles += $relPath
    }
}
$totalChecks++

if ($placeholderFiles.Count -gt 0) {
    Write-Host "  [PASS] $($placeholderFiles.Count) .qmd file(s) contain [IMAGE-NN:] placeholders:" -ForegroundColor Green
    $placeholderFiles | ForEach-Object {
        Write-Host "         $_" -ForegroundColor Green
    }
} else {
    Write-Host "  [WARN] No .qmd files contain [IMAGE-NN:] placeholders yet" -ForegroundColor Yellow
    Write-Host "         Run 05-seed-image-prompts.ps1 to inject them" -ForegroundColor Yellow
}

# ═══════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════
Write-Host "`n╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║              SUMMARY                      ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan

if ($totalIssues -eq 0) {
    Write-Host "`n  ALL CHECKS PASSED ($totalChecks checks)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Ready to commit and push:" -ForegroundColor White
    Write-Host '    git add -A' -ForegroundColor White
    Write-Host '    git commit -m "fix(docs): repair links, add sidebar entries, enrich landing page, seed image prompts"' -ForegroundColor White
    Write-Host '    git push origin main' -ForegroundColor White
} else {
    Write-Host "`n  $totalIssues ISSUE(S) FOUND across $totalChecks checks" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Review the [FAIL] items above and re-run the appropriate fix script." -ForegroundColor Yellow
    Write-Host "  Then re-run this verification script to confirm." -ForegroundColor Yellow
}

Write-Host "`n  After pushing, verify the live site at:" -ForegroundColor Cyan
Write-Host "    https://whalermike.github.io/uiao/" -ForegroundColor White
Write-Host ""
