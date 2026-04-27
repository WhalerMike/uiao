"""
tests/test_intune_adapter.py
----------------------------
Tests for the IntuneAdapter sovereign-cloud Graph endpoint resolution.

Background
~~~~~~~~~~
Prior to this change ``IntuneAdapter._graph_endpoint`` was hardcoded to
``https://graph.microsoft.com/beta``, which silently fails against
GCC-High and DoD tenants where the Graph hostname is
``graph.microsoft.us`` / ``dod-graph.microsoft.us`` respectively.
ADR-033 explicitly notes that GCC-Moderate uses the commercial Graph
endpoint, so the same default still serves GCC-Moderate customers.

These tests pin the cloud → endpoint mapping and the back-compat path
where an explicit ``graph_endpoint`` config key still wins.
"""

from __future__ import annotations

import pytest

from uiao.adapters.intune_adapter import (
    DEFAULT_CLOUD,
    DEFAULT_GRAPH_API_VERSION,
    GRAPH_ENDPOINTS,
    IntuneAdapter,
)

# ---------------------------------------------------------------------------
# Endpoint table
# ---------------------------------------------------------------------------


def test_graph_endpoints_table_contains_all_three_sovereign_clouds() -> None:
    assert set(GRAPH_ENDPOINTS) == {"commercial", "gcc-high", "dod"}


def test_graph_endpoints_table_uses_canonical_microsoft_hostnames() -> None:
    """Canonical Microsoft 365 government service description hostnames."""
    assert GRAPH_ENDPOINTS["commercial"] == "https://graph.microsoft.com"
    assert GRAPH_ENDPOINTS["gcc-high"] == "https://graph.microsoft.us"
    assert GRAPH_ENDPOINTS["dod"] == "https://dod-graph.microsoft.us"


def test_default_cloud_is_commercial() -> None:
    assert DEFAULT_CLOUD == "commercial"


def test_default_graph_api_version_is_beta() -> None:
    assert DEFAULT_GRAPH_API_VERSION == "beta"


# ---------------------------------------------------------------------------
# Endpoint resolution per cloud
# ---------------------------------------------------------------------------


def test_default_config_resolves_commercial_beta() -> None:
    """Empty config preserves the historical default endpoint."""
    adapter = IntuneAdapter({})
    assert adapter._graph_endpoint == "https://graph.microsoft.com/beta"


def test_explicit_commercial_resolves_same_as_default() -> None:
    adapter = IntuneAdapter({"cloud": "commercial"})
    assert adapter._graph_endpoint == "https://graph.microsoft.com/beta"


def test_gcc_high_resolves_to_microsoft_us() -> None:
    adapter = IntuneAdapter({"cloud": "gcc-high"})
    assert adapter._graph_endpoint == "https://graph.microsoft.us/beta"


def test_dod_resolves_to_dod_graph_microsoft_us() -> None:
    adapter = IntuneAdapter({"cloud": "dod"})
    assert adapter._graph_endpoint == "https://dod-graph.microsoft.us/beta"


def test_graph_api_version_v1_0_overrides_default() -> None:
    adapter = IntuneAdapter({"cloud": "gcc-high", "graph_api_version": "v1.0"})
    assert adapter._graph_endpoint == "https://graph.microsoft.us/v1.0"


# ---------------------------------------------------------------------------
# Back-compat: explicit graph_endpoint overrides cloud-derived URL
# ---------------------------------------------------------------------------


def test_explicit_graph_endpoint_overrides_cloud() -> None:
    """Callers pinning a custom or staging endpoint must keep working."""
    adapter = IntuneAdapter({"cloud": "gcc-high", "graph_endpoint": "https://custom.example/beta"})
    assert adapter._graph_endpoint == "https://custom.example/beta"


def test_explicit_graph_endpoint_alone_still_works() -> None:
    """No cloud key at all + explicit endpoint = explicit endpoint wins."""
    adapter = IntuneAdapter({"graph_endpoint": "https://staging.example/v1.0"})
    assert adapter._graph_endpoint == "https://staging.example/v1.0"


# ---------------------------------------------------------------------------
# Fail-closed on unknown clouds
# ---------------------------------------------------------------------------


def test_unknown_cloud_raises_valueerror_at_construction() -> None:
    with pytest.raises(ValueError) as excinfo:
        IntuneAdapter({"cloud": "mars"})
    msg = str(excinfo.value)
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_empty_string_cloud_raises_valueerror() -> None:
    with pytest.raises(ValueError):
        IntuneAdapter({"cloud": ""})


# ---------------------------------------------------------------------------
# End-to-end: resolved endpoint flows through connect() and execute_query()
# ---------------------------------------------------------------------------


def test_connect_endpoint_reflects_gcc_high_cloud() -> None:
    adapter = IntuneAdapter({"cloud": "gcc-high", "tenant_id": "contoso.us"})
    conn = adapter.connect()
    assert conn.endpoint == "https://graph.microsoft.us/beta/deviceManagement"
    assert conn.identity == "intune:contoso.us"


def test_execute_query_targets_dod_graph() -> None:
    adapter = IntuneAdapter({"cloud": "dod"})
    qp = adapter.execute_query({"from": "managedDevices"})
    assert qp.vendor_query.startswith("GET https://dod-graph.microsoft.us/beta/deviceManagement/managedDevices")


def test_normalize_source_reference_reflects_cloud() -> None:
    adapter = IntuneAdapter({"cloud": "gcc-high"})
    claim_set = adapter.normalize([])
    assert claim_set.source_reference == "https://graph.microsoft.us/beta/deviceManagement"
