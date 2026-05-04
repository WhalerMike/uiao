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


# ---------------------------------------------------------------------------
# MSAL token scope (sovereign-cloud OAuth2 .default)
# ---------------------------------------------------------------------------


SCOPE_ADAPTERS = [
    pytest.param(EntraDynamicGroupsAdapter, id="dynamic-groups"),
    pytest.param(EntraAdminUnitsAdapter, id="admin-units"),
]


@pytest.mark.parametrize("cls", SCOPE_ADAPTERS)
def test_default_scope_is_commercial(cls: type) -> None:
    a = cls({"tenant_id": "t"})
    assert a._graph_scope == "https://graph.microsoft.com/.default"


@pytest.mark.parametrize("cls", SCOPE_ADAPTERS)
def test_gcc_high_scope_uses_microsoft_us(cls: type) -> None:
    a = cls({"tenant_id": "t", "cloud": "gcc-high"})
    assert a._graph_scope == "https://graph.microsoft.us/.default"


@pytest.mark.parametrize("cls", SCOPE_ADAPTERS)
def test_dod_scope_uses_dod_graph_microsoft_us(cls: type) -> None:
    a = cls({"tenant_id": "t", "cloud": "dod"})
    assert a._graph_scope == "https://dod-graph.microsoft.us/.default"


@pytest.mark.parametrize("cls", SCOPE_ADAPTERS)
def test_scope_host_matches_endpoint_host(cls: type) -> None:
    """A token scoped for the wrong cloud's Graph would be rejected by the sovereign endpoint."""
    for cloud in ("commercial", "gcc-high", "dod"):
        a = cls({"tenant_id": "t", "cloud": cloud})
        # Both URLs start with the same host (no path); comparing host segments suffices.
        endpoint_host = a._graph_endpoint.rsplit("/", 1)[0]  # strip trailing /v1.0 or /beta
        scope_host = a._graph_scope.rsplit("/", 1)[0]  # strip trailing /.default
        assert endpoint_host == scope_host


@pytest.mark.parametrize(
    "cls,cloud,expected_scope",
    [
        (EntraDynamicGroupsAdapter, "commercial", "https://graph.microsoft.com/.default"),
        (EntraDynamicGroupsAdapter, "gcc-high", "https://graph.microsoft.us/.default"),
        (EntraDynamicGroupsAdapter, "dod", "https://dod-graph.microsoft.us/.default"),
        (EntraAdminUnitsAdapter, "commercial", "https://graph.microsoft.com/.default"),
        (EntraAdminUnitsAdapter, "gcc-high", "https://graph.microsoft.us/.default"),
        (EntraAdminUnitsAdapter, "dod", "https://dod-graph.microsoft.us/.default"),
    ],
)
def test_auth_flow_requests_token_with_cloud_appropriate_scope(
    cls: type,
    cloud: str,
    expected_scope: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock azure.identity + httpx and capture the scope passed to get_token().

    The ``_graph_client()`` body is otherwise ``# pragma: no cover - network
    path`` because it depends on optional auth deps and a live Graph
    endpoint. This test stubs both, exercises the auth_flow once via a
    fake request, and asserts the scope string matches the cloud setting.
    """
    captured_scopes: list[str] = []

    # Stub azure.identity.ClientSecretCredential
    class _StubCred:
        def __init__(self, **kwargs: object) -> None:
            pass

        def get_token(self, scope: str) -> object:
            captured_scopes.append(scope)
            return type("Tok", (), {"token": "fake-token-" + scope})()

    # Stub httpx.Auth so we can drive auth_flow without a real httpx
    class _StubAuthBase:
        pass

    class _StubReq:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

    class _StubClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self.auth = kwargs.get("auth")

    # The adapter imports azure.identity / httpx inside _graph_client(),
    # so monkeypatch sys.modules entries.
    import sys
    import types

    fake_az = types.ModuleType("azure")
    fake_az_identity = types.ModuleType("azure.identity")
    fake_az_identity.ClientSecretCredential = _StubCred  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "azure", fake_az)
    monkeypatch.setitem(sys.modules, "azure.identity", fake_az_identity)

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.Auth = _StubAuthBase  # type: ignore[attr-defined]
    fake_httpx.Client = _StubClient  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)

    a = cls({"tenant_id": "t", "client_id": "c", "client_secret": "s", "cloud": cloud})
    client = a._graph_client()
    assert client is not None, "_graph_client() returned None even with stubbed deps"

    # Drive auth_flow once via a fake request to trigger get_token()
    auth = client.auth
    request = _StubReq()
    gen = auth.auth_flow(request)
    next(gen)  # advance past the yield

    assert captured_scopes == [expected_scope], f"expected scope {expected_scope!r}, got {captured_scopes!r}"
    assert request.headers["Authorization"] == f"Bearer fake-token-{expected_scope}"
