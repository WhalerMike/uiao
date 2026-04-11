<#
.SYNOPSIS
    Deterministic full-sync script for uiao-core.

.DESCRIPTION
    Provides three governance-aligned sync modes:
      Safe Mode   (default) — Refuses to run if local drift is detected.
      Force Mode  (-Force)  — Stashes all changes, syncs, then auto-restores.
      Nuclear Mode (-Nuclear) — Deletes and reclones the repo from scratch.

    Features:
      - Full transcript logging to timestamped log files
      - Branch, cleanliness, and repo-existence guardrails
      - Deterministic, governance-grade console output
      - Proper exit codes for automation integration
      - Mutual exclusion of -Force and -Nuclear

.PARAMETER Force
    Stash all local changes (tracked + untracked), hard-reset to origin/main,
    then auto-restore the stash. Zero-loss, zero-drift.

.PARAMETER Nuclear
    Remove the entire local repo and reclone from origin.
    Use only when the local substrate is contaminated beyond recovery.

.PARAMETER LogDir
    Directory for transcript logs. Defaults to ~\uiao-logs.

.EXAMPLE
    .\sync-uiao.ps1
    # Safe Mode — aborts if uncommitted changes exist.

.EXAMPLE
    .\sync-uiao.ps1 -Force
    # Force Mode — stash, sync, auto-restore.

.EXAMPLE
    .\sync-uiao.ps1 -Nuclear
    # Nuclear Mode — delete and reclone.

.NOTES
    Canonical UIAO-Core Sync Script
    Classification: Controlled
    Repository: uiao-core
    Author: Michael Stratton
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$Nuclear,
    [string]$LogDir = "$env:USERPROFILE\uiao-logs"
)

# =======================================================
# CONFIG
# =======================================================
$ErrorActionPreference = 'Stop'

$RepoPath     = "C:\Users\whale\uiao-core"
$RepoUrl      = "https://github.com/WhalerMike/uiao-core.git"
$OriginBranch = "origin/main"
$Branch       = "main"
$StashLabel   = "uiao-auto-stash"
$Timestamp    = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"

# =======================================================
# TRANSCRIPT LOGGING
# =======================================================
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

$LogFile = Join-Path $LogDir "sync-uiao_$Timestamp.log"
Start-Transcript -Path $LogFile -Append | Out-Null

# =======================================================
# HELPERS
# =======================================================
function Write-Banner {
    param([string]$Text, [string]$Color = "Cyan")
    Write-Host ""
    Write-Host ("=" * 50) -ForegroundColor $Color
    Write-Host "  $Text" -ForegroundColor $Color
    Write-Host ("=" * 50) -ForegroundColor $Color
    Write-Host ""
}

function Write-Step {
    param([int]$Number, [string]$Text)
    Write-Host "[$Number] $Text" -ForegroundColor White
}

function Write-Ok {
    param([string]$Text)
    Write-Host "    OK  $Text" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Text)
    Write-Host "    WARN  $Text" -ForegroundColor Yellow
}

function Write-Fail {
    param([string]$Text)
    Write-Host "    FAIL  $Text" -ForegroundColor Red
}

function Invoke-Git {
    param([string[]]$Arguments)
    $output = & git @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed (exit $LASTEXITCODE): $output"
    }
    return $output
}

function Stop-WithError {
    param([string]$Message, [int]$Code = 1)
    Write-Fail $Message
    Write-Host ""
    Stop-Transcript | Out-Null
    exit $Code
}

# =======================================================
# MUTUAL EXCLUSION GUARD
# =======================================================
if ($Force -and $Nuclear) {
    Stop-WithError "Cannot combine -Force and -Nuclear. Choose one mode."
}

# =======================================================
# DETERMINE MODE
# =======================================================
$Mode = if ($Nuclear) { "Nuclear" }
        elseif ($Force) { "Force (Auto-Restore)" }
        else            { "Safe" }

Write-Banner "UIAO-Core Sync Script"
Write-Host "  Repo Path : $RepoPath"
Write-Host "  Mode      : $Mode"
Write-Host "  Timestamp : $Timestamp"
Write-Host "  Log File  : $LogFile"
Write-Host ""

# =======================================================
# NUCLEAR MODE — delete + reclone
# =======================================================
if ($Nuclear) {
    Write-Step 1 "Removing entire local repo..."

    if (Test-Path $RepoPath) {
        Remove-Item -Recurse -Force $RepoPath
        Write-Ok "Removed $RepoPath"
    }
    else {
        Write-Warn "Repo path did not exist — nothing to remove."
    }

    Write-Step 2 "Cloning fresh from origin..."
    Invoke-Git @("clone", $RepoUrl, $RepoPath)
    Write-Ok "Clone complete."

    Write-Banner "NUCLEAR SYNC COMPLETE" "Green"
    Write-Host "  Repo is pristine."
    Write-Host "  Branch: $Branch"
    Write-Host "  Source: $RepoUrl"
    Write-Host ""
    Stop-Transcript | Out-Null
    exit 0
}

# =======================================================
# STEP 1 — Validate repo exists
# =======================================================
Write-Step 1 "Validating repo path..."

if (-not (Test-Path (Join-Path $RepoPath ".git"))) {
    Stop-WithError "Not a valid Git repo: $RepoPath (missing .git directory)"
}

Set-Location $RepoPath
Write-Ok "Repo validated at $RepoPath"

# =======================================================
# STEP 2 — Ensure correct branch
# =======================================================
Write-Step 2 "Checking branch..."

$currentBranch = Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD")
$currentBranch = $currentBranch.Trim()

if ($currentBranch -ne $Branch) {
    Write-Warn "On branch '$currentBranch' — switching to '$Branch'..."
    Invoke-Git @("checkout", $Branch)
    Write-Ok "Switched to $Branch"
}
else {
    Write-Ok "Already on $Branch"
}

# =======================================================
# STEP 3 — Drift check (Safe Mode gate)
# =======================================================
Write-Step 3 "Checking for local drift..."

$status = Invoke-Git @("status", "--porcelain")

$hasDrift = -not [string]::IsNullOrWhiteSpace($status)

if ($hasDrift -and -not $Force) {
    Write-Fail "Uncommitted changes detected — aborting (Safe Mode)."
    Write-Host ""
    Write-Host "  Dirty files:" -ForegroundColor Yellow
    $status -split "`n" | ForEach-Object { Write-Host "    $_" }
    Write-Host ""
    Write-Host "  Options:" -ForegroundColor Cyan
    Write-Host "    -Force   : Stash changes, sync, then auto-restore"
    Write-Host "    -Nuclear : Delete everything and reclone"
    Write-Host ""
    Stop-WithError "Local drift blocks Safe Mode sync."
}
elseif ($hasDrift) {
    Write-Warn "Drift detected — Force Mode will stash and restore."
}
else {
    Write-Ok "Working tree is clean."
}

# =======================================================
# STEP 4 — Force Mode: Stash everything
# =======================================================
$didStash = $false

if ($Force -and $hasDrift) {
    Write-Step 4 "Stashing all changes (tracked + untracked)..."

    $stashMsg = "$StashLabel-$Timestamp"
    Invoke-Git @("stash", "push", "-u", "-m", $stashMsg)
    $didStash = $true
    Write-Ok "Stashed as: $stashMsg"
}
elseif ($Force) {
    Write-Step 4 "No drift to stash — skipping stash."
    Write-Ok "Clean working tree."
}

# =======================================================
# STEP 5 — Fetch latest from origin
# =======================================================
Write-Step 5 "Fetching latest from origin..."
Invoke-Git @("fetch", "origin")
Write-Ok "Fetch complete."

# =======================================================
# STEP 6 — Hard reset to origin/main
# =======================================================
Write-Step 6 "Resetting to $OriginBranch..."
Invoke-Git @("reset", "--hard", $OriginBranch)
Write-Ok "Hard reset complete."

# =======================================================
# STEP 7 — Clean untracked files
# =======================================================
Write-Step 7 "Cleaning untracked files and directories..."
Invoke-Git @("clean", "-fd")
Write-Ok "Clean complete."

# =======================================================
# STEP 8 — Force Mode: Auto-Restore from stash
# =======================================================
if ($Force -and $didStash) {
    Write-Step 8 "Auto-restoring stashed changes..."

    $stashList = Invoke-Git @("stash", "list")
    $matchLine = ($stashList -split "`n") |
        Where-Object { $_ -match [regex]::Escape($stashMsg) } |
        Select-Object -First 1

    if ($matchLine) {
        $stashRef = ($matchLine -split ":")[0].Trim()

        try {
            Invoke-Git @("stash", "pop", $stashRef)
            Write-Ok "Auto-restore complete (stash popped)."
        }
        catch {
            Write-Warn "Stash pop had conflicts — stash preserved."
            Write-Warn "Resolve conflicts manually, then run: git stash drop $stashRef"
            Write-Host ""
            Write-Host "  Conflict details:" -ForegroundColor Yellow
            $conflictStatus = & git status --porcelain 2>&1
            $conflictStatus -split "`n" | ForEach-Object { Write-Host "    $_" }
        }
    }
    else {
        Write-Warn "Could not locate stash '$stashMsg' — manual restore required."
        Write-Host "  Run: git stash list" -ForegroundColor Yellow
    }
}

# =======================================================
# STEP 9 — Final Status
# =======================================================
$headSha = (Invoke-Git @("rev-parse", "--short", "HEAD")).Trim()

Write-Banner "SYNC COMPLETE" "Green"
Write-Host "  Mode      : $Mode"
Write-Host "  Branch    : $Branch"
Write-Host "  Aligned   : $OriginBranch"
Write-Host "  HEAD      : $headSha"
Write-Host "  Log       : $LogFile"
Write-Host ""

Stop-Transcript | Out-Null
exit 0
