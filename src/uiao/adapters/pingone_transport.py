"""Concrete PingOne transport — the write seam for the ``pingone`` binding profile.

The PingOne binding profile (ADR-099 / UIAO_193) stores OrgPath facets as
PingOne directory custom user attributes — arbitrary keys, the enterprise
counterpart to the Okta Universal Directory profile. :class:`PingOneTransport`
applies a planned :class:`FacetOperation` set against a live environment by
issuing PingOne platform API user updates.

Like :class:`uiao.adapters.okta_transport.OktaTransport`, it is callable
``(method, path, body) -> dict`` so it drops into any caller, and it imports
``httpx`` lazily so importing this module never hard-requires the ``[api]``
extra. The region API base URL and environment id come from operator
configuration (never a hardcoded host); only commercial PingOne endpoints are
in scope per ADR-098's Moderate/Commercial boundary.

Applying facet writes is a convenience built on the callable: each ``write``
operation becomes a ``PATCH /v1/environments/{env}/users/{id}`` carrying the
facet's attribute set to the value. ``uncaptured`` operations (overflow
casualties from the planner) are never sent — they exist only to surface as
drift.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from uiao.modernization.orgtree.types import FacetOperation


class PingOneTransport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + a PingOne access token."""

    def __init__(self, api_url: str, environment_id: str, access_token: str, *, timeout: float = 30.0) -> None:
        if not api_url:
            raise ValueError("PingOneTransport requires an api_url (resolved from operator config, never hardcoded)")
        if not environment_id:
            raise ValueError("PingOneTransport requires an environment_id")
        self._base = api_url.rstrip("/")
        self._env_id = environment_id
        self._token = access_token
        self._timeout = timeout

    @classmethod
    def from_environment(
        cls, *, api_url: str, environment_id: str, access_token: str, timeout: float = 30.0
    ) -> PingOneTransport:
        """Construct from explicit operator-supplied config (commercial endpoints only)."""
        return cls(api_url=api_url, environment_id=environment_id, access_token=access_token, timeout=timeout)

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
        """Apply ``write`` operations as PingOne custom-attribute updates. Returns the count applied."""
        applied = 0
        for op in operations:
            if op.op != "write":
                continue
            self("PATCH", f"/v1/environments/{self._env_id}/users/{op.target}", {op.attribute: op.value})
            applied += 1
        return applied
