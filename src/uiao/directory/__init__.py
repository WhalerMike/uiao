"""Active Governance Directory (AGD) — the in-path LDAP projection plane.

The AGD is UIAO's *protocol layer*: it exposes the governance substrate
over the LDAPv3 wire protocol so directory-bound tooling can query the
Active Governance Directory in the terms it already speaks. Per ADR-100
it is a sanctioned, read-only data-plane exception to the ADR-092 §1
control-plane boundary — it sits in the LDAP request path but holds no
write op, so it cannot mutate canon or the provider of record.

Public surface:

* :mod:`uiao.directory.ber` — minimal BER/ASN.1 codec for the LDAP subset.
* :mod:`uiao.directory.protocol` — LDAPv3 message parse/serialize + filter model.
* :mod:`uiao.directory.dit` — projection of the Codebook + principal snapshot
  into a read-only Directory Information Tree.
* :mod:`uiao.directory.policy` — per-bind read scoping (ADR-100 §5): sensitive
  facets require an authenticated bind.
* :mod:`uiao.directory.server` — the asyncio LDAP server (LDAPS-capable).
"""

from __future__ import annotations

from uiao.directory.dit import Directory, build_directory
from uiao.directory.policy import ReadPolicy, default_read_policy
from uiao.directory.server import LdapServer, build_server_tls_context

__all__ = [
    "Directory",
    "LdapServer",
    "ReadPolicy",
    "build_directory",
    "build_server_tls_context",
    "default_read_policy",
]
