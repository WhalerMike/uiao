from __future__ import annotations

"""
Cisco SD-WAN evidence collector.

This collector is responsible for:
- Retrieving SD-WAN policy definitions and compliance status
- Inspecting tunnel health and connectivity
- Providing evidence for overlay enforcement and segmentation KSIs
"""

from typing import Any, Dict

from ..base_collector import BaseCollector, EvidenceObject


class SdwanCollector(BaseCollector):
    """
    Collector for Cisco SD-WAN policy and tunnel telemetry.
    """

    COLLECTOR_ID: str = "sdwan"

    def __init__(self, config: Dict[str, Any]) -> None:
        """
        Initialize the SD-WAN collector.

        Expected configuration keys (illustrative):
        - base_url: str (e.g., 'https://vmanage.example.com')
        - username: str
        - password: str or credential reference
        - verify_ssl: bool
        - policy_filter: Optional[str]
        """
        super().__init__(config=config)
        self._base_url: str = self._config.get("base_url", "")
        self._verify_ssl: bool = bool(self._config.get("verify_ssl", True))

    def collect(self, ksi_id: str) -> EvidenceObject:
        """
        Collect SD-WAN policy and tunnel evidence for the given KSI.

        This stub implementation demonstrates the structure and should be
        replaced with real Cisco SD-WAN/vManage API calls.

        Parameters
        ----------
        ksi_id:
            Identifier of the KSI for which evidence is being collected.

        Returns
        -------
        EvidenceObject
            Canonical evidence object containing raw and normalized SD-WAN data.
        """
        # ---------------------------------------------------------------------
        # Placeholder: simulate SD-WAN API responses
        # ---------------------------------------------------------------------
        raw_data: Dict[str, Any] = {
            "simulated": True,
            "source": "CiscoSDWAN",
            "base_url": self._base_url,
            "policies": [],
            "tunnels": [],
        }

        normalized_data: Dict[str, Any] = {
            "policy_compliant": False,
            "non_compliant_policies": [],
            "tunnel_status": [],
        }

        provenance = self._build_provenance(raw_data=raw_data)

        evidence = EvidenceObject(
            ksi_id=ksi_id,
            source="CiscoSDWAN",
            timestamp=self._now(),
            raw_data=raw_data,
            normalized_data=normalized_data,
            provenance=provenance,
            freshness_valid=False,
        )
        return evidence

    def health_check(self) -> bool:
        """
        Perform a basic health check for the SD-WAN collector.

        This stub implementation only checks for presence of minimal configuration.
        A real implementation might:
        - Authenticate to vManage
        - Call a lightweight endpoint (e.g., /dataservice/client/device)
        """
        if not self._base_url:
            return False
        return True
