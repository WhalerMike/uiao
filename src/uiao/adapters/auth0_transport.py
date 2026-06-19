"""Concrete Auth0 transport — the write seam for the ``auth0`` binding profile.

The Auth0 binding profile (ADR-099 / UIAO_193) stores OrgPath facets in the
user profile's ``app_metadata`` namespace — administrator-controlled (not
user-editable), the CIAM counterpart to the Okta Universal Directory profile.
:class:`Auth0Transport` applies a planned :class:`FacetOperation` set against a
live tenant by issuing Management API user updates.

Like :class:`uiao.adapters.okta_transport.OktaTransport`, it is callable
``(method, path, body) -> dict`` so it drops into any caller, and it imports
``httpx`` lazily so importing this module never hard-requires the ``[api]``
extra. The tenant Management API base URL comes from operator configuration
(never a hardcoded host); only commercial Auth0 endpoints are in scope per
ADR-098's Moderate/Commercial boundary.

Applying facet writes is a convenience built on the callable: each ``write``
operation becomes a ``PATCH /api/v2/users/{id}`` whose ``app_metadata`` map
carries the facet's attribute set to the value. ``uncaptured`` operations
(overflow casualties from the planner) are never sent — they exist only to
surface as drift.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from uiao.modernization.orgtree.types import FacetOperation


class Auth0Transport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + an Auth0 Management API token."""

    def __init__(self, tenant_url: str, access_token: str, *, timeout: float = 30.0) -> None:
        if not tenant_url:
            raise ValueError("Auth0Transport requires a tenant_url (resolved from operator config, never hardcoded)")
        self._base = tenant_url.rstrip("/")
        self._token = access_token
        self._timeout = timeout

    @classmethod
    def from_environment(cls, *, tenant_url: str, access_token: str, timeout: float = 30.0) -> Auth0Transport:
        """Construct from explicit operator-supplied config (commercial endpoints only)."""
        return cls(tenant_url=tenant_url, access_token=access_token, timeout=timeout)

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base}{path}"

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.request(method, self._url(path), json=body, headers=headers)
            resp.raise_for_status()
            if not resp.content:
                return {}
            return dict(resp.json())

    def apply(self, operations: Iterable[FacetOperation]) -> int:
        """Apply ``write`` operations as Auth0 ``app_metadata`` updates. Returns the count applied."""
        applied = 0
        for op in operations:
            if op.op != "write":
                continue
            self("PATCH", f"/api/v2/users/{op.target}", {"app_metadata": {op.attribute: op.value}})
            applied += 1
        return applied
