"""Tests for src/uiao_core/abstractions/."""

from __future__ import annotations

import pytest

from uiao_core.abstractions import DNSProvider, IdentityProvider, NetworkEdge, PIVAuthenticationService, PolicyEnforcementPoint, VulnerabilityScanner
from uiao_core.abstractions.providers import Capability

# ---------------------------------------------------------------------------
# Smoke-test: public API is importable
# ---------------------------------------------------------------------------


def test_imports():
    assert IdentityProvider
    assert NetworkEdge
    assert DNSProvider
    assert PolicyEnforcementPoint


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


def test_policy_enforcement_point_is_abstract():
    with pytest.raises(TypeError):
        PolicyEnforcementPoint()  # type: ignore[abstract]


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
    assert PolicyEnforcementPoint.abstract_name == "Policy Enforcement Point"
    assert PIVAuthenticationService.abstract_name == "PIV Authentication Service"
    assert VulnerabilityScanner.abstract_name == "Vulnerability Scanner"


def test_abstract_capabilities_include_expected_tags():
    assert "MFA" in IdentityProvider.abstract_capabilities
    assert "ZTNA" in NetworkEdge.abstract_capabilities
    assert "DNS" in DNSProvider.abstract_capabilities
    assert "RBAC" in PolicyEnforcementPoint.abstract_capabilities
    assert "least-privilege" in PolicyEnforcementPoint.abstract_capabilities
    assert "PIV" in PIVAuthenticationService.abstract_capabilities
    assert "CAC" in PIVAuthenticationService.abstract_capabilities
    assert "FPKI" in PIVAuthenticationService.abstract_capabilities
    assert "authenticated-scan" in VulnerabilityScanner.abstract_capabilities
    assert "CVE-detection" in VulnerabilityScanner.abstract_capabilities


def test_piv_authentication_service_is_abstract():
    with pytest.raises(TypeError):
        PIVAuthenticationService()  # type: ignore[abstract]


class ConcretePIV(PIVAuthenticationService):
    @property
    def vendor_name(self) -> str:
        return "GSA USAccess"

    @property
    def capabilities(self):
        from uiao_core.abstractions.providers import Capability
        return [Capability("PIV"), Capability("CAC"), Capability("FPKI")]


def test_concrete_piv_to_oscal_component():
    piv = ConcretePIV()
    comp = piv.to_oscal_component()
    assert comp["title"] == "PIV Authentication Service"
    assert comp["description"] == "Vendor: GSA USAccess"
    props = {p["name"]: p["value"] for p in comp["props"]}
    assert props["vendor"] == "GSA USAccess"
    assert "PIV" in props["capabilities"]


def test_vulnerability_scanner_is_abstract():
    with pytest.raises(TypeError):
        VulnerabilityScanner()  # type: ignore[abstract]


class ConcreteScanner(VulnerabilityScanner):
    @property
    def vendor_name(self) -> str:
        return "Tenable Nessus"

    @property
    def capabilities(self):
        from uiao_core.abstractions.providers import Capability
        return [Capability("authenticated-scan"), Capability("CVE-detection")]


def test_concrete_scanner_to_oscal_component():
    scanner = ConcreteScanner()
    comp = scanner.to_oscal_component()
    assert comp["title"] == "Vulnerability Scanner"
    assert comp["description"] == "Vendor: Tenable Nessus"
    props = {p["name"]: p["value"] for p in comp["props"]}
    assert props["vendor"] == "Tenable Nessus"
    assert "authenticated-scan" in props["capabilities"]
