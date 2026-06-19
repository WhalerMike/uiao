"""Concrete Keycloak transport — the write seam for the ``keycloak`` binding profile.

The Keycloak binding profile (ADR-099 / UIAO_193) stores OrgPath facets as
Keycloak user attributes — arbitrary key/value pairs on the user
representation, the open-source counterpart to the Okta Universal Directory
profile. :class:`KeycloakTransport` applies a planned :class:`FacetOperation`
set against a live realm by issuing Admin REST user updates.

Like :class:`uiao.adapters.okta_transport.OktaTransport`, it is callable
``(method, path, body) -> dict`` so it drops into any caller, and it imports
``httpx`` lazily so importing this module never hard-requires the ``[api]``
extra. The realm admin base URL and realm name come from operator
configuration (never a hardcoded host); only commercial / on-prem Keycloak
endpoints are in scope per ADR-098's Moderate/Commercial boundary.

Applying facet writes is a convenience built on the callable: each ``write``
operation becomes a ``PUT /admin/realms/{realm}/users/{id}`` whose
``attributes`` map carries the facet's attribute set to a single-element list
(Keycloak attribute values are multi-valued). ``uncaptured`` operations
(overflow casualties from the planner) are never sent — they exist only to
surface as drift.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from uiao.modernization.orgtree.types import FacetOperation


class KeycloakTransport:
    """A callable ``(method, path, body) -> dict`` backed by httpx + a Keycloak admin token."""

    def __init__(self, server_url: str, realm: str, access_token: str, *, timeout: float = 30.0) -> None:
        if not server_url:
            raise ValueError("KeycloakTransport requires a server_url (resolved from operator config, never hardcoded)")
        if not realm:
            raise ValueError("KeycloakTransport requires a realm")
        self._base = server_url.rstrip("/")
        self._realm = realm
        self._token = access_token
        self._timeout = timeout

    @classmethod
    def from_environment(
        cls, *, server_url: str, realm: str, access_token: str, timeout: float = 30.0
    ) -> KeycloakTransport:
        """Construct from explicit operator-supplied config (commercial / on-prem endpoints only)."""
        return cls(server_url=server_url, realm=realm, access_token=access_token, timeout=timeout)

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
        """Apply ``write`` operations as Keycloak user-attribute updates. Returns the count applied."""
        applied = 0
        for op in operations:
            if op.op != "write":
                continue
            self(
                "PUT",
                f"/admin/realms/{self._realm}/users/{op.target}",
                {"attributes": {op.attribute: [op.value]}},
            )
            applied += 1
        return applied
