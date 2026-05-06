<#
.SYNOPSIS
  UIAO Fix 03 — Convert plain-text index table entries into clickable links.

.DESCRIPTION
  The four "family" index pages (adapter-specs, validation-suites,
  modernization-specs, case-studies) list documents as plain-text slugs
  in their Markdown tables. This script rewrites each table row so the
  slug column becomes a clickable link pointing to the rendered .html page.

  Targets:
    - docs/customer-documents/adapter-specs/index.qmd         (16 adapters)
    - docs/customer-documents/validation-suites/index.qmd     (22 suites)
    - docs/customer-documents/modernization-specs/index.qmd   (6 domains)
    - docs/customer-documents/case-studies/index.qmd           (3 studies)

.NOTES
  Run from the repo root after 02-add-missing-sidebar-entries.ps1.
  Idempotent — will not double-wrap already-linked slugs.
#>

param(
    [switch]$DryRun,
    [string]$RepoRoot = (Get-Location).Path
)

$docsPath = Join-Path $RepoRoot "docs" "customer-documents"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UIAO Fix 03: Index Page Link Repair" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "[DRY RUN] No files will be modified.`n" -ForegroundColor Yellow
}

$totalFixed = 0

# ─── HELPER: Linkify table slugs ───
function Convert-TableSlugs {
    param(
        [string]$FilePath,
        [string]$SlugPattern,       # Regex to match the slug cell content
        [string]$LinkTemplate,      # Template with {slug} placeholder
        [string]$Description
    )

    if (-not (Test-Path $FilePath)) {
        Write-Host "  [SKIP] File not found: $FilePath" -ForegroundColor Yellow
        return 0
    }

    $content = Get-Content -Path $FilePath -Raw -Encoding UTF8
    $original = $content

    # Match table rows where the slug is plain text (not already a link)
    # Pattern: | `slug` | or | slug |
    # But NOT: | [`slug`](url) | or | [slug](url) |
    $lines = $content -split "`n"
    $modified = @()
    $changeCount = 0

    foreach ($line in $lines) {
        $newLine = $line

        # Match table cells with backtick-wrapped slugs: | `some-slug` |
        # that are NOT already links: | [`some-slug`](...) |
        if ($line -match '^\|' -and $line -match $SlugPattern) {
            # Extract the slug
            if ($line -match '\|\s*`([a-z0-9][-a-z0-9]*)`\s*\|' -and $line -notmatch '\[`[a-z]') {
                $slug = $Matches[1]
                $link = $LinkTemplate -replace '\{slug\}', $slug
                $newLine = $line -replace "\|\s*``$slug``\s*\|", "| [``$slug``]($link) |"
                if ($newLine -ne $line) { $changeCount++ }
            }
        }

        $modified += $newLine
    }

    $newContent = $modified -join "`n"

    if ($changeCount -gt 0) {
        $relPath = $FilePath.Substring($RepoRoot.Length + 1)
        if ($DryRun) {
            Write-Host "  [WOULD FIX] $relPath — $changeCount slug(s) in $Description" -ForegroundColor Yellow
        } else {
            Set-Content -Path $FilePath -Value $newContent -Encoding UTF8 -NoNewline
            Write-Host "  [FIXED] $relPath — $changeCount slug(s) linked in $Description" -ForegroundColor Green
        }
    }

    return $changeCount
}

# ─── ADAPTER SPECS ───
$adapterFile = Join-Path $docsPath "adapter-specs" "index.qmd"
$count = Convert-TableSlugs `
    -FilePath $adapterFile `
    -SlugPattern '`[a-z][-a-z0-9]*`' `
    -LinkTemplate '{slug}/{slug}.html' `
    -Description "Adapter Specs table"
$totalFixed += $count

# ─── VALIDATION SUITES (Adapters) ───
$validationFile = Join-Path $docsPath "validation-suites" "index.qmd"
$count = Convert-TableSlugs `
    -FilePath $validationFile `
    -SlugPattern '`[a-z][-a-z0-9]*`' `
    -LinkTemplate 'adapters/{slug}/{slug}.html' `
    -Description "Validation Suites (adapter) table"
$totalFixed += $count

# ─── MODERNIZATION SPECS ───
$modSpecFile = Join-Path $docsPath "modernization-specs" "index.qmd"
$count = Convert-TableSlugs `
    -FilePath $modSpecFile `
    -SlugPattern '`[a-z][-a-z0-9]*`' `
    -LinkTemplate '{slug}/{slug}.html' `
    -Description "Modernization Specs table"
$totalFixed += $count

# ─── CASE STUDIES ───
$caseFile = Join-Path $docsPath "case-studies" "index.qmd"
$count = Convert-TableSlugs `
    -FilePath $caseFile `
    -SlugPattern '`[a-z][-a-z0-9]*`' `
    -LinkTemplate '{slug}.html' `
    -Description "Case Studies table"
$totalFixed += $count

# ─── SUMMARY ───
Write-Host ""
if ($totalFixed -eq 0) {
    Write-Host "No plain-text slugs found — tables may already be linked or have a different format." -ForegroundColor Green
    Write-Host ""
    Write-Host "If slugs still appear unlinked, manually check the table format in each index.qmd." -ForegroundColor Yellow
    Write-Host "The script expects: | ``slug-name`` | Description | ... |" -ForegroundColor Yellow
} else {
    if ($DryRun) {
        Write-Host "DRY RUN COMPLETE: Would link $totalFixed table slug(s)." -ForegroundColor Yellow
    } else {
        Write-Host "COMPLETE: Linked $totalFixed table slug(s) across index pages." -ForegroundColor Green
    }
}

Write-Host "`nMANUAL VERIFICATION:" -ForegroundColor Cyan
Write-Host "  After running, do a local 'quarto preview' and check:" -ForegroundColor White
Write-Host "    - https://localhost:.../customer-documents/adapter-specs/" -ForegroundColor White
Write-Host "    - https://localhost:.../customer-documents/validation-suites/" -ForegroundColor White
Write-Host "    - https://localhost:.../customer-documents/modernization-specs/" -ForegroundColor White
Write-Host "    - https://localhost:.../customer-documents/case-studies/" -ForegroundColor White
Write-Host "  Confirm slug names are now blue/teal clickable links.`n" -ForegroundColor White

Write-Host "Next step: Run 04-enrich-landing-page.ps1`n" -ForegroundColor Cyan
