<#
.SYNOPSIS
    Audit the whole monorepo for lingering references to old paths
    (core/canon, core/schemas, core/rules, core/ksi) after the
    canon/reorganize-to-src-uiao migration.

.DESCRIPTION
    Read-only. Scans every text file under the repo (skipping .git,
    build artifacts, the migration scripts themselves, and the moved
    trees) and prints every match with filename, line number, and the
    matching line. Also prints a summary count per pattern.

    Does NOT modify anything. Review the output, then apply targeted
    fixes for each case.

    The migration scripts (scripts/reorganize_monorepo.py,
    scripts/fix_paths_after_reorg.py) intentionally contain references
    to core/... as migration inputs and are excluded from the scan.

.EXAMPLE
    .\scripts\audit_old_paths.ps1

.EXAMPLE
    .\scripts\audit_old_paths.ps1 | Tee-Object audit.txt

.NOTES
    Run from the monorepo root (the monorepo root).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Patterns we care about — any reference to the old canon/schemas/rules/ksi
# roots that should probably be src/uiao/*.
$Patterns = @(
    'core/canon/',
    'core/schemas/',
    'core/rules/',
    'core/ksi/'
)

# Directories we never scan.
$ExcludeDirs = @(
    '.git',
    '.venv',
    'node_modules',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    '_site',     # Quarto render output
    '_freeze',   # Quarto cache
    'htmlcov',
    'dist',
    'build'
)

# Individual files we never scan (migration scripts + build artifacts).
$ExcludeFiles = @(
    'scripts/reorganize_monorepo.py',
    'scripts/fix_paths_after_reorg.py',
    'scripts/audit_old_paths.ps1'
)

# File extensions worth scanning. Anything else is skipped as likely binary.
$IncludeExtensions = @(
    '.py','.ps1','.psm1','.psd1','.sh',
    '.yaml','.yml','.json','.toml','.ini','.cfg',
    '.md','.qmd','.rst','.txt','.tex',
    '.html','.htm','.xml','.svg',
    '.js','.ts','.mjs','.cjs'
)

$repoRoot = (Resolve-Path '.').Path
$ExcludeFilesFull = $ExcludeFiles | ForEach-Object { Join-Path $repoRoot $_ }

function Test-ShouldScan {
    param([string]$Path)
    foreach ($dir in $ExcludeDirs) {
        if ($Path -match "[\\/]$([regex]::Escape($dir))[\\/]") { return $false }
        if ($Path -match "[\\/]$([regex]::Escape($dir))$") { return $false }
    }
    foreach ($f in $ExcludeFilesFull) {
        if ($Path -eq $f) { return $false }
    }
    $ext = [IO.Path]::GetExtension($Path).ToLower()
    return $IncludeExtensions -contains $ext
}

Write-Host "=== Auditing $repoRoot ===" -ForegroundColor Cyan
Write-Host "Patterns: $($Patterns -join ', ')"
Write-Host "Excluded dirs: $($ExcludeDirs -join ', ')"
Write-Host ""

$patternCounts = @{}
foreach ($p in $Patterns) { $patternCounts[$p] = 0 }
$fileHits = @{}
$totalMatches = 0

$allFiles = Get-ChildItem -Path $repoRoot -Recurse -File -Force |
    Where-Object { Test-ShouldScan $_.FullName }

foreach ($file in $allFiles) {
    try {
        $lines = Get-Content -LiteralPath $file.FullName -ErrorAction Stop
    } catch {
        continue  # unreadable / locked; move on
    }
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        foreach ($pattern in $Patterns) {
            if ($line -like "*$pattern*") {
                $rel = $file.FullName.Substring($repoRoot.Length).TrimStart('\','/')
                $lineNum = $i + 1
                $snippet = $line.Trim()
                if ($snippet.Length -gt 120) { $snippet = $snippet.Substring(0, 117) + '...' }
                Write-Host ("{0}:{1}: {2}" -f $rel, $lineNum, $snippet) -ForegroundColor Yellow
                $patternCounts[$pattern]++
                if (-not $fileHits.ContainsKey($rel)) { $fileHits[$rel] = 0 }
                $fileHits[$rel]++
                $totalMatches++
                break  # one hit per line is enough
            }
        }
    }
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Total matches: $totalMatches"
Write-Host ""
Write-Host "Per-pattern:"
foreach ($p in $Patterns) {
    Write-Host ("  {0,-18} {1,6} hits" -f $p, $patternCounts[$p])
}
Write-Host ""
Write-Host "Per-file (top 20):"
$fileHits.GetEnumerator() |
    Sort-Object -Property Value -Descending |
    Select-Object -First 20 |
    ForEach-Object { Write-Host ("  {0,6}  {1}" -f $_.Value, $_.Key) }

if ($totalMatches -eq 0) {
    Write-Host ""
    Write-Host "Clean — no stale core/ references found." -ForegroundColor Green
    exit 0
} else {
    Write-Host ""
    Write-Host "Review the hits above and apply targeted fixes." -ForegroundColor Yellow
    exit 1
}
