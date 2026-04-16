"""Vendor-neutral abstraction layer for UIAO-Core.

Agencies running different identity, network, or DNS stacks can provide
concrete implementations of the abstract base classes defined here without
modifying any of the core generators.

Typical usage::

    from uiao_impl.abstractions import IdentityProvider, NetworkEdge, DNSProvider

Concrete vendor implementations live in ``data/vendor-overlays/``.  The
overlay YAML files are deep-merged into the context at load time by
:func:`uiao_impl.utils.context.load_context`.
"""

from uiao_impl.abstractions.providers import (
    DNSProvider,
    IdentityProvider,
    NetworkEdge,
    PIVAuthenticationService,
    PolicyEnforcementPoint,
    VulnerabilityScanner,
)

__all__ = [
    "DNSProvider",
    "IdentityProvider",
    "NetworkEdge",
    "PIVAuthenticationService",
    "PolicyEnforcementPoint",
    "VulnerabilityScanner",
]

