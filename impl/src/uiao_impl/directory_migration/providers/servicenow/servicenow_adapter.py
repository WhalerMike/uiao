from typing import Dict, Any
from core.drift.drift_engine import DriftState
from core.providers.base_adapter import BaseAdapter


class ServiceNowAdapter(BaseAdapter):
    """
    Minimal deterministic ServiceNow provider.
    ARC 5 defines structure only -- ARC 6 adds real ServiceNow API calls.
    """

    version = "0.1.0"
    capabilities = ["incidents", "cmdb", "catalog"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "servicenow"}

    def fetch_state(self) -> Dict[str, Any]:
        # ARC 5: Static placeholder state
        return {"provider": "servicenow", "incidents": [], "cmdb": [], "catalog": []}

    def expected_state(self) -> Dict[str, Any]:
        # ARC 5: No expectations yet
        return {"provider": "servicenow", "incidents": [], "cmdb": [], "catalog": []}

    def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
        return {"status": "noop", "provider": "servicenow"}
