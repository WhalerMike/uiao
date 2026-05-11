# UIAO-DocAudit-v3.ps1
# Added from v2:
#   - STAGING-INBOX category for inbox\ folder
#   - PHASE2-SPEC category for phase2\ folder
#   - INFRA-SCRIPTS category for scripts\
#   - Better handling of docs\governance\, docs\narrative\, docs\findings\, docs\reports\

param(
    [string]$RepoRoot  = "C:\Users\whale\git\uiao",
    [string]$OutputCsv = "C:\Users\whale\git\uiao\doc-audit-v3.csv"
)

$ExcludeDirWildcards = @('*\.venv\*','*\node_modules\*','*\.claude\*','*\_site\*','*\.pytest_cache\*')
$InfraFileNames = @('README.md','CHANGELOG.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md',
    'SECURITY.md','SUPPORT.md','AGENTS.md','CLAUDE.md','RELEASE_NOTES.md',
    'PULL_REQUEST_TEMPLATE.md','LICENSE.md','template.md','best_practices.md')

function Get-Category {
    param([string]$RelPath, [long]$Size, [string]$Ext)

    if ($Size -eq 0)                   { return "SHELL" }
    if ($Size -ge 1 -and $Size -le 100){ return "MICRO-SHELL" }

    if ($RelPath -like "ai-hallucination-archive\*") { return "ARCHIVE" }
    if ($RelPath -like "*IMAGE-PROMPTS*")            { return "DATA-IMAGEPROMPT" }
    if ($RelPath -like ".github\*")                  { return "INFRA-GITHUB" }
    if ($RelPath -like "docs\.github\*")             { return "INFRA-GITHUB" }
    if ($RelPath -like "inbox\*")                    { return "STAGING-INBOX" }
    if ($RelPath -like "phase2\*")                   { return "PHASE2-SPEC" }
    if ($RelPath -like "scripts\*")                  { return "INFRA-SCRIPTS" }
    if ($RelPath -like "src\*")                      { return "SRC-CODEDOC" }
    if ($RelPath -like "tests\*")                    { return "INFRA-TEST" }
    if ($RelPath -like "tools\*")                    { return "INFRA-TOOL" }
    if ($RelPath -like "diagrams\*")                 { return "INFRA-DIAGRAMS" }
    if ($RelPath -like "canon\*")                    { return "INFRA-CANON" }

    $leaf = Split-Path $RelPath -Leaf
    if ($InfraFileNames -contains $leaf -and $RelPath -notlike "*\*\*") { return "INFRA-GITHUB" }

    if ($Ext -eq ".qmd" -and $RelPath -like "docs\docs\*") { return "LIVE-QMD" }
    if ($Ext -eq ".md"  -and $RelPath -like "docs\docs\*") { return "LEGACY-DOCS" }
    if ($Ext -eq ".qmd" -and $RelPath -like "docs\*")      { return "LIVE-QMD" }
    if ($Ext -eq ".md"  -and $RelPath -like "docs\*")      { return "ORPHAN-MD" }

    if ($InfraFileNames -contains $leaf) { return "INFRA-GITHUB" }
    if ($RelPath -notlike "*\*")         { return "INFRA-GITHUB" }

    return "UNCATEGORIZED"
}

function Get-Action {
    param([string]$Category, [string]$RelPath)
    switch ($Category) {
        "SHELL"         { return "DECIDE: write content, promote to shell .qmd, or delete" }
        "MICRO-SHELL"   { return "DELETE: 47-byte placeholder with no content — or write content first" }
        "ORPHAN-MD"     {
            if ($RelPath -like "docs\findings\*")   { return "CONVERT NOW: findings nav is live, users see broken index" }
            if ($RelPath -like "docs\governance\*") { return "CONVERT: governance doc, rename to .qmd + YAML header" }
            if ($RelPath -like "docs\narrative\*")  { return "CONVERT: narrative layer doc" }
            if ($RelPath -like "docs\reports\*")    { return "EVALUATE: audit report — publish or internal?" }
            return "CONVERT: rename to .qmd, add YAML header, add to nav/index link"
        }
        "LEGACY-DOCS"   {
            if ($RelPath -like "*gcc-boundary*")             { return "PRIORITY-CONVERT: key differentiator content" }
            if ($RelPath -like "*cli-reference*")            { return "CONVERT-OR-VERIFY: check if superseded" }
            if ($RelPath -like "*adapter-authoring-tutorial*"){ return "VERIFY: may be superseded by academy version" }
            if ($RelPath -like "*session-logs\*")            { return "LEAVE: development history, not site content" }
            if ($RelPath -like "*uiao-substrate-roadmap*")   { return "EVALUATE: 72KB roadmap — publish?" }
            return "EVALUATE: check if superseded by .qmd equivalent"
        }
        "STAGING-INBOX" { return "LEAVE: staging area — promote when ready, do not convert in place" }
        "PHASE2-SPEC"   {
            if ($RelPath -like "*_legacy\*") { return "REVIEW: superseded by phase2\domains\ ? Archive if so" }
            return "LEAVE: active specification — not site content yet"
        }
        "LIVE-QMD"      { return "OK: verify YAML header and nav entry" }
        "ARCHIVE"       { return "LEAVE: frozen history" }
        "DATA-IMAGEPROMPT" { return "LEAVE: NanoBanana pipeline input" }
        "INFRA-GITHUB"  { return "LEAVE: must stay .md" }
        "INFRA-SCRIPTS" { return "LEAVE: script documentation" }
        "SRC-CODEDOC"   { return "LEAVE: code-tree doc" }
        default         { return "REVIEW: uncategorized" }
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
    param([string]$Category, [string]$RelPath)
    if ($Category -eq "ORPHAN-MD" -and $RelPath -like "docs\findings\*") { return 1 }
    switch ($Category) {
        "SHELL"         { return 2 }
        "MICRO-SHELL"   { return 3 }
        "ORPHAN-MD"     { return 3 }
        "LEGACY-DOCS"   { return 4 }
        "LIVE-QMD"      { return 5 }
        "STAGING-INBOX" { return 8 }
        "PHASE2-SPEC"   { return 8 }
        "UNCATEGORIZED" { return 6 }
        default         { return 9 }
    }
}

Write-Host ""
Write-Host "UIAO Documentation Audit v3" -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan
Write-Host "Root:   $RepoRoot"
Write-Host "Output: $OutputCsv"
Write-Host ""

$allFiles = Get-ChildItem -Path $RepoRoot -Recurse -File -Include "*.md","*.qmd" -ErrorAction SilentlyContinue |
    Where-Object {
        $p = $_.FullName
        $skip = $false
        foreach ($wc in $ExcludeDirWildcards) {
            if ($p -like $wc) { $skip = $true; break }
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
    $priority = Get-Priority -Category $cat -RelPath $rel

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

$order = @("SHELL","MICRO-SHELL","ORPHAN-MD","LEGACY-DOCS","LIVE-QMD","STAGING-INBOX",
           "PHASE2-SPEC","UNCATEGORIZED","INFRA-GITHUB","SRC-CODEDOC","INFRA-TEST",
           "INFRA-TOOL","INFRA-DIAGRAMS","INFRA-CANON","INFRA-SCRIPTS","DATA-IMAGEPROMPT","ARCHIVE")

Write-Host "CATEGORY SUMMARY" -ForegroundColor Yellow
Write-Host "----------------"
foreach ($cat in $order) {
    $count = ($results | Where-Object { $_.Category -eq $cat }).Count
    if ($count -gt 0) {
        $color = switch ($cat) {
            {$_ -in "SHELL","MICRO-SHELL"}          { "Red"    }
            {$_ -in "ORPHAN-MD","LEGACY-DOCS"}       { "Yellow" }
            "LIVE-QMD"                               { "Green"  }
            {$_ -in "STAGING-INBOX","PHASE2-SPEC"}   { "Cyan"   }
            "UNCATEGORIZED"                          { "Magenta"}
            default                                  { "Gray"   }
        }
        Write-Host ("  {0,-22}  {1,4} files" -f $cat, $count) -ForegroundColor $color
    }
}

Write-Host ""
Write-Host "PRIORITY 1 — CONVERT NOW (findings nav is live but broken)" -ForegroundColor Red
$p1 = $results | Where-Object { $_.Priority -eq 1 } | Sort-Object RelativePath
$p1 | ForEach-Object { Write-Host ("  {0,-70}  {1,7} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor Red }

Write-Host ""
Write-Host "SHELL PAGES (0 bytes)" -ForegroundColor Red
$results | Where-Object { $_.Category -eq "SHELL" } | Sort-Object RelativePath |
    ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Red }

Write-Host ""
Write-Host "MICRO-SHELL PAGES (1-100 bytes) — recommend DELETE" -ForegroundColor DarkRed
$results | Where-Object { $_.Category -eq "MICRO-SHELL" } | Sort-Object RelativePath |
    ForEach-Object { Write-Host ("  {0,-80}  {1} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor DarkRed }

Write-Host ""
Write-Host "ORPHAN-MD (not findings)" -ForegroundColor Yellow
$results | Where-Object { $_.Category -eq "ORPHAN-MD" -and $_.Priority -ne 1 } | Sort-Object RelativePath |
    ForEach-Object { Write-Host ("  {0,-80}  {1,7} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor Yellow }

Write-Host ""
Write-Host "LEGACY docs\docs\ — HIGH VALUE (gcc-boundary in RED)" -ForegroundColor Yellow
$results | Where-Object { $_.Category -eq "LEGACY-DOCS" } | Sort-Object SizeBytes -Descending |
    Select-Object -First 20 |
    ForEach-Object {
        $color = if ($_.RelativePath -like "*gcc-boundary*" -or $_.SizeBytes -gt 10000) { "Red" } else { "Yellow" }
        Write-Host ("  {0,-80}  {1,7} bytes" -f $_.RelativePath, $_.SizeBytes) -ForegroundColor $color
    }
Write-Host "  (top 20 by size shown — see CSV for complete list)"

Write-Host ""
Write-Host "LIVE .qmd MISSING YAML HEADER" -ForegroundColor Magenta
$results | Where-Object { $_.Category -eq "LIVE-QMD" -and $_.HasYamlHeader -eq $false } | Sort-Object RelativePath |
    ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Magenta }

Write-Host ""
Write-Host "UNCATEGORIZED (still remaining)" -ForegroundColor Cyan
$results | Where-Object { $_.Category -eq "UNCATEGORIZED" } | Sort-Object RelativePath |
    ForEach-Object { Write-Host "  $($_.RelativePath)" -ForegroundColor Cyan }

Write-Host ""
Write-Host "Done. CSV: $OutputCsv" -ForegroundColor Cyan
Write-Host "Priority 1 = convert findings now. Priority 2 = shells. Priority 3 = orphans + micro-shells." -ForegroundColor Gray
Write-Host ""
