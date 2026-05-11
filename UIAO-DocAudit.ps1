# UIAO-DocAudit.ps1
# Scans the uiao repo and classifies every .md and .qmd file.
# Outputs a CSV to the repo root and prints a summary to the console.
#
# Usage:
#   .\UIAO-DocAudit.ps1
#   .\UIAO-DocAudit.ps1 -RepoRoot "C:\Users\whale\git\uiao" -OutputCsv "C:\temp\doc-audit.csv"

param(
    [string]$RepoRoot  = "C:\Users\whale\git\uiao",
    [string]$OutputCsv = "C:\Users\whale\git\uiao\doc-audit.csv"
)

$ExcludeDirs = @('.venv', 'node_modules', '.claude', 'ai-hallucination-archive')
$InfraFiles  = @(
    'README.md','CHANGELOG.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md',
    'SECURITY.md','SUPPORT.md','AGENTS.md','CLAUDE.md','RELEASE_NOTES.md',
    'PULL_REQUEST_TEMPLATE.md','LICENSE.md','template.md','best_practices.md'
)

function Get-Category {
    param([string]$RelPath, [long]$Size, [string]$Ext)

    if ($Size -eq 0)                                  { return "SHELL" }
    if ($RelPath -like "ai-hallucination-archive\*")  { return "ARCHIVE" }
    if ($RelPath -like "*IMAGE-PROMPTS*")             { return "DATA-IMAGEPROMPT" }
    if ($RelPath -like ".venv\*")                     { return "VENV-SKIP" }
    if ($RelPath -like ".claude\*")                   { return "WORKTREE-SKIP" }
    if ($RelPath -like "src\*")                       { return "SRC-CODEDOC" }
    if ($RelPath -like "tests\*")                     { return "INFRA-TEST" }
    if ($RelPath -like "tools\*")                     { return "INFRA-TOOL" }
    if ($RelPath -like "diagrams\*")                  { return "INFRA-DIAGRAMS" }
    if ($RelPath -like "canon\*")                     { return "INFRA-CANON" }
    if ($RelPath -like ".github\*")                   { return "INFRA-GITHUB" }

    $leaf = Split-Path $RelPath -Leaf
    if ($InfraFiles -contains $leaf)                  { return "INFRA-GITHUB" }

    if ($Ext -eq ".qmd" -and $RelPath -like "docs\*") { return "LIVE-QMD" }
    if ($Ext -eq ".md"  -and $RelPath -like "docs\*") { return "ORPHAN-MD" }
    if ($RelPath -notlike "*\*")                       { return "INFRA-GITHUB" }

    return "UNCATEGORIZED"
}

function Get-Action {
    param([string]$Category)
    switch ($Category) {
        "SHELL"            { return "DECIDE: write content, promote to shell .qmd, or delete" }
        "ORPHAN-MD"        { return "CONVERT: rename to .qmd, add YAML header, add nav/link" }
        "LIVE-QMD"         { return "REVIEW: verify YAML header and nav entry; fix table links" }
        "ARCHIVE"          { return "LEAVE: frozen history — do not edit" }
        "DATA-IMAGEPROMPT" { return "LEAVE: NanoBanana pipeline input, not a web page" }
        "INFRA-GITHUB"     { return "LEAVE: must stay .md (GitHub requirement)" }
        "SRC-CODEDOC"      { return "LEAVE: code-tree doc, not a Quarto page" }
        "INFRA-TEST"       { return "LEAVE: developer doc" }
        "INFRA-TOOL"       { return "LEAVE: developer doc" }
        "INFRA-DIAGRAMS"   { return "LEAVE: internal spec, not a Quarto page" }
        "INFRA-CANON"      { return "LEAVE: canon README" }
        "VENV-SKIP"        { return "SKIP: virtual environment library file" }
        "WORKTREE-SKIP"    { return "SKIP: Claude worktree copy" }
        default            { return "REVIEW: uncategorized — check manually" }
    }
}

function Get-HasYamlHeader {
    param([string]$FullPath, [long]$Size)
    if ($Size -eq 0) { return $false }
    try {
        $first = Get-Content $FullPath -TotalCount 1 -ErrorAction Stop
        return ($first.Trim() -eq "---")
    } catch { return $false }
}

function Get-Priority {
    param([string]$Category)
    switch ($Category) {
        "SHELL"   { return 1 }
        "ORPHAN-MD" { return 2 }
        "LIVE-QMD"  { return 3 }
        default     { return 9 }
    }
}

Write-Host ""
Write-Host "UIAO Documentation Audit" -ForegroundColor Cyan
Write-Host "========================" -ForegroundColor Cyan
Write-Host "Scanning: $RepoRoot"
Write-Host ""

$allFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Include "*.md","*.qmd" -ErrorAction SilentlyContinue |
    Where-Object {
        $p = $_.FullName
        $skip = $false
        foreach ($ex in $ExcludeDirs) {
            if ($p -like "*\$ex\*") { $skip = $true; break }
        }
        -not $skip
    }

Write-Host "Found $($allFiles.Count) .md/.qmd files (excluding $($ExcludeDirs -join ', '))"
Write-Host ""

$results = foreach ($f in $allFiles) {
    $rel      = $f.FullName.Replace($RepoRoot + "\", "")
    $cat      = Get-Category -RelPath $rel -Size $f.Length -Ext $f.Extension
    $hasYaml  = Get-HasYamlHeader -FullPath $f.FullName -Size $f.Length
    $action   = Get-Action -Category $cat
    $priority = Get-Priority -Category $cat

    [PSCustomObject]@{
        Priority      = $priority
        Category      = $cat
        Extension     = $f.Extension
        SizeBytes     = $f.Length
        HasYamlHeader = $hasYaml
        LastModified  = $f.LastWriteTime.ToString("yyyy-MM-dd")
        RelativePath  = $rel
        Action        = $action
    }
}

$results | Sort-Object Priority, RelativePath |
    Export-Csv -Path $OutputCsv -NoTypeInformation -Encoding UTF8

Write-Host "SUMMARY BY CATEGORY" -ForegroundColor Yellow
Write-Host "-------------------"
$groups = $results | Group-Object Category | Sort-Object {
    switch ($_.Name) {
        "SHELL"        { 1 }; "ORPHAN-MD"    { 2 }; "LIVE-QMD"     { 3 }
        "UNCATEGORIZED"{ 4 }; "INFRA-GITHUB" { 5 }; "SRC-CODEDOC"  { 6 }
        "INFRA-TEST"   { 7 }; "INFRA-TOOL"   { 8 }; "DATA-IMAGEPROMPT" { 9 }
        "INFRA-DIAGRAMS"{ 10}; "INFRA-CANON" { 11}; "ARCHIVE"      { 12 }
        "VENV-SKIP"    { 13}; "WORKTREE-SKIP"{ 14}; default        { 99 }
    }
}
foreach ($g in $groups) {
    $color = switch ($g.Name) {
        "SHELL"     { "Red"    }
        "ORPHAN-MD" { "Yellow" }
        "LIVE-QMD"  { "Green"  }
        "ARCHIVE"   { "Gray"   }
        default     { "White"  }
    }
    Write-Host ("  {0,-22} {1,4} files" -f $g.Name, $g.Count) -ForegroundColor $color
}

Write-Host ""
Write-Host "SHELL PAGES (0-byte — need decision)" -ForegroundColor Red
Write-Host "--------------------------------------"
$shells = $results | Where-Object { $_.Category -eq "SHELL" } | Sort-Object RelativePath
if ($shells) {
    foreach ($s in $shells) { Write-Host "  $($s.RelativePath)" -ForegroundColor Red }
} else { Write-Host "  None found." -ForegroundColor Green }

Write-Host ""
Write-Host "ORPHANED .md IN docs/ (have content, wrong extension)" -ForegroundColor Yellow
Write-Host "-------------------------------------------------------"
$orphans = $results | Where-Object { $_.Category -eq "ORPHAN-MD" } | Sort-Object RelativePath
if ($orphans) {
    foreach ($o in $orphans) {
        Write-Host ("  {0,-70} {1,6} bytes" -f $o.RelativePath, $o.SizeBytes) -ForegroundColor Yellow
    }
} else { Write-Host "  None found." -ForegroundColor Green }

Write-Host ""
Write-Host "LIVE .qmd PAGES MISSING YAML HEADER" -ForegroundColor Magenta
Write-Host "-------------------------------------"
$noYaml = $results | Where-Object { $_.Category -eq "LIVE-QMD" -and $_.HasYamlHeader -eq $false } |
    Sort-Object RelativePath
if ($noYaml) {
    foreach ($n in $noYaml) { Write-Host "  $($n.RelativePath)" -ForegroundColor Magenta }
} else { Write-Host "  All live pages have YAML headers." -ForegroundColor Green }

Write-Host ""
Write-Host "UNCATEGORIZED (review manually)" -ForegroundColor Cyan
$unc = $results | Where-Object { $_.Category -eq "UNCATEGORIZED" } | Sort-Object RelativePath
if ($unc) {
    foreach ($u in $unc) { Write-Host "  $($u.RelativePath)" -ForegroundColor Cyan }
} else { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "Output CSV: $OutputCsv" -ForegroundColor Cyan
Write-Host "Open in Excel to filter/sort by Category and Priority." -ForegroundColor Gray
Write-Host ""
