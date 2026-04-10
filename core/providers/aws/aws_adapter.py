from typing import Dict, Any
from core.drift.drift_engine import DriftState
from core.providers.base_adapter import BaseAdapter


class AWSConfigAdapter(BaseAdapter):
    """
    Minimal deterministic AWS Config provider.
    ARC 5 defines structure only -- ARC 6 adds real AWS API calls.
    """

    version = "0.1.0"
    capabilities = ["config", "resources", "compliance"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "aws-config"}

    def fetch_state(self) -> Dict[str, Any]:
        # ARC 5: Static placeholder state
        return {"provider": "aws-config", "resources": [], "compliance": []}

    def expected_state(self) -> Dict[str, Any]:
        # ARC 5: No expectations yet
        return {"provider": "aws-config", "resources": [], "compliance": []}

    def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
        return {"status": "noop", "provider": "aws-config"}
