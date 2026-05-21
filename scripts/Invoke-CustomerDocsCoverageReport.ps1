<#
.SYNOPSIS
    Emit a per-.qmd coverage CSV across customer-documents/ for image-need triage.

.DESCRIPTION
    Pass 1 of the customer-docs image-coverage assessment. For every .qmd
    under docs/customer-documents/, writes one row to CSV with structural
    signals useful for identifying under-imaged documents:

      Section       Top-level folder under customer-documents/ (or '(root)')
      File          Section-relative path with forward slashes
      Title         Frontmatter `title` (if present)
      Subtitle      Frontmatter `subtitle` (if present)
      DocType       Frontmatter `doc-type` (if present)
      Status        Frontmatter `status` (if present)
      Words         Body word count (excludes YAML frontmatter and fenced
                    code blocks; markdown noise stripped before counting)
      H2s           Count of `^## ` headings
      H3s           Count of `^### ` headings
      CodeBlocks    Count of fenced ``` blocks
      Images        Count of `![](*.png)` references in body
      WordsPerImg   Words / Images (blank if Images=0)

    Read-only. Writes a single CSV. No console output by default — the file
    is the artifact. Pass -Verbose for a one-line completion summary.

    Build directories (_freeze, _site, .quarto, node_modules, __pycache__)
    are excluded from the walk.

.PARAMETER OutPath
    Override the CSV output path. Defaults to
    inbox/.qmd-image-coverage.csv at the repo root.

.PARAMETER Root
    Override the customer-documents root.

.EXAMPLE
    pwsh scripts/Invoke-CustomerDocsCoverageReport.ps1
    Writes the CSV silently to inbox/.qmd-image-coverage.csv.

.EXAMPLE
    pwsh scripts/Invoke-CustomerDocsCoverageReport.ps1 -Verbose
    Same, plus a one-line "wrote N rows to <path>" summary.

.NOTES
    Workflow:
      1. Run this script.
      2. Open the CSV in Excel.
      3. Sort by WordsPerImg descending (large = under-imaged candidate)
         and by Images ascending (zero-image docs surface to the top).
      4. Pick 15-25 outliers worth deeper assessment.
      5. Pass 2 (next): content-based assessment of just those outliers.

    Exit codes:
      0   CSV written successfully
      2   precondition failure (root missing, output dir not writable)
#>
[CmdletBinding()]
param(
    [string]$OutPath,
    [string]$Root
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
if (-not $Root) {
    $Root = Join-Path $repoRoot 'docs\customer-documents'
}
if (-not (Test-Path $Root)) {
    Write-Error "Root not found: $Root"
    exit 2
}
if (-not $OutPath) {
    $OutPath = Join-Path $repoRoot 'inbox\.qmd-image-coverage.csv'
}
$outDir = Split-Path -Parent $OutPath
if (-not (Test-Path $outDir)) {
    Write-Error "Output directory does not exist: $outDir"
    exit 2
}

$excludeDirs = @('_freeze', '_site', '.quarto', 'node_modules', '__pycache__')

function Test-PathInExcludedDir {
    param([string]$AbsPath, [string]$Base, [string[]]$Excluded)
    $rel = $AbsPath.Substring($Base.Length).TrimStart('\','/')
    $sep = @([IO.Path]::DirectorySeparatorChar, [IO.Path]::AltDirectorySeparatorChar)
    foreach ($seg in $rel.Split($sep)) {
        if ($Excluded -contains $seg) { return $true }
    }
    return $false
}

# Parse YAML frontmatter into a hashtable. Single-line key:value only —
# nested keys and block scalars are tolerated but not captured.
function Get-Frontmatter {
    param([string]$Text)
    $out = @{}
    if (-not $Text.StartsWith('---')) { return $out }
    $idx = $Text.IndexOf("`n---", 3)
    if ($idx -lt 0) { return $out }
    $body = $Text.Substring(3, $idx - 3)
    foreach ($line in $body -split "`r?`n") {
        $trimmed = $line.TrimEnd()
        if (-not $trimmed) { continue }
        if ($trimmed.StartsWith('#')) { continue }
        if ($trimmed.StartsWith(' ')) { continue }
        if ($trimmed -notmatch ':') { continue }
        $key, $rest = $trimmed -split ':', 2
        $key = $key.Trim()
        $value = $rest.Trim()
        if ($value.Length -ge 2 -and $value[0] -eq '"' -and $value[-1] -eq '"') {
            $value = $value.Substring(1, $value.Length - 2)
        }
        $out[$key] = $value
    }
    return $out
}

# Body metrics: word count, headings, code blocks, image refs. Frontmatter
# and fenced code blocks are stripped before word counting so prose density
# isn't inflated by long code listings.
function Get-BodyMetrics {
    param([string]$Text)

    # Strip frontmatter.
    $body = $Text
    if ($Text.StartsWith('---')) {
        $idx = $Text.IndexOf("`n---", 3)
        if ($idx -ge 0) { $body = $Text.Substring($idx + 4) }
    }

    # Count and strip fenced code blocks.
    $codeBlockRx = [regex]'(?ms)^```.*?^```\s*$'
    $codeBlockCount = $codeBlockRx.Matches($body).Count
    $body = $codeBlockRx.Replace($body, '')

    # Headings (after code-block strip so commented headings in code don't count).
    $h2 = ([regex]::Matches($body, '(?m)^## [^#]')).Count
    $h3 = ([regex]::Matches($body, '(?m)^### [^#]')).Count

    # Image refs.
    $imgs = ([regex]::Matches($body, '!\[[^\]]*\]\([^)]+\.png\)')).Count

    # Rough prose word count — comparative signal, not exact.
    $plain = $body
    $plain = $plain -replace '`[^`]*`', ' '                  # inline code
    $plain = $plain -replace '!\[[^\]]*\]\([^)]*\)', ' '     # images: drop
    $plain = $plain -replace '\[([^\]]*)\]\([^)]*\)', '$1'   # links: keep label
    $plain = $plain -replace '<[^>]+>', ' '                  # HTML tags
    $plain = $plain -replace '\s+', ' '
    $words = @($plain.Trim() -split ' ' | Where-Object { $_ -match '\w' }).Count

    return [pscustomobject]@{
        Words      = $words
        H2s        = $h2
        H3s        = $h3
        CodeBlocks = $codeBlockCount
        Images     = $imgs
    }
}

# Walk the tree.
$qmds = @(Get-ChildItem -Path $Root -Filter '*.qmd' -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { -not (Test-PathInExcludedDir -AbsPath $_.FullName -Base $Root -Excluded $excludeDirs) })

$rows = @(foreach ($q in $qmds) {
    $text = Get-Content -Path $q.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if (-not $text) { continue }

    $fm = Get-Frontmatter -Text $text
    $m  = Get-BodyMetrics  -Text $text

    $rel = $q.FullName.Substring($Root.Length).TrimStart('\','/').Replace('\','/')
    $section = if ($rel -match '/') { ($rel -split '/')[0] } else { '(root)' }

    $wpi = if ($m.Images -gt 0) { [math]::Round($m.Words / $m.Images, 1) } else { $null }

    [pscustomobject]@{
        Section     = $section
        File        = $rel
        Title       = if ($fm.ContainsKey('title'))    { $fm['title'] }    else { '' }
        Subtitle    = if ($fm.ContainsKey('subtitle')) { $fm['subtitle'] } else { '' }
        DocType     = if ($fm.ContainsKey('doc-type')) { $fm['doc-type'] } else { '' }
        Status      = if ($fm.ContainsKey('status'))   { $fm['status'] }   else { '' }
        Words       = $m.Words
        H2s         = $m.H2s
        H3s         = $m.H3s
        CodeBlocks  = $m.CodeBlocks
        Images      = $m.Images
        WordsPerImg = $wpi
    }
})

$rows = @($rows | Sort-Object Section, File)
$rows | Export-Csv -Path $OutPath -NoTypeInformation -Encoding UTF8

Write-Verbose ("Wrote {0} rows to {1}" -f $rows.Count, $OutPath)

exit 0
