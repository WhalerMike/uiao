<#
.SYNOPSIS
    Invoke-UIAOInboxInventory.ps1
    Pre-sync inventory of UIAO inbox ZIP files.
    Run BEFORE git push. Read-only — no changes made.

.DESCRIPTION
    Enumerates all ZIP files in the inbox/ directory,
    lists their contents, checks for conflicts against
    the existing repo structure, and produces a
    promotion plan showing where each file belongs.

.PARAMETER RepoRoot
    Path to the uiao repo root. Defaults to current directory.

.PARAMETER InboxPath
    Path to inbox folder. Defaults to .\inbox

.EXAMPLE
    .\Invoke-UIAOInboxInventory.ps1
    .\Invoke-UIAOInboxInventory.ps1 -RepoRoot "C:\src\uiao"
#>

[CmdletBinding()]
param(
    [string]$RepoRoot  = (Get-Location).Path,
    [string]$InboxPath = $null
)

$ErrorActionPreference = "Stop"

if (-not $InboxPath) {
    $InboxPath = Join-Path $RepoRoot "inbox"
}

# ---------------------------------------------------------------
# Canonical target paths (from AGENTS.md and our session work)
# ---------------------------------------------------------------
$CanonicalPaths = @{
    # AD adapter (Session 1 output)
    "survey.py"                      = "impl/src/uiao/impl/adapters/modernization/active-directory/"
    "orgpath.py"                     = "impl/src/uiao/impl/adapters/modernization/active-directory/"
    "__init__.py"                    = "impl/src/uiao/impl/adapters/modernization/active-directory/"
    "Invoke-ADSurvey.ps1"            = "scripts/ad-survey/"
    "adapter-manifest.json"          = "impl/src/uiao/impl/adapters/modernization/active-directory/"

    # API layer (Session 2 output)
    "app.py"                         = "impl/src/uiao/impl/api/"
    "kerberos.py"                    = "impl/src/uiao/impl/api/auth/"
    "entra_token.py"                 = "impl/src/uiao/impl/api/auth/"
    "routes.py"                      = "impl/src/uiao/impl/api/routes/"
    "boundary.py"                    = "impl/src/uiao/impl/api/routes/"
    "web.config"                     = "deploy/windows-server/"
    "run.py"                         = "deploy/windows-server/"
    "requirements-windows.txt"       = "deploy/windows-server/"
    "deploy-scripts.ps1"             = "scripts/deploy/"

    # GCC boundary probe (Session 3 output)
    "probe.py"                       = "impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/"
    "telemetry.py"                   = "impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/"

    # Canon artifacts
    "adr-029-ad-survey-adapter.md"                = "src/uiao/canon/adr/"
    "adr-030-gcc-boundary-drift-class.md"         = "src/uiao/canon/adr/"
    "adr-031-three-plane-device-model.md"         = "src/uiao/canon/adr/"
    "gcc-boundary-gap-registry.yaml"              = "src/uiao/canon/"
    "computer-object-crosswalk.yaml"              = "src/uiao/canon/"
    "registry-entry-and-adr.yaml"                 = "src/uiao/canon/"

    # Documentation
    "PROJECT-PLAN.md"                             = "docs/docs/"
    "gcc-boundary-problem-statement.md"           = "docs/docs/"
    "gcc-boundary-solution-architecture.md"       = "docs/docs/"
    "drift-detection-boundary-amendment.md"       = "docs/docs/"
    "GAE-computer-object-decomposition.md"        = "docs/docs/"
    "GAD-modernization-impact-model.md"           = "docs/docs/"

    # Diagrams
    "computer-object-decomposition.mermaid"       = "diagrams/"
    "device-disposition-by-type.mermaid"          = "diagrams/"

    # Python classifier
    "disposition.py"                              = "impl/src/uiao/impl/adapters/modernization/active-directory/"
}

# ---------------------------------------------------------------
# Files that should be SPLIT before placing (consolidated outputs)
# ---------------------------------------------------------------
$SplitRequired = @{
    "routes.py"          = @(
        "Split into: routes/health.py (health_router)",
        "            routes/survey.py (survey_router)",
        "            routes/orgpath.py (orgpath_router)"
    )
    "deploy-scripts.ps1" = @(
        "Split into: scripts/deploy/Install-UIAOServer.ps1",
        "            scripts/deploy/Register-ServiceAccount.ps1",
        "            scripts/deploy/Register-UIAOAPI.ps1"
    )
}

# ---------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------
function Write-Header { param([string]$Text)
    Write-Host "`n$('='*65)" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "$('='*65)" -ForegroundColor Cyan
}

function Write-Section { param([string]$Text)
    Write-Host "`n--- $Text ---" -ForegroundColor Yellow
}

function Test-FileExistsInRepo {
    param([string]$FileName, [string]$RepoRoot)
    $results = Get-ChildItem -Path $RepoRoot -Recurse -Filter $FileName `
               -Exclude "inbox" -ErrorAction SilentlyContinue |
               Where-Object { $_.FullName -notlike "*\inbox\*" }
    return $results
}

# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------
Write-Header "UIAO Inbox Pre-Sync Inventory"
Write-Host "  Repo root : $RepoRoot"
Write-Host "  Inbox path: $InboxPath"
Write-Host "  Timestamp : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

if (-not (Test-Path $InboxPath)) {
    Write-Host "`nERROR: inbox/ not found at $InboxPath" -ForegroundColor Red
    exit 1
}

$ZipFiles = Get-ChildItem -Path $InboxPath -Filter "*.zip" | Sort-Object Name

if ($ZipFiles.Count -eq 0) {
    Write-Host "`nNo ZIP files found in $InboxPath" -ForegroundColor Yellow
    exit 0
}

Write-Host "`nFound $($ZipFiles.Count) ZIP file(s)" -ForegroundColor Green

# ---------------------------------------------------------------
# Per-ZIP analysis
# ---------------------------------------------------------------
$AllFiles         = @()   # every file across all ZIPs
$ConflictFiles    = @()   # files that already exist in repo
$SplitFiles       = @()   # files that need splitting
$UnknownFiles     = @()   # files with no canonical target
$ReadyFiles       = @()   # files ready to place

foreach ($Zip in $ZipFiles) {
    Write-Section "ZIP: $($Zip.Name)  ($([math]::Round($Zip.Length/1KB,1)) KB)"

    try {
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        $Archive = [System.IO.Compression.ZipFile]::OpenRead($Zip.FullName)
        $Entries = $Archive.Entries | Sort-Object FullName

        foreach ($Entry in $Entries) {
            if ($Entry.Name -eq "") { continue }   # directory entry

            $FileName    = $Entry.Name
            $ZipPath     = $Entry.FullName
            $SizeKB      = [math]::Round($Entry.Length/1KB, 1)

            # Determine canonical target
            $Target      = $CanonicalPaths[$FileName]
            $Needsplit   = $SplitRequired[$FileName]

            # Check if file already exists in repo
            $Existing    = Test-FileExistsInRepo -FileName $FileName -RepoRoot $RepoRoot

            $FileInfo = [PSCustomObject]@{
                ZipName    = $Zip.Name
                ZipPath    = $ZipPath
                FileName   = $FileName
                SizeKB     = $SizeKB
                Target     = if ($Target) { $Target } else { "UNKNOWN" }
                NeedsSplit = ($null -ne $Needsplit)
                SplitNotes = if ($Needsplit) { $Needsplit -join "; " } else { "" }
                Conflicts  = if ($Existing) { ($Existing.FullName | ForEach-Object { $_.Replace($RepoRoot,"") }) -join "; " } else { "" }
                Status     = ""
            }

            # Classify
            if ($null -ne $Needsplit) {
                $FileInfo.Status = "SPLIT_REQUIRED"
                $SplitFiles += $FileInfo
            } elseif ($Existing) {
                $FileInfo.Status = "CONFLICT"
                $ConflictFiles += $FileInfo
            } elseif ($Target) {
                $FileInfo.Status = "READY"
                $ReadyFiles += $FileInfo
            } else {
                $FileInfo.Status = "UNKNOWN_TARGET"
                $UnknownFiles += $FileInfo
            }

            $AllFiles += $FileInfo

            # Console output per file
            $color = switch ($FileInfo.Status) {
                "READY"          { "Green"  }
                "CONFLICT"       { "Red"    }
                "SPLIT_REQUIRED" { "Yellow" }
                default          { "Gray"   }
            }
            $prefix = switch ($FileInfo.Status) {
                "READY"          { "  [OK]      " }
                "CONFLICT"       { "  [CONFLICT]" }
                "SPLIT_REQUIRED" { "  [SPLIT]   " }
                default          { "  [UNKNOWN] " }
            }
            Write-Host "$prefix $FileName  ($SizeKB KB)" -ForegroundColor $color
            if ($FileInfo.Conflicts) {
                Write-Host "             Exists at: $($FileInfo.Conflicts)" -ForegroundColor DarkRed
            }
            if ($Needsplit) {
                foreach ($note in $Needsplit) {
                    Write-Host "             $note" -ForegroundColor DarkYellow
                }
            }
            if ($Target -and -not $Needsplit -and -not $Existing) {
                Write-Host "             → $Target" -ForegroundColor DarkGreen
            }
        }
        $Archive.Dispose()

    } catch {
        Write-Host "  ERROR reading ZIP: $_" -ForegroundColor Red
    }
}

# ---------------------------------------------------------------
# Summary
# ---------------------------------------------------------------
Write-Header "SUMMARY"

Write-Host "`nTotal files across all ZIPs : $($AllFiles.Count)"
Write-Host "  Ready to place            : $($ReadyFiles.Count)" -ForegroundColor Green
Write-Host "  Need splitting first      : $($SplitFiles.Count)" -ForegroundColor Yellow
Write-Host "  Conflicts (already exist) : $($ConflictFiles.Count)" -ForegroundColor $(if ($ConflictFiles.Count -gt 0) {"Red"} else {"Green"})
Write-Host "  Unknown target            : $($UnknownFiles.Count)" -ForegroundColor $(if ($UnknownFiles.Count -gt 0) {"Gray"} else {"Green"})

# ---------------------------------------------------------------
# Conflict detail
# ---------------------------------------------------------------
if ($ConflictFiles.Count -gt 0) {
    Write-Section "CONFLICTS — Review before placing"
    Write-Host "These files already exist in the repo."
    Write-Host "Decide: overwrite, merge, or skip."
    foreach ($f in $ConflictFiles) {
        Write-Host "`n  File    : $($f.FileName)" -ForegroundColor Red
        Write-Host "  From ZIP: $($f.ZipName)"
        Write-Host "  Exists  : $($f.Conflicts)"
        Write-Host "  Target  : $($f.Target)"
    }
}

# ---------------------------------------------------------------
# Split required detail
# ---------------------------------------------------------------
if ($SplitFiles.Count -gt 0) {
    Write-Section "SPLIT REQUIRED — Do not place as-is"
    foreach ($f in $SplitFiles) {
        Write-Host "`n  File    : $($f.FileName)" -ForegroundColor Yellow
        Write-Host "  From ZIP: $($f.ZipName)"
        foreach ($note in ($f.SplitNotes -split "; ")) {
            Write-Host "  $note"
        }
    }
}

# ---------------------------------------------------------------
# Unknown files
# ---------------------------------------------------------------
if ($UnknownFiles.Count -gt 0) {
    Write-Section "UNKNOWN TARGET — Needs manual placement decision"
    foreach ($f in $UnknownFiles) {
        Write-Host "  $($f.FileName)  (from $($f.ZipName))" -ForegroundColor Gray
    }
}

# ---------------------------------------------------------------
# Export report
# ---------------------------------------------------------------
$ReportPath = Join-Path $InboxPath "inbox-inventory-$(Get-Date -Format 'yyyyMMdd-HHmmss').csv"
$AllFiles | Export-Csv -Path $ReportPath -NoTypeInformation
Write-Host "`nFull report saved: $ReportPath" -ForegroundColor Cyan

# ---------------------------------------------------------------
# Promotion plan
# ---------------------------------------------------------------
Write-Header "PROMOTION PLAN (paste output to share with Claude)"

Write-Host "`n-- BEGIN INVENTORY OUTPUT --"
Write-Host "ZIP files  : $($ZipFiles.Count)"
Write-Host "Total files: $($AllFiles.Count)"
Write-Host "Ready      : $($ReadyFiles.Count)"
Write-Host "Conflicts  : $($ConflictFiles.Count)"
Write-Host "Split      : $($SplitFiles.Count)"
Write-Host "Unknown    : $($UnknownFiles.Count)"
Write-Host ""

Write-Host "FILES BY STATUS:"
$AllFiles | Sort-Object Status, FileName |
    Format-Table ZipName, FileName, Status, Target -AutoSize

Write-Host "-- END INVENTORY OUTPUT --"

Write-Host "`nNext step: paste the 'BEGIN/END INVENTORY OUTPUT' block to Claude." -ForegroundColor Cyan
Write-Host "Claude will generate the exact placement commands." -ForegroundColor Cyan
