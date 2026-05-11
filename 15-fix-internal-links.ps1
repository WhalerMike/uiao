# 15-fix-internal-links.ps1
# Fixes broken internal cross-references inside .qmd files.
# All converted files still reference siblings by their old .md extension.
# This script finds every such reference and updates it to .qmd.
#
# Scope: any .qmd file under docs\ that contains a markdown link or
#        href pointing to a .md file that has since been renamed to .qmd.
#
# Usage:  .\15-fix-internal-links.ps1
# Dry run: .\15-fix-internal-links.ps1 -WhatIf

param(
    [string]$RepoRoot = "C:\Users\whale\git\uiao",
    [switch]$WhatIf
)

$filesFixed  = 0
$linksFixed  = 0
$filesClean  = 0

Write-Host ""
Write-Host "15-fix-internal-links.ps1" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
if ($WhatIf) { Write-Host "(DRY RUN -- no files will be changed)" -ForegroundColor Yellow }
Write-Host ""

# Scan all .qmd files under docs/
$qmdFiles = Get-ChildItem (Join-Path $RepoRoot "docs") -Recurse -Filter "*.qmd" -ErrorAction SilentlyContinue
Write-Host "Scanning $($qmdFiles.Count) .qmd files for stale .md links..." -ForegroundColor Gray
Write-Host ""

foreach ($file in $qmdFiles) {
    $content  = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    # Match markdown links and href values pointing to .md files.
    # Patterns covered:
    #   [text](path/to/file.md)
    #   [text](path/to/file.md#anchor)
    #   href: path/to/file.md
    # We only replace .md -> .qmd when the linked file actually exists as .qmd
    # in the repo. This avoids fixing links to truly external or missing files.

    $original = $content
    $changed  = 0

    # Find all candidate .md references
    $matches = [regex]::Matches($content, '(?<=\]\(|href:\s{0,4})([^)\s"'']+?)\.md(#[^\s"'')]*)?(?=\)|$|\s|")')

    # Collect unique stems to check existence once
    $stems = @{}
    foreach ($m in $matches) {
        $stem = $m.Groups[1].Value
        if (-not $stems.ContainsKey($stem)) { $stems[$stem] = $null }
    }

    # For each stem, check if the .qmd counterpart exists relative to the file
    foreach ($stem in $stems.Keys) {
        # Resolve relative to the containing file's directory
        $dir     = Split-Path $file.FullName -Parent
        $mdPath  = Join-Path $dir "$stem.md"  -Resolve -ErrorAction SilentlyContinue
        $qmdPath = Join-Path $dir "$stem.qmd"

        # Also try absolute from repo root (for paths like docs\something)
        $mdAbs  = Join-Path $RepoRoot "docs\$stem.md"
        $qmdAbs = Join-Path $RepoRoot "docs\$stem.qmd"

        $qmdExists = (Test-Path $qmdPath) -or (Test-Path $qmdAbs)

        if ($qmdExists) {
            # Escape for regex: dots and backslashes in the stem
            $escapedStem = [regex]::Escape($stem)
            # Replace stem.md with stem.qmd in link contexts
            $before = $content
            $content = $content -replace "($escapedStem)\.md(#[^\s""`')\]]*)?", '$1.qmd$2'
            if ($content -ne $before) { $changed++ }
        }
    }

    if ($changed -gt 0) {
        $rel = $file.FullName.Replace($RepoRoot + "\", "")
        if (-not $WhatIf) {
            Set-Content $file.FullName -Value $content -Encoding UTF8 -NoNewline
        }
        $verb = if ($WhatIf) { "[WHATIF]" } else { "FIXED" }
        Write-Host "$verb $rel ($changed link groups updated)" -ForegroundColor $(if ($WhatIf) { "Cyan" } else { "Green" })
        $filesFixed++
        $linksFixed += $changed
    } else {
        $filesClean++
    }
}

# Also fix findings/ and other top-level dirs outside docs/
$otherDirs = @("findings", "governance", "narrative", "reports", "runbook", "security",
               "appendices", "ato", "customer-documents")
foreach ($dir in $otherDirs) {
    $dirPath = Join-Path $RepoRoot $dir
    if (-not (Test-Path $dirPath)) { continue }
    $files = Get-ChildItem $dirPath -Recurse -Filter "*.qmd" -ErrorAction SilentlyContinue
    foreach ($file in $files) {
        $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
        if (-not $content) { continue }
        $original = $content
        $changed  = 0

        $matches = [regex]::Matches($content, '(?<=\]\(|href:\s{0,4})([^)\s"'']+?)\.md(#[^\s"'')]*)?(?=\)|$|\s|")')
        $stems = @{}
        foreach ($m in $matches) { $stems[$m.Groups[1].Value] = $null }

        foreach ($stem in $stems.Keys) {
            $fileDir = Split-Path $file.FullName -Parent
            $qmdPath = Join-Path $fileDir "$stem.qmd"
            $qmdAbs  = Join-Path $RepoRoot "$stem.qmd"
            if ((Test-Path $qmdPath) -or (Test-Path $qmdAbs)) {
                $escaped = [regex]::Escape($stem)
                $before  = $content
                $content = $content -replace "($escaped)\.md(#[^\s""`')\]]*)?", '$1.qmd$2'
                if ($content -ne $before) { $changed++ }
            }
        }

        if ($changed -gt 0) {
            $rel = $file.FullName.Replace($RepoRoot + "\", "")
            if (-not $WhatIf) { Set-Content $file.FullName -Value $content -Encoding UTF8 -NoNewline }
            $verb = if ($WhatIf) { "[WHATIF]" } else { "FIXED" }
            Write-Host "$verb $rel ($changed link groups updated)" -ForegroundColor $(if ($WhatIf) { "Cyan" } else { "Green" })
            $filesFixed++
            $linksFixed += $changed
        }
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Done." -ForegroundColor Cyan
if ($WhatIf) {
    Write-Host "  Would fix  : $filesFixed files, $linksFixed link groups" -ForegroundColor Cyan
    Write-Host "  Already clean: $filesClean files" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Dry run complete -- rerun without -WhatIf to apply." -ForegroundColor Yellow
} else {
    Write-Host "  Fixed   : $filesFixed files, $linksFixed link groups updated" -ForegroundColor Green
    Write-Host "  Already clean: $filesClean files" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. quarto preview docs/ -- verify WARN count drops significantly" -ForegroundColor White
    Write-Host "  2. git add -A && git commit -m 'fix: update stale .md cross-references to .qmd in content files'" -ForegroundColor White
    Write-Host "  3. git push" -ForegroundColor White
    Write-Host "  4. Fix executive-briefs index table slug links (manual edit in VS Code)" -ForegroundColor White
}
Write-Host ""
