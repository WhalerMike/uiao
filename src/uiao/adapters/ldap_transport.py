"""Concrete LDAP transport — the write seam for the ``ldap`` binding profile.

The LDAP binding profile (ADR-098 / UIAO_193) stores OrgPath facets as
directory attributes — by default a governed auxiliary objectClass
(``uiaoOrgPath<Facet>``), or, where schema extension is forbidden, a
tenant-supplied reserved-attribute locator table. :class:`LdapTransport`
applies a planned :class:`FacetOperation` set against a live directory by
issuing ``modify`` operations on each principal's DN.

It imports ``ldap3`` lazily so importing this module never hard-requires
the dependency, mirroring the lazy-import discipline of the Graph/ARM
transports. The directory host/port and bind credentials come from
operator configuration; only commercial / on-prem directories are in
scope per ADR-098's Moderate/Commercial boundary.

Unlike the Graph and Okta transports there is no HTTP ``(method, path,
body)`` surface — LDAP is not HTTP — so the public seam is
:meth:`modify` (set one attribute on one DN) plus the :meth:`apply`
convenience over a planned operation set. ``uncaptured`` operations are
never written; they exist only to surface as drift.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from uiao.modernization.orgtree.types import FacetOperation

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ldap3 import Connection


class LdapTransport:
    """Applies OrgPath facet writes to a directory via ldap3 ``modify``."""

    def __init__(self, connection: Connection) -> None:
        self._conn = connection

    @classmethod
    def from_environment(
        cls,
        *,
        host: str,
        bind_dn: str,
        password: str,
        use_ssl: bool = True,
        port: int | None = None,
    ) -> LdapTransport:
        """Open an ldap3 connection from operator-supplied config (commercial/on-prem only)."""
        if not host:
            raise ValueError("LdapTransport requires a host (resolved from operator config, never hardcoded)")
        from ldap3 import ALL, Connection, Server

        server = Server(host, port=port, use_ssl=use_ssl, get_info=ALL)
        connection = Connection(server, user=bind_dn, password=password, auto_bind=True)
        return cls(connection)

    def modify(self, dn: str, attribute: str, value: str) -> dict[str, Any]:
        """Replace one attribute on one DN. Returns the ldap3 result dict."""
        from ldap3 import MODIFY_REPLACE

        self._conn.modify(dn, {attribute: [(MODIFY_REPLACE, [value])]})
        return dict(self._conn.result)

    def apply(self, operations: Iterable[FacetOperation]) -> int:
        """Apply ``write`` operations as directory modifications. Returns the count applied."""
        applied = 0
        for op in operations:
            if op.op != "write":
                continue
            self.modify(op.target, op.attribute, op.value or "")
            applied += 1
        return applied
