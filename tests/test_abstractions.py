"""Tests for src/uiao_core/abstractions/."""

from __future__ import annotations

import pytest

from uiao_core.abstractions import DNSProvider, IdentityProvider, NetworkEdge
from uiao_core.abstractions.providers import BaseProvider, Capability


# ---------------------------------------------------------------------------
# Smoke-test: public API is importable
# ---------------------------------------------------------------------------

def test_imports():
    assert IdentityProvider
    assert NetworkEdge
    assert DNSProvider


# ---------------------------------------------------------------------------
# Capability dataclass
# ---------------------------------------------------------------------------

def test_capability_defaults():
    cap = Capability(name="MFA")
    assert cap.name == "MFA"
    assert cap.description == ""
    assert cap.evidence_source == ""


def test_capability_full():
    cap = Capability(name="SSO", description="Single sign-on", evidence_source="Azure AD sign-in logs")
    assert cap.description == "Single sign-on"
    assert cap.evidence_source == "Azure AD sign-in logs"


# ---------------------------------------------------------------------------
# Abstract classes are not directly instantiable
# ---------------------------------------------------------------------------

def test_identity_provider_is_abstract():
    with pytest.raises(TypeError):
        IdentityProvider()  # type: ignore[abstract]


def test_network_edge_is_abstract():
    with pytest.raises(TypeError):
        NetworkEdge()  # type: ignore[abstract]


def test_dns_provider_is_abstract():
    with pytest.raises(TypeError):
        DNSProvider()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Concrete subclass satisfies contract
# ---------------------------------------------------------------------------

class ConcreteIdP(IdentityProvider):
    @property
    def vendor_name(self) -> str:
        return "Acme IdP"

    @property
    def capabilities(self) -> list[Capability]:
        return [Capability("SSO"), Capability("MFA")]


def test_concrete_idp_vendor_name():
    idp = ConcreteIdP()
    assert idp.vendor_name == "Acme IdP"


def test_concrete_idp_capabilities():
    idp = ConcreteIdP()
    caps = idp.capabilities
    assert len(caps) == 2
    assert caps[0].name == "SSO"
    assert caps[1].name == "MFA"


def test_concrete_idp_to_oscal_component():
    idp = ConcreteIdP()
    comp = idp.to_oscal_component()
    assert comp["title"] == "Identity Provider"
    assert comp["description"] == "Vendor: Acme IdP"
    props = {p["name"]: p["value"] for p in comp["props"]}
    assert props["vendor"] == "Acme IdP"
    assert "SSO" in props["capabilities"]
    assert "MFA" in props["capabilities"]


# ---------------------------------------------------------------------------
# Abstract class metadata
# ---------------------------------------------------------------------------

def test_abstract_names():
    assert IdentityProvider.abstract_name == "Identity Provider"
    assert NetworkEdge.abstract_name == "Network Edge / ZTNA"
    assert DNSProvider.abstract_name == "DNS / IPAM"


def test_abstract_capabilities_include_expected_tags():
    assert "MFA" in IdentityProvider.abstract_capabilities
    assert "ZTNA" in NetworkEdge.abstract_capabilities
    assert "DNS" in DNSProvider.abstract_capabilities
