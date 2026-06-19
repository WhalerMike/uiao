"""Tests for the Keycloak / Auth0 / PingOne OrgPath binding-profile transports.

These three transports (ADR-113, authorizing the first activation stage of the
ADR-099 IdP binding profiles) are pure-identity write seams modeled on the Okta
transport: each turns a planned ``FacetOperation`` set into native user-attribute
updates. As with the Okta/LDAP transport tests, the dispatch tests use recording
fakes — no live IdP — to confirm the ``apply`` convenience dispatches only
``write`` operations to the right path/body, and never emits ``uncaptured``
overflow casualties.
"""

from __future__ import annotations

import pytest

from uiao.adapters.auth0_transport import Auth0Transport
from uiao.adapters.keycloak_transport import KeycloakTransport
from uiao.adapters.pingone_transport import PingOneTransport
from uiao.modernization.orgtree.profile_assign import BindingProfilePlanner
from uiao.modernization.orgtree.binding_profiles import load_binding_profile
from uiao.modernization.orgtree.types import FacetOperation

_OPS = [
    FacetOperation(facet="region", attribute="region", op="write", value="NCR", target="u1"),
    FacetOperation(facet="division", attribute="", op="uncaptured", value="CyberOps", target="u1"),
]


# ---------------------------------------------------------------------------
# Profiles load and route to bare-facet custom attributes (okta shape)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("profile_id", ["keycloak", "auth0", "pingone"])
def test_idp_profile_routes_to_custom_attributes(profile_id):
    planner = BindingProfilePlanner(load_binding_profile(profile_id))
    ops = planner.plan_principal("user-1", {"region": "NCR", "department": "IT"}, plane="identity")
    assert {o.facet for o in ops} == {"region", "department"}
    assert all(o.op == "write" for o in ops)
    region = next(o for o in ops if o.facet == "region")
    assert region.attribute == "region"  # locator == facet name, no overflow
    assert region.metadata["locator_kind"] == "custom_attribute"
    assert region.metadata["profile"] == profile_id


# ---------------------------------------------------------------------------
# Keycloak
# ---------------------------------------------------------------------------


def test_keycloak_transport_apply_only_writes():
    calls: list[tuple[str, str, dict | None]] = []

    class _Recording(KeycloakTransport):
        def __call__(self, method, path, body=None):
            calls.append((method, path, body))
            return {}

    transport = _Recording(server_url="https://kc.example.gov", realm="agency", access_token="t")
    assert transport.apply(_OPS) == 1
    assert calls == [
        ("PUT", "/admin/realms/agency/users/u1", {"attributes": {"region": ["NCR"]}}),
    ]


def test_keycloak_transport_requires_server_url_and_realm():
    with pytest.raises(ValueError, match="server_url"):
        KeycloakTransport(server_url="", realm="agency", access_token="t")
    with pytest.raises(ValueError, match="realm"):
        KeycloakTransport(server_url="https://kc.example.gov", realm="", access_token="t")


# ---------------------------------------------------------------------------
# Auth0
# ---------------------------------------------------------------------------


def test_auth0_transport_apply_only_writes():
    calls: list[tuple[str, str, dict | None]] = []

    class _Recording(Auth0Transport):
        def __call__(self, method, path, body=None):
            calls.append((method, path, body))
            return {}

    transport = _Recording(tenant_url="https://tenant.us.auth0.com", access_token="t")
    assert transport.apply(_OPS) == 1
    assert calls == [
        ("PATCH", "/api/v2/users/u1", {"app_metadata": {"region": "NCR"}}),
    ]


def test_auth0_transport_requires_tenant_url():
    with pytest.raises(ValueError, match="tenant_url"):
        Auth0Transport(tenant_url="", access_token="t")


# ---------------------------------------------------------------------------
# PingOne
# ---------------------------------------------------------------------------


def test_pingone_transport_apply_only_writes():
    calls: list[tuple[str, str, dict | None]] = []

    class _Recording(PingOneTransport):
        def __call__(self, method, path, body=None):
            calls.append((method, path, body))
            return {}

    transport = _Recording(api_url="https://api.pingone.com", environment_id="env-1", access_token="t")
    assert transport.apply(_OPS) == 1
    assert calls == [
        ("PATCH", "/v1/environments/env-1/users/u1", {"region": "NCR"}),
    ]


def test_pingone_transport_requires_api_url_and_environment():
    with pytest.raises(ValueError, match="api_url"):
        PingOneTransport(api_url="", environment_id="env-1", access_token="t")
    with pytest.raises(ValueError, match="environment_id"):
        PingOneTransport(api_url="https://api.pingone.com", environment_id="", access_token="t")
