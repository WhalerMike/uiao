"""
impl/src/uiao/impl/adapters/modernization/gcc-boundary-probe/__init__.py
"""

from .probe import (
    BoundaryFinding,
    BoundaryProbeReport,
    run_boundary_probe,
    run_boundary_probe_sync,
)
from .sentinel_probe import (
    QUERY_REGISTRY,
    DashboardCompletenessScore,
    SentinelFinding,
    SentinelProbe,
    dashboard_completeness_score,
    load_kql_query,
)
from .telemetry import (
    DeviceHealthRecord,
    InBoundaryTelemetry,
    collect_local_wmi_health,
)

__all__ = [
    "BoundaryFinding",
    "BoundaryProbeReport",
    "run_boundary_probe",
    "run_boundary_probe_sync",
    "SentinelProbe",
    "SentinelFinding",
    "DashboardCompletenessScore",
    "QUERY_REGISTRY",
    "load_kql_query",
    "dashboard_completeness_score",
    "InBoundaryTelemetry",
    "DeviceHealthRecord",
    "collect_local_wmi_health",
]

ADAPTER_ID = "gcc-boundary-probe-v1"
ADAPTER_CLASS = "modernization"
MISSION_CLASS = "enforcement"
