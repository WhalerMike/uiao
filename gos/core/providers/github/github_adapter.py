from typing import Dict, Any
from core.drift.drift_engine import DriftState
from core.providers.base_adapter import BaseAdapter


class GitHubAdapter(BaseAdapter):
    """
    Minimal deterministic GitHub provider.
    ARC 5 defines structure only -- ARC 6 adds real GitHub REST/GraphQL calls.
    """

    version = "0.1.0"
    capabilities = ["repos", "orgs", "teams", "permissions"]

    def health_check(self) -> Dict[str, Any]:
        # ARC 5: Always healthy
        return {"status": "ok", "provider": "github"}

    def fetch_state(self) -> Dict[str, Any]:
        # ARC 5: Static placeholder state
        return {"provider": "github", "organizations": [], "repositories": [], "teams": []}

    def expected_state(self) -> Dict[str, Any]:
        # ARC 5: No expectations yet
        return {"provider": "github", "organizations": [], "repositories": [], "teams": []}

    def remediate(self, drift: DriftState) -> Dict[str, Any] | None:
        # ARC 5: No remediation yet
        return {"status": "noop", "provider": "github"}
