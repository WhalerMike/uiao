"""
uiao.adapters._graph_clouds
---------------------------

Shared sovereign-cloud Graph endpoint resolution for the adapter
package. Centralizes the cloud → hostname mapping so every Graph-using
adapter points at the same canonical table.

The endpoint table is derived from the Microsoft 365 government service
description. Per ADR-033 the ``"commercial"`` entry also serves
GCC-Moderate tenants (a tenancy designation on commercial
infrastructure with FedRAMP Moderate authorization, not a separate
endpoint).

This module deliberately exports only the truly-shared constants
(``GRAPH_ENDPOINTS``, ``DEFAULT_CLOUD``) and a single resolver helper.
Each adapter keeps its own ``DEFAULT_GRAPH_API_VERSION`` because the
appropriate version differs by use case (e.g. ``IntuneAdapter`` uses
``beta`` for early access to compliance fields; ``InBoundaryTelemetry``
uses GA-stable ``v1.0``).

Adapter authors should call ``resolve_graph_base()`` from ``__init__``
with whatever config keys they expose, then store the resolved URL on
``self._graph_endpoint`` (or equivalent) and interpolate it into every
Graph call site.
"""

from __future__ import annotations

from typing import Optional

# Microsoft Graph base URLs by sovereign cloud.
GRAPH_ENDPOINTS: dict[str, str] = {
    "commercial": "https://graph.microsoft.com",
    "gcc-high": "https://graph.microsoft.us",
    "dod": "https://dod-graph.microsoft.us",
}

DEFAULT_CLOUD = "commercial"


def resolve_graph_base(
    *,
    cloud: str,
    graph_api_version: str,
    explicit: Optional[str] = None,
    adapter_name: str = "adapter",
) -> str:
    """Resolve the Graph base URL for an adapter.

    Resolution order:

    1. If ``explicit`` is non-empty it wins (back-compat for callers
       pinning a custom or staging endpoint).
    2. Otherwise the ``cloud`` is looked up in
       :data:`GRAPH_ENDPOINTS` and joined with ``graph_api_version``.
    3. Unknown cloud names raise :class:`ValueError` — production
       blockers should not silently fall back.

    Parameters
    ----------
    cloud:
        One of ``commercial`` / ``gcc-high`` / ``dod``.
    graph_api_version:
        Path segment appended to the cloud host (e.g. ``v1.0``,
        ``beta``). The resolver does not inspect or validate the
        value; the adapter chooses the appropriate surface.
    explicit:
        If set, used verbatim and the cloud lookup is skipped.
    adapter_name:
        Included in the ValueError message to help operators identify
        the misconfigured adapter when several Graph clients are
        wired in parallel.
    """
    if explicit:
        return str(explicit)
    if cloud not in GRAPH_ENDPOINTS:
        raise ValueError(
            f"{adapter_name}: unknown cloud {cloud!r}. "
            f"Supported clouds: {sorted(GRAPH_ENDPOINTS)}. "
            "Set the cloud parameter or pass an explicit Graph endpoint."
        )
    return f"{GRAPH_ENDPOINTS[cloud]}/{graph_api_version}"
