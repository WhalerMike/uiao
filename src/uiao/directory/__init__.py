"""Active Governance Directory (AGD) — the in-path LDAP projection plane.

The AGD is UIAO's *protocol layer*: it exposes the governance substrate
over the LDAPv3 wire protocol so directory-bound tooling can query the
Active Governance Directory in the terms it already speaks. Per ADR-100
it is a sanctioned, read-only data-plane exception to the ADR-092 §1
control-plane boundary — it holds **no writable store** (ADR-109): it can
accept writes, but only as governed intent routed to the provider of
record, never by mutating its own projection.

Public surface:

* :mod:`uiao.directory.ber` — minimal BER/ASN.1 codec for the LDAP subset.
* :mod:`uiao.directory.protocol` — LDAPv3 message parse/serialize + filter model.
* :mod:`uiao.directory.dit` — projection of the Codebook + principal snapshot
  into a read-only Directory Information Tree.
* :mod:`uiao.directory.policy` — per-bind read scoping (ADR-100 §5): sensitive
  facets require an authenticated bind.
* :mod:`uiao.directory.sasl` — SASL mechanisms (ADR-101): GSSAPI/Kerberos
  gate-only ticket validation, behind the ``[kerberos]`` extra.
* :mod:`uiao.directory.writes` — write-as-governed-intent (ADR-109): translate a
  modify into FacetOperations and route them dry-run-by-default.
* :mod:`uiao.directory.ad_schema` — read-only AD-compatibility veneer (ADR-110):
  synthesized, non-authoritative sAMAccountName / objectSid / objectClass.
* :mod:`uiao.directory.server` — the asyncio LDAP server (LDAPS + StartTLS + SASL).
"""

from __future__ import annotations

from uiao.directory.ad_schema import synthesize as synthesize_ad_veneer
from uiao.directory.dit import Directory, build_directory
from uiao.directory.policy import ReadPolicy, default_read_policy
from uiao.directory.sasl import SaslMechanism, SaslResult
from uiao.directory.server import LdapServer, build_server_tls_context
from uiao.directory.writes import WritePlan, WriteRouter, translate_modify

__all__ = [
    "Directory",
    "LdapServer",
    "ReadPolicy",
    "SaslMechanism",
    "SaslResult",
    "WritePlan",
    "WriteRouter",
    "build_directory",
    "build_server_tls_context",
    "default_read_policy",
    "synthesize_ad_veneer",
    "translate_modify",
]
