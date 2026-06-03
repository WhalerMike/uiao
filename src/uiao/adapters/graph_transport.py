"""Concrete Microsoft Graph transport — the first real implementation of the
``Transport = Callable[[str, str, dict | None], dict]`` seam the Entra adapters
expect.

Until now every adapter took an *injected* transport and tests passed a
recorder; there was no production transport. :class:`GraphTransport` provides
one: it resolves the cloud-correct Graph base via
:func:`uiao.adapters._graph_clouds.resolve_graph_base`, authenticates with the
existing :class:`uiao.api.auth.entra_token.EntraTokenProvider` (MSAL
client-credentials), and dispatches HTTP via httpx.

It is callable, so it drops straight into any adapter::

    transport = GraphTransport.from_environment(cloud="gcc-high")
    adapter = EntraDeviceOrgPathAdapter(planner, graph_transport=transport)
    adapter.apply(ops, dry_run=False)   # now writes to a live tenant

httpx and msal are part of the ``[api]`` extra; this module imports httpx
lazily so importing it never hard-requires the extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uiao.adapters._graph_clouds import resolve_graph_base

if TYPE_CHECKING:
    from uiao.api.auth.entra_token import EntraTokenProvider


class GraphTransport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + MSAL.

    ``path`` may be a Graph-relative path (``/devices/{id}``) — joined onto the
    resolved base — or an absolute URL (e.g. an ``@odata.nextLink``), which is
    used verbatim.
    """

    def __init__(
        self,
        token_provider: EntraTokenProvider,
        *,
        cloud: str = "commercial",
        graph_api_version: str = "v1.0",
        graph_endpoint: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._tokens = token_provider
        self._base = resolve_graph_base(
            cloud=cloud,
            graph_api_version=graph_api_version,
            explicit=graph_endpoint,
            adapter_name="GraphTransport",
        )
        self._timeout = timeout

    @classmethod
    def from_environment(
        cls,
        *,
        cloud: str = "commercial",
        graph_api_version: str = "v1.0",
        graph_endpoint: str | None = None,
    ) -> GraphTransport:
        """Build a transport from ``UIAO_ENTRA_*`` env vars (see EntraTokenProvider)."""
        from uiao.api.auth.entra_token import EntraTokenProvider

        return cls(
            EntraTokenProvider.from_environment(),
            cloud=cloud,
            graph_api_version=graph_api_version,
            graph_endpoint=graph_endpoint,
        )

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base}{path}"

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        import httpx

        headers = self._tokens.get_auth_headers()
        headers["Content-Type"] = "application/json"
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.request(method.upper(), self._url(path), json=body, headers=headers)
            resp.raise_for_status()
            if resp.status_code == 204 or not resp.content:
                return {}
            return dict(resp.json())
