# 16-fix-warn-gaps.ps1
# Resolves the 9 remaining quarto preview WARNs.
# Four are real content gaps -> create shell .qmd pages with callouts.
# Four are broken references -> remove or fix the link in the source file.
# One (documents/index.qmd) -> remove reference (purpose unclear, stub deleted).
#
# Usage:  .\16-fix-warn-gaps.ps1
# Dry run: .\16-fix-warn-gaps.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$created = 0
$fixed   = 0

function Write-Action {
    param([string]$Verb, [string]$Path, [string]$Color = "Green")
    if ($WhatIf) { Write-Host "[WHATIF] $Verb`: $Path" -ForegroundColor Cyan }
    else         { Write-Host "$Verb`: $Path" -ForegroundColor $Color }
}

function New-ShellPage {
    param([string]$RelPath, [string]$Title, [string]$Subtitle, [string]$Body)
    $fullPath = Join-Path $RepoRoot $RelPath
    if (Test-Path $fullPath) {
        Write-Host "  EXISTS: $RelPath" -ForegroundColor Gray; return
    }
    $dir = Split-Path $fullPath -Parent
    $content  = "---`n"
    $content += "title: `"$Title`"`n"
    $content += "subtitle: `"$Subtitle`"`n"
    $content += "---`n`n"
    $content += "::: {.callout-note}`n"
    $content += "## Page in preparation`n"
    $content += "$Body`n"
    $content += ":::`n"
    if (-not $WhatIf) {
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Set-Content $fullPath -Value $content -Encoding UTF8 -NoNewline
    }
    Write-Action "CREATED" $RelPath "Green"
    $script:created++
}

function Fix-BrokenRef {
    param([string]$FilePath, [string]$Pattern, [string]$Replacement, [string]$Description)
    $fullPath = Join-Path $RepoRoot $FilePath
    if (-not (Test-Path $fullPath)) {
        Write-Host "  NOT FOUND: $FilePath" -ForegroundColor Red; return
    }
    $c = Get-Content $fullPath -Raw
    $new = $c -replace $Pattern, $Replacement
    if ($new -eq $c) {
        Write-Host "  NO MATCH ($Description): $FilePath" -ForegroundColor Yellow
        return
    }
    if (-not $WhatIf) { Set-Content $fullPath -Value $new -Encoding UTF8 -NoNewline }
    Write-Action "FIXED ($Description)" $FilePath "Green"
    $script:fixed++
}

Write-Host ""
Write-Host "16-fix-warn-gaps.ps1" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN -- no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# ---------------------------------------------------------------------------
# GROUP 1: Create shell pages for real content gaps
# ---------------------------------------------------------------------------
Write-Host "Group 1: Create shell pages for real content gaps" -ForegroundColor Yellow
Write-Host ""

New-ShellPage `
    -RelPath "docs\docs\adapter-framework.qmd" `
    -Title "Adapter Framework" `
    -Subtitle "The UIAO adapter execution framework -- lifecycle, sandboxing, and hot-swap" `
    -Body "Full documentation is being drafted. See the [Adapter Authoring Tutorial](adapter-authoring-tutorial.qmd) and the [Adapter Plane appendix](appendix/a-adapter-plane/index.qmd) for current coverage."

New-ShellPage `
    -RelPath "docs\docs\adapter-development-guide.qmd" `
    -Title "Adapter Development Guide" `
    -Subtitle "End-to-end guide for building production UIAO adapters" `
    -Body "Full documentation is being drafted. See the [Adapter Authoring Tutorial](adapter-authoring-tutorial.qmd) to get started, and the [Adapter Plane appendix](appendix/a-adapter-plane/index.qmd) for the technical specification."

New-ShellPage `
    -RelPath "docs\docs\adr\index.qmd" `
    -Title "Architecture Decision Records" `
    -Subtitle "Index of UIAO architectural decisions" `
    -Body "The UIAO ADR corpus lives in ``src/uiao/canon/adr/``. See the [ADR index on GitHub](https://github.com/WhalerMike/uiao/tree/main/src/uiao/canon/adr) for the current list of decision records."

New-ShellPage `
    -RelPath "docs\docs\canon\canonical-rules.qmd" `
    -Title "Canon Canonical Rules" `
    -Subtitle "The normative rules governing UIAO canon document structure and validity" `
    -Body "Full documentation is being drafted from the [UIAO Document Metadata Contract](../meta/uiao-document-metadata-contract.qmd) and [ADR Metadata Contract](../meta/adr-metadata-contract.qmd)."

Write-Host ""

# ---------------------------------------------------------------------------
# GROUP 2: Fix broken references in source files
# ---------------------------------------------------------------------------
Write-Host "Group 2: Fix broken references in source files" -ForegroundColor Yellow
Write-Host ""

# canon/corpus-status-dashboard.qmd -- remove link to deleted documents/index.qmd
Fix-BrokenRef `
    -FilePath "docs\docs\canon\corpus-status-dashboard.qmd" `
    -Pattern '\[([^\]]+)\]\(docs\\documents\\index\.qmd\)' `
    -Replacement '$1' `
    -Description "remove deleted documents/index.qmd link"

# canon/corpus-status-dashboard.qmd -- update adr/index.qmd (now exists as shell)
# (no change needed -- the shell page we created above resolves it)

# canon/index.qmd -- remove references to archived canon/migration-plan.md
Fix-BrokenRef `
    -FilePath "docs\docs\canon\index.qmd" `
    -Pattern '\[([^\]]+)\]\(migration-plan\.md\)' `
    -Replacement '$1 *(archived)*' `
    -Description "replace migration-plan.md link (archived)"

# canon/index.qmd -- remove references to archived canon/pdf-layout-spec.md
Fix-BrokenRef `
    -FilePath "docs\docs\canon\index.qmd" `
    -Pattern '\[([^\]]+)\]\(pdf-layout-spec\.md\)' `
    -Replacement '$1 *(archived)*' `
    -Description "replace pdf-layout-spec.md link (archived)"

# canon/index.qmd -- fix adr/index.md -> adr/index.qmd (shell page now exists)
Fix-BrokenRef `
    -FilePath "docs\docs\canon\index.qmd" `
    -Pattern 'adr/index\.md' `
    -Replacement 'adr/index.qmd' `
    -Description "fix adr/index.md -> adr/index.qmd"

# canon/index.qmd -- fix canonical-rules.md -> canonical-rules.qmd (shell page now exists)
Fix-BrokenRef `
    -FilePath "docs\docs\canon\index.qmd" `
    -Pattern 'canonical-rules\.md' `
    -Replacement 'canonical-rules.qmd' `
    -Description "fix canonical-rules.md -> canonical-rules.qmd"

# adapter-authoring-tutorial.qmd -- fix adapter-development-guide.md -> .qmd
Fix-BrokenRef `
    -FilePath "docs\docs\adapter-authoring-tutorial.qmd" `
    -Pattern 'adapter-development-guide\.md' `
    -Replacement 'adapter-development-guide.qmd' `
    -Description "fix adapter-development-guide.md -> .qmd"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would create : $created shell pages" -ForegroundColor Cyan
    Write-Host "  Would fix    : $fixed source file references" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Dry run complete -- rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Created : $created shell pages" -ForegroundColor Green
    Write-Host "  Fixed   : $fixed source file references" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. quarto preview docs/ -- WARNs should drop to 0 or 1" -ForegroundColor White
    Write-Host "  2. git add -A && git commit -m 'fix: resolve 9 quarto preview WARNs'" -ForegroundColor White
    Write-Host "  3. git push" -ForegroundColor White
}
Write-Host ""
