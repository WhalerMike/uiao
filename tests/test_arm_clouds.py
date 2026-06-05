"""
tests/test_arm_clouds.py
------------------------
Tests for the shared sovereign-cloud ARM endpoint resolver
(``uiao.adapters._arm_clouds``).

This module is the single source of truth for the cloud → ARM hostname
and the cloud → ARM token-audience mapping consumed by the Arc-plane
device OrgPath writeback. Drift in the table or the resolver semantics
would silently send a wrong-audience token to ARM (HTTP 401), so the
helper gets dedicated coverage — mirroring ``test_graph_clouds.py``.
"""

from __future__ import annotations

import pytest

from uiao.adapters._arm_clouds import (
    ARM_ENDPOINTS,
    DEFAULT_CLOUD,
    arm_token_scope,
    resolve_arm_base,
)


def test_table_has_three_sovereign_clouds() -> None:
    assert set(ARM_ENDPOINTS) == {"commercial", "gcc-high", "dod"}


def test_table_uses_canonical_arm_hostnames() -> None:
    assert ARM_ENDPOINTS["commercial"] == "https://management.azure.com"
    # gcc-high and dod both transact ARM through Azure Government.
    assert ARM_ENDPOINTS["gcc-high"] == "https://management.usgovcloudapi.net"
    assert ARM_ENDPOINTS["dod"] == "https://management.usgovcloudapi.net"


def test_default_cloud_is_commercial() -> None:
    """commercial also serves GCC-Moderate per ADR-033."""
    assert DEFAULT_CLOUD == "commercial"


@pytest.mark.parametrize(
    "cloud,expected",
    [
        ("commercial", "https://management.azure.com"),
        ("gcc-high", "https://management.usgovcloudapi.net"),
        ("dod", "https://management.usgovcloudapi.net"),
    ],
)
def test_resolves_known_clouds(cloud: str, expected: str) -> None:
    assert resolve_arm_base(cloud=cloud) == expected


def test_arm_base_carries_no_api_version_segment() -> None:
    """ARM api-version is a per-request query param, not part of the base."""
    base = resolve_arm_base(cloud="commercial")
    assert not base.rstrip("/").endswith(("v1.0", "beta"))
    assert base == "https://management.azure.com"


def test_explicit_endpoint_wins_over_cloud() -> None:
    out = resolve_arm_base(cloud="gcc-high", explicit="https://staging.example")
    assert out == "https://staging.example"


def test_empty_explicit_falls_through_to_cloud_lookup() -> None:
    """An empty string for explicit must NOT short-circuit cloud lookup."""
    out = resolve_arm_base(cloud="commercial", explicit="")
    assert out == "https://management.azure.com"


def test_none_explicit_falls_through_to_cloud_lookup() -> None:
    out = resolve_arm_base(cloud="commercial", explicit=None)
    assert out == "https://management.azure.com"


def test_unknown_cloud_raises_valueerror_with_supported_list() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_arm_base(cloud="mars")
    msg = str(excinfo.value)
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_adapter_name_appears_in_error_message() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_arm_base(cloud="atlantis", adapter_name="MyArmWriter")
    assert "MyArmWriter" in str(excinfo.value)


# ---------------------------------------------------------------------------
# arm_token_scope — sovereign-cloud MSAL .default scope derivation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cloud,expected",
    [
        ("commercial", "https://management.azure.com/.default"),
        ("gcc-high", "https://management.usgovcloudapi.net/.default"),
        ("dod", "https://management.usgovcloudapi.net/.default"),
    ],
)
def test_token_scope_returns_dot_default_per_cloud(cloud: str, expected: str) -> None:
    """OAuth2 client-credential flow uses ``{arm-host}/.default`` per cloud."""
    assert arm_token_scope(cloud) == expected


def test_arm_scope_is_not_a_graph_scope() -> None:
    """The whole point: ARM audience must differ from the Graph audience."""
    assert "graph.microsoft" not in arm_token_scope("commercial")
    assert "graph.microsoft" not in arm_token_scope("gcc-high")


def test_token_scope_unknown_cloud_raises_with_supported_list() -> None:
    with pytest.raises(ValueError) as excinfo:
        arm_token_scope("mars")
    msg = str(excinfo.value)
    assert "mars" in msg
    assert "commercial" in msg and "gcc-high" in msg and "dod" in msg


def test_token_scope_host_matches_endpoint_table() -> None:
    """Scope derivation must use the same host as resolve_arm_base()."""
    for cloud in ARM_ENDPOINTS:
        scope = arm_token_scope(cloud)
        assert scope.startswith(ARM_ENDPOINTS[cloud])
        assert scope.endswith("/.default")
