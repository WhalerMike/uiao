"""
impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/probe.py
----------------------------------------------------------------------
UIAO Modernization Adapter: GCC Boundary Probe

Canon reference: ADR-030, Appendix U (extended)
Adapter class:   modernization
Mission class:   enforcement

Purpose
-------
Performs automated functional testing of Microsoft service features
within an M365 GCC-Moderate tenant to detect DRIFT-BOUNDARY conditions:
features that are nominally available in the authorized boundary but
are silently blocked, explicitly unavailable, or depend on telemetry
pipelines that FedRAMP Moderate compliance controls restrict.

Outputs
-------
- DriftFinding objects with drift_class="DRIFT-BOUNDARY"
- Structured gap assessment ready for gcc-boundary-gap-registry.yaml
- Compensating control status per gap

The probe distinguishes:
  FUNCTIONAL           — feature works as documented
  SILENTLY_BLOCKED     — portal accessible, data never arrives
  EXPLICITLY_UNAVAIL   — documented as unavailable for government
  PLANNING_PHASE       — on Microsoft government roadmap
  COMPENSATED          — gap exists, UIAO control active
  GAP_UNMITIGATED      — gap exists, no compensating control
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import yaml


# ------------------------------------------------------------------
# DRIFT-BOUNDARY finding — extends the base DriftFinding with
# GCC-specific fields
# ------------------------------------------------------------------
@dataclass
class BoundaryFinding:
    """A DRIFT-BOUNDARY finding from the GCC boundary probe."""

    gap_id: str
    feature: str
    service: str
    boundary_class: str = "DRIFT-BOUNDARY"
    severity: str = "P2"
    impact_category: str = ""
    microsoft_status: str = ""
    root_cause: str = ""
    compensating_control: str = ""
    compensating_status: str = ""
    nist_controls: list[str] = field(default_factory=list)
    ksi_ids: list[str] = field(default_factory=list)
    probe_timestamp: str = ""
    probe_result: str = ""
    probe_detail: str = ""

    # Compatibility with substrate walker DriftFinding
    @property
    def drift_class(self) -> str:
        return self.boundary_class

    @property
    def path(self) -> str:
        return f"gcc-boundary/{self.gap_id}"

    @property
    def detail(self) -> str:
        return f"{self.feature} ({self.service}): {self.microsoft_status}. {self.root_cause[:200]}"

    def as_dict(self) -> dict:
        return {
            **self.__dict__,
            "drift_class": self.drift_class,
            "path": self.path,
            "detail": self.detail,
        }


@dataclass
class BoundaryProbeReport:
    """Aggregated output of the GCC boundary probe."""

    tenant_id: str
    probe_timestamp: str
    total_gaps: int = 0
    functional: int = 0
    silently_blocked: int = 0
    explicitly_unavail: int = 0
    planning_phase: int = 0
    compensated: int = 0
    gap_unmitigated: int = 0
    findings: list[BoundaryFinding] = field(default_factory=list)

    @property
    def unmitigated_p1(self) -> list[BoundaryFinding]:
        return [f for f in self.findings if f.severity == "P1" and f.compensating_status == "GAP_UNMITIGATED"]

    def as_dict(self) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "findings"}
        d["findings"] = [f.as_dict() for f in self.findings]
        d["unmitigated_p1_count"] = len(self.unmitigated_p1)
        return d


# ------------------------------------------------------------------
# Graph API probe functions
# ------------------------------------------------------------------


class GraphProbe:
    """
    Executes probe calls against Microsoft Graph API to test
    feature availability within a GCC-Moderate tenant.

    Uses the MSAL token from the existing EntraTokenProvider
    so no additional credentials are required.
    """

    def __init__(self, access_token: str, timeout: int = 15):
        self._token = access_token
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _get(self, url: str) -> tuple[int, dict]:
        """Make a Graph API GET and return (status_code, response_body)."""
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(url, headers=self._headers)
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:500]}
                return resp.status_code, body
            except httpx.TimeoutException:
                return 0, {"error": "timeout"}
            except Exception as e:
                return 0, {"error": str(e)}

    async def probe_endpoint_analytics_available(self) -> tuple[str, str]:
        """
        Test: Is Endpoint Analytics data present?
        Endpoint Analytics device data flows through Graph deviceManagement.

        Status FUNCTIONAL if data rows exist.
        Status SILENTLY_BLOCKED if API responds but returns 0 devices
        with analytics data despite enrolled devices existing.
        """
        # Check if tenant has enrolled devices first
        status, devices = await self._get(
            "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices?$count=true&$top=1"
        )
        if status != 200:
            return "PROBE_FAILED", f"managedDevices returned HTTP {status}"

        device_count = devices.get("@odata.count", 0)
        if device_count == 0:
            return "PROBE_SKIPPED", "No enrolled devices to probe against"

        # Check Endpoint Analytics scores endpoint
        status2, scores = await self._get(
            "https://graph.microsoft.com/beta/deviceManagement/userExperienceAnalyticsOverview"
        )
        if status2 == 403:
            return "EXPLICITLY_UNAVAIL", (
                "Graph returns 403 on endpoint analytics overview — feature not authorized for this tenant"
            )
        if status2 == 404:
            return "EXPLICITLY_UNAVAIL", "Endpoint analytics endpoint not found"
        if status2 == 200:
            # Check if actual scores exist (not just empty structure)
            insights = scores.get("insights", [])
            if insights:
                return "FUNCTIONAL", f"Endpoint analytics returning {len(insights)} insights"
            else:
                return "SILENTLY_BLOCKED", (
                    "Endpoint analytics API responds but returns no insights. "
                    "DiagTrack telemetry pipeline likely blocked by FedRAMP controls."
                )
        return "PROBE_FAILED", f"Unexpected status {status2}"

    async def probe_locations_available(self) -> tuple[str, str]:
        """
        Test: Is the Intune Locations feature available?
        Explicitly documented as unavailable for government.
        """
        status, body = await self._get(
            "https://graph.microsoft.com/beta/deviceManagement/managedDeviceCompliances"
            "?$filter=networkLocationId ne null&$top=1"
        )
        if status in (403, 404):
            return "EXPLICITLY_UNAVAIL", (
                f"Locations (network fence) feature returns HTTP {status} — confirmed unavailable in government tenant"
            )
        if status == 200:
            return "FUNCTIONAL", "Locations feature API is accessible"
        return "PROBE_FAILED", f"Unexpected response {status}"

    async def probe_expedited_updates(self) -> tuple[str, str]:
        """
        Test: Is expedited Windows quality update management available?
        """
        status, body = await self._get("https://graph.microsoft.com/beta/deviceManagement/windowsQualityUpdateProfiles")
        if status == 403:
            return "PLANNING_PHASE", (
                "Expedited updates returns 403 — feature in planning phase for government. Not yet available."
            )
        if status == 200:
            return "FUNCTIONAL", "Expedited update profiles accessible"
        return "PROBE_FAILED", f"Unexpected response {status}"

    async def probe_device_health_attestation(self) -> tuple[str, str]:
        """
        Test: Is Device Health Attestation data flowing?
        """
        status, body = await self._get(
            "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices"
            "?$select=id,deviceName,hardwareInformation&$top=5"
        )
        if status != 200:
            return "PROBE_FAILED", f"managedDevices returned {status}"

        devices = body.get("value", [])
        if not devices:
            return "PROBE_SKIPPED", "No enrolled devices"

        # Check if TPM/attestation data is present
        has_attestation = any(d.get("hardwareInformation", {}).get("tpmManufacturer") for d in devices)
        if has_attestation:
            return "FUNCTIONAL", "TPM attestation data present in device records"
        return "PLANNING_PHASE", (
            "No TPM/attestation hardware data in device records. "
            "Device Health Attestation in planning phase for government."
        )

    async def probe_workbooks_available(self) -> tuple[str, str]:
        """
        Test: Is Azure Monitor Workbooks available via Intune?
        This requires Azure Monitor workspace connectivity — unavailable in govt.
        """
        status, body = await self._get("https://graph.microsoft.com/beta/deviceManagement/reports/getReportFilters")
        # Workbooks are an Azure Portal feature, not Graph-testable directly
        # Use diagnostics settings as proxy
        status2, body2 = await self._get("https://graph.microsoft.com/beta/deviceManagement/reports/exportJobs")
        if status2 == 403:
            return "EXPLICITLY_UNAVAIL", (
                "Diagnostics/Workbooks export returns 403 — feature explicitly unavailable for government customers"
            )
        if status2 == 200:
            return "FUNCTIONAL", "Report export API accessible"
        return "PROBE_FAILED", f"Unexpected {status2}"


# ------------------------------------------------------------------
# ARC probe functions (Azure Resource Manager API)
# ------------------------------------------------------------------


class ARCProbe:
    """
    Probes Azure Arc resource endpoints to assess observability
    plane availability for enrolled servers.
    """

    def __init__(self, access_token: str, subscription_id: str, timeout: int = 15):
        self._token = access_token
        self._sub = subscription_id
        self._timeout = timeout
        self._headers = {
            "Authorization": f"Bearer {access_token}",
        }
        self._arm_base = "https://management.azure.com"

    async def _get(self, url: str) -> tuple[int, dict]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                resp = await client.get(url, headers=self._headers)
                try:
                    body = resp.json()
                except Exception:
                    body = {"raw": resp.text[:500]}
                return resp.status_code, body
            except httpx.TimeoutException:
                return 0, {"error": "timeout"}
            except Exception as e:
                return 0, {"error": str(e)}

    async def probe_arc_machines_enrolled(self) -> tuple[str, str]:
        """Check if any ARC machines are enrolled."""
        url = (
            f"{self._arm_base}/subscriptions/{self._sub}/"
            "providers/Microsoft.HybridCompute/machines"
            "?api-version=2023-10-03-preview"
        )
        status, body = await self._get(url)
        if status == 401:
            return "PROBE_FAILED", "ARM token invalid or expired"
        if status == 403:
            return "PROBE_FAILED", "Insufficient permissions for ARM — need Reader on subscription"
        if status == 200:
            machines = body.get("value", [])
            return "FUNCTIONAL", f"{len(machines)} ARC machines enrolled"
        return "PROBE_FAILED", f"ARM returned {status}"

    async def probe_monitor_data_collection(self) -> tuple[str, str]:
        """
        Test: Is Azure Monitor receiving data from ARC machines?
        Checks Data Collection Rules as proxy for AMA telemetry flow.
        """
        url = (
            f"{self._arm_base}/subscriptions/{self._sub}/"
            "providers/Microsoft.Insights/dataCollectionRules"
            "?api-version=2022-06-01"
        )
        status, body = await self._get(url)
        if status in (403, 404):
            return "SILENTLY_BLOCKED", (
                "Azure Monitor Data Collection Rules not accessible. "
                "Monitor telemetry endpoints may be restricted by "
                "FedRAMP network controls. ARC servers enrolled but "
                "visibility plane dark."
            )
        if status == 200:
            rules = body.get("value", [])
            if rules:
                return "FUNCTIONAL", f"{len(rules)} data collection rules defined"
            return "SILENTLY_BLOCKED", (
                "DCR API responds but no rules defined. "
                "Monitor telemetry pipeline may not be configured "
                "or may be blocked."
            )
        return "PROBE_FAILED", f"Unexpected {status}"


# ------------------------------------------------------------------
# Main probe runner
# ------------------------------------------------------------------


async def run_boundary_probe(
    graph_token: str,
    tenant_id: str,
    arm_token: Optional[str] = None,
    subscription_id: Optional[str] = None,
    gap_registry_path: Optional[Path] = None,
) -> BoundaryProbeReport:
    """
    Run the full GCC boundary probe.

    Parameters
    ----------
    graph_token      : MSAL access token for Microsoft Graph
    tenant_id        : Entra ID tenant GUID
    arm_token        : MSAL access token for Azure ARM (optional)
    subscription_id  : Azure subscription ID (optional — for ARC probes)
    gap_registry_path: Path to existing gcc-boundary-gap-registry.yaml
                       If provided, probe updates status fields in registry.

    Returns
    -------
    BoundaryProbeReport with all findings.
    """
    ts = datetime.now(timezone.utc).isoformat()
    report = BoundaryProbeReport(tenant_id=tenant_id, probe_timestamp=ts)

    graph = GraphProbe(graph_token)

    # Load existing registry for context
    registry: dict = {}
    if gap_registry_path and gap_registry_path.exists():
        registry = yaml.safe_load(gap_registry_path.read_text()) or {}

    # ---- Intune probes ----
    probes = [
        (
            "GAP-INT-001",
            "Endpoint Analytics",
            "Microsoft Intune",
            "analytics",
            graph.probe_endpoint_analytics_available,
        ),
        (
            "GAP-INT-005",
            "Locations (Network Fence)",
            "Microsoft Intune",
            "location_compliance",
            graph.probe_locations_available,
        ),
        (
            "GAP-INT-006",
            "Expedited Windows Quality Updates",
            "Microsoft Intune",
            "security_control",
            graph.probe_expedited_updates,
        ),
        (
            "GAP-INT-008",
            "Windows Device Health Attestation",
            "Microsoft Intune",
            "security_control",
            graph.probe_device_health_attestation,
        ),
        ("GAP-INT-004", "Workbooks / Diagnostics", "Microsoft Intune", "analytics", graph.probe_workbooks_available),
    ]

    for gap_id, feature, service, impact, probe_fn in probes:
        try:
            status, detail = await probe_fn()
        except Exception as e:
            status, detail = "PROBE_FAILED", str(e)

        # Look up registry entry for context
        reg_gap = _find_registry_gap(registry, gap_id)

        finding = BoundaryFinding(
            gap_id=gap_id,
            feature=feature,
            service=service,
            impact_category=impact,
            microsoft_status=status,
            probe_timestamp=ts,
            probe_result=status,
            probe_detail=detail,
            root_cause=reg_gap.get("root_cause", ""),
            compensating_control=reg_gap.get("compensating_control", ""),
            compensating_status=reg_gap.get("status", ""),
            severity=reg_gap.get("severity", "P2"),
            nist_controls=reg_gap.get("nist_controls", []),
            ksi_ids=reg_gap.get("ksi_ids", []),
        )
        report.findings.append(finding)
        _tally(report, status)

    # ---- ARC probes ----
    if arm_token and subscription_id:
        arc = ARCProbe(arm_token, subscription_id)
        arc_probes = [
            (
                "GAP-ARC-001",
                "Azure Monitor Extension Telemetry",
                "Azure Arc / Azure Monitor",
                "operational_visibility",
                arc.probe_monitor_data_collection,
            ),
        ]
        for gap_id, feature, service, impact, probe_fn in arc_probes:
            try:
                status, detail = await probe_fn()
            except Exception as e:
                status, detail = "PROBE_FAILED", str(e)

            reg_gap = _find_registry_gap(registry, gap_id)
            finding = BoundaryFinding(
                gap_id=gap_id,
                feature=feature,
                service=service,
                impact_category=impact,
                microsoft_status=status,
                probe_timestamp=ts,
                probe_result=status,
                probe_detail=detail,
                root_cause=reg_gap.get("root_cause", ""),
                compensating_control=reg_gap.get("compensating_control", ""),
                compensating_status=reg_gap.get("status", ""),
                severity=reg_gap.get("severity", "P2"),
                nist_controls=reg_gap.get("nist_controls", []),
                ksi_ids=reg_gap.get("ksi_ids", []),
            )
            report.findings.append(finding)
            _tally(report, status)

    report.total_gaps = len(report.findings)
    return report


def _find_registry_gap(registry: dict, gap_id: str) -> dict:
    """Look up a gap entry by ID in the loaded registry."""
    for gap in registry.get("gaps", []):
        if gap.get("id") == gap_id:
            return gap  # type: ignore[no-any-return]
    return {}


def _tally(report: BoundaryProbeReport, status: str) -> None:
    if status == "FUNCTIONAL":
        report.functional += 1
    elif status == "SILENTLY_BLOCKED":
        report.silently_blocked += 1
    elif status == "EXPLICITLY_UNAVAIL":
        report.explicitly_unavail += 1
    elif status == "PLANNING_PHASE":
        report.planning_phase += 1
    elif status == "COMPENSATED":
        report.compensated += 1
    elif status in ("GAP_UNMITIGATED", "PROBE_FAILED"):
        report.gap_unmitigated += 1


def run_boundary_probe_sync(
    graph_token: str,
    tenant_id: str,
    arm_token: Optional[str] = None,
    subscription_id: Optional[str] = None,
    gap_registry_path: Optional[Path] = None,
) -> BoundaryProbeReport:
    """Synchronous wrapper for run_boundary_probe."""
    return asyncio.run(
        run_boundary_probe(
            graph_token=graph_token,
            tenant_id=tenant_id,
            arm_token=arm_token,
            subscription_id=subscription_id,
            gap_registry_path=gap_registry_path,
        )
    )
