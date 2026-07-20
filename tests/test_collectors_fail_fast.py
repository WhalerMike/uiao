"""Reserved collectors fail fast instead of emitting simulated evidence.

The InfoBlox and Cisco SD-WAN collectors have no real upstream
integration. They must raise on instantiation (the reserved-adapter
pattern from ``uiao.adapters.ccm_bir_adapter``) rather than returning
``{"simulated": True, ...}`` payloads through the normal ``collect()``
path, and the KSI validator engine must degrade to missing-evidence
rather than crash when they are configured.
"""

from __future__ import annotations

import pytest

from uiao.collectors import REGISTRY, create_collector
from uiao.collectors.infoblox.infoblox_collector import (
    InfobloxCollector,
    InfobloxCollectorNotYetAvailable,
)
from uiao.collectors.sdwan.sdwan_collector import (
    SdwanCollector,
    SdwanCollectorNotYetAvailable,
)
from uiao.validators.ksi_validator import KSIValidatorEngine


def test_reserved_ids_stay_registered() -> None:
    """The IDs remain listed as known-but-unavailable integration surfaces."""
    assert "infoblox" in REGISTRY
    assert "sdwan" in REGISTRY
    assert REGISTRY["infoblox"] is InfobloxCollector
    assert REGISTRY["sdwan"] is SdwanCollector


def test_infoblox_instantiation_fails_fast() -> None:
    with pytest.raises(InfobloxCollectorNotYetAvailable):
        InfobloxCollector(config={"base_url": "https://infoblox.example.gov"})


def test_sdwan_instantiation_fails_fast() -> None:
    with pytest.raises(SdwanCollectorNotYetAvailable):
        SdwanCollector(config={"base_url": "https://vmanage.example.gov"})


def test_create_collector_propagates_the_failure() -> None:
    with pytest.raises(InfobloxCollectorNotYetAvailable):
        create_collector("infoblox", {})
    with pytest.raises(SdwanCollectorNotYetAvailable):
        create_collector("sdwan", {})


def test_reserved_status_is_introspectable() -> None:
    assert InfobloxCollector.STATUS == "reserved"
    assert SdwanCollector.STATUS == "reserved"


def test_engine_degrades_to_no_collector_not_a_crash() -> None:
    """Configuring a reserved collector must not take the engine down.

    ``KSIValidatorEngine._init_collectors`` logs the failure and drops
    the collector, so KSIs sourced from it report missing evidence
    instead of receiving fabricated payloads.
    """
    engine = KSIValidatorEngine(
        ksi_catalog={},
        collector_configs={"infoblox": {}, "sdwan": {}},
    )
    assert engine._collectors == {}
