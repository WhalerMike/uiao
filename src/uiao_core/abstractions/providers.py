"""Base provider interfaces for vendor-neutral UIAO-Core components.

Each abstract class defines the *capabilities* contract that any concrete
vendor implementation must satisfy.  Agencies swap implementations by:

1. Sub-classing the relevant base class, or
2. Providing a ``data/vendor-overlays/<vendor>.yaml`` overlay that replaces
   the component metadata (name, vendor, capabilities) without any Python code.

Python sub-classing is optional – the YAML overlay path is sufficient for
the OSCAL/SSP generators.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# Shared capability descriptor
# ---------------------------------------------------------------------------


@dataclass
class Capability:
    """A single discrete capability advertised by a provider."""

    name: str
    description: str = ""
    evidence_source: str = ""


# ---------------------------------------------------------------------------
# Abstract base classes
# ---------------------------------------------------------------------------


class BaseProvider(ABC):
    """Common contract for all vendor-neutral provider abstractions."""

    #: Human-readable display name (e.g. "Identity Provider").
    abstract_name: str = ""

    #: Generic capability tags consumed by generators (e.g. "MFA", "SSO").
    abstract_capabilities: list[str] = []

    @property
    @abstractmethod
    def vendor_name(self) -> str:
        """Return the concrete vendor name (e.g. 'Microsoft Entra ID')."""

    @property
    @abstractmethod
    def capabilities(self) -> list[Capability]:
        """Return the ordered list of concrete capabilities."""

    def to_oscal_component(self, component_id: str = "") -> dict[str, Any]:
        """Render an OSCAL component-definition component dict.

        The default implementation builds a minimal valid component from the
        abstract name and capabilities.  Subclasses may override for richer
        output.
        """
        return {
            "title": self.abstract_name or self.vendor_name,
            "description": f"Vendor: {self.vendor_name}",
            "props": [
                {"name": "vendor", "value": self.vendor_name},
                {
                    "name": "capabilities",
                    "value": ", ".join(c.name for c in self.capabilities),
                },
            ],
        }


class IdentityProvider(BaseProvider):
    """Abstract Identity Provider (IdP).

    Concrete examples: Microsoft Entra ID, Okta, Google Workspace, Ping Identity.
    """

    abstract_name = "Identity Provider"
    abstract_capabilities = ["SSO", "MFA", "SCIM", "RBAC"]


class NetworkEdge(BaseProvider):
    """Abstract Network Edge / Zero Trust Network Access (ZTNA) provider.

    Concrete examples: Cisco Secure Access, Palo Alto Prisma Access,
    Zscaler Private Access.
    """

    abstract_name = "Network Edge / ZTNA"
    abstract_capabilities = ["ZTNA", "SWG", "CASB", "FW"]


class DNSProvider(BaseProvider):
    """Abstract DNS / IPAM provider.

    Concrete examples: InfoBlox, BlueCat, AWS Route 53 Resolver, Cloudflare.
    """

    abstract_name = "DNS / IPAM"
    abstract_capabilities = ["DNS", "DHCP", "IPAM", "DNSSEC"]


class PolicyEnforcementPoint(BaseProvider):
    """Abstract Policy Enforcement Point (PEP).

    Evaluates access requests against policy rules and enforces permit/deny
    decisions at application and infrastructure layers.  Implements RBAC and
    attribute-based access control (ABAC) aligned with NIST AC-3.

    Concrete examples: Open Policy Agent (OPA), AWS IAM, Azure RBAC,
    Cisco ISE, Zero Trust Policy Engine.
    """

    abstract_name = "Policy Enforcement Point"
    abstract_capabilities = ["RBAC", "ABAC", "least-privilege", "policy-evaluation"]
