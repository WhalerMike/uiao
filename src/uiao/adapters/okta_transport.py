"""Concrete Okta transport — the write seam for the ``okta`` binding profile.

The Okta binding profile (ADR-098 / UIAO_193) stores OrgPath facets as
Universal Directory custom profile attributes. :class:`OktaTransport` is the
callable that applies a planned :class:`FacetOperation` set against a live
Okta org by issuing Users API profile updates.

Like :class:`uiao.adapters.graph_transport.GraphTransport`, it is callable
``(method, path, body) -> dict`` so it drops into any caller, and it imports
``httpx`` lazily so importing this module never hard-requires the ``[api]``
extra. The org base URL is resolved from operator configuration (never a
hardcoded host); only commercial Okta endpoints are in scope per ADR-098's
Moderate/Commercial boundary.

Applying facet writes is a convenience built on the callable: each
``write`` operation becomes a ``POST /api/v1/users/{id}`` with the facet's
profile attribute set to the value. ``uncaptured`` operations (overflow
casualties from the planner) are never sent — they exist only to surface as
drift.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from uiao.modernization.orgtree.types import FacetOperation

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


class OktaTransport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + an Okta API token."""

    def __init__(self, org_url: str, api_token: str, *, timeout: float = 30.0) -> None:
        if not org_url:
            raise ValueError("OktaTransport requires an org_url (resolved from operator config, never hardcoded)")
        self._base = org_url.rstrip("/")
        self._token = api_token
        self._timeout = timeout

    @classmethod
    def from_environment(cls, *, org_url: str, api_token: str, timeout: float = 30.0) -> OktaTransport:
        """Construct from explicit operator-supplied config (commercial endpoints only)."""
        return cls(org_url=org_url, api_token=api_token, timeout=timeout)

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._base}{path}"

    def __call__(self, method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        import httpx

        headers = {
            "Authorization": f"SSWS {self._token}",
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
        """Apply ``write`` operations as Okta profile updates. Returns the count applied."""
        applied = 0
        for op in operations:
            if op.op != "write":
                continue
            self("POST", f"/api/v1/users/{op.target}", {"profile": {op.attribute: op.value}})
            applied += 1
        return applied
