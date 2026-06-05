"""
uiao.adapters._arm_clouds
-------------------------

Shared sovereign-cloud **Azure Resource Manager (ARM)** endpoint
resolution — the ARM counterpart to :mod:`uiao.adapters._graph_clouds`.

The device-plane OrgPath writeback (ADR-038 / ADR-084 §C9) dispatches
``ARC-SERVER`` dispositions to ARM (tag PATCH on the Arc machine
resource), while ``ENTRA-DEVICE`` dispositions go to Microsoft Graph.
The two planes resolve *different* hostnames and require *different*
OAuth2 token audiences:

* Graph audience  → ``https://graph.microsoft.com/.default`` (per cloud)
* ARM   audience  → ``https://management.azure.com/.default`` (per cloud)

A Graph-audience token sent to ARM is rejected with HTTP 401 (invalid
audience), so the ARM writeback needs its own base + scope resolution.
This module centralizes that mapping so every ARM-writing surface points
at the same canonical table.

Per ADR-033 the ``"commercial"`` entry also serves GCC-Moderate tenants
(a tenancy designation on commercial infrastructure with FedRAMP
Moderate authorization, not a separate endpoint). Azure Government
(``gcc-high`` and ``dod``) share a single ARM gateway,
``management.usgovcloudapi.net``.

Unlike Graph, ARM does **not** carry an API version in the base URL —
the ``api-version`` is a per-request query parameter (e.g.
``2023-03-15-preview`` for ``Microsoft.HybridCompute/machines``), so the
resolver returns the bare host with no version segment.
"""

from __future__ import annotations

from typing import Optional

# Azure Resource Manager base URLs by sovereign cloud.
# gcc-high and dod tenants both transact ARM through Azure Government.
ARM_ENDPOINTS: dict[str, str] = {
    "commercial": "https://management.azure.com",
    "gcc-high": "https://management.usgovcloudapi.net",
    "dod": "https://management.usgovcloudapi.net",
}

DEFAULT_CLOUD = "commercial"


def arm_token_scope(cloud: str, *, adapter_name: str = "adapter") -> str:
    """Return the MSAL ``.default`` token scope for ARM in the given cloud.

    Azure Resource Manager's resource identifier for OAuth2
    client-credential flows is ``{arm-host}/.default``. The hostname
    differs between Azure Public and Azure Government — using the wrong
    scope (e.g. a Graph audience, or the public ARM audience against a
    Government tenant) returns a token the ARM endpoint rejects with 401.

    Examples
    --------
    >>> arm_token_scope("commercial")
    'https://management.azure.com/.default'
    >>> arm_token_scope("gcc-high")
    'https://management.usgovcloudapi.net/.default'
    >>> arm_token_scope("dod")
    'https://management.usgovcloudapi.net/.default'

    Unknown cloud names raise :class:`ValueError` so misconfiguration
    surfaces at construction time rather than as a 401 from ARM.
    """
    if cloud not in ARM_ENDPOINTS:
        raise ValueError(
            f"{adapter_name}: unknown cloud {cloud!r}. "
            f"Supported clouds: {sorted(ARM_ENDPOINTS)}. "
            "Set the cloud parameter to derive the ARM token scope."
        )
    return f"{ARM_ENDPOINTS[cloud]}/.default"


def resolve_arm_base(
    *,
    cloud: str,
    explicit: Optional[str] = None,
    adapter_name: str = "adapter",
) -> str:
    """Resolve the ARM base URL for a transport.

    Resolution order:

    1. If ``explicit`` is non-empty it wins (back-compat for callers
       pinning a custom or staging endpoint).
    2. Otherwise the ``cloud`` is looked up in :data:`ARM_ENDPOINTS`.
    3. Unknown cloud names raise :class:`ValueError` — production
       blockers should not silently fall back.

    Parameters
    ----------
    cloud:
        One of ``commercial`` / ``gcc-high`` / ``dod``.
    explicit:
        If set, used verbatim and the cloud lookup is skipped.
    adapter_name:
        Included in the ValueError message to help operators identify
        the misconfigured transport when several Azure clients are
        wired in parallel.
    """
    if explicit:
        return str(explicit)
    if cloud not in ARM_ENDPOINTS:
        raise ValueError(
            f"{adapter_name}: unknown cloud {cloud!r}. "
            f"Supported clouds: {sorted(ARM_ENDPOINTS)}. "
            "Set the cloud parameter or pass an explicit ARM endpoint."
        )
    return ARM_ENDPOINTS[cloud]
