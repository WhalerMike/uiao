#Requires -Version 5.1
<#
.SYNOPSIS
    Audit a SQL Server instance against the hardening checklist (read-only).

.DESCRIPTION
    Connects to one or more SQL instances and reports authentication mode, the
    dangerous server-config switches that should be OFF, the sa account status,
    and version/patch level. Read-only (L1 — Observe). Emits a per-instance
    findings object and a roll-up.

    SCOPE BOUNDARY: this covers the SQL *hardening-checklist* surface only. The
    SQL *engine-authentication* transformation (Windows/SQL auth -> Entra ID for
    SQL Server 2022+) is governed by canon ADR-091 and is discovered by the
    canonical `Get-SQLServerAuthAudit.ps1` (Spec3-D1.8) — use that, do not
    duplicate it here.

.EXAMPLE
    .\Invoke-SqlHardeningAudit.ps1 -ServerInstance 'sql01.agency.gov' -OutputPath .\sql-hardening.csv
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string[]]$ServerInstance,   # CONFIGURE: one or more instances
    [string]$OutputPath = '.\sql-hardening-audit.csv'
)
$mod = Get-ChildItem -Path $PSScriptRoot, "$PSScriptRoot/../lib", "$PSScriptRoot/lib" -Filter 'IntuneArcModernization.psm1' -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $mod) { throw 'IntuneArcModernization.psm1 not found beside the script or in ../lib' }
Import-Module $mod.FullName -Force

$dangerous = Get-SqlDangerousConfig
$inList = ($dangerous | ForEach-Object { "'$_'" }) -join ','

$query = @"
SELECT
  CAST(SERVERPROPERTY('ServerName') AS sysname)            AS ServerName,
  CAST(SERVERPROPERTY('ProductVersion') AS nvarchar(64))   AS Version,
  CAST(SERVERPROPERTY('ProductLevel') AS nvarchar(64))     AS PatchLevel,
  CAST(SERVERPROPERTY('Edition') AS nvarchar(128))         AS Edition,
  CAST(SERVERPROPERTY('IsIntegratedSecurityOnly') AS int)  AS WindowsAuthOnly;
SELECT name, CAST(value_in_use AS int) AS value_in_use
  FROM sys.configurations WHERE name IN ($inList);
SELECT name, is_disabled FROM sys.sql_logins WHERE name = 'sa';
"@

$findings = foreach ($inst in $ServerInstance) {
    try {
        # Invoke-Sqlcmd ships with the SqlServer module; fall back if absent.
        if (-not (Get-Command Invoke-Sqlcmd -ErrorAction SilentlyContinue)) {
            throw 'Invoke-Sqlcmd not found. Install with: Install-Module SqlServer -Scope CurrentUser'
        }
        $ds = Invoke-Sqlcmd -ServerInstance $inst -Query $query -TrustServerCertificate -OutputAs DataTables
        $srv  = $ds[0] | Select-Object -First 1
        $cfg  = $ds[1]
        $sa   = $ds[2] | Select-Object -First 1
        $on   = ($cfg | Where-Object { $_.value_in_use -ne 0 } | Select-Object -ExpandProperty name) -join '; '
        [pscustomobject]@{
            Instance = $inst; Version = $srv.Version; PatchLevel = $srv.PatchLevel; Edition = $srv.Edition
            WindowsAuthOnly = [bool]$srv.WindowsAuthOnly
            DangerousConfigsOn = if ($on) { $on } else { '(none)' }
            SaDisabled = if ($sa) { [bool]$sa.is_disabled } else { 'n/a' }
            HardeningPass = ([bool]$srv.WindowsAuthOnly -and -not $on)
        }
    } catch {
        Write-ModernizationLog -Level WARN -Message "Could not audit $inst : $_"
    }
}

$findings | Export-Csv -Path $OutputPath -NoTypeInformation
Write-ModernizationLog -Level INFO -Message "SQL hardening audit -> $OutputPath"
$findings | Format-Table Instance, Version, WindowsAuthOnly, DangerousConfigsOn, SaDisabled, HardeningPass -AutoSize
