"""Tests for the cloud-/audience-aware EntraTokenProvider wiring.

The provider previously hardcoded the commercial Microsoft Graph scope
and login authority for every caller, so ARM writers (and sovereign-cloud
Graph writers) silently acquired a wrong-audience / wrong-authority token
that the target endpoint rejects with HTTP 401. These tests pin the new
behavior: the audience and authority are selectable, with commercial
Graph as the back-compat default.

MSAL's ``ConfidentialClientApplication`` performs eager network authority
discovery at construction, so it is stubbed here — the assertions target
the audience/authority *we* compute and hand to MSAL, which is the surface
this change owns.
"""

from __future__ import annotations

import pytest

from uiao.api.auth import entra_token
from uiao.api.auth.entra_token import (
    AUTHORITY_BASE,
    GRAPH_SCOPE,
    EntraTokenProvider,
    resolve_authority_base,
)


class _FakeMsalApp:
    """Records construction kwargs; performs no network discovery."""

    def __init__(self, **kwargs) -> None:  # noqa: ANN003
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def _no_network_msal(monkeypatch) -> None:
    monkeypatch.setattr(entra_token.msal, "ConfidentialClientApplication", _FakeMsalApp)


def _provider(**kwargs) -> EntraTokenProvider:
    return EntraTokenProvider(
        tenant_id="11111111-1111-1111-1111-111111111111",
        client_id="22222222-2222-2222-2222-222222222222",
        client_secret="not-a-real-secret",
        **kwargs,
    )


def test_default_audience_is_commercial_graph() -> None:
    """Back-compat: callers that pass no scope get the commercial Graph audience."""
    provider = _provider()
    assert provider._scopes == GRAPH_SCOPE
    assert provider._authority.startswith(AUTHORITY_BASE)


def test_arm_scope_flows_to_provider() -> None:
    provider = _provider(scopes=["https://management.azure.com/.default"])
    assert provider._scopes == ["https://management.azure.com/.default"]
    # The decisive property: the ARM audience is not a Graph audience.
    assert all("graph.microsoft" not in s for s in provider._scopes)


def test_configured_scope_is_handed_to_msal() -> None:
    """get_token must request the configured audience, not a hardcoded one."""
    provider = _provider(scopes=["https://management.azure.com/.default"])
    captured: dict[str, list[str]] = {}

    def fake_acquire(scopes: list[str]):  # noqa: ANN202
        captured["scopes"] = scopes
        return {"access_token": "tok", "expires_in": 3600}

    provider._msal_app.acquire_token_for_client = fake_acquire  # type: ignore[attr-defined]
    provider.get_token()
    assert captured["scopes"] == ["https://management.azure.com/.default"]


def test_authority_base_override_applies() -> None:
    provider = _provider(authority_base="https://login.microsoftonline.us")
    assert provider._authority == "https://login.microsoftonline.us/11111111-1111-1111-1111-111111111111"


@pytest.mark.parametrize(
    "cloud,expected",
    [
        ("commercial", "https://login.microsoftonline.com"),
        ("gcc-high", "https://login.microsoftonline.us"),
        ("dod", "https://login.microsoftonline.us"),
    ],
)
def test_resolve_authority_base_per_cloud(cloud: str, expected: str) -> None:
    assert resolve_authority_base(cloud) == expected


def test_resolve_authority_base_unknown_cloud_raises() -> None:
    with pytest.raises(ValueError) as excinfo:
        resolve_authority_base("mars")
    assert "mars" in str(excinfo.value)


def test_from_environment_sets_government_authority(monkeypatch) -> None:
    monkeypatch.setenv("UIAO_ENTRA_TENANT_ID", "33333333-3333-3333-3333-333333333333")
    monkeypatch.setenv("UIAO_ENTRA_CLIENT_ID", "44444444-4444-4444-4444-444444444444")
    monkeypatch.setenv("UIAO_ENTRA_CLIENT_SECRET", "not-a-real-secret")

    provider = EntraTokenProvider.from_environment(
        scopes=["https://management.usgovcloudapi.net/.default"],
        cloud="gcc-high",
    )
    assert provider._authority.startswith("https://login.microsoftonline.us/")
    assert provider._scopes == ["https://management.usgovcloudapi.net/.default"]
