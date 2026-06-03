"""AD directory readers — feed AD object records to the OrgPath assigner.

Two readers, one record shape (a flat dict of AD attributes):

* :func:`read_records_from_export` — load records from a JSON export. Pure and
  offline-testable; the repeatable input for ``uiao orgtree assess``.
* :class:`LdapDirectoryReader` — a thin live ldap3 read (this is the "engine
  does live LDAP" path). It issues one focused ``$select``-style query for just
  the attributes the mapping needs, rather than duplicating the full forest
  survey in ``survey.py``. ldap3 is imported lazily so the offline path never
  needs it.

The ldap3-entry → record conversion and the attribute-list derivation are pure
functions (:func:`attributes_for_mapping`, :func:`entry_to_record`) so they can
be tested without a live directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from uiao.modernization.orgtree.ad_mapping import OrgPathMapping, default_mapping

# Attributes the assigner always needs regardless of the mapping: identity,
# group membership + SPNs (account_type derivation), object class.
_ALWAYS = (
    "distinguishedName",
    "sAMAccountName",
    "objectGUID",
    "objectClass",
    "memberOf",
    "servicePrincipalNames",
)
# Attributes that are naturally multi-valued and should stay lists.
_MULTIVALUED = frozenset({"objectClass", "memberOf", "servicePrincipalNames", "servicePrincipalName"})


def attributes_for_mapping(mapping: OrgPathMapping | None = None) -> list[str]:
    """The AD attribute set to request: every rule source + the always-needed keys."""
    mapping = mapping or default_mapping()
    attrs: list[str] = list(_ALWAYS)
    for rule in mapping.rules:
        if rule.source and rule.source not in attrs:
            attrs.append(rule.source)
    return attrs


def entry_to_record(attrs_dict: Mapping[str, Any], wanted: Iterable[str]) -> dict[str, Any]:
    """Flatten an ldap3 ``entry_attributes_as_dict`` mapping into a record.

    Single-valued attributes collapse to their first value; known multi-valued
    attributes (objectClass, memberOf, SPNs) stay as lists.
    """
    record: dict[str, Any] = {}
    for key in wanted:
        if key not in attrs_dict:
            continue
        value = attrs_dict[key]
        if isinstance(value, (list, tuple)):
            if key in _MULTIVALUED:
                record[key] = [str(v) for v in value]
            elif value:
                record[key] = value[0]
        else:
            record[key] = value
    return record


def read_records_from_export(path: Path | str) -> list[dict[str, Any]]:
    """Load AD object records from a JSON export.

    Accepts a top-level list, or a dict containing a ``records`` / ``users`` /
    ``computers`` / ``objects`` list.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(r) for r in payload]
    if isinstance(payload, Mapping):
        for key in ("records", "users", "computers", "objects"):
            seq = payload.get(key)
            if isinstance(seq, list):
                return [dict(r) for r in seq]
    raise ValueError("export must be a JSON list, or a dict with a 'records'/'users'/'computers'/'objects' list")


class LdapDirectoryReader:
    """A thin live ldap3 reader for OrgPath assessment.

    Issues one focused query for just the attributes the mapping needs. Empty
    ``username`` uses Kerberos/GSSAPI (domain-joined host), mirroring
    ``survey.py``'s convention.
    """

    # Default LDAP filters for the two object planes OrgPath cares about.
    USER_FILTER = "(&(objectClass=user)(objectCategory=person))"
    COMPUTER_FILTER = "(objectClass=computer)"

    def __init__(self, server: str, base_dn: str, username: str = "", password: str = "") -> None:
        self.server = server
        self.base_dn = base_dn
        self.username = username
        self.password = password

    def _connect(self):  # type: ignore[no-untyped-def]
        # Lazy import so the offline export path never requires ldap3.
        from ldap3 import ALL, Connection, Server  # type: ignore

        srv = Server(self.server, get_info=ALL)
        if self.username:
            return Connection(srv, user=self.username, password=self.password, auto_bind=True)
        from ldap3 import GSSAPI, SASL  # type: ignore

        return Connection(srv, authentication=SASL, sasl_mechanism=GSSAPI, auto_bind=True)

    def read(self, ldap_filter: str, attributes: list[str]) -> list[dict[str, Any]]:
        """Run one paged search and return flattened records."""
        conn = self._connect()
        records: list[dict[str, Any]] = []
        try:
            conn.search(self.base_dn, ldap_filter, attributes=attributes, paged_size=500)
            for entry in conn.entries:
                records.append(entry_to_record(entry.entry_attributes_as_dict, attributes))
        finally:
            conn.unbind()
        return records

    def read_users(self, mapping: OrgPathMapping | None = None) -> list[dict[str, Any]]:
        return self.read(self.USER_FILTER, attributes_for_mapping(mapping))

    def read_computers(self, mapping: OrgPathMapping | None = None) -> list[dict[str, Any]]:
        return self.read(self.COMPUTER_FILTER, attributes_for_mapping(mapping))
