"""Smoke tests for the adapter registry and base contracts."""

import pytest
from uiao.adapters import (
    BlueCatAdapter,
    CyberArkAdapter,
    DatabaseAdapterBase,
    EntraAdapter,
    InfobloxAdapter,
    IntuneAdapter,
    M365Adapter,
    MainframeAdapter,
    PaloAltoAdapter,
    PatchStateAdapter,
    PkiCaAdapter,
    ScubaGearAdapter,
    ServiceNowAdapter,
    SiemAdapter,
    StigComplianceAdapter,
    TerraformAdapter,
    VulnScanAdapter,
)

ADAPTER_REGISTRY = {
    "bluecat-address-manager": BlueCatAdapter,
    "cyberark": CyberArkAdapter,
    "database": DatabaseAdapterBase,
    "entra-id": EntraAdapter,
    "infoblox": InfobloxAdapter,
    "intune": IntuneAdapter,
    "m365": M365Adapter,
    "mainframe": MainframeAdapter,
    "palo-alto": PaloAltoAdapter,
    "patch-state": PatchStateAdapter,
    "pki-ca": PkiCaAdapter,
    "scubagear": ScubaGearAdapter,
    "servicenow": ServiceNowAdapter,
    "siem": SiemAdapter,
    "stig-compliance": StigComplianceAdapter,
    "terraform": TerraformAdapter,
    "vuln-scan": VulnScanAdapter,
}

BaseAdapter = DatabaseAdapterBase.__bases__[0] if DatabaseAdapterBase.__bases__ else object


def test_registry_not_empty():
    assert len(ADAPTER_REGISTRY) > 0


def test_all_registered_are_base_adapter_subclasses():
    for name, cls in ADAPTER_REGISTRY.items():
        assert issubclass(cls, BaseAdapter), f"{name} is not a BaseAdapter subclass"


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_metadata(adapter_id):
    cls = ADAPTER_REGISTRY[adapter_id]
    assert hasattr(cls, "ADAPTER_ID")
    assert cls.ADAPTER_ID


@pytest.mark.parametrize("adapter_id", list(ADAPTER_REGISTRY.keys()))
def test_adapter_connect(adapter_id):
    import inspect

    cls = ADAPTER_REGISTRY[adapter_id]
    if inspect.isabstract(cls):
        pytest.skip(f"{adapter_id} is abstract")
    instance = cls({})
    result = instance.connect()
    assert result is not None
