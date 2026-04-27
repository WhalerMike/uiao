"""
tests/test_entra_adapter_cloud.py
----------------------------------
Tests for EntraAdapter sovereign-cloud Graph endpoint resolution.

EntraAdapter previously hardcoded ``https://graph.microsoft.com/v1.0``
in two sites (``connect()`` provenance and the ``signIns``
``source_reference``), which silently failed against GCC-High and DoD
tenants. This change wires the same cloud-resolution pattern used by
IntuneAdapter and InBoundaryTelemetry through the shared
``uiao.adapters._graph_clouds`` module.
"""

from __future__ import annotations

import pytest

from uiao.adapters._graph_clouds import GRAPH_ENDPOINTS
from uiao.adapters.entra_adapter import DEFAULT_GRAPH_API_VERSION, EntraAdapter


def test_entra_default_graph_api_version_is_v1_0() -> None:
    """Identity APIs are GA on v1.0; differs from IntuneAdapter (beta)."""
    assert DEFAULT_GRAPH_API_VERSION == "v1.0"


def test_entra_default_construction_preserves_legacy_endpoint() -> None:
    """Empty config must yield the previously-hardcoded URL byte-for-byte."""
    a = EntraAdapter({"tenant_id": "contoso.onmicrosoft.com"})
    assert a._graph_endpoint == "https://graph.microsoft.com/v1.0"


def test_entra_explicit_commercial_resolves_same_as_default() -> None:
    a = EntraAdapter({"tenant_id": "t", "cloud": "commercial"})
    assert a._graph_endpoint == "https://graph.microsoft.com/v1.0"


def test_entra_gcc_high_resolves_to_microsoft_us() -> None:
    a = EntraAdapter({"tenant_id": "t", "cloud": "gcc-high"})
    assert a._graph_endpoint == "https://graph.microsoft.us/v1.0"


def test_entra_dod_resolves_to_dod_graph_microsoft_us() -> None:
    a = EntraAdapter({"tenant_id": "t", "cloud": "dod"})
    assert a._graph_endpoint == "https://dod-graph.microsoft.us/v1.0"


def test_entra_graph_api_version_beta_overrides_default() -> None:
    a = EntraAdapter({"tenant_id": "t", "cloud": "gcc-high", "graph_api_version": "beta"})
    assert a._graph_endpoint == "https://graph.microsoft.us/beta"


def test_entra_explicit_graph_endpoint_overrides_cloud() -> None:
    """Callers pinning a custom or staging endpoint keep working."""
    a = EntraAdapter(
        {
            "tenant_id": "t",
            "cloud": "gcc-high",
            "graph_endpoint": "https://staging.example/v1.0",
        }
    )
    assert a._graph_endpoint == "https://staging.example/v1.0"


def test_entra_unknown_cloud_raises_valueerror() -> None:
    with pytest.raises(ValueError) as excinfo:
        EntraAdapter({"tenant_id": "t", "cloud": "mars"})
    msg = str(excinfo.value)
    assert "EntraAdapter" in msg
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_entra_connect_endpoint_reflects_cloud() -> None:
    a = EntraAdapter({"tenant_id": "contoso.us", "cloud": "gcc-high"})
    conn = a.connect()
    assert conn.endpoint == "https://graph.microsoft.us/v1.0"
    assert conn.identity == "entra:contoso.us"


@pytest.mark.parametrize(
    "cloud,expected_host",
    [
        ("commercial", "graph.microsoft.com"),
        ("gcc-high", "graph.microsoft.us"),
        ("dod", "dod-graph.microsoft.us"),
    ],
)
def test_entra_signin_source_reference_includes_cloud_host(cloud: str, expected_host: str) -> None:
    """The source_reference URL on the empty-records ClaimSet must reflect the cloud setting.

    Regression guard: before this fix, the second hardcoded Graph URL
    (in ``normalize()``'s ``source_reference``) would always point at
    commercial regardless of the configured cloud.
    """
    a = EntraAdapter({"tenant_id": "tenant-1", "cloud": cloud})
    claim_set = a.normalize([])
    assert expected_host in claim_set.source_reference, (
        f"source_reference {claim_set.source_reference!r} did not contain expected host {expected_host!r}"
    )


def test_entra_graph_endpoints_table_is_shared_with_other_adapters() -> None:
    """Single source of truth for the cloud → host table."""
    assert set(GRAPH_ENDPOINTS) == {"commercial", "gcc-high", "dod"}
