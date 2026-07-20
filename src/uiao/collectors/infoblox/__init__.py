from __future__ import annotations

"""
InfoBlox DNS/IPAM evidence collector package.

STATUS: RESERVED — instantiation raises
:class:`InfobloxCollectorNotYetAvailable` until a real WAPI integration
ships. The missing ``__init__.py`` previously kept this package out of
the registry's auto-discovery walk entirely; it is present so the
reserved ID is listed as a known-but-unavailable integration surface.
"""

from .infoblox_collector import InfobloxCollector, InfobloxCollectorNotYetAvailable

__all__ = ["InfobloxCollector", "InfobloxCollectorNotYetAvailable"]
