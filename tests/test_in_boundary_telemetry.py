"""
tests/test_in_boundary_telemetry.py
------------------------------------
Tests for the InBoundaryTelemetry sovereign-cloud Graph endpoint
resolution.

The collector hits the Graph management plane to read Intune
managedDevices health (a compensating control for blocked Microsoft
telemetry pipelines per ADR-033). The mechanism is identical across
sovereign clouds; only the Graph hostname differs. These tests pin
the cloud → endpoint mapping and confirm the resolved URL is what the
HTTP request paths interpolate.

The companion ``probe.py`` is intentionally NOT cloud-parameterized:
its scope is GCC-Moderate boundary detection against commercial
endpoints (per ADR-033), and re-pointing it would require redesigning
its gap definitions.
"""

from __future__ import annotations

import pytest

from uiao.adapters.modernization.gcc_boundary_probe.telemetry import (
    DEFAULT_CLOUD,
    DEFAULT_GRAPH_API_VERSION,
    GRAPH_ENDPOINTS,
    InBoundaryTelemetry,
)

# ---------------------------------------------------------------------------
# Endpoint table
# ---------------------------------------------------------------------------


def test_graph_endpoints_table_contains_all_three_sovereign_clouds() -> None:
    assert set(GRAPH_ENDPOINTS) == {"commercial", "gcc-high", "dod"}


def test_graph_endpoints_table_uses_canonical_hostnames() -> None:
    assert GRAPH_ENDPOINTS["commercial"] == "https://graph.microsoft.com"
    assert GRAPH_ENDPOINTS["gcc-high"] == "https://graph.microsoft.us"
    assert GRAPH_ENDPOINTS["dod"] == "https://dod-graph.microsoft.us"


def test_default_cloud_is_commercial() -> None:
    assert DEFAULT_CLOUD == "commercial"


def test_default_graph_api_version_is_v1_0() -> None:
    """Telemetry uses v1.0 (GA-stable), not beta — distinct from IntuneAdapter."""
    assert DEFAULT_GRAPH_API_VERSION == "v1.0"


# ---------------------------------------------------------------------------
# Endpoint resolution per cloud
# ---------------------------------------------------------------------------


def test_default_construction_preserves_legacy_endpoint() -> None:
    """Empty kwargs must yield the same URL the class previously hardcoded."""
    t = InBoundaryTelemetry("token")
    assert t._graph_base == "https://graph.microsoft.com/v1.0"


def test_explicit_commercial_resolves_same_as_default() -> None:
    t = InBoundaryTelemetry("token", cloud="commercial")
    assert t._graph_base == "https://graph.microsoft.com/v1.0"


def test_gcc_high_resolves_to_microsoft_us() -> None:
    t = InBoundaryTelemetry("token", cloud="gcc-high")
    assert t._graph_base == "https://graph.microsoft.us/v1.0"


def test_dod_resolves_to_dod_graph_microsoft_us() -> None:
    t = InBoundaryTelemetry("token", cloud="dod")
    assert t._graph_base == "https://dod-graph.microsoft.us/v1.0"


def test_graph_api_version_beta_overrides_default() -> None:
    t = InBoundaryTelemetry("token", cloud="gcc-high", graph_api_version="beta")
    assert t._graph_base == "https://graph.microsoft.us/beta"


# ---------------------------------------------------------------------------
# graph_base= explicit override (back-compat for staging / pinned URLs)
# ---------------------------------------------------------------------------


def test_explicit_graph_base_overrides_cloud_choice() -> None:
    t = InBoundaryTelemetry(
        "token",
        cloud="gcc-high",
        graph_base="https://staging.example/v1.0",
    )
    assert t._graph_base == "https://staging.example/v1.0"


def test_explicit_graph_base_alone_works_without_cloud() -> None:
    t = InBoundaryTelemetry("token", graph_base="https://custom.example/beta")
    assert t._graph_base == "https://custom.example/beta"


# ---------------------------------------------------------------------------
# Fail-closed on unknown clouds
# ---------------------------------------------------------------------------


def test_unknown_cloud_raises_valueerror() -> None:
    with pytest.raises(ValueError) as excinfo:
        InBoundaryTelemetry("token", cloud="mars")
    msg = str(excinfo.value)
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_empty_cloud_raises_valueerror() -> None:
    with pytest.raises(ValueError):
        InBoundaryTelemetry("token", cloud="")


# ---------------------------------------------------------------------------
# Auth header still wired correctly after refactor
# ---------------------------------------------------------------------------


def test_authorization_header_carries_bearer_token() -> None:
    t = InBoundaryTelemetry("super-secret", cloud="gcc-high")
    assert t._headers == {"Authorization": "Bearer super-secret"}


def test_timeout_kwarg_preserved() -> None:
    t = InBoundaryTelemetry("token", timeout=60, cloud="dod")
    assert t._timeout == 60
    assert t._graph_base.startswith("https://dod-graph.microsoft.us")


# ---------------------------------------------------------------------------
# URL interpolation reaches the actual Graph call sites
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cloud,expected_host",
    [
        ("commercial", "graph.microsoft.com"),
        ("gcc-high", "graph.microsoft.us"),
        ("dod", "dod-graph.microsoft.us"),
    ],
)
def test_intune_health_url_includes_cloud_host(
    cloud: str,
    expected_host: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the URL passed to httpx.AsyncClient.get reflects the cloud setting.

    We monkeypatch httpx.AsyncClient to capture the URL of the first GET call
    without making a real network request, then assert the host matches.
    """
    import asyncio

    from uiao.adapters.modernization.gcc_boundary_probe import telemetry as telemetry_mod

    captured_urls: list[str] = []

    class _StubResp:
        status_code = 500  # forces the inner loop to break before parsing

        def json(self) -> dict:
            return {}

    class _StubClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> _StubClient:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def get(self, url: str, headers: dict | None = None) -> _StubResp:
            captured_urls.append(url)
            return _StubResp()

    monkeypatch.setattr(telemetry_mod.httpx, "AsyncClient", _StubClient)

    t = InBoundaryTelemetry("token", cloud=cloud)
    asyncio.run(t.collect_intune_device_health())

    assert captured_urls, "expected at least one Graph GET"
    assert expected_host in captured_urls[0], (
        f"URL {captured_urls[0]!r} did not contain expected host {expected_host!r}"
    )
