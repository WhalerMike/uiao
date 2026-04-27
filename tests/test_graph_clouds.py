"""
tests/test_graph_clouds.py
---------------------------
Tests for the shared sovereign-cloud Graph endpoint resolver
(``uiao.adapters._graph_clouds``).

This module is the single source of truth for the cloud → Graph
hostname mapping consumed by IntuneAdapter, EntraAdapter, and
InBoundaryTelemetry. Drift in the table or the resolver semantics
would silently propagate to every Graph-using adapter, so the helper
itself gets dedicated coverage.
"""

from __future__ import annotations

import pytest

from uiao.adapters._graph_clouds import (
    DEFAULT_CLOUD,
    GRAPH_ENDPOINTS,
    resolve_graph_base,
)


def test_table_has_three_sovereign_clouds() -> None:
    assert set(GRAPH_ENDPOINTS) == {"commercial", "gcc-high", "dod"}


def test_table_uses_canonical_microsoft_hostnames() -> None:
    assert GRAPH_ENDPOINTS["commercial"] == "https://graph.microsoft.com"
    assert GRAPH_ENDPOINTS["gcc-high"] == "https://graph.microsoft.us"
    assert GRAPH_ENDPOINTS["dod"] == "https://dod-graph.microsoft.us"


def test_default_cloud_is_commercial() -> None:
    """commercial also serves GCC-Moderate per ADR-033."""
    assert DEFAULT_CLOUD == "commercial"


@pytest.mark.parametrize(
    "cloud,api,expected",
    [
        ("commercial", "v1.0", "https://graph.microsoft.com/v1.0"),
        ("commercial", "beta", "https://graph.microsoft.com/beta"),
        ("gcc-high", "v1.0", "https://graph.microsoft.us/v1.0"),
        ("gcc-high", "beta", "https://graph.microsoft.us/beta"),
        ("dod", "v1.0", "https://dod-graph.microsoft.us/v1.0"),
        ("dod", "beta", "https://dod-graph.microsoft.us/beta"),
    ],
)
def test_resolves_known_clouds(cloud: str, api: str, expected: str) -> None:
    assert resolve_graph_base(cloud=cloud, graph_api_version=api) == expected


def test_explicit_endpoint_wins_over_cloud() -> None:
    out = resolve_graph_base(
        cloud="gcc-high",
        graph_api_version="v1.0",
        explicit="https://staging.example/beta",
    )
    assert out == "https://staging.example/beta"


def test_empty_explicit_falls_through_to_cloud_lookup() -> None:
    """An empty string for explicit must NOT short-circuit cloud lookup."""
    out = resolve_graph_base(cloud="commercial", graph_api_version="v1.0", explicit="")
    assert out == "https://graph.microsoft.com/v1.0"


def test_none_explicit_falls_through_to_cloud_lookup() -> None:
    out = resolve_graph_base(cloud="commercial", graph_api_version="v1.0", explicit=None)
    assert out == "https://graph.microsoft.com/v1.0"


def test_unknown_cloud_raises_valueerror_with_supported_list() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_graph_base(cloud="mars", graph_api_version="v1.0")
    msg = str(excinfo.value)
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_adapter_name_appears_in_error_message() -> None:
    """Operators with multiple Graph clients must be able to identify the misconfigured one."""
    with pytest.raises(ValueError) as excinfo:
        resolve_graph_base(
            cloud="atlantis",
            graph_api_version="v1.0",
            adapter_name="MyCustomAdapter",
        )
    assert "MyCustomAdapter" in str(excinfo.value)


def test_default_adapter_name_when_unspecified() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_graph_base(cloud="atlantis", graph_api_version="v1.0")
    assert "adapter" in str(excinfo.value)
