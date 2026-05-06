<#
.SYNOPSIS
  UIAO Fix 01 — Fix .qmd/.md link extensions in document content.

.DESCRIPTION
  Scans all .qmd files under docs/ for href="...qmd" and markdown-style
  links like [text](file.qmd) that point to .qmd or .md source files.
  Rewrites them to .html so they resolve correctly on GitHub Pages.

  Does NOT modify _quarto.yml (those references are correct for Quarto's
  build system). Only modifies document content.

.NOTES
  Run from the repo root after a full git pull.
  Idempotent — safe to run multiple times.
#>

param(
    [switch]$DryRun,
    [string]$RepoRoot = (Get-Location).Path
)

$docsPath = Join-Path $RepoRoot "docs"
if (-not (Test-Path $docsPath)) {
    Write-Error "docs/ directory not found at $docsPath. Run this script from the repo root."
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 01: Link Extension Repair" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified.`n" -ForegroundColor Yellow
}

# Patterns to fix:
#   1. href="something.qmd"         -> href="something.html"
#   2. href="something.md"          -> href="something.html"
#   3. [text](something.qmd)        -> [text](something.html)
#   4. [text](something.md)         -> [text](something.html)
#
# Exclusions:
#   - _quarto.yml (Quarto needs .qmd refs)
#   - IMAGE-PROMPTS.md files
#   - Lines that are YAML frontmatter (between --- markers)

$qmdFiles = Get-ChildItem -Path $docsPath -Recurse -Filter "*.qmd" |
    Where-Object { $_.Name -ne "_quarto.yml" }

$totalFixed = 0
$filesModified = 0

foreach ($file in $qmdFiles) {
    $content = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $original = $content

    # Fix href="...qmd" -> href="...html" (in raw HTML blocks)
    $content = $content -replace 'href="([^"]*?)\.qmd"', 'href="$1.html"'
    $content = $content -replace "href='([^']*?)\.qmd'", "href='`$1.html'"

    # Fix href="...md" -> href="...html" (but not external URLs or _quarto.yml refs)
    # Only match relative paths (no http:// or https://)
    $content = $content -replace 'href="((?!https?://)[^"]*?)\.md"', 'href="$1.html"'
    $content = $content -replace "href='((?!https?://)[^']*?)\.md'", "href='`$1.html'"

    # Fix markdown-style links: [text](file.qmd) -> [text](file.html)
    $content = $content -replace '\]\(([^)]*?)\.qmd\)', ']($1.html)'

    # Fix markdown-style links: [text](file.md) -> [text](file.html)
    # But not external URLs
    $content = $content -replace '\]\(((?!https?://)[^)]*?)\.md\)', ']($1.html)'

    if ($content -ne $original) {
        $relPath = $file.FullName.Substring($RepoRoot.Length + 1)

        # Count changes
        $changeCount = 0
        $origLines = $original -split "`n"
        $newLines = $content -split "`n"
        for ($i = 0; $i -lt [Math]::Max($origLines.Count, $newLines.Count); $i++) {
            if ($i -lt $origLines.Count -and $i -lt $newLines.Count) {
                if ($origLines[$i] -ne $newLines[$i]) { $changeCount++ }
            }
        }

        if ($DryRun) {
            Write-Host "  [WOULD FIX] $relPath ($changeCount link(s))" -ForegroundColor Yellow
        } else {
            Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
            Write-Host "  [FIXED] $relPath ($changeCount link(s))" -ForegroundColor Green
        }
        $totalFixed += $changeCount
        $filesModified++
    }
}

Write-Host ""
if ($DryRun) {
    Write-Host "DRY RUN COMPLETE: Would fix $totalFixed link(s) in $filesModified file(s)." -ForegroundColor Yellow
} else {
    Write-Host "COMPLETE: Fixed $totalFixed link(s) in $filesModified file(s)." -ForegroundColor Green
}

if ($totalFixed -eq 0) {
    Write-Host "No broken link extensions found — all clean!" -ForegroundColor Green
}

Write-Host "`nNext step: Run 02-add-missing-sidebar-entries.ps1`n" -ForegroundColor Cyan
