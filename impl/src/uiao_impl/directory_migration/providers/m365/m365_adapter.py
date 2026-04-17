from typing import Dict, Any
from core.drift.drift_engine import DriftState
from core.providers.base_adapter import BaseAdapter


class M365ComplianceAdapter(BaseAdapter):
    """
    Minimal deterministic M365 Compliance provider.
    ARC 5 defines structure only -- ARC 6 adds real M365 compliance APIs.
    """

    version = "0.1.0"
    capabilities = ["compliance", "policies", "alerts"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "m365-compliance"}

    def fetch_state(self) -> Dict[str, Any]:
        # ARC 5: Static placeholder state
        return {"provider": "m365-compliance", "policies": [], "alerts": []}

    def expected_state(self) -> Dict[str, Any]:
        # ARC 5: No expectations yet
        return {"provider": "m365-compliance", "policies": [], "alerts": []}

    def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
        return {"status": "noop", "provider": "m365-compliance"}
