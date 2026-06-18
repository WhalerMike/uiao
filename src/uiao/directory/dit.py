"""Directory Information Tree for the Active Governance Directory.

The AGD does not store its own identities — it *projects* the governance
substrate over the LDAP wire format. The Directory Information Tree (DIT)
is therefore a read-only view computed from two governed inputs:

* the **OrgPath Codebook** (UIAO_151) — the facet semantics; and
* a **principal snapshot** (the same shape the OrgPath governance runtime
  consumes: ``{principal_id, principal_type, attributes}`` where
  ``attributes`` maps ``extensionAttribute1..15`` slots to values).

Each governed facet slot is surfaced under its canonical LDAP attribute
name from the **``ldap`` binding profile** (UIAO_193 / ADR-098) — the
``uiaoOrgPath<Facet>`` auxiliary objectClass. This keeps the wire schema
traceable to canon rather than inventing attribute names here.

Because the DIT is a projection, the directory is read-only by
construction (ADR-100 §L1): there are no add/modify/delete entries, only
``search``. Writes flow through the existing OrgPath modernization
adapters into the provider of record, never into this in-path view.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from uiao.directory.ad_schema import ad_object_classes
from uiao.directory.ad_schema import synthesize as synthesize_ad
from uiao.directory.protocol import Entry, Filter, Scope
from uiao.modernization.orgtree.binding_profiles import BindingProfile, load_binding_profile
from uiao.modernization.orgtree.codebook import Codebook, default_codebook

_IDENTITY_PLANE = "identity"


def _normalize_dn(dn: str) -> str:
    """Case- and whitespace-fold a DN for comparison (caseIgnore RDNs)."""
    return ",".join(part.strip().lower() for part in dn.split(","))


def _parent_dn(dn: str) -> str:
    head, _, tail = dn.partition(",")
    return tail.strip()


@dataclass(frozen=True)
class Directory:
    """An ordered, read-only set of projected LDAP entries."""

    base_dn: str
    entries: tuple[Entry, ...] = field(default_factory=tuple)

    def _by_dn(self) -> dict[str, Entry]:
        return {_normalize_dn(e.dn): e for e in self.entries}

    def contains(self, dn: str) -> bool:
        """True when an entry with this DN exists in the tree.

        An empty DN denotes the configured suffix (treated as present).
        Used to distinguish ``noSuchObject`` — the base object does not
        exist (RFC 4511 §4.5.3) — from a base that exists but matches no
        entries (``success`` / 0 results).
        """
        target = _normalize_dn(dn) if dn else _normalize_dn(self.base_dn)
        return any(_normalize_dn(e.dn) == target for e in self.entries)

    def search(self, base_object: str, scope: Scope, filt: Filter) -> list[Entry]:
        """Return entries in ``scope`` of ``base_object`` matching ``filt``."""
        norm_base = _normalize_dn(base_object) if base_object else _normalize_dn(self.base_dn)
        candidates: list[Entry] = []
        for entry in self.entries:
            ndn = _normalize_dn(entry.dn)
            if scope == Scope.BASE_OBJECT:
                in_scope = ndn == norm_base
            elif scope == Scope.SINGLE_LEVEL:
                in_scope = _normalize_dn(_parent_dn(entry.dn)) == norm_base
            else:  # WHOLE_SUBTREE
                in_scope = ndn == norm_base or ndn.endswith("," + norm_base)
            if in_scope and match(filt, entry):
                candidates.append(entry)
        return candidates


# ---------------------------------------------------------------------------
# Filter evaluation (RFC 4511 §4.5.1; caseIgnore semantics)
# ---------------------------------------------------------------------------
def _values_ci(entry: Entry, attribute: str) -> list[str] | None:
    """Case-insensitive attribute lookup; None when absent."""
    wanted = attribute.lower()
    for name, values in entry.attributes.items():
        if name.lower() == wanted:
            return values
    return None


def match(filt: Filter, entry: Entry) -> bool:
    """Evaluate a parsed :class:`Filter` against one entry."""
    if filt.kind == "and":
        return all(match(c, entry) for c in filt.children)
    if filt.kind == "or":
        return any(match(c, entry) for c in filt.children)
    if filt.kind == "not":
        return not match(filt.children[0], entry)
    if filt.kind == "present":
        # The RFC special-cases (objectClass=*) as "any entry"; every
        # projected entry carries an objectClass, so presence holds.
        return _values_ci(entry, filt.attribute) is not None
    if filt.kind == "equality":
        values = _values_ci(entry, filt.attribute)
        return values is not None and any(v.lower() == filt.value.lower() for v in values)
    if filt.kind == "substrings":
        values = _values_ci(entry, filt.attribute)
        return values is not None and any(_substring_match(filt, v) for v in values)
    return False


def _substring_match(filt: Filter, value: str) -> bool:
    text = value.lower()
    pos = 0
    if filt.initial is not None:
        if not text.startswith(filt.initial.lower()):
            return False
        pos = len(filt.initial)
    for chunk in filt.any:
        idx = text.find(chunk.lower(), pos)
        if idx < 0:
            return False
        pos = idx + len(chunk)
    if filt.final is not None:
        if not text.endswith(filt.final.lower()):
            return False
        if len(text) - len(filt.final) < pos:
            return False
    return True


# ---------------------------------------------------------------------------
# Projection: governance substrate -> DIT
# ---------------------------------------------------------------------------
_OBJECTCLASS_BY_TYPE = {
    "user": ["top", "person", "organizationalPerson", "inetOrgPerson", "uiaoOrgPath"],
    "device": ["top", "device", "uiaoOrgPath"],
    "servicePrincipal": ["top", "applicationProcess", "uiaoOrgPath"],
}

_CN_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _rdn_value(principal_id: str) -> str:
    """A DN-safe RDN value derived from the principal id."""
    return _CN_SAFE.sub("-", principal_id).strip("-") or "principal"


def _facet_locators(codebook: Codebook, profile: BindingProfile) -> dict[str, str]:
    """Map each ``extensionAttributeN`` slot to its ``uiaoOrgPath<Facet>`` name."""
    out: dict[str, str] = {}
    for name, facet in codebook.facets.items():
        locator = profile.locator_for(name, _IDENTITY_PLANE)
        if locator:
            out[facet.attribute] = locator
    return out


def build_directory(
    principals: list[dict],
    *,
    base_dn: str = "dc=agd,dc=uiao,dc=gov",
    codebook: Codebook | None = None,
    ad_veneer: bool = False,
) -> Directory:
    """Project a principal snapshot into a read-only :class:`Directory`.

    ``principals`` is a list of ``{principal_id, principal_type,
    attributes}`` dicts — the OrgPath governance-runtime snapshot shape.
    Empty-valued facet slots are dropped (an absent value is not a
    governed assertion).

    When ``ad_veneer`` is True, each person entry additionally carries the
    bounded, read-only AD-compatibility veneer (ADR-110): synthesized
    ``sAMAccountName`` / ``userPrincipalName`` / ``displayName`` / AD
    ``objectClass`` values / a non-authoritative synthetic ``objectSid``.
    Off by default; the veneer never adds a writable or governed attribute.
    """
    cb = codebook or default_codebook()
    profile = load_binding_profile("ldap")
    slot_to_locator = _facet_locators(cb, profile)

    people_dn = f"ou=people,{base_dn}"
    entries: list[Entry] = [
        Entry(dn=base_dn, attributes={"objectClass": ["top", "domain"], "dc": [base_dn.split(",")[0].split("=")[1]]}),
        Entry(dn=people_dn, attributes={"objectClass": ["top", "organizationalUnit"], "ou": ["people"]}),
    ]

    for p in principals:
        principal_id = str(p["principal_id"])
        ptype = str(p.get("principal_type", "user"))
        cn = _rdn_value(principal_id)
        attrs: dict[str, list[str]] = {
            "objectClass": list(_OBJECTCLASS_BY_TYPE.get(ptype, _OBJECTCLASS_BY_TYPE["user"])),
            "cn": [principal_id],
            "uiaoPrincipalType": [ptype],
        }
        for slot, value in (p.get("attributes") or {}).items():
            if not value:
                continue
            locator = slot_to_locator.get(slot)
            if locator:
                attrs[locator] = [str(value)]
        if ad_veneer:
            # Read-only AD-compatibility veneer (ADR-110): synthesized at build
            # time, never stored authoritatively. AD objectClass values merge
            # onto the existing ones; the rest are added as-is.
            veneer = synthesize_ad(principal_id, ptype)
            attrs["objectClass"] = attrs["objectClass"] + ad_object_classes(ptype)
            attrs.update(veneer)
        entries.append(Entry(dn=f"cn={cn},{people_dn}", attributes=attrs))

    return Directory(base_dn=base_dn, entries=tuple(entries))
