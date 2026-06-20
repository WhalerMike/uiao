#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Backs up the Gitea SQLite database using Volume Shadow Copy for consistency.

.DESCRIPTION
    Stops Gitea, takes a VSS-consistent copy of gitea.db, compresses it with a
    timestamp, copies to local and network backup targets, enforces 30-day
    retention, restarts Gitea, and logs all operations.

    NOTE ON ARCHITECTURE: This script backs up a *SQLite* `gitea.db` to on-prem
    local + SMB targets. The canonical UIAO Git host (ADR-041, build-guide
    Phase 12) runs Gitea on PostgreSQL and backs up via `gitea dump` to Azure
    Blob. Use this script only against a SQLite-backed instance (lab / Option-A
    deployment); it is not a substitute for `Backup-UIAOGitea` on the canonical
    Postgres host.

.OUTPUTS
    Exit code 0 on success, 1 on any failure.
#>
[CmdletBinding()]
param(
    [string]$LogFile    = 'D:\UIAO\Logs\backup.log',
    [string]$SourceDB   = 'D:\Gitea\data\gitea.db',
    [string]$LocalDest  = 'D:\UIAO\Backups\db',
    [string]$NetDest    = '\\backup-server\UIAO\db',
    [int]   $RetainDays = 30
)

$ErrorActionPreference = 'Stop'

$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$ZipName   = "gitea-db-$Timestamp.zip"
$TempDir   = "D:\UIAO\Backups\temp\db-$Timestamp"

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = 'INFO'
    )

    $entry = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] [$Level] $Message"
    Add-Content -Path $LogFile -Value $entry
    Write-Host $entry
}

try {
    Write-Log "=== Gitea DB Backup Started ==="

    # 1. Stop Gitea service
    Write-Log "Stopping Gitea service..."
    Stop-Service -Name 'gitea' -Force -ErrorAction Stop
    Start-Sleep -Seconds 5
    Write-Log "Gitea service stopped."

    # 2. Create temp directory
    New-Item -Path $TempDir -ItemType Directory -Force | Out-Null

    # 3. Copy database using a VSS shadow copy of the D: volume
    Write-Log "Creating VSS shadow copy of D:\..."
    $shadow = (Get-WmiObject -List Win32_ShadowCopy).Create('D:\', 'ClientAccessible')
    if ($shadow.ReturnValue -ne 0) {
        throw "VSS shadow copy creation failed (Win32_ShadowCopy.Create returned $($shadow.ReturnValue))"
    }

    # Select the shadow we just created by its ID (not by install date — other
    # shadows on the volume could otherwise be picked up).
    $shadowObj = Get-WmiObject Win32_ShadowCopy | Where-Object { $_.ID -eq $shadow.ShadowID }
    if (-not $shadowObj) {
        throw "Could not resolve the shadow copy with ID $($shadow.ShadowID)"
    }

    $shadowPath  = $shadowObj.DeviceObject + '\'
    $vssSourceDB = $shadowPath + 'Gitea\data\gitea.db'

    # Copy gitea.db out of the read-only VSS snapshot. cmd's copy reads the
    # \\?\GLOBALROOT device path that PowerShell cmdlets cannot address directly.
    Write-Log "Copying gitea.db from VSS snapshot..."
    $copyCmd = "copy `"$vssSourceDB`" `"$TempDir\gitea.db`""
    cmd.exe /c $copyCmd

    if (-not (Test-Path "$TempDir\gitea.db")) {
        throw "VSS copy failed - gitea.db not found in temp directory"
    }

    # Release the shadow copy
    $shadowObj.Delete()
    Write-Log "VSS shadow copy released."

    # 4. Compress with timestamp
    Write-Log "Compressing to $ZipName..."
    Compress-Archive -Path "$TempDir\gitea.db" -DestinationPath "$TempDir\$ZipName" -Force

    # 5. Copy to local backup target
    Write-Log "Copying to local backup: $LocalDest"
    if (-not (Test-Path $LocalDest)) {
        New-Item -Path $LocalDest -ItemType Directory -Force | Out-Null
    }
    Copy-Item -Path "$TempDir\$ZipName" -Destination "$LocalDest\$ZipName" -Force

    # 6. Copy to network backup target
    Write-Log "Copying to network backup: $NetDest"
    if (-not (Test-Path $NetDest)) {
        New-Item -Path $NetDest -ItemType Directory -Force | Out-Null
    }
    Copy-Item -Path "$TempDir\$ZipName" -Destination "$NetDest\$ZipName" -Force

    # 7. Enforce retention on both targets
    Write-Log "Enforcing $RetainDays-day retention..."
    $cutoff = (Get-Date).AddDays(-$RetainDays)

    Get-ChildItem -Path $LocalDest -Filter 'gitea-db-*.zip' |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Write-Log "Deleting expired local backup: $($_.Name)"
            Remove-Item $_.FullName -Force
        }

    Get-ChildItem -Path $NetDest -Filter 'gitea-db-*.zip' |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        ForEach-Object {
            Write-Log "Deleting expired network backup: $($_.Name)"
            Remove-Item $_.FullName -Force
        }

    # 8. Clean up temp directory
    Remove-Item -Path $TempDir -Recurse -Force

    # 9. Restart Gitea service
    Write-Log "Restarting Gitea service..."
    Start-Service -Name 'gitea' -ErrorAction Stop
    Start-Sleep -Seconds 5

    $svcStatus = (Get-Service -Name 'gitea').Status
    if ($svcStatus -ne 'Running') {
        throw "Gitea service did not restart. Status: $svcStatus"
    }
    Write-Log "Gitea service running."

    Write-Log "=== Gitea DB Backup Completed Successfully ==="
    exit 0
}
catch {
    Write-Log "BACKUP FAILED: $($_.Exception.Message)" -Level 'ERROR'
    Write-Log "Stack trace: $($_.ScriptStackTrace)" -Level 'ERROR'

    # Attempt to restart Gitea if it was left stopped
    try {
        $svc = Get-Service -Name 'gitea' -ErrorAction SilentlyContinue
        if ($svc -and $svc.Status -ne 'Running') {
            Write-Log "Attempting emergency Gitea restart..." -Level 'WARN'
            Start-Service -Name 'gitea'
        }
    }
    catch {
        Write-Log "Emergency restart failed: $($_.Exception.Message)" -Level 'ERROR'
    }

    exit 1
}
