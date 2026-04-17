from typing import Dict, Any

from core.drift.drift_engine import DriftState
from core.providers.base_adapter import BaseAdapter

class EntraIDAdapter(BaseAdapter):
    """
    Minimal deterministic Entra ID provider.
    ARC 5 only defines structure — ARC 6 adds real Graph calls.
    """

    version = "0.1.0"
    capabilities = ["users", "groups", "directoryObjects"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "entra-id"}

    def fetch_state(self) -> Dict[str, Any]:
                return {"provider": "entra-id", "users": [], "groups": []}
                
    def expected_state(self) -> Dict[str, Any]:
                                # ARC 5: No expectations yet
        return {"provider": "entra-id", "users": [], "groups": []}
        
                                            def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
                                                                return {"status": "noop", "provider": "entra-id"}# ARC 5: Static placeholder DriftState                                                        