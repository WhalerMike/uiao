<#
.SYNOPSIS
    UIAO Claude Integration - Full Two-Way Sync
.DESCRIPTION
    Deploys remaining Claude Code integration files to uiao (16 files)
    and uiao-docs (27 files) using two atomic commits to main.
    Expects companion payload files in the same directory:
      - uiao-remaining.b64  (base64-encoded zip of uiao files)
      - uiao-docs-remaining.b64  (base64-encoded zip of uiao-docs files)
.PARAMETER WorkDir
    Temporary working directory. Default: $env:TEMP\uiao-sync-<timestamp>
.EXAMPLE
    .\Sync-ClaudeIntegration.ps1
    .\Sync-ClaudeIntegration.ps1 -WorkDir "C:\temp\uiao-sync"
#>
[CmdletBinding()]
param(
    [string]$WorkDir = (Join-Path $env:TEMP "uiao-sync-$(Get-Date -Format 'yyyyMMdd-HHmmss')")
)

$ErrorActionPreference = 'Stop'
$ScriptDir = $PSScriptRoot

# Banner
Write-Host ""
Write-Host "=== UIAO Claude Integration - Full Two-Way Sync ===" -ForegroundColor Cyan
Write-Host "    16 files -> uiao  |  27 files -> uiao-docs" -ForegroundColor Cyan
Write-Host ""

# Preflight
Write-Host "[PREFLIGHT] Checking git..." -ForegroundColor Yellow
try { $null = & git --version 2>&1 } catch {
    Write-Error "git is not installed or not in PATH."
    return
}

$coreB64 = Join-Path $ScriptDir "uiao-remaining.b64"
$docsB64 = Join-Path $ScriptDir "uiao-docs-remaining.b64"

foreach ($f in @($coreB64, $docsB64)) {
    if (-not (Test-Path $f)) {
        Write-Error "Missing companion file: $f"
        return
    }
}

New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
Write-Host "[PREFLIGHT] Work dir: $WorkDir" -ForegroundColor DarkGray

# Decode Payloads
Write-Host "[PAYLOAD] Decoding archives..." -ForegroundColor Yellow

$coreZip = Join-Path $WorkDir "uiao-remaining.zip"
$docsZip = Join-Path $WorkDir "uiao-docs-remaining.zip"
$coreDir = Join-Path $WorkDir "uiao-files"
$docsDir = Join-Path $WorkDir "uiao-docs-files"

[IO.File]::WriteAllBytes($coreZip, [Convert]::FromBase64String((Get-Content $coreB64 -Raw).Trim()))
[IO.File]::WriteAllBytes($docsZip, [Convert]::FromBase64String((Get-Content $docsB64 -Raw).Trim()))

Expand-Archive -Path $coreZip -DestinationPath $coreDir -Force
Expand-Archive -Path $docsZip -DestinationPath $docsDir -Force

Write-Host "  Core: $((Get-ChildItem $coreDir -Recurse -File).Count) files" -ForegroundColor DarkGray
Write-Host "  Docs: $((Get-ChildItem $docsDir -Recurse -File).Count) files" -ForegroundColor DarkGray

# Deploy Function
function Deploy-ToRepo {
    param(
        [string]$RepoUrl,
        [string]$RepoName,
        [string]$SourcePath,
        [string]$CommitMessage
    )

    $repoPath = Join-Path $WorkDir $RepoName

    Write-Host ""
    Write-Host "=== DEPLOYING: $RepoName ===" -ForegroundColor Green

    Write-Host "  [1/4] Cloning..." -ForegroundColor Yellow
    & git clone --depth 1 $RepoUrl $repoPath 2>&1 |
        ForEach-Object { Write-Host "        $_" -ForegroundColor DarkGray }
    if ($LASTEXITCODE -ne 0) { Write-Error "Clone failed: $RepoUrl"; return $false }

    Write-Host "  [2/4] Copying files..." -ForegroundColor Yellow
    Get-ChildItem -Path $SourcePath -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($SourcePath.Length + 1)
        $dest = Join-Path $repoPath $rel
        $dir  = Split-Path $dest -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Copy-Item $_.FullName $dest -Force
        Write-Host "        + $rel" -ForegroundColor DarkGray
    }

    Write-Host "  [3/4] Committing..." -ForegroundColor Yellow
    Push-Location $repoPath
    try {
        & git add -A
        $staged = & git diff --staged --name-only
        if (-not $staged) {
            Write-Host "        No changes (files may already exist)" -ForegroundColor Yellow
            Pop-Location; return $true
        }
        & git commit -m $CommitMessage 2>&1 |
            ForEach-Object { Write-Host "        $_" -ForegroundColor DarkGray }

        Write-Host "  [4/4] Pushing to main..." -ForegroundColor Yellow
        & git push origin main 2>&1 |
            ForEach-Object { Write-Host "        $_" -ForegroundColor DarkGray }
        if ($LASTEXITCODE -ne 0) { Write-Error "Push failed"; Pop-Location; return $false }
    } finally { Pop-Location }

    Write-Host "  DONE: $RepoName deployed" -ForegroundColor Green
    return $true
}

# Phase 1: uiao
$coreMsg = @"
[UIAO-CORE] ADD: Claude integration - skills, commands, CI, tools, schema, CLAUDE.md

Skills: appendix-indexing.md, dashboard-export.md
Commands: validate-metadata.md, scan-drift.md, sync-appendices.md, export-dashboard.md
CI: metadata-validator.yml, drift-scan.yml, appendix-sync.yml, dashboard-export.yml
Tools: metadata_validator.py, drift_detector.py, appendix_indexer.py, dashboard_exporter.py
Schema: dashboard-schema.json  |  CLAUDE.md updated
"@

$r1 = Deploy-ToRepo -RepoUrl "https://github.com/WhalerMike/uiao.git" `
    -RepoName "uiao" -SourcePath $coreDir -CommitMessage $coreMsg

# Phase 2: uiao-docs
$docsMsg = @"
[UIAO-DOCS] ADD: Full Claude Code integration layer

Agents (5): docs-governance-agent, docs-drift-detector, docs-appendix-manager,
            docs-dashboard-exporter, docs-publisher
Rules (4) | Skills (4) | Commands (4) | CI (4) | Tools (4)
Schema: dashboard-schema.json  |  CLAUDE.md
"@

$r2 = Deploy-ToRepo -RepoUrl "https://github.com/WhalerMike/uiao-docs.git" `
    -RepoName "uiao-docs" -SourcePath $docsDir -CommitMessage $docsMsg

# Summary
Write-Host ""
Write-Host "=== SYNC COMPLETE ===" -ForegroundColor Cyan
Write-Host "  uiao: $(if($r1){'PASS'}else{'FAIL'})" -ForegroundColor $(if($r1){'Green'}else{'Red'})
Write-Host "  uiao-docs: $(if($r2){'PASS'}else{'FAIL'})" -ForegroundColor $(if($r2){'Green'}else{'Red'})
Write-Host ""

$c = Read-Host "Clean up $WorkDir? (y/N)"
if ($c -eq 'y') { Remove-Item $WorkDir -Recurse -Force; Write-Host "Cleaned." }
else { Write-Host "Preserved: $WorkDir" -ForegroundColor DarkGray }
