# UIAO-DocAudit-v2.ps1
# Fixed version — three bugs corrected from v1:
#   1. Now excludes docs\_site\ (Quarto build output — was producing false positives)
#   2. Now correctly identifies docs\.github\ as INFRA-GITHUB (not ORPHAN-MD)
#   3. Added MICRO-SHELL category for 1-100 byte files (47-byte governance placeholders)
#   4. Added LEGACY-DOCS category for docs\docs\ files awaiting migration decision
#
# Usage:
#   .\UIAO-DocAudit-v2.ps1
#   .\UIAO-DocAudit-v2.ps1 -RepoRoot "C:\Users\whale\git\uiao" -OutputCsv "C:\temp\doc-audit-v2.csv"

param(
    [string]$RepoRoot  = "C:\Users\whale\git\uiao",
    [string]$OutputCsv = "C:\Users\whale\git\uiao\doc-audit-v2.csv"
)

# Directories to skip entirely (matched anywhere in the path)
$ExcludeDirPatterns = @(
    '\\.venv\\',
    '\\node_modules\\',
    '\\.claude\\',
    '\\_site\\',         # FIX 1: Quarto build output — was causing false positives
    '\\.pytest_cache\\'
)

$InfraFileNames = @(
    'README.md','CHANGELOG.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md',
    'SECURITY.md','SUPPORT.md','AGENTS.md','CLAUDE.md','RELEASE_NOTES.md',
    'PULL_REQUEST_TEMPLATE.md','LICENSE.md','template.md','best_practices.md'
)

function Get-Category {
    param([string]$RelPath, [long]$Size, [string]$Ext)

    # --- Size-based first ---
    if ($Size -eq 0)            { return "SHELL" }
    if ($Size -ge 1 -and $Size -le 100) { return "MICRO-SHELL" }

    # --- Archive ---
    if ($RelPath -like "ai-hallucination-archive\*") { return "ARCHIVE" }

    # --- Image prompts (NanoBanana pipeline data) ---
    if ($RelPath -like "*IMAGE-PROMPTS*") { return "DATA-IMAGEPROMPT" }

    # --- GitHub and docs/.github templates ---
    # FIX 2: Check both .github\ at root AND docs\.github\ inside the docs tree
    if ($RelPath -like ".github\*")      { return "INFRA-GITHUB" }
    if ($RelPath -like "docs\.github\*") { return "INFRA-GITHUB" }

    # --- Source code co-located docs ---
    if ($RelPath -like "src\*")     { return "SRC-CODEDOC" }
    if ($RelPath -like "tests\*")   { return "INFRA-TEST" }
    if ($RelPath -like "tools\*")   { return "INFRA-TOOL" }
    if ($RelPath -like "diagrams\*"){ return "INFRA-DIAGRAMS" }
    if ($RelPath -like "canon\*")   { return "INFRA-CANON" }

    # --- Root-level infra files ---
    $leaf = Split-Path $RelPath -Leaf
    if ($InfraFileNames -contains $leaf -and $RelPath -notlike "*\*\*") {
        return "INFRA-GITHUB"
    }

    # --- docs\docs\ legacy structure (partially migrated, needs evaluation) ---
    # FIX 4: This folder is active but mixed — .qmd files render, .md files are orphaned
    if ($Ext -eq ".qmd" -and $RelPath -like "docs\docs\*") { return "LIVE-QMD" }
    if ($Ext -eq ".md"  -and $RelPath -like "docs\docs\*") { return "LEGACY-DOCS" }

    # --- Main docs tree ---
    if ($Ext -eq ".qmd" -and $RelPath -like "docs\*") { return "LIVE-QMD" }
    if ($Ext -eq ".md"  -and $RelPath -like "docs\*") { return "ORPHAN-MD" }

    # --- Root files not already matched ---
    if ($InfraFileNames -contains $leaf) { return "INFRA-GITHUB" }
    if ($RelPath -notlike "*\*")         { return "INFRA-GITHUB" }

    return "UNCATEGORIZED"
}

function Get-Action {
    param([string]$Category, [string]$RelPath)
    switch ($Category) {
        "SHELL"       { return "DECIDE: write content, promote to shell .qmd, or delete" }
        "MICRO-SHELL" { return "DECIDE: probably delete (47-byte placeholder) or write content and convert to .qmd" }
        "ORPHAN-MD"   { return "CONVERT: rename to .qmd, add YAML header, add to nav/index link" }
        "LEGACY-DOCS" {
            if ($RelPath -like "*gcc-boundary*") { return "PRIORITY-CONVERT: high-value content, rename to .qmd, add to site nav" }
            if ($RelPath -like "*cli-reference*") { return "CONVERT-OR-VERIFY: check if superseded by newer content" }
            if ($RelPath -like "*adapter-authoring-tutorial*") { return "VERIFY: may be superseded by docs\academy version" }
            return "EVALUATE: check if superseded by .qmd equivalent in academy/ or customer-documents/"
        }
        "LIVE-QMD"         { return "OK: verify YAML header present and nav entry exists" }
        "ARCHIVE"          { return "LEAVE: frozen history — do not edit" }
        "DATA-IMAGEPROMPT" { return "LEAVE: NanoBanana pipeline input, not a web page" }
        "INFRA-GITHUB"     { return "LEAVE: must stay .md (GitHub or docs template requirement)" }
        "SRC-CODEDOC"      { return "LEAVE: code-tree doc, not a Quarto page" }
        "INFRA-TEST"       { return "LEAVE: developer doc" }
        "INFRA-TOOL"       { return "LEAVE: developer doc" }
        "INFRA-DIAGRAMS"   { return "LEAVE: internal spec, not a Quarto page" }
        "INFRA-CANON"      { return "LEAVE: canon README" }
        default            { return "REVIEW: uncategorized — check manually" }
    }
}

function Get-HasYamlHeader {
    param([string]$FullPath, [long]$Size)
    if ($Size -lt 3) { return $false }
    try {
        $first = Get-Content $FullPath -TotalCount 1 -ErrorAction Stop
        return ($first.Trim() -eq "---")
    } catch { return $false }
}

function Get-Priority {
    param([string]$Category)
    switch ($Category) {
        "SHELL"        { return 1 }
        "MICRO-SHELL"  { return 2 }
        "ORPHAN-MD"    { return 3 }
        "LEGACY-DOCS"  { return 4 }
        "LIVE-QMD"     { return 5 }
        "UNCATEGORIZED"{ return 6 }
        default        { return 9 }
    }
}

# --- Scan ---
Write-Host ""
Write-Host "UIAO Documentation Audit v2" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Root:    $RepoRoot"
Write-Host "Output:  $OutputCsv"
Write-Host ""

$allFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Include "*.md","*.qmd" -ErrorAction SilentlyContinue |
    Where-Object {
        $p = $_.FullName
        $skip = $false
        foreach ($pat in $ExcludeDirPatterns) {
            if ($p -match [regex]::Escape($pat).Replace('\\\\','\\')) { $skip = $true; break }
            if ($p -like "*$($pat.Replace('\\','\\'))*") { $skip = $true; break }
        }
        -not $skip
    }

Write-Host "Found $($allFiles.Count) .md/.qmd source files"
Write-Host ""

$results = foreach ($f in $allFiles) {
    $rel      = $f.FullName.Replace($RepoRoot + "\", "")
    $cat      = Get-Category -RelPath $rel -Size $f.Length -Ext $f.Extension
    $hasYaml  = Get-HasYamlHeader -FullPath $f.FullName -Size $f.Length
    $action   = Get-Action -Category $cat -RelPath $rel
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

# --- Summary ---
Write-Host "CATEGORY SUMMARY" -ForegroundColor Yellow
Write-Host "----------------"
$categoryOrder = @("SHELL","MICRO-SHELL","ORPHAN-MD","LEGACY-DOCS","LIVE-QMD","UNCATEGORIZED",
                   "INFRA-GITHUB","SRC-CODEDOC","INFRA-TEST","INFRA-TOOL","INFRA-DIAGRAMS",
                   "INFRA-CANON","DATA-IMAGEPROMPT","ARCHIVE")
foreach ($cat in $categoryOrder) {
    $count = ($results | Where-Object { $_.Category -eq $cat }).Count
    if ($count -gt 0) {
        $color = switch ($cat) {
            "SHELL"        { "Red"     }
            "MICRO-SHELL"  { "Red"     }
            "ORPHAN-MD"    { "Yellow"  }
            "LEGACY-DOCS"  { "Yellow"  }
            "LIVE-QMD"     { "Green"   }
            "UNCATEGORIZED"{ "Magenta" }
            default        { "Gray"    }
        }
        Write-Host ("  {0,-22}  {1,4} files" -f $cat, $count) -ForegroundColor $color
    }
}
$unc = $results | Where-Object { $_.Category -notin $categoryOrder }
if ($unc) {
    Write-Host ("  {0,-22}  {1,4} files" -f "OTHER", $unc.Count) -ForegroundColor Magenta
}

# --- Drilldowns ---
Write-Host ""
Write-Host "SHELL PAGES (0 bytes)" -ForegroundColor Red
Write-Host "---------------------"
$shells = $results | Where-Object { $_.Category -eq "SHELL" } | Sort-Object RelativePath
if ($shells) { $shells | ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Red } }
else         { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "MICRO-SHELL PAGES (1-100 bytes)" -ForegroundColor Red
Write-Host "--------------------------------"
$micro = $results | Where-Object { $_.Category -eq "MICRO-SHELL" } | Sort-Object RelativePath
if ($micro) { $micro | ForEach-Object { Write-Host ("  {0,-80} {1} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor DarkRed } }
else        { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "ORPHANED .md IN docs/ (not in docs\docs\)" -ForegroundColor Yellow
Write-Host "------------------------------------------"
$orphans = $results | Where-Object { $_.Category -eq "ORPHAN-MD" } | Sort-Object RelativePath
if ($orphans) { $orphans | ForEach-Object { Write-Host ("  {0,-80} {1,7} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor Yellow } }
else          { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "LEGACY docs\docs\ FILES (evaluate each)" -ForegroundColor Yellow
Write-Host "----------------------------------------"
$legacy = $results | Where-Object { $_.Category -eq "LEGACY-DOCS" } | Sort-Object RelativePath
if ($legacy) {
    $legacy | ForEach-Object {
        $color = if ($_.RelativePath -like "*gcc-boundary*") { "Red" } else { "Yellow" }
        Write-Host ("  {0,-80} {1,7} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor $color
    }
    Write-Host ""
    Write-Host "  GCC boundary files flagged RED — high-priority unrendered content." -ForegroundColor Red
}
else { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "LIVE .qmd MISSING YAML HEADER" -ForegroundColor Magenta
Write-Host "------------------------------"
$noYaml = $results | Where-Object { $_.Category -eq "LIVE-QMD" -and $_.HasYamlHeader -eq $false } | Sort-Object RelativePath
if ($noYaml) { $noYaml | ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Magenta } }
else         { Write-Host "  All live pages have YAML headers." -ForegroundColor Green }

Write-Host ""
Write-Host "UNCATEGORIZED (review manually)" -ForegroundColor Cyan
$unc2 = $results | Where-Object { $_.Category -eq "UNCATEGORIZED" } | Sort-Object RelativePath
if ($unc2) { $unc2 | ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Cyan } }
else       { Write-Host "  None." -ForegroundColor Green }

Write-Host ""
Write-Host "Done. CSV written to: $OutputCsv" -ForegroundColor Cyan
Write-Host "Open in Excel, filter by Priority column (1=most urgent), sort by RelativePath within each priority." -ForegroundColor Gray
Write-Host ""
