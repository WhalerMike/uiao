"""
tests/test_modernization_adapters_cloud.py
-------------------------------------------
Tests for sovereign-cloud Graph endpoint resolution across
M365Adapter, EntraDynamicGroupsAdapter, and EntraAdminUnitsAdapter.

These three adapters previously resolved their Graph base URL inline
from a config key (``graph_endpoint`` for M365; ``api_base_url`` for
the two Entra adapters), defaulting to a hardcoded
``https://graph.microsoft.com/v1.0``. After this change they share the
``_graph_clouds.resolve_graph_base()`` helper with IntuneAdapter,
EntraAdapter, and InBoundaryTelemetry.

Each adapter's existing config key (``graph_endpoint`` or
``api_base_url``) is preserved as the explicit-override path for
back-compat with callers that already pin a custom or staging URL.
"""

from __future__ import annotations

import pytest

from uiao.adapters.entra_admin_units import EntraAdminUnitsAdapter
from uiao.adapters.entra_dynamic_groups import EntraDynamicGroupsAdapter
from uiao.adapters.m365_adapter import M365Adapter

# Each adapter advertises the shared resolver via the same instance
# attribute name, so most tests parametrize across all three.
ADAPTERS_AND_OVERRIDE_KEYS = [
    pytest.param(M365Adapter, "graph_endpoint", "M365Adapter", id="m365"),
    pytest.param(EntraDynamicGroupsAdapter, "api_base_url", "EntraDynamicGroupsAdapter", id="dynamic-groups"),
    pytest.param(EntraAdminUnitsAdapter, "api_base_url", "EntraAdminUnitsAdapter", id="admin-units"),
]


# ---------------------------------------------------------------------------
# Default + each cloud
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_default_construction_preserves_legacy_endpoint(cls: type, override_key: str, _name: str) -> None:
    """Empty config must yield the previously-hardcoded URL byte-for-byte."""
    a = cls({"tenant_id": "t"})
    assert a._graph_endpoint == "https://graph.microsoft.com/v1.0"


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_explicit_commercial_resolves_same_as_default(cls: type, override_key: str, _name: str) -> None:
    a = cls({"tenant_id": "t", "cloud": "commercial"})
    assert a._graph_endpoint == "https://graph.microsoft.com/v1.0"


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_gcc_high_resolves_to_microsoft_us(cls: type, override_key: str, _name: str) -> None:
    a = cls({"tenant_id": "t", "cloud": "gcc-high"})
    assert a._graph_endpoint == "https://graph.microsoft.us/v1.0"


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_dod_resolves_to_dod_graph_microsoft_us(cls: type, override_key: str, _name: str) -> None:
    a = cls({"tenant_id": "t", "cloud": "dod"})
    assert a._graph_endpoint == "https://dod-graph.microsoft.us/v1.0"


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_graph_api_version_beta_overrides_default(cls: type, override_key: str, _name: str) -> None:
    a = cls({"tenant_id": "t", "cloud": "gcc-high", "graph_api_version": "beta"})
    assert a._graph_endpoint == "https://graph.microsoft.us/beta"


# ---------------------------------------------------------------------------
# Back-compat: explicit URL via the adapter's pre-existing override key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_explicit_override_key_wins_over_cloud(cls: type, override_key: str, _name: str) -> None:
    """Each adapter's pre-existing override key still pins a custom URL."""
    a = cls({"tenant_id": "t", "cloud": "gcc-high", override_key: "https://staging.example/v1.0"})
    assert a._graph_endpoint == "https://staging.example/v1.0"


@pytest.mark.parametrize("cls,override_key,_name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_explicit_override_alone_works_without_cloud(cls: type, override_key: str, _name: str) -> None:
    a = cls({"tenant_id": "t", override_key: "https://custom.example/beta"})
    assert a._graph_endpoint == "https://custom.example/beta"


# ---------------------------------------------------------------------------
# Fail-closed on unknown clouds, with adapter name in the error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cls,override_key,name", ADAPTERS_AND_OVERRIDE_KEYS)
def test_unknown_cloud_raises_with_adapter_name(cls: type, override_key: str, name: str) -> None:
    with pytest.raises(ValueError) as excinfo:
        cls({"tenant_id": "t", "cloud": "mars"})
    msg = str(excinfo.value)
    assert name in msg
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


# ---------------------------------------------------------------------------
# M365-specific: connect() endpoint reflects cloud
# ---------------------------------------------------------------------------


def test_m365_connect_endpoint_reflects_cloud() -> None:
    a = M365Adapter({"tenant_id": "contoso.us", "cloud": "gcc-high"})
    conn = a.connect()
    assert conn.endpoint == "https://graph.microsoft.us/v1.0"
    assert conn.identity == "m365:contoso.us"


# ---------------------------------------------------------------------------
# Cross-adapter parity: shared resolver yields identical hostnames
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("cloud", ["commercial", "gcc-high", "dod"])
def test_all_three_adapters_resolve_to_same_endpoint_for_same_cloud(cloud: str) -> None:
    """Single source of truth: ``_graph_clouds.GRAPH_ENDPOINTS``."""
    m365 = M365Adapter({"tenant_id": "t", "cloud": cloud})
    dg = EntraDynamicGroupsAdapter({"tenant_id": "t", "cloud": cloud})
    au = EntraAdminUnitsAdapter({"tenant_id": "t", "cloud": cloud})
    assert m365._graph_endpoint == dg._graph_endpoint == au._graph_endpoint
