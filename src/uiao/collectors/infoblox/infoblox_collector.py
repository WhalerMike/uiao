from __future__ import annotations

"""
InfoBlox DNS/IPAM evidence collector.

STATUS: RESERVED — no real InfoBlox WAPI integration exists yet.

This collector will be responsible for:
- Retrieving DNS and IPAM records
- Validating that overlay identities map correctly to IP/DNS entries
- Providing evidence for KSIs related to name/address integrity and segmentation

Until the WAPI integration ships, any attempt to instantiate this
collector raises :class:`InfobloxCollectorNotYetAvailable` so that
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


class InfobloxCollectorNotYetAvailable(NotImplementedError):
    """Raised on any attempt to instantiate the InfoBlox collector.

    The InfoBlox WAPI integration has not been implemented; there is no
    real evidence source behind this collector. Instantiation fails fast
    instead of returning simulated payloads.
    """


class InfobloxCollector(BaseCollector):
    """
    Collector for InfoBlox DNS/IPAM records and validation — reserved stub.

    Any attempt to instantiate raises
    :class:`InfobloxCollectorNotYetAvailable`. The class exists so the
    registry can list the ID and so the eventual implementation has a
    stable home; it never emits evidence.
    """

    COLLECTOR_ID: str = "infoblox"
    STATUS: str = STATUS

    def __init__(self, config: Dict[str, Any]) -> None:
        raise InfobloxCollectorNotYetAvailable(
            "The InfoBlox DNS/IPAM collector has no real WAPI integration yet "
            "and no longer returns simulated evidence. Remove 'infoblox' from "
            "collector_configs (KSIs sourced from InfoBlox will report "
            "missing evidence) or implement the WAPI calls before enabling it."
        )

    def collect(self, ksi_id: str) -> EvidenceObject:
        """Unreachable — instantiation always raises. Kept to satisfy the ABC."""
        raise InfobloxCollectorNotYetAvailable(ksi_id)

    def health_check(self) -> bool:
        """Unreachable — instantiation always raises. Kept to satisfy the ABC."""
        raise InfobloxCollectorNotYetAvailable()
