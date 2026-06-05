"""Concrete Azure Resource Manager (ARM) transport — the ARM-plane
counterpart to :class:`uiao.adapters.graph_transport.GraphTransport`.

The device-plane OrgPath writeback (ADR-038 / ADR-084 §C9) routes
``ARC-SERVER`` (and ``STAY-AD-DEPENDENCY`` /
``MANAGED-IDENTITY-CANDIDATE``) dispositions to ARM, where each device's
10 facet values land as tags on the Arc machine resource
(``Microsoft.HybridCompute/machines``). That plane needs a transport
that (a) resolves the cloud-correct ARM base
(``management.azure.com`` for commercial / GCC-Moderate,
``management.usgovcloudapi.net`` for Azure Government) and (b)
authenticates with an **ARM-audience** token — not a Graph one.

Re-using the Graph transport for ARM (``arm_transport = graph_transport``)
silently fails against a live tenant: the Graph-audience bearer token is
rejected by ARM with HTTP 401 (invalid audience). :class:`ArmTransport`
closes that gap.

It is callable, so it drops straight into the dual-transport adapter::

    arm = ArmTransport.from_environment(cloud="commercial")
    adapter = EntraDeviceOrgPathAdapter(planner, arm_transport=arm)
    adapter.apply(ops, dry_run=False)   # ARC-SERVER ops now reach ARM

httpx and msal are part of the ``[api]`` extra; this module imports httpx
lazily so importing it never hard-requires the extra.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from uiao.adapters._arm_clouds import resolve_arm_base

if TYPE_CHECKING:
    from uiao.api.auth.entra_token import EntraTokenProvider


class ArmTransport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + MSAL.

    ``path`` may be an ARM-relative resource path
    (``/subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.HybridCompute/machines/{name}?api-version=...``)
    — joined onto the resolved ARM base — or an absolute URL, which is
    used verbatim. Unlike Graph, the ARM base carries no API version
    segment; callers supply ``api-version`` as a query parameter on the
    path.
    """

    def __init__(
        self,
        token_provider: EntraTokenProvider,
        *,
        cloud: str = "commercial",
        arm_endpoint: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._tokens = token_provider
        self._base = resolve_arm_base(
            cloud=cloud,
            explicit=arm_endpoint,
            adapter_name="ArmTransport",
        )
        self._timeout = timeout

    @classmethod
    def from_environment(
        cls,
        *,
        cloud: str = "commercial",
        arm_endpoint: str | None = None,
    ) -> ArmTransport:
        """Build a transport from ``UIAO_ENTRA_*`` env vars (see EntraTokenProvider).

        The token is acquired with the cloud-correct **ARM** audience and
        login authority. The same app registration used for Graph writes
        works here provided it has been granted the relevant Azure RBAC
        role (e.g. *Tags Contributor* / *Contributor*) on the target Arc
        resources — ARM authorization is role-based, not Graph
        application-permission-based.
        """
        from uiao.adapters._arm_clouds import arm_token_scope
        from uiao.api.auth.entra_token import EntraTokenProvider

        return cls(
            EntraTokenProvider.from_environment(
                scopes=[arm_token_scope(cloud, adapter_name="ArmTransport")],
                cloud=cloud,
            ),
            cloud=cloud,
            arm_endpoint=arm_endpoint,
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
