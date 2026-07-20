from __future__ import annotations

"""
Cisco SD-WAN evidence collector package.

STATUS: RESERVED — instantiation raises
:class:`SdwanCollectorNotYetAvailable` until a real vManage integration
ships. The missing ``__init__.py`` previously kept this package out of
the registry's auto-discovery walk entirely; it is present so the
reserved ID is listed as a known-but-unavailable integration surface.
"""

from .sdwan_collector import SdwanCollector, SdwanCollectorNotYetAvailable

__all__ = ["SdwanCollector", "SdwanCollectorNotYetAvailable"]
