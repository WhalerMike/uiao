from __future__ import annotations

"""
Cisco SD-WAN evidence collector.

STATUS: RESERVED — no real vManage integration exists yet.

This collector will be responsible for:
- Retrieving SD-WAN policy definitions and compliance status
- Inspecting tunnel health and connectivity
- Providing evidence for overlay enforcement and segmentation KSIs

Until the vManage integration ships, any attempt to instantiate this
collector raises :class:`SdwanCollectorNotYetAvailable` so that
misconfigured pipelines fail fast rather than emitting fabricated
(``simulated``) evidence into the evidence fabric. This mirrors the
reserved-adapter pattern in :mod:`uiao.adapters.ccm_bir_adapter` and
:mod:`uiao.adapters.vdr_adapter`.

The class stays importable and keeps its ``COLLECTOR_ID`` so the
collector registry still lists the ID as a known-but-unavailable
integration surface.
"""

from typing import Any, Dict

from ..base_collector import BaseCollector, EvidenceObject

STATUS: str = "reserved"


class SdwanCollectorNotYetAvailable(NotImplementedError):
    """Raised on any attempt to instantiate the SD-WAN collector.

    The Cisco SD-WAN/vManage integration has not been implemented; there
    is no real evidence source behind this collector. Instantiation
    fails fast instead of returning simulated payloads.
    """


class SdwanCollector(BaseCollector):
    """
    Collector for Cisco SD-WAN policy and tunnel telemetry — reserved stub.

    Any attempt to instantiate raises
    :class:`SdwanCollectorNotYetAvailable`. The class exists so the
    registry can list the ID and so the eventual implementation has a
    stable home; it never emits evidence.
    """

    COLLECTOR_ID: str = "sdwan"
    STATUS: str = STATUS

    def __init__(self, config: Dict[str, Any]) -> None:
        raise SdwanCollectorNotYetAvailable(
            "The Cisco SD-WAN collector has no real vManage integration yet "
            "and no longer returns simulated evidence. Remove 'sdwan' from "
            "collector_configs (KSIs sourced from CiscoSDWAN will report "
            "missing evidence) or implement the vManage calls before enabling "
            "it."
        )

    def collect(self, ksi_id: str) -> EvidenceObject:
        """Unreachable — instantiation always raises. Kept to satisfy the ABC."""
        raise SdwanCollectorNotYetAvailable(ksi_id)

    def health_check(self) -> bool:
        """Unreachable — instantiation always raises. Kept to satisfy the ABC."""
        raise SdwanCollectorNotYetAvailable()
