"""
impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/telemetry.py
--------------------------------------------------------------------------
UIAO In-Boundary Telemetry Aggregation
Compensating control for blocked Microsoft telemetry pipelines.

This replaces the following blocked Microsoft capabilities:
  - Endpoint Analytics (DiagTrack/commercial endpoints blocked)
  - Azure Monitor on ARC servers (ARM telemetry endpoints blocked)
  - Windows Update compliance reporting (some graph endpoints)

Data sources used (all within FedRAMP boundary):
  - WMI/CIM via PowerShell subprocess (local, no external endpoint)
  - Microsoft Graph management plane (available in GCC-Moderate)
  - Intune compliance report via Graph (management, not telemetry)
  - AD survey data from active-directory adapter

Maps to NIST 800-137 continuous monitoring requirements.
Feeds KSI signal set (Appendix T).
"""

from __future__ import annotations

import json
import platform
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class DeviceHealthRecord:
    """In-boundary device health record replacing Endpoint Analytics."""
    device_id: str
    device_name: str
    os_version: str
    last_sync_time: str
    compliance_state: str          # compliant | noncompliant | unknown
    update_compliance: str         # upToDate | notUpToDate | unknown
    disk_health: str               # healthy | warning | critical | unknown
    memory_gb: float = 0.0
    cpu_model: str = ""
    last_boot_time: str = ""
    pending_reboot: bool = False
    enrolled_in_intune: bool = False
    entra_joined: bool = False
    orgpath: str = ""
    source: str = "uiao-in-boundary"
    collected_at: str = ""


class InBoundaryTelemetry:
    """
    Collects device health telemetry within the FedRAMP boundary
    using Graph API management plane (not telemetry plane).

    Graph management plane endpoints ARE available in GCC-Moderate:
      - /deviceManagement/managedDevices (Intune enrollment/compliance)
      - /devices (Entra device objects)
      - /users/{id}/managedDevices (per-user device list)

    These are management API calls, not telemetry streams.
    They do not require DiagTrack or commercial telemetry endpoints.
    """

    GRAPH_BASE = "https://graph.microsoft.com/v1.0"

    def __init__(self, access_token: str, timeout: int = 30):
        self._token = access_token
        self._headers = {"Authorization": f"Bearer {access_token}"}
        self._timeout = timeout

    async def collect_intune_device_health(self) -> list[DeviceHealthRecord]:
        """
        Collect device health from Intune management plane via Graph.
        This uses the management API, not telemetry — available in GCC-Moderate.
        """
        url = (
            f"{self.GRAPH_BASE}/deviceManagement/managedDevices"
            "?$select=id,deviceName,operatingSystem,osVersion,"
            "complianceState,lastSyncDateTime,totalStorageSpaceInBytes,"
            "freeStorageSpaceInBytes,physicalMemoryInBytes,"
            "model,manufacturer,enrolledDateTime,"
            "azureADDeviceId,joinType,managementState"
            "&$top=999"
        )
        records: list[DeviceHealthRecord] = []
        ts = datetime.now(timezone.utc).isoformat()

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            while url:
                resp = await client.get(url, headers=self._headers)
                if resp.status_code != 200:
                    break
                data = resp.json()
                for d in data.get("value", []):
                    total_storage = d.get("totalStorageSpaceInBytes", 0) or 0
                    free_storage = d.get("freeStorageSpaceInBytes", 0) or 0
                    if total_storage > 0:
                        used_pct = (total_storage - free_storage) / total_storage
                        disk_health = (
                            "critical" if used_pct > 0.90 else
                            "warning" if used_pct > 0.80 else
                            "healthy"
                        )
                    else:
                        disk_health = "unknown"

                    memory_bytes = d.get("physicalMemoryInBytes", 0) or 0
                    records.append(DeviceHealthRecord(
                        device_id=d.get("id", ""),
                        device_name=d.get("deviceName", ""),
                        os_version=d.get("osVersion", ""),
                        last_sync_time=str(d.get("lastSyncDateTime", "")),
                        compliance_state=d.get("complianceState", "unknown"),
                        update_compliance="unknown",  # enriched below
                        disk_health=disk_health,
                        memory_gb=round(memory_bytes / (1024 ** 3), 1),
                        cpu_model=d.get("model", ""),
                        enrolled_in_intune=True,
                        entra_joined=d.get("joinType", "") != "azureADRegistered",
                        collected_at=ts,
                    ))
                url = data.get("@odata.nextLink")

        return records

    async def collect_update_compliance(self) -> dict[str, str]:
        """
        Collect Windows Update compliance state via Graph.
        Windows Update for Business reports ARE available in GCC-Moderate
        through the Graph deviceManagement reports endpoint.
        Returns dict of device_id -> compliance_state.
        """
        url = (
            f"{self.GRAPH_BASE}/deviceManagement/managedDevices"
            "?$select=id,osVersion,deviceActionResults"
            "&$filter=operatingSystem eq 'Windows'"
            "&$top=999"
        )
        compliance: dict[str, str] = {}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url, headers=self._headers)
            if resp.status_code == 200:
                for d in resp.json().get("value", []):
                    # Derive update compliance from OS version freshness
                    # This is a proxy — actual Update for Business compliance
                    # requires Windows Update for Business reports (Graph beta)
                    device_id = d.get("id", "")
                    os_ver = d.get("osVersion", "")
                    # Windows 11 24H2 = 10.0.26100.x, 23H2 = 10.0.22631.x
                    # Simple heuristic: mark known EOL versions as non-compliant
                    if "10.0.19041" in os_ver or "10.0.18362" in os_ver:
                        compliance[device_id] = "notUpToDate"
                    else:
                        compliance[device_id] = "unknown"
        return compliance


# ------------------------------------------------------------------
# WMI/CIM collection (on-premises, Windows-only)
# Used for local device health collection on the survey server
# or for ARC-enrolled servers where Azure Monitor is blocked
# ------------------------------------------------------------------

def collect_local_wmi_health(computer_name: Optional[str] = None) -> dict:
    """
    Collect device health via WMI/CIM using PowerShell subprocess.
    No external endpoint required — purely local Windows API.

    If computer_name is None, collects from local machine.
    For remote collection, requires WinRM access.
    """
    if platform.system() != "Windows":
        return {"error": "WMI collection only available on Windows"}

    target = f"-ComputerName {computer_name}" if computer_name else ""
    script = f"""
$ErrorActionPreference = 'Stop'
$comp = Get-CimInstance Win32_ComputerSystem {target}
$os   = Get-CimInstance Win32_OperatingSystem {target}
$disk = Get-CimInstance Win32_LogicalDisk {target} -Filter "DeviceID='C:'"
$tpm  = Get-CimInstance Win32_Tpm {target} -Namespace root\\cimv2\\security\\microsofttpm `
        -ErrorAction SilentlyContinue

$pending = $false
try {{
    $reboot = Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired' -ErrorAction SilentlyContinue
    $pending = $reboot -ne $null
}} catch {{}}

[PSCustomObject]@{{
    ComputerName    = $comp.Name
    Manufacturer    = $comp.Manufacturer
    Model           = $comp.Model
    TotalMemoryGB   = [math]::Round($comp.TotalPhysicalMemory / 1GB, 1)
    OSVersion       = $os.Version
    OSBuild         = $os.BuildNumber
    LastBootTime    = $os.LastBootUpTime.ToString('o')
    DiskTotalGB     = [math]::Round($disk.Size / 1GB, 1)
    DiskFreeGB      = [math]::Round($disk.FreeSpace / 1GB, 1)
    DiskUsedPct     = [math]::Round(($disk.Size - $disk.FreeSpace) / $disk.Size * 100, 1)
    TpmPresent      = ($tpm -ne $null)
    TpmEnabled      = if ($tpm) {{ $tpm.IsEnabled_InitialValue }} else {{ $false }}
    TpmActivated    = if ($tpm) {{ $tpm.IsActivated_InitialValue }} else {{ $false }}
    PendingReboot   = $pending
    CollectedAt     = [datetime]::UtcNow.ToString('o')
}} | ConvertTo-Json -Depth 2
"""
    try:
        result = subprocess.run(
            ["powershell", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return {"error": result.stderr[:500]}
    except subprocess.TimeoutExpired:
        return {"error": "WMI query timed out"}
    except Exception as e:
        return {"error": str(e)}


def collect_bulk_wmi_via_script(
    computer_list: list[str],
    output_dir: Path,
    max_parallel: int = 10,
) -> Path:
    """
    Run WMI collection against a list of computers in parallel
    using PowerShell jobs. Returns path to JSON output file.

    Used for ARC server survey where Azure Monitor is blocked.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"wmi-survey-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"

    computer_array = ", ".join(f'"{c}"' for c in computer_list)
    script = f"""
$computers = @({computer_array})
$jobs = @()
$results = @()

foreach ($c in $computers) {{
    while (@($jobs | Where-Object {{ $_.State -eq 'Running' }}).Count -ge {max_parallel}) {{
        Start-Sleep -Milliseconds 200
        $jobs | Where-Object {{ $_.State -eq 'Completed' }} | ForEach-Object {{
            $results += Receive-Job $_
            Remove-Job $_
        }}
    }}
    $jobs += Start-Job -ScriptBlock {{
        param($comp)
        try {{
            $os   = Get-CimInstance Win32_OperatingSystem -ComputerName $comp -ErrorAction Stop
            $disk = Get-CimInstance Win32_LogicalDisk -ComputerName $comp -Filter "DeviceID='C:'" -ErrorAction Stop
            [PSCustomObject]@{{
                ComputerName = $comp
                OSVersion    = $os.Version
                DiskFreeGB   = [math]::Round($disk.FreeSpace/1GB, 1)
                DiskUsedPct  = [math]::Round(($disk.Size-$disk.FreeSpace)/$disk.Size*100,1)
                Status       = 'ok'
            }}
        }} catch {{
            [PSCustomObject]@{{ ComputerName = $comp; Status = 'unreachable'; Error = $_.Exception.Message }}
        }}
    }} -ArgumentList $c
}}

$jobs | Wait-Job | ForEach-Object {{
    $results += Receive-Job $_
    Remove-Job $_
}}

$results | ConvertTo-Json -Depth 2 | Out-File -FilePath '{output_file}' -Encoding UTF8
"""
    subprocess.run(
        ["powershell", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, timeout=600
    )
    return output_file
